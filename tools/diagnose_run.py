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
    _mentions_version_gap,
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
            for url, text in (state.get("evidence") or {}).items()}
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
        words = content_words(line)
        if not words:
            continue
        cites = CITE.findall(line) + extra_cites
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
        # consultation itself (mirrors verification_report.check_support)
        # — but the cited source must be about the named entity (S2
        # premise); a foreign doc is a loose citation, not a premise.
        if cited_docs and not missing and is_lacuna_declaration(line):
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
        version_miss = bool(claim_vers) \
            and not _mentions_version_gap(anchor) and not any(
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
