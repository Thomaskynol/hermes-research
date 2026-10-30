#!/usr/bin/env python3
"""Calibração do validador de suporte contra fontes reais (sem modelo).

Para cada caso de ``tools/calibration_sample.json`` (fato lido DIRETAMENTE
da fonte, independente da saída do assessor) executa o pipeline REAL:
- excerpt via ``adaptive_coordinator._relevant_excerpt`` (1200 chars, mesmos
  termos do assessor: critérios/entidades + ponte EN + âncoras + op targets)
  e os mesmos grupos de excerpt;
- veredito do modelo = evaluation registrada no state para
  (criterion_id, entity_id), se existir (dado congelado, sem nova chamada);
- checagem via ``verification_report.check_support`` por claim isolada
  (claim + ``[1]`` contra o texto COMPLETO do doc citado).

Atribuição da fonte de erro (precedência documentada: o validador roda no
doc completo, sem desculpa de excerpt):
1. check diverge do expected ................. ``validacao``
2. expected supported + fato fora do excerpt . ``contexto``
3. expected supported + fato no excerpt
   + recorded insufficient .................. ``julgamento_modelo``
4. expected unsupported/absent + check nega
   + recorded covered ........................ ``julgamento_modelo``
   (modelo sustentou o que o validador nega)
5. senão ..................................... ``ok``

Saída: tabela por caso + agregados por tipo × fonte-de-erro, lado a lado
com o ``BEFORE`` (mesmos casos rodados no HEAD antes das correções,
``before_head`` abaixo). Uso::

    python3 tools/run_calibration.py /path/to/adaptive_state [--json out]

Exit 0 quando o state pode ser lido; exit 2 em erro de uso/IO.
"""

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adaptive_coordinator import (  # noqa: E402
    _ANCHOR_FACT_TERMS,
    _criterion_groups,
    _expand_terms_en,
    _op_target_terms,
    _relevant_excerpt,
)
from verification_report import check_support  # noqa: E402

STATE_DEFAULT = ("/tmp/hermes-real-run/accept15/adaptive_accept15/"
                 "state.json")
EXCERPT_CHARS = 1200

#: HEAD em que o BEFORE foi medido (antes das correções do validador).
BEFORE_HEAD = "34c760c"
#: Resultado do check (supported? 1/0) por caso no BEFORE_HEAD.
BEFORE_CHECK = {
    "a1": 0, "a2": 0, "a3": 0, "a4": 1, "a5": 0,
    "b1": 0, "b2": 1, "b3": 0, "b4": 0,
    "c1": 1, "c2": 1, "c3": 1, "c4": 1,
    "d1": 1, "d2": 0, "d3": 1, "d4": 1,
    "e1": 0, "e2": 0, "e3": 0, "e4": 0,
    "f1": 1, "f2": 1, "f3": 1, "f4": 1,
}

SOURCES = ("ok", "contexto", "julgamento_modelo", "validacao")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def assessor_terms(state: dict) -> tuple[list[str], dict]:
    """Termos e grupos idênticos aos do assessor (sem modelo)."""
    plan = state.get("plan") or {}
    terms: list[str] = []
    for crit in plan.get("criteria", []) or []:
        for key in ("label", "id"):
            if crit.get(key):
                terms.extend(str(crit[key]).split())
    terms.extend(_expand_terms_en(terms))
    for ent in plan.get("entities", []) or []:
        for key in ("label", "id"):
            if ent.get(key):
                terms.extend(str(ent[key]).split())
    terms.extend(_expand_terms_en(terms))
    terms.extend(list(_ANCHOR_FACT_TERMS))
    terms.extend(_op_target_terms(state))
    return terms, _criterion_groups(plan)


def latest_eval(state: dict, cid, eid):
    found = None
    for ev in state.get("evaluations") or []:
        if ev.get("criterion_id") != cid:
            continue
        if eid is None and ev.get("entity_id") is None:
            found = ev
        elif eid is not None and ev.get("entity_id") == eid:
            found = ev
    return found or {}


def truth_of(expected: str) -> bool:
    return expected == "supported"


def attribute(case: dict, check_supported: bool, excerpt_has: bool,
              recorded: str) -> str:
    """Fonte de erro (precedência: validacao > contexto > julgamento)."""
    if check_supported != truth_of(case["expected"]):
        return "validacao"
    if case["expected"] == "supported":
        if not excerpt_has:
            return "contexto"
        if recorded == "insufficient":
            return "julgamento_modelo"
        return "ok"
    if recorded == "covered":
        return "julgamento_modelo"
    return "ok"


