#!/usr/bin/env python3
"""Diagnose a finished adaptive run: why each required cell is not covered.

Usage: python3 tools/diagnose_run.py /path/to/adaptive_<run_id> [--json out.json]

Prints JSON with ``cells`` (buckets + one row per required cell) and
``synthesis`` (supported/unsupported/uncited counts and the unsupported
sentences), followed by a readable summary. Exit 0 whenever the state can be
read; exit 2 with a clear message when the directory/state does not exist.

Buckets (per required cell):
- ok                       covered with a referenced supporting document
- synthesis_unsupported    covered without any referenced supporting document
- missing_entity_evidence  no corpus document mentions the entity at all
- missing_dimension_evidence  entity documented, nothing about this dimension
- selection_context        a supporting document exists but no evaluation cites it
- assessor_error           evaluation cites a supporting document yet says insufficient
- partial_legit            evaluation cites a supporting document and says partial

Synthesis audit: the final rendered markdown is split into claim lines;
citations [n] are mapped to corpus documents by the renderer's numbering. A
claim is supported when the cited document shares >=35% of its content words
or >=2 rare words (len>=6); when the claim names a plan entity, a cited
document must also contain a token of that entity label. Claims without any
citation are counted as ``uncited``.
Generic: no question-specific names; uses plan labels, corpus text and the
existing PT->EN research bridge.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import report_renderer as renderer  # noqa: E402
from adaptive_coordinator import _expand_terms_en, _PT_EN_RESEARCH  # noqa: E402
from verification_report import (  # noqa: E402
    _entity_mentioned,
    _expand_support_tokens,
    _text_versions,
    is_lacuna_declaration,
)

# Generic dimension vocabulary (PT/EN). Not answers: only words that name a
# research dimension so we can tell "nothing about it" from "not shown".
DIMENSION_TERMS = {
    # Strong, dimension-specific terms only: generic words ("support",
    # "requires", "plan") make every document look like evidence.
    "compat": ("version", "versions", "compatible", "compatibility"),
    "depend": ("depend", "dependency", "dependencies", "npm", "bun", "pnpm",
               "yarn", "package.json"),
    "custo": ("cost", "costs", "price", "pricing", "paid", "free", "license",
              "licence", "mit", "apache", "gpl", "subscription"),
    "manut": ("maintainer", "maintained", "commit", "commits", "release",
              "releases", "archived", "changelog", "updated"),
    "limita": ("limitation", "limitations", "caveat", "caveats", "workaround",
               "unsupported", "known issue", "known issues"),
    "func": ("feature", "features", "command", "commands", "workflow", "hook",
             "hooks"),
    "planej": ("plan", "plans", "planning", "planner", "todo", "tasks"),
    "implement": ("implement", "implementation", "edit", "edits", "generate"),
    "teste": ("test", "tests", "testing", "coverage", "tdd", "spec", "specs"),
    "revis": ("review", "reviews", "reviewer", "lint", "diff"),
}
GENERIC_ENTITY_TOKENS = {
    "plugin", "plugins", "opencode", "command", "commands", "pattern", "agent",
    "agents", "candidate", "candidato", "candidatos", "tool", "tools",
    "extension", "extensions", "skill", "skills", "package",
}
STOP = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "has", "have", "had", "not", "but", "you", "your", "its", "their", "they",
    "can", "will", "would", "should", "could", "may", "might", "into", "than",
    "then", "there", "these", "those", "which", "what", "when", "where", "who",
    "how", "all", "any", "each", "more", "most", "some", "such", "only", "also",
    "use", "used", "using", "one", "two", "three", "four", "five", "six",
    "uma", "um", "dos", "das", "para", "por", "com", "sem", "que", "como",
    "mais", "menos", "sobre", "entre", "cada", "pelo", "pela", "nos", "nas",
    "aos", "aas", "seu", "sua", "seus", "suas", "nao", "sim", "ele", "ela",
}
WORD = re.compile(r"[a-z0-9][a-z0-9+._-]*")
ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,4}\b")

# Extra function words for the synthesis audit only (the cell classifier keeps
# the smaller STOP set so its bucket counts stay stable).
AUDIT_STOP = STOP | {
    "them", "without", "whom", "whose", "while", "been", "being", "does",
    "did", "doing", "about", "above", "after", "again", "against", "before",
    "below", "between", "both", "during", "few", "other", "over", "same",
    "under", "until", "very",
    "fonte", "fontes", "source", "sources", "referencia", "referencias",
    "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
    "isso", "isto", "aquele", "aquela", "neste", "nesta", "nestes",
    "nestas", "deste", "desta", "destes", "destas", "num", "numa",
    "tambem", "apenas", "pode", "podem", "deve", "devem", "foi", "foram",
    "ser", "sao", "esta", "estao", "tem", "ter", "nosso", "nossa", "qual",
    "quais", "cujo", "cuja",
}


def norm_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str, min_len: int = 3) -> list[str]:
    return [w for w in WORD.findall(norm_text(text))
            if len(w) >= min_len and w not in STOP]


def entity_tokens(entity: dict) -> list[str]:
    raw = tokens(f"{entity.get('label', '')} {entity.get('id', '')}", 4)
    out = []
    for w in raw:
        if w in GENERIC_ENTITY_TOKENS or w.isdigit():
            continue
        if w not in out:
            out.append(w)
    return out


def criterion_terms(label: str) -> list[str]:
    base = tokens(label, 3)
    terms = list(base) + _expand_terms_en(base)
    norm = norm_text(label)
    for key, extra in DIMENSION_TERMS.items():
        stem = key
        if stem in norm:
            terms.extend(extra)
    # de-duplicate, keep order
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def docs_mentioning(corpus: dict, terms: list[str]) -> list[str]:
    out = []
    for url, text in corpus.items():
        low = norm_text(text or "")
        if any(t in low for t in terms):
            out.append(url)
    return out


def latest_eval(evals: list, cid: str, eid):
    found = None
    for ev in evals:
        if ev.get("criterion_id") != cid:
            continue
        if eid is None and ev.get("entity_id") is None:
            found = ev
        elif eid is not None and ev.get("entity_id") == eid:
            found = ev
    return found


def required_cells(plan: dict) -> list[tuple[str, str | None]]:
    ents = [e for e in plan.get("entities", []) if e.get("required", True)]
    ids = [e.get("id") for e in ents]
    cells = []
    for c in plan.get("criteria", []):
        if not c.get("required", True):
            continue
        applies = c.get("applies_to")
        if applies:
            for eid in applies:
                if eid in ids:
                    cells.append((c["id"], eid))
        else:
            cells.append((c["id"], None))
    return cells


def classify(state: dict) -> dict:
    plan = state.get("plan") or {}
    corpus = state.get("evidence") or {}
    evals = state.get("evaluations") or []
    ents = {e.get("id"): e for e in plan.get("entities", [])}
    crits = {c.get("id"): c for c in plan.get("criteria", [])}
    rows = []
    for cid, eid in required_cells(plan):
        ev = latest_eval(evals, cid, eid) or {}
        st = ev.get("state") or "uninvestigated"
        refs = [r.get("url") for r in ev.get("references") or []
                if isinstance(r, dict) and r.get("url")]
        ent = ents.get(eid) or {}
        etoks = entity_tokens(ent) if eid else []
        cterms = criterion_terms(crits.get(cid, {}).get("label", ""))
        entity_docs = docs_mentioning(corpus, etoks) if etoks else list(corpus)
        support_docs = [u for u in entity_docs
                        if any(t in norm_text(corpus.get(u, "")) for t in cterms)]
        ref_support = [u for u in refs if u in support_docs]
        if st == "covered":
            bucket = "ok" if ref_support else "synthesis_unsupported"
        elif not entity_docs:
            bucket = "missing_entity_evidence"
        elif not support_docs:
            bucket = "missing_dimension_evidence"
        elif ref_support:
            bucket = ("partial_legit" if st == "partial"
                      else "assessor_error")
        else:
            bucket = "selection_context"
        rows.append({
            "criterion_id": cid,
            "entity_id": eid,
            "state": st,
            "bucket": bucket,
            "entity_docs": len(entity_docs),
            "support_docs": len(support_docs),
            "support_urls": support_docs[:6],
            "refs": refs[:6],
            "ref_support": ref_support[:6],
            "justification": (ev.get("justification") or "")[:400],
            "entity_label": ent.get("label"),
            "criterion_label": crits.get(cid, {}).get("label"),
        })
    return {"rows": rows,
            "counts": dict(Counter(r["bucket"] for r in rows)),
            "total": len(rows)}


CITE = re.compile(r"\[(\d+)\]")


def content_words(text: str) -> set[str]:
    words = {w for w in WORD.findall(norm_text(text))
             if len(w) >= 4 and w not in AUDIT_STOP}
    # Acronyms and version tags ("MIT", "V2", "API") carry identifying
    # content despite their length: keep all-uppercase tokens (len>=2)
    # that are not stopwords. Case is read from the raw text because
    # norm_text lowercases.
    words |= {w.lower() for w in ACRONYM.findall(str(text or ""))
              if len(w) >= 2 and w.lower() not in AUDIT_STOP}
    return words


def _number_map(state: dict) -> dict[int, str]:
    """Citation number -> normalized corpus URL, in the delivered order.

    Prefer the numbering persisted with the report (E2: ``report.numbers``).
    Older runs lack it; the report's own source table is then authoritative
    (it was rendered with the same numbering as the text). Rebuilding from
    the obtained counter is the last resort and can disagree with the
    delivered artifact (accept12: 23/42 numbers differed).
    """
    persisted = (state.get("report") or {}).get("numbers") or {}
    if isinstance(persisted, dict) and persisted:
        out = {}
        for n, url in persisted.items():
            try:
                out[int(n)] = renderer._norm(str(url))
            except (TypeError, ValueError):
                continue
        if out:
            return out
    report = state.get("report") or {}
    markdown = report.get("markdown") or report.get("text") or ""
    import re as _re
    table = {int(n): renderer._norm(u)
             for n, u in _re.findall(r"\| \[(\d+)\] \| (\S+)", markdown)}
    if table:
        return table
    evidence = state.get("evidence") or {}
    obtained = ((state.get("counters") or {}).get("documents") or {}).get(
        "obtained")
    if isinstance(obtained, list) and obtained:
        raw_by_norm = {renderer._norm(u): u for u in evidence}
        ordered: dict = {}
        for url in obtained:
            raw = raw_by_norm.get(renderer._norm(url))
            if raw is not None and raw not in ordered:
                ordered[raw] = evidence[raw]
        if ordered:
            state = {**state, "evidence": ordered}
    return {n: url for url, n in renderer._numbers(state).items()}


def _audit_entities(state: dict) -> list[tuple[str, object, list[str]]]:
    out = []
    for ent in (state.get("plan") or {}).get("entities", []):
        # Parenthetical text describes the entity ("OpenCode (versão
        # instalada...)"); the name is what a claim can actually cite.
        label = re.sub(r"\([^)]*\)", " ", ent.get("label") or "")
        toks = entity_tokens({**ent, "label": label})
        if toks:
            out.append((ent.get("label") or ent.get("id") or "?",
                        ent.get("id"), toks))
    return out


def _is_reference_line(line: str) -> bool:
    """Renderer metadata line ("Referências: [2]") is not a claim."""
    stripped = re.sub(r"^[\s*_`]+", "", line)
    return bool(re.match(r"refer[êe]ncias?\s*:", stripped, re.I))


def synthesis_audit(state: dict) -> dict:
    report = state.get("report") or {}
    markdown = report.get("markdown") or report.get("text") or ""
    numbers = _number_map(state)
    docs = {renderer._norm(url): norm_text(text or "")
            for url, text in (state.get("evidence") or {}).items()}
    entities = _audit_entities(state)
    supported = unsupported = uncited = 0
    items: list[dict] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "|", ">", "```")):
            continue
        if _is_reference_line(line):
            continue
        words = content_words(line)
        if not words:
            continue
        cites = CITE.findall(line)
        if not cites:
            # No citation: only long prose statements count as claims.
            for sent in re.split(r"(?<=[.!?])\s+", line):
                if len(sent.split()) >= 12:
                    uncited += 1
            continue
        cited_docs = []
        missing = []
        for n in cites:
            url = numbers.get(int(n))
            doc = docs.get(renderer._norm(url), "") if url else ""
            if not doc:
                missing.append(n)
            else:
                cited_docs.append((n, doc))
        named = [(label, eid, toks) for label, eid, toks in entities
                 if any(t in norm_text(line) for t in toks)]
        # Absence declaration over consulted sources: sustained by the
        # consultation itself (mirrors verification_report.check_support).
        if cited_docs and not missing and is_lacuna_declaration(line):
            supported += 1
            continue
        # Inference-marked claim: audit the factual anchor only (mirrors
        # verification_report._factual_anchor).
        from verification_report import _factual_anchor as _anchor
        anchor = _anchor(line)
        words = content_words(anchor) if anchor != line else words
        named = [(label, eid, toks) for label, eid, toks in entities
                 if any(t in norm_text(anchor) for t in toks)] \
            if anchor != line else named
        # Cell entity must be named in full ("opencode agents" is not
        # "opencode-planner"); a claimed version absent from the cited
        # doc never sustains, however high the remaining overlap is.
        # Both mirror verification_report (shared helpers, single source).
        missing_entities = []
        if named and not any(
                _entity_mentioned(label, eid, doc)
                for label, eid, _toks in named for _, doc in cited_docs):
            missing_entities = [label for label, _eid, _toks in named]
        claim_vers = _text_versions(anchor)
        version_miss = bool(claim_vers) and not any(
            not (claim_vers - _text_versions(doc))
            for _, doc in cited_docs)
        expanded = _expand_support_tokens(words)
        best, rare = 0.0, 0
        for _, doc in cited_docs:
            hits = {w for w in expanded if w in doc}
            if words:
                best = max(best, len(hits) / len(words))
            rare = max(rare, sum(1 for w in hits if len(w) >= 6))
        if not cited_docs:
            reason = "citação fora do corpus: " + ", ".join(
                f"[{n}]" for n in missing)
        elif missing_entities:
            reason = "entidade ausente no doc citado: " + ", ".join(
                missing_entities)
        elif version_miss:
            reason = "versão ausente no doc citado"
        elif best < 0.35 and rare < 2:
            reason = (f"overlap {best:.2f} < 0.35 e "
                      f"{rare} palavra(s) rara(s) em comum")
        else:
            supported += 1
            continue
        unsupported += 1
        items.append({"sentence": line[:300], "cites": cites,
                      "reason": reason})
    return {"supported": supported, "unsupported": unsupported,
            "uncited": uncited, "unsupported_items": items}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    run_dir = Path(argv[1])
    state_path = run_dir / "state.json" if run_dir.is_dir() else run_dir
    try:
        state = json.loads(state_path.read_text())
    except (OSError, ValueError) as exc:
        print(f"erro: não foi possível ler o state em {state_path}: {exc}",
              file=sys.stderr)
        return 2
    diag = classify(state)
    synthesis = synthesis_audit(state)
    payload = {
        "cells": {
            "buckets": diag["counts"],
            "total": diag["total"],
            "rows": diag["rows"],
        },
        "synthesis": synthesis,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print(f"cells: {diag['total']} required | " + ", ".join(
        f"{bucket}={n}" for bucket, n in sorted(diag["counts"].items())))
    print(f"synthesis: {synthesis['supported']} supported, "
          f"{synthesis['unsupported']} unsupported, "
          f"{synthesis['uncited']} uncited")
    for item in synthesis["unsupported_items"][:8]:
        print(f"  unsupported {item['cites']}: {item['sentence'][:160]}")
        print(f"    {item['reason']}")
    if len(argv) > 3 and argv[2] == "--json":
        Path(argv[3]).write_text(json.dumps(payload, ensure_ascii=False,
                                            indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
