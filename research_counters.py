#!/usr/bin/env python3
"""Six-stage source counters, observed events only (stdlib, no network).

Stages (document/URL units, never chunks)::

    discovered         URLs seen in search results
    obtained           content really retrieved with text
    usable             post-qualification: usable/partial WITH usable text
    analyzed           documents in the selection actually sent to the assessor
    used_in_synthesis  documents included in the writer prompt (real selection)
    cited              corpus URLs referenced by the delivered report

Honesty rules (modelagem §7):
* metadata-only records, bibliographic entries and videos without a transcript
  never increment ``obtained`` (nor the stages that depend on it);
* duplicate URLs are deduped by normalized URL; identical bytes under another
  URL are a *republication* relation, distinct excerpts of one URL are a
  *version* relation — versions count separately but stay related;
* nothing is inferred: each stage only grows when the corresponding event was
  observed (search hit, fetch with text, selection, report reference).
"""
from __future__ import annotations

import time

STAGES = ("discovered", "obtained", "usable", "analyzed",
          "used_in_synthesis", "cited")

_METADATA_STATUSES = frozenset({
    "metadata", "metadata_only", "metadata-only", "bibliographic",
    "record", "record_only", "description_only",
})


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _norm(url) -> str | None:
    try:
        from scripts import citation_audit as ca
    except ImportError:  # scripts/ on sys.path directly
        import citation_audit as ca  # type: ignore
    return ca.normalize_url(url)


def default_counters() -> dict:
    """Fresh, JSON-serialisable counter structure (all six stages at 0)."""
    return {
        "counts": {stage: 0 for stage in STAGES},
        "documents": {stage: [] for stage in STAGES},
        "meta": {},        # url -> {obtained_at, raw_chars, usable_chars,
                           #         status, type, title}
        "relations": [],   # [{url, related_to, kind, at}]
        "outside_corpus_citations": [],
        "note": ("contadores de eventos observados; metadado/vídeo sem "
                 "transcrição não conta como obtido"),
    }


def ensure(state: dict) -> dict:
    """Return state['counters'], creating/filling defaults (retrocompatible)."""
    counters = state.get("counters")
    if not isinstance(counters, dict):
        counters = default_counters()
    base = default_counters()
    for key in ("counts", "documents", "meta", "relations",
                "outside_corpus_citations"):
        value = counters.get(key)
        if not isinstance(value, type(base[key])):
            counters[key] = base[key]
    for stage in STAGES:
        counters["counts"].setdefault(stage, 0)
        if not isinstance(counters["documents"].get(stage), list):
            counters["documents"][stage] = []
    state["counters"] = counters
    return counters


def _add(counters: dict, stage: str, url: str) -> bool:
    docs = counters["documents"][stage]
    if url in docs:
        return False
    docs.append(url)
    counters["counts"][stage] = len(docs)
    return True


def _is_youtube(url: str) -> bool:
    return any(h in (url or "").lower()
               for h in ("youtube.com/watch", "youtu.be/", "music.youtube.com"))


def classify_type(url: str, text: str, qualification: dict | None = None) -> str:
    """Observed content type, from markers/qualification only (no guessing)."""
    q = qualification or {}
    status = str(q.get("status", "") or "").strip().lower()
    if status in _METADATA_STATUSES:
        return "metadata"
    body = (text or "").strip()
    if body.startswith("[metadata]") or body.startswith("[record]"):
        return "metadata"
    if _is_youtube(url):
        return "transcript" if "[spoken" in body else "description"
    low = (url or "").lower()
    if any(h in low for h in ("github.com", "gist.github.com",
                              "raw.githubusercontent.com")):
        return "repository"
    if any(h in low for h in ("arxiv.org", "openalex.org", "doi.org",
                              "semanticscholar.org", "crossref.org")):
        return "academic"
    if body.startswith("[abstract]"):
        return "academic"
    return "page"


_NOT_CONTENT_STATUSES = frozenset({
    "error", "failed", "fetch_error", "timeout", "access_failure",
    "access-failure", "empty", "blocked", "unavailable", "absent",
})


def is_content_bearing(url: str, text: str,
                       qualification: dict | None = None) -> bool:
    """True only when real text content was retrieved (not metadata only).

    A page excluded by relevance/insufficiency was still obtained (it has
    text); an error/empty payload was not. Metadata-only records and videos
    without a transcript never count as obtained.
    """
    body = (text or "").strip()
    if not body:
        return False
    q = qualification or {}
    status = str(q.get("status", "") or "").strip().lower()
    if status in _METADATA_STATUSES or status in _NOT_CONTENT_STATUSES:
        return False
    if q.get("content_bearing") is False:
        return False
    if body.startswith("[metadata]") or body.startswith("[record]"):
        return False
    if _is_youtube(url) and "[spoken" not in body:
        # Title/description help discovery but never prove the spoken content.
        return False
    return True


