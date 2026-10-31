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
    _audit_inference,
    _claims_version_functionally,
    _entity_mentioned,
    _expand_support_tokens,
    _has_inference_marker,
    _is_evidence_literal,
    _is_numeric_comparison,
    _is_own_note_line,
    _is_user_premise,
    _mentions_version_gap,
    _quoted_literals,
    _split_inference,
    _text_exact_versions,
    _text_family_versions,
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


def entity_docs_strict(corpus: dict, ent: dict) -> list[str]:
    """Corpus URLs really about the entity (identity as concept).

    One shared word ("planning", "memory") is not aboutness, and neither
    is a far-apart coincidence of common words: the doc must name the
    entity (label full form, separator-insensitive); only single-token
    entities fall back to token presence. Mirrors the product selection
    rule (adaptive_coordinator._identity_matches).
    """
    label = str((ent or {}).get("label") or "")
    if not label:
        return []
    toks = entity_tokens(ent or {})
    phrase = re.sub(r"[^a-z0-9]+", " ", norm_text(label)).strip()
    cleaned = []
    for _u, _t in (corpus or {}).items():
        if isinstance(_u, str) and not _u.startswith("user://"):
            cleaned.append(
                re.sub(r"[^a-z0-9]+", " ", norm_text(_t or "")).strip())
    # Singleton gate, corpus-relative (mirrors the product rule): a lone
    # common word never identifies; a rare one keeps the presence rule.
    single_ok = True
    if len(toks) == 1:
        df = sum(1 for _d in cleaned if toks[0] in _d)
        single_ok = df <= max(2, len(cleaned) // 10)
    out = []
    for url, text in (corpus or {}).items():
        if not isinstance(url, str) or url.startswith("user://"):
            continue
        doc = re.sub(r"[^a-z0-9]+", " ", norm_text(text or "")).strip()
        if not doc:
            continue
        if phrase and phrase in doc:
            out.append(url)
        elif single_ok and len(toks) == 1 and toks[0] in doc:
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


DIMENSION_LOCALITY_WINDOW = 1500


def _mention_positions(haystack: str, needle: str) -> list[int]:
    pos, out = 0, []
    while True:
        i = haystack.find(needle, pos)
        if i < 0:
            return out
        out.append(i)
        pos = i + max(1, len(needle))


def dimension_supports(text: str, label: str, toks: list[str],
                       cterms: list[str],
                       window: int = DIMENSION_LOCALITY_WINDOW) -> bool:
    """Dimension terms count only near the entity mention (locality).

    A long page can name the candidate once and discuss the dimension
    pages away about something else (accept18: the marketplace lists
    opencode-local-memory once and describes planning for lit-opencode
    elsewhere). Support requires a dimension term within ``window``
    chars of an entity mention — the same scale the assessor excerpts
    at. Single-token entities use every token occurrence as anchor.
    """
    cleaned = re.sub(r"[^a-z0-9]+", " ", norm_text(text or "")).strip()
    if not cleaned:
        return False
    phrase = re.sub(r"[^a-z0-9]+", " ", norm_text(label or "")).strip()
    anchors: list[int] = []
    if phrase:
        anchors.extend(_mention_positions(cleaned, phrase))
    if len(toks) == 1 and toks[0]:
        anchors.extend(_mention_positions(cleaned, toks[0]))
    if not anchors:
        return False
    hits: list[int] = []
    for term in cterms or []:
        if term:
            hits.extend(_mention_positions(cleaned, term))
    if not hits:
        return False
    hits.sort()
    for a in anchors:
        for h in hits:
            if abs(h - a) <= window:
                return True
            if h - a > window:
                break
    return False


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
        cterms = criterion_terms(crits.get(cid, {}).get("label", ""))
        entity_docs = entity_docs_strict(corpus, ent) if eid else list(corpus)
        label = str(ent.get("label") or "")
        etoks = entity_tokens(ent) if eid else []
        support_docs = [u for u in entity_docs
                        if dimension_supports(corpus.get(u, ""), label,
                                              etoks, cterms)]
        ref_support = [u for u in refs if u in support_docs]
        if st == "covered":
            bucket = "ok" if ref_support else "synthesis_unsupported"
        elif st == "not_applicable":
            # M7: fora de escopo com evidência não é erro — é veredito
            # documentado (fora do denominador, nunca cobertura).
            bucket = "na_scoped" if ref_support else "na_bare"
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
    """Renderer metadata line ("Referências: [2]", "Fontes:") is not a claim."""
    stripped = re.sub(r"^[\s*_`]+", "", line)
    return bool(re.match(r"(refer[êe]ncias?|fontes?)\s*:",
                         stripped, re.I))


def _attach_floating_cites(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Attach cite-only lines to the preceding claim (genus3: writer puts
    citations on a separate "Fontes:" + "- [1]" block; without this the
    claims read as uncited and the audit blames the synthesis instead of
    the layout). Returns (line, extra_cites); cite-only lines are dropped."""
    merged: list[tuple[str, list[str]]] = []
    claim_idx: int | None = None
    for raw in lines:
        line = raw.strip()
        cites = CITE.findall(line)
        if cites:
            bare = re.sub(r"[\s*_`>\-#|]", "", line)
            bare = CITE.sub("", bare)
            if len(bare) < 3:
                if claim_idx is not None:
                    merged[claim_idx][1].extend(cites)
                continue
        merged.append([line, []])
        if line and not line.startswith(("#", "|", ">", "```")) \
                and content_words(line):
            claim_idx = len(merged) - 1
    return [(line, extra) for line, extra in merged]


def synthesis_audit(state: dict) -> dict:
    report = state.get("report") or {}
    markdown = report.get("markdown") or report.get("text") or ""
    numbers = _number_map(state)
    docs = {renderer._norm(url): norm_text(text or "")
            for url, text in (state.get("evidence") or {}).items()
            if not (isinstance(url, str) and url.startswith("user://"))}
    # remove a chave None de user:// (norm None) se existir
    docs.pop(None, None)
    entities = _audit_entities(state)
    supported = unsupported = uncited = 0
    items: list[dict] = []
    for raw_line, extra_cites in _attach_floating_cites(
            markdown.splitlines()):
        line = raw_line.strip()
        if not line or line.startswith(("#", "|", ">", "```")):
            continue
        if _is_reference_line(line):
            continue
        # Unificação Div1 (mesmo filtro do verify): linha de nota própria
        # (tabela §7, notas render/support) é inventário, nunca afirmação.
        if _is_own_note_line(line):
            continue
        words = content_words(line)
        if not words:
            continue
        cites = CITE.findall(line) + extra_cites
        # Unificação Div1 (mesmo extract_references/Classify do verify):
        # URL evidência sem [N] ([guia](https://...), Source:) dentro do
        # corpus entra em cited_docs; fora vira missing (failed, nunca
        # uncited). Bare utility/in_command nunca pondera (como no verify).
        _ev_docs: list[tuple[str, str]] = []
        _ev_missing: list[str] = []
        try:
            try:
                from scripts import citation_audit as _ca1
            except ImportError:  # pragma: no cover
                import citation_audit as _ca1  # type: ignore
            for _r in _ca1.extract_references(line):
                try:
                    if _ca1.classify_reference(_r) != "evidence":
                        continue
                except Exception:
                    continue
                _u = _r.get("url")
                if not _u:
                    continue
                _n = renderer._norm(_u)
                _d = docs.get(_n, "") if _n else ""
                if not _d:
                    if _u not in _ev_missing:
                        _ev_missing.append(_u)
                else:
                    _ev_docs.append((_u, _d))
        except Exception:
            pass
        if not cites and not _ev_docs and not _ev_missing:
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
        # Evidência sem [N] compõe o mesmo veredito (nunca uncited).
        cited_docs.extend(_ev_docs)
        # missing de URL nua usa a URL no motivo (mesmo "fora do corpus").
        _missing_urls = list(_ev_missing)
        named = [(label, eid, toks) for label, eid, toks in entities
                 if any(t in norm_text(line) for t in toks)]
        # URL evidência fora do corpus = failed imediato (mesmo unknown
        # do verify); nunca uncited nem sustentada por [N] válido ao lado.
        if _missing_urls:
            _all_missing = ([f"[{n}]" for n in missing]
                            + list(_missing_urls))
            unsupported += 1
            items.append({"sentence": line[:300], "cites": cites,
                          "reason": "citação fora do corpus: " + ", ".join(
                              _all_missing)[:300]})
            continue
        # Premissa explicita do usuario: citavel sem numero de corpus,
        # nunca LACUNA automatica (isenta o gate da versao do contexto).
        if _is_user_premise(line) and not is_lacuna_declaration(line):
            if cited_docs and not missing and not _missing_urls:
                _prem = sum(
                    1 for _, doc in cited_docs
                    if not named or any(
                        _entity_mentioned(label, eid, doc)
                        for label, eid, _toks in named))
                if named and not _prem:
                    unsupported += 1
                    items.append({"sentence": line[:300], "cites": cites,
                                  "reason": "entidade ausente no doc citado "
                                            "(premissa sem doc da entidade)"})
                    continue
                # Regra estreita versão-premissa (Missão 3): comparação
                # numérica contra mínimo declarado = sustentada
                # (premissa + corpus); compat funcional/integração sem
                # fonte que mencione a tag exata = LACUNA.
                _exact_s = _text_exact_versions(line)
                if (_exact_s and not _is_numeric_comparison(line)
                        and _claims_version_functionally(line)):
                    _exact_u: set[str] = set()
                    for _, _doc in cited_docs:
                        _exact_u |= _text_exact_versions(_doc)
                    if not _exact_s <= _exact_u:
                        unsupported += 1
                        items.append({
                            "sentence": line[:300], "cites": cites,
                            "reason": "versão exata ausente no doc citado"})
                        continue
                supported += 1
                continue
        # Absence declaration over consulted sources: sustained by the
        # consultation itself (mirrors verification_report.check_support)
        # — but the cited source must be about the named entity (S2
        # premise); a foreign doc is a loose citation, not a premise.
        # Espelho Div2 (gates do check_support): versão exata/família e
        # literal citado aplicam em LACUNA; sem eles, LACUNA com versão
        # ausente no doc falha (não sustenta).
        if cited_docs and not missing and not _missing_urls \
                and is_lacuna_declaration(line):
            _premise = sum(
                1 for _, doc in cited_docs
                if not named or any(
                    _entity_mentioned(label, eid, doc)
                    for label, eid, _toks in named))
            if named and not _premise:
                unsupported += 1
                items.append({"sentence": line[:300], "cites": cites,
                              "reason": "entidade ausente no doc citado "
                                        "(premissa sem doc da entidade)"})
                continue
            # Gate versão exata/família (espelha check_support): tag
            # afirmada sem isenção de lacuna exige presença no doc citado.
            _exact_s = _text_exact_versions(line)
            _fam_s = _text_family_versions(line)
            if (_exact_s or _fam_s) and not _mentions_version_gap(line):
                _exact_u: set[str] = set()
                _fam_u: set[str] = set()
                for _, _doc in cited_docs:
                    _exact_u |= _text_exact_versions(_doc)
                    _fam_u |= _text_family_versions(_doc)
                if _exact_s and not _exact_s <= _exact_u:
                    unsupported += 1
                    items.append({
                        "sentence": line[:300], "cites": cites,
                        "reason": "versão exata ausente no doc citado"})
                    continue
                if _fam_s and not _fam_s <= _fam_u:
                    unsupported += 1
                    items.append({
                        "sentence": line[:300], "cites": cites,
                        "reason": "família funcional ausente no doc citado"})
                    continue
            # Gate literal citado (espelha check_support): literal
            # substantivo entre aspas deve ocorrer no doc citado.
            _lits = [lit for lit in _quoted_literals(line)
                     if _is_evidence_literal(lit)]
            if _lits:
                _absent = [lit for lit in _lits
                           if not any(lit.lower() in (_doc or "").lower()
                                      for _, _doc in cited_docs)]
                if _absent:
                    unsupported += 1
                    items.append({
                        "sentence": line[:300], "cites": cites,
                        "reason": "literal ausente no doc citado: "
                                  + ", ".join(_absent)[:160]})
                    continue
            supported += 1
            continue
        # Inferencia marcada: audita ancora E relacao separadamente
        # (complementaridade plausivel != integracao testada).
        if _has_inference_marker(line):
            from verification_report import _factual_anchor as _anchor_fn
            from verification_report import _content_tokens as _ctoks
            _anchor_txt, _rel_txt = _split_inference(line)
            _a_toks = set(_ctoks(_anchor_txt))
            _r_toks = set(_ctoks(_rel_txt)) or set(_ctoks(line))
            _named_a = [(label, eid, toks) for label, eid, toks in entities
                        if any(t in norm_text(_anchor_txt) for t in toks)]
            _named_r = [(label, eid, toks) for label, eid, toks in entities
                        if any(t in norm_text(_rel_txt or line)
                               for t in toks)]
            # converte entidades do diagnose para o formato do verificador
            _ent_a = [(set(t for t in _t if len(t) >= 4), _l, _e)
                      for _l, _e, _t in _named_a]
            _ent_r = [(set(t for t in _t if len(t) >= 4), _l, _e)
                      for _l, _e, _t in _named_r]
            _interop = False
            _any_a = False
            _rel_reason = ""
            if not cited_docs and missing:
                unsupported += 1
                items.append({"sentence": line[:300], "cites": cites,
                              "reason": "citação fora do corpus: " + ", ".join(
                                  f"[{n}]" for n in missing)})
                continue
            for _, doc in cited_docs:
                a_ok, r_ok, _ar, rr = _audit_inference(
                    _anchor_txt, _rel_txt or line, doc, _ent_a, _ent_r)
                if a_ok:
                    _any_a = True
                if a_ok and r_ok:
                    _interop = True
                    break
                _rel_reason = rr or _ar
            if _interop:
                supported += 1
                continue
            unsupported += 1
            items.append({"sentence": line[:300], "cites": cites,
                          "reason": _rel_reason or
                          "inferência sem citação de interoperabilidade "
                          "(complementaridade plausível, não integração "
                          "testada)"})
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
        # "opencode-planner"); gate separado tag exata vs familia
        # funcional (conclusoes separadas). Ambos espelham o verificador.
        missing_entities = []
        if named and not any(
                _entity_mentioned(label, eid, doc)
                for label, eid, _toks in named for _, doc in cited_docs):
            missing_entities = [label for label, _eid, _toks in named]
        _exact_c = _text_exact_versions(anchor)
        _fam_c = _text_family_versions(anchor)
        version_miss = False
        version_reason = "versão ausente no doc citado"
        if (_exact_c or _fam_c) and not _mentions_version_gap(anchor) \
                and not _is_user_premise(anchor):
            _exact_u: set[str] = set()
            _fam_u: set[str] = set()
            for _, doc in cited_docs:
                _exact_u |= _text_exact_versions(doc)
                _fam_u |= _text_family_versions(doc)
            if _exact_c and not _exact_c <= _exact_u:
                version_miss = True
                version_reason = "versão exata ausente no doc citado"
            elif _fam_c and not _fam_c <= _fam_u:
                version_miss = True
                version_reason = "família funcional ausente no doc citado"
        # Trava de interoperabilidade (Missão 3, unificada com o
        # ramo marcado e check_support): claim com >=2 entidades exige
        # um doc que mencione >=2 delas (integração testada); âncoras
        # ok em docs separados = complementaridade plausível (LACUNA
        # explícita, não unsupported genérico); resto unsupported.
        _needs_interop = len(named) >= 2
        if _needs_interop:
            # Nomeação frouxa (token compartilhado como "widget") não
            # arma a trava: exige menção estrita de >=2 entidades na
            # frase (mesmo critério _entity_mentioned usado nos docs).
            _interop_named = [
                entry for entry in named
                if _entity_mentioned(entry[0], entry[1], line)]
            _needs_interop = len(_interop_named) >= 2
        else:
            _interop_named = []
        _has_interop_doc = _needs_interop and any(
            sum(1 for label, eid, _t in _interop_named
                if _entity_mentioned(label, eid, _doc)) >= 2
            for _, _doc in cited_docs)
        _anchors_separate = bool(_needs_interop and not _has_interop_doc
                                 and cited_docs and all(
                                     any(_entity_mentioned(label, eid, _doc)
                                         for _, _doc in cited_docs)
                                     for label, eid, _t in _interop_named))
        expanded = _expand_support_tokens(words)
        best, rare = 0.0, 0
        for _, doc in cited_docs:
            hits = {w for w in expanded if w in doc}
            if words:
                best = max(best, len(hits) / len(words))
            rare = max(rare, sum(1 for w in hits if len(w) >= 6))
        _overlap_ok = not (best < 0.35 and rare < 2)
        if _overlap_ok and _needs_interop and not _has_interop_doc:
            # overlap ok em doc(s) só, mas nenhum doc citado menciona
            # >=2 entidades: não é integração testada (resto: a
            # entidade descoberta entra no motivo, abaixo)
            _overlap_ok = False
            if not _anchors_separate:
                missing_entities = [
                    label for label, eid, _t in _interop_named
                    if not any(_entity_mentioned(label, eid, _d)
                               for _, _d in cited_docs)]
        if not cited_docs:
            reason = "citação fora do corpus: " + ", ".join(
                f"[{n}]" for n in missing)
        elif _anchors_separate:
            reason = ("inferência sem citação de interoperabilidade "
                      "(complementaridade plausível, não integração "
                      "testada)")
        elif missing_entities:
            reason = "entidade ausente no doc citado: " + ", ".join(
                missing_entities)
        elif version_miss:
            reason = version_reason
        elif _overlap_ok and (not _needs_interop or _has_interop_doc):
            supported += 1
            continue
        elif missing_entities:
            reason = "entidade ausente no doc citado: " + ", ".join(
                missing_entities)
        else:
            reason = (f"overlap {best:.2f} < 0.35 e "
                      f"{rare} palavra(s) rara(s) em comum")
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
