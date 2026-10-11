#!/usr/bin/env python3
"""Depth profiles for the Hermes deep-research skill.

Final parameter table (implemented below in PROFILES):

| profile | report_type     | iterations | breadth | depth | words | vast_max | yt_live |
|---------|-----------------|------------|---------|-------|-------|----------|---------|
| light   | quick_report    | 1          | 2       | 1     | 600   | 6        | 1       |
| medium  | research_report | 2          | 3       | 2     | 1200  | 10       | 2       |
| hard    | detailed_report | 3          | 5       | 3     | 2500  | 12       | 3       |
| deep    | deep            | 5          | 8       | 4     | 4000  | 12       | 3       |

Field mapping: iterations -> MAX_ITERATIONS, breadth -> DEEP_RESEARCH_BREADTH,
depth -> DEEP_RESEARCH_DEPTH, words -> TOTAL_WORDS, vast_max -> documents
max_results cap, yt_live -> live YouTube transcript fetch cap.

Contracts (never widen without changing both sides):
- vast_max <= 12: vast_local_retriever.MAX_RESULTS = 12. The retriever
  endpoint always enforces this server-side; the profile cap is recorded in
  the resolved config and exported as VAST_DOCS_CAP for forward use.
- yt_live <= 3: vast_local_retriever.YT_ENRICH_MAX = 3 (phase B live fetch).
  Exported as VAST_YT_LIVE_CAP for forward use.

Fixed site-packages values (documented, never varied here): EmbeddingsFilter
k=20 default, top-10 cut in pretty_print_docs, chunk 1000/100.

Legacy CLI aliases: quick == light, standard == medium, detailed == hard,
deep == deep.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

# Contract ceilings shared with vast_local_retriever.py (do not raise here
# without changing the retriever side too).
VAST_MAX_RESULTS = 12
YT_LIVE_MAX = 3

# Library default kept when a profile does not set it.
DEFAULT_CONCURRENCY = 4

PROFILES: dict[str, dict] = {
    "light": {
        "report_type": "quick_report",
        "MAX_ITERATIONS": 1,
        "DEEP_RESEARCH_BREADTH": 2,
        "DEEP_RESEARCH_DEPTH": 1,
        "TOTAL_WORDS": 600,
        "vast_max": 6,
        "yt_live": 1,
    },
    "medium": {
        "report_type": "research_report",
        "MAX_ITERATIONS": 2,
        "DEEP_RESEARCH_BREADTH": 3,
        "DEEP_RESEARCH_DEPTH": 2,
        "TOTAL_WORDS": 1200,
        "vast_max": 10,
        "yt_live": 2,
    },
    "hard": {
        "report_type": "detailed_report",
        "MAX_ITERATIONS": 3,
        "DEEP_RESEARCH_BREADTH": 5,
        "DEEP_RESEARCH_DEPTH": 3,
        "TOTAL_WORDS": 2500,
        "vast_max": 12,
        "yt_live": 3,
    },
    "deep": {
        "report_type": "deep",
        "MAX_ITERATIONS": 5,
        "DEEP_RESEARCH_BREADTH": 8,
        "DEEP_RESEARCH_DEPTH": 4,
        "TOTAL_WORDS": 4000,
        "vast_max": 12,
        "yt_live": 3,
    },
}

PROFILE_ALIASES: dict[str, str] = {
    "light": "light",
    "quick": "light",
    "medium": "medium",
    "standard": "medium",
    "hard": "hard",
    "detailed": "hard",
    "deep": "deep",
}

ALLOWED_OVERRIDES = frozenset({
    "TOTAL_WORDS",
    "MAX_ITERATIONS",
    "DEEP_RESEARCH_BREADTH",
    "DEEP_RESEARCH_DEPTH",
    "DEEP_RESEARCH_CONCURRENCY",
    "vast_max",
    "yt_live",
})

# Stop-rule thresholds.
COVERAGE_DONE = 0.95  # aspects_covered >= this -> coverage stop
COVERAGE_OK = 0.60  # aspects decent enough for a novelty stop
NOVELTY_FLOOR = 0.15  # novelty_last_rounds <= this counts as "low"

_URL_RE = re.compile(r"https?://[^\s`)\]]+")


def _citation_audit():
    """Lazy import (mirrors gpt_researcher_integration.run_provenance_audit)."""
    try:
        from scripts import citation_audit as ca
        return ca
    except ImportError:  # scripts/ on sys.path directly (verify scripts)
        import citation_audit as ca
        return ca


def resolve(profile: str, overrides: dict | None = None) -> dict:
    """Validate a profile name + per-run overrides, return resolved config.

    Returns dict with keys: profile, report_type, MAX_ITERATIONS,
    DEEP_RESEARCH_BREADTH, DEEP_RESEARCH_DEPTH, DEEP_RESEARCH_CONCURRENCY,
    TOTAL_WORDS, vast_max, yt_live.

    Raises ValueError on unknown profile name or unknown override key.
    vast_max is clamped to <= 12 and yt_live to <= 3 (retriever contract).
    """
    if not isinstance(profile, str):
        raise ValueError(f"unknown depth profile {profile!r}")
    canonical = PROFILE_ALIASES.get(profile.strip().lower(), None)
    if canonical is None or canonical not in PROFILES:
        raise ValueError(
            f"unknown depth profile {profile!r}; "
            f"expected one of {sorted(PROFILE_ALIASES)}"
        )
    base = PROFILES[canonical]
    ov = dict(overrides or {})
    unknown = sorted(set(ov) - set(ALLOWED_OVERRIDES))
    if unknown:
        raise ValueError(
            f"unknown override keys {unknown}; "
            f"allowed: {sorted(ALLOWED_OVERRIDES)}"
        )
    resolved = {
        "profile": canonical,
        "report_type": base["report_type"],
        "MAX_ITERATIONS": base["MAX_ITERATIONS"],
        "DEEP_RESEARCH_BREADTH": base["DEEP_RESEARCH_BREADTH"],
        "DEEP_RESEARCH_DEPTH": base["DEEP_RESEARCH_DEPTH"],
        "DEEP_RESEARCH_CONCURRENCY": DEFAULT_CONCURRENCY,
        "TOTAL_WORDS": base["TOTAL_WORDS"],
        "vast_max": base["vast_max"],
        "yt_live": base["yt_live"],
    }
    for key, value in ov.items():
        try:
            resolved[key] = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"override {key}={value!r} is not an integer"
            )
    if resolved["vast_max"] < 0 or resolved["yt_live"] < 0:
        raise ValueError("vast_max and yt_live must be >= 0")
    # Contract clamps: never exceed what the retriever enforces server-side.
    resolved["vast_max"] = min(resolved["vast_max"], VAST_MAX_RESULTS)
    resolved["yt_live"] = min(resolved["yt_live"], YT_LIVE_MAX)
    return resolved


def apply_profile(config_path: str | Path, resolved: dict) -> dict:
    """Write resolved numeric settings into config.json + export env caps.

    Must be called AFTER sync_config.sync() (which rewrites config.json at
    import). Only touches the five numeric keys the library reads from the
    config file; prompts and everything else are preserved byte-identical.
    vast_max/yt_live are exported as VAST_DOCS_CAP / VAST_YT_LIVE_CAP
    (intent + forward use; the retriever enforces 12/3 server-side).
    Returns the resolved dict unchanged.
    """
    path = Path(config_path)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("MAX_ITERATIONS", "DEEP_RESEARCH_BREADTH",
                "DEEP_RESEARCH_DEPTH", "DEEP_RESEARCH_CONCURRENCY",
                "TOTAL_WORDS"):
        cfg[key] = int(resolved[key])
    path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    os.environ["VAST_DOCS_CAP"] = str(int(resolved["vast_max"]))
    os.environ["VAST_YT_LIVE_CAP"] = str(int(resolved["yt_live"]))
    return resolved


def _item_url(item) -> str | None:
    if isinstance(item, dict):
        return item.get("url")
    if isinstance(item, str):
        return item
    return None


def _dedupe_urls(raw_urls) -> dict:
    """Normalize + dedupe; chunks of the same doc collapse to one entry.

    Malformed URLs (normalize_url -> None) are skipped.
    Returns {normalized_url: first_raw_url}.
    """
    ca = _citation_audit()
    out: dict[str, str] = {}
    for raw in raw_urls:
        if not isinstance(raw, str):
            continue
        norm = ca.normalize_url(raw)
        if norm is None:
            continue
        out.setdefault(norm, raw)
    return out


def _channel(norm_url: str) -> str:
    try:
        host = (urlsplit(norm_url).hostname or "").lower()
    except ValueError:
        return "web"
    if host.endswith(("youtube.com", "youtu.be", "music.youtube.com")):
        return "youtube"
    if host.endswith(("github.com", "gist.github.com",
                      "raw.githubusercontent.com")):
        return "github"
    if host.endswith(("bilibili.com", "b23.tv")):
        return "bilibili"
    if host.endswith("v2ex.com"):
        return "v2ex"
    if host.endswith(("arxiv.org", "export.arxiv.org")):
        return "arxiv"
    return "web"


def count_sources(discovered=(), with_content=(), used_in_analysis=(),
                   in_messages="", cited_report="", manifest=None) -> dict:
    """Count sources across pipeline stages, deduped by normalized URL.

    discovered/with_content/used_in_analysis: lists of dict (with 'url') or
      str. with_content is unioned with content-bearing manifest entries.
    in_messages: str (free text, URLs extracted) or list of dict|str.
    cited_report: final report text (references extracted via
      citation_audit.extract_references).
    manifest: citation_audit manifest dict (norm_url -> entry) or None.

    Returns {discovered, unique, with_content, used_in_analysis,
    in_messages, cited, by_channel}. Chunks of the same doc count once;
    malformed URLs are skipped.
    """
    ca = _citation_audit()
    disc = _dedupe_urls(_item_url(i) for i in (discovered or ()))
    cont = _dedupe_urls(_item_url(i) for i in (with_content or ()))
    if manifest:
        for norm, entry in manifest.items():
            if not isinstance(entry, dict) or not entry.get("content_bearing"):
                continue
            if ca.normalize_url(norm) is None:
                continue
            cont.setdefault(norm, entry.get("url", norm))
    used = _dedupe_urls(_item_url(i) for i in (used_in_analysis or ()))
    if isinstance(in_messages, str):
        msg_urls = _URL_RE.findall(in_messages)
    else:
        msg_urls = [_item_url(i) for i in (in_messages or ())]
    msgs = _dedupe_urls(msg_urls)
    cited = {}
    if isinstance(cited_report, str) and cited_report:
        refs = [r.get("url") for r in ca.extract_references(cited_report)]
        cited = _dedupe_urls(refs)
    union = set(disc) | set(cont) | set(used) | set(msgs) | set(cited)
    by_channel: dict[str, int] = {}
    for norm in union:
        by_channel[_channel(norm)] = by_channel.get(_channel(norm), 0) + 1
    return {
        "discovered": len(disc),
        "unique": len(union),
        "with_content": len(cont),
        "used_in_analysis": len(used),
        "in_messages": len(msgs),
        "cited": len(cited),
        "by_channel": by_channel,
    }


def decide_stop(aspects_covered: float = 0.0,
                novelty_last_rounds: float = 1.0,
                budget: dict | None = None,
                blocked: bool = False,
                gaps: list | None = None) -> dict:
    """Decide whether to stop investigating.

    aspects_covered: 0..1 fraction of question aspects covered.
    novelty_last_rounds: 0..1 fraction of new findings in recent rounds
      (low = rounds repeat what is known).
    budget: e.g. {time_used_s, time_budget_s, tokens_used, tokens_budget,
      rounds_used, rounds_budget}; zero/None/missing budget = unbounded.
    blocked: external block (source down, access denied, ...).
    gaps: remaining open questions list.

    Returns {stop, stop_reason, partial} with stop_reason in
    {coverage, novelty, budget, blocked, continue}. A simple question ends
    early even in deep (high coverage + low novelty -> stop). Budget
    exhausted with gaps, or a block with gaps, is an explicit partial.
    """
    gaps = list(gaps or [])
    budget = dict(budget or {})
    try:
        coverage = max(0.0, min(1.0, float(aspects_covered)))
    except (TypeError, ValueError):
        coverage = 0.0
    try:
        novelty = max(0.0, min(1.0, float(novelty_last_rounds)))
    except (TypeError, ValueError):
        novelty = 1.0

    if blocked:
        return {"stop": True, "stop_reason": "blocked",
                "partial": bool(gaps)}
    if coverage >= COVERAGE_DONE:
        return {"stop": True, "stop_reason": "coverage", "partial": False}
    for used_k, budget_k in (("time_used_s", "time_budget_s"),
                             ("tokens_used", "tokens_budget"),
                             ("rounds_used", "rounds_budget")):
        try:
            used = float(budget.get(used_k, 0) or 0)
            limit = float(budget.get(budget_k, 0) or 0)
        except (TypeError, ValueError):
            continue
        if limit > 0 and used >= limit:
            return {"stop": True, "stop_reason": "budget",
                    "partial": bool(gaps)}
    if novelty <= NOVELTY_FLOOR and coverage >= COVERAGE_OK:
        return {"stop": True, "stop_reason": "novelty", "partial": False}
    return {"stop": False, "stop_reason": "continue", "partial": False}


def carry_provenance(sections: list[dict]) -> list[dict]:
    """Carry source identity through intermediate synthesis.

    Each section keeps its url plus an evidence_type derived the same way
    citation_audit.build_manifest types content (transcript when [spoken i/M]
    labels or a [transcript header] are present, description when a
    [description] section is present, unknown otherwise) plus all original
    provenance fields. Never drops a section: even a section whose URL is
    malformed is kept with evidence_type best-effort typed.
    """
    carried: list[dict] = []
    for sec in (sections or []):
        if not isinstance(sec, dict):
            continue
        out = dict(sec)
        url = out.get("url", "")
        content = out.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        has_spoken = bool(re.search(r"\[spoken \d+/\d+\]", content))
        has_header = "[transcript" in content
        has_desc = "[description]" in content
        if has_spoken or has_header:
            evidence_type = "transcript"
        elif has_desc:
            evidence_type = "description"
        else:
            evidence_type = "unknown"
        out["url"] = url
        out["evidence_type"] = evidence_type
        out.setdefault("provenance", "")
        carried.append(out)
    return carried