def record_discovered(state: dict, urls) -> int:
    """Count URLs seen in search results (normalized dedupe). Returns new ones."""
    counters = ensure(state)
    added = 0
    for item in urls or ():
        raw = item.get("url") if isinstance(item, dict) else item
        norm = _norm(raw)
        if norm and _add(counters, "discovered", norm):
            added += 1
    return added


def record_obtained(state: dict, url: str, text: str,
                    qualification: dict | None = None) -> bool:
    """Count one document as obtained only when content really came back."""
    norm = _norm(url)
    if not norm or not is_content_bearing(url, text, qualification):
        return False
    counters = ensure(state)
    added = _add(counters, "obtained", norm)
    q = qualification or {}
    counters["meta"][norm] = {
        "obtained_at": _utcnow(),
        "raw_chars": len(text or ""),
        "usable_chars": len((q.get("usable_text") or text or "")),
        "status": q.get("status", "?"),
        "type": classify_type(url, text, qualification),
        "title": q.get("title") or None,
    }
    return added


def record_usable(state: dict, url: str,
                  qualification: dict | None = None) -> bool:
    """Count post-qualification usable material (usable/partial + real text)."""
    norm = _norm(url)
    if not norm:
        return False
    counters = ensure(state)
    if norm not in counters["documents"]["obtained"]:
        return False
    q = qualification or {}
    status = str(q.get("status", "") or "").strip().lower()
    if q.get("excluded") or status not in ("usable", "partial"):
        return False
    if not (q.get("usable_text") or "").strip():
        return False
    return _add(counters, "usable", norm)


def record_analyzed(state: dict, urls) -> int:
    """Document units in the REAL assessor selection (last_selection['urls'])."""
    counters = ensure(state)
    added = 0
    for raw in urls or ():
        norm = _norm(raw)
        if not norm or norm not in counters["documents"]["obtained"]:
            continue
        if _add(counters, "analyzed", norm):
            added += 1
    return added


def record_used_in_synthesis(state: dict, urls) -> int:
    """Document units really included in the writer prompt selection."""
    counters = ensure(state)
    added = 0
    for raw in urls or ():
        norm = _norm(raw)
        if not norm or norm not in counters["documents"]["obtained"]:
            continue
        if _add(counters, "used_in_synthesis", norm):
            added += 1
    return added


def record_cited_urls(state: dict, urls) -> dict:
    """Count corpus URLs cited by the delivered body (document units)."""
    counters = ensure(state)
    corpus = set(counters["documents"]["obtained"])
    added = 0
    outside: list[str] = []
    for raw in urls or ():
        norm = _norm(raw)
        if norm is None:
            continue
        if norm in corpus:
            if _add(counters, "cited", norm):
                added += 1
        elif norm not in outside:
            outside.append(norm)
    if outside:
        known = counters["outside_corpus_citations"]
        counters["outside_corpus_citations"] = known + [
            u for u in outside if u not in known]
    return {"cited": added, "outside_corpus": outside}


def record_cited(state: dict, report_text: str) -> dict:
    """Count references in a report text (via citation_audit extraction)."""
    try:
        from scripts import citation_audit as ca
    except ImportError:  # pragma: no cover - scripts/ on sys.path
        import citation_audit as ca  # type: ignore
    refs = [ref.get("url") for ref in ca.extract_references(report_text or "")]
    return record_cited_urls(state, refs)


def register_relation(state: dict, url_a: str, url_b: str, kind: str,
                      detail: str = "") -> None:
    """Record a duplicate/version relation between two documents.

    A *version* relation may point a URL to itself (distinct excerpts of the
    same document); duplicate/republication needs two distinct URLs.
    """
    counters = ensure(state)
    a, b = _norm(url_a), _norm(url_b)
    if not a or not b:
        return
    if a == b and kind != "version":
        return
    for rel in counters["relations"]:
        if rel.get("kind") == kind and \
                {rel.get("url"), rel.get("related_to")} == {a, b}:
            return
    counters["relations"].append({"url": a, "related_to": b, "kind": kind,
                                  "detail": detail, "at": _utcnow()})


def counters_snapshot(state: dict) -> dict:
    """JSON-safe copy for report/manifest (counts + provenance + relations)."""
    counters = ensure(state)
    return {
        "counts": dict(counters["counts"]),
        "documents": {stage: list(counters["documents"][stage])
                      for stage in STAGES},
        "meta": {u: dict(v) for u, v in counters["meta"].items()},
        "relations": [dict(r) for r in counters["relations"]],
        "outside_corpus_citations": list(
            counters.get("outside_corpus_citations", [])),
        "units": "document (URL normalizada; chunks do mesmo doc contam 1)",
    }