def run_case(case: dict, state: dict, evidence: dict, terms: list[str],
             groups: dict, check_sup: bool | None = None) -> dict:
    url = case["url"]
    full = evidence.get(url, "")
    excerpt, _stripped, _windows = _relevant_excerpt(
        full, EXCERPT_CHARS, list(terms), groups=groups)
    low_full, low_ex = norm(full), norm(excerpt)
    markers = [str(m) for m in case.get("fact_markers", [])]
    in_full = all(norm(m) in low_full for m in markers)
    excerpt_has = all(norm(m) in low_ex for m in markers)
    if check_sup is None:
        eid = case.get("entity_id")
        label = case.get("entity_label")
        plan = {"entities": ([{"id": eid, "label": label}]
                             if eid else []),
                "criteria": []}
        res = check_support(case["claim_pt"] + " [1]", {1: url},
                            {url: full}, plan)
        check_sup = bool(res["supported"])
    ev = latest_eval(state, case.get("criterion_id"),
                     case.get("entity_id"))
    recorded = ev.get("state", "?")
    source = attribute(case, check_sup, excerpt_has, recorded)
    return {
        "id": case["id"], "type": case["type"],
        "expected": case["expected"],
        "check_supported": check_sup,
        "fact_in_full": in_full,
        "in_current_excerpt": excerpt_has,
        "sample_says_excerpt": bool(case.get("in_current_excerpt")),
        "recorded": recorded,
        "source": source,
        "known_limitation": case.get("known_limitation"),
    }


def aggregate(rows: list[dict]) -> dict:
    by_type: dict[str, dict[str, int]] = {}
    for row in rows:
        cell = by_type.setdefault(row["type"], {})
        cell[row["source"]] = cell.get(row["source"], 0) + 1
    total = dict(Counter(r["source"] for r in rows))
    return {"by_type": by_type, "total": total}


def main(argv: list[str]) -> int:
    state_path = Path(argv[1]) if len(argv) > 1 else Path(STATE_DEFAULT)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"erro: não foi possível ler o state em {state_path}: {exc}",
              file=sys.stderr)
        return 2
    sample_path = ROOT / "tools" / "calibration_sample.json"
    try:
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"erro: amostra ilegível em {sample_path}: {exc}",
              file=sys.stderr)
        return 2
    evidence = state.get("evidence") or {}
    terms, groups = assessor_terms(state)
    rows, warnings = [], []
    for case in sample.get("cases", []):
        row = run_case(case, state, evidence, terms, groups)
        rows.append(row)
        if row["in_current_excerpt"] != row["sample_says_excerpt"]:
            warnings.append(
                f"{row['id']}: amostra diz excerpt="
                f"{row['sample_says_excerpt']}, pipeline diz "
                f"{row['in_current_excerpt']}")
        if row["expected"] in ("supported", "unsupported") \
                and not row["fact_in_full"]:
            warnings.append(f"{row['id']}: marcadores ausentes no doc "
                            "completo (amostra inconsistente)")
    after = aggregate(rows)
    before_rows = []
    for row in rows:
        case = next(c for c in sample["cases"] if c["id"] == row["id"])
        check_sup = bool(BEFORE_CHECK.get(row["id"], row["check_supported"]))
        before_rows.append({**row, "check_supported": check_sup,
                            "source": attribute(case, check_sup,
                                                row["in_current_excerpt"],
                                                row["recorded"])})
    before = aggregate(before_rows)
    print(f"{'id':>4} {'tipo':>4} {'esperado':>10} "
          f"{'check':>11} {'excerpt?':>8} {'recorded':>12} "
          f"{'fonte(antes->depois)':>20}")
    for row, brow in zip(rows, before_rows):
        mark = "" if row["source"] == brow["source"] \
            else f"  << {brow['source']}->{row['source']}"
        known = "  [limitação conhecida]" if row["known_limitation"] else ""
        print(f"{row['id']:>4} {row['type']:>4} {row['expected']:>10} "
              f"{int(brow['check_supported'])}->{int(row['check_supported']):<9} "
              f"{str(row['in_current_excerpt']):>8} "
              f"{row['recorded']:>12} "
              f"{brow['source']:>12}->{row['source']:<12}"
              f"{mark}{known}")
    print()
    print("agregado tipo × fonte (antes -> depois):")
    for tipo in sorted(set(after['by_type']) | set(before['by_type'])):
        print(f"  tipo {tipo}: {before['by_type'].get(tipo, {})} "
              f"-> {after['by_type'].get(tipo, {})}")
    print(f"  total: {before['total']} -> {after['total']}")
    for known in [r for r in rows if r["known_limitation"]]:
        print(f"  limitação {known['id']}: {known['known_limitation']}")
    for warning in warnings:
        print(f"  AVISO: {warning}")
    if len(argv) > 3 and argv[2] == "--json":
        payload = {"before_head": BEFORE_HEAD, "before": before,
                   "before_rows": [{k: r[k] for k in (
                       "id", "type", "expected", "check_supported",
                       "recorded", "source")} for r in before_rows],
                   "after": after, "rows": rows, "warnings": warnings}
        Path(argv[3]).write_text(json.dumps(payload, ensure_ascii=False,
                                            indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
