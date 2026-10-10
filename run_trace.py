#!/usr/bin/env python3
"""Opt-in per-run trace artifacts for the Deep Research pipeline.

Enabled ONLY when the `RUN_TRACE_DIR` env var points at a directory
(default `./runs` under the workdir when set to `1`, explicit path
otherwise). Unset/empty = tracing off, behavior byte-identical.

What it records (see `new_run` / `RunTracer`):
  run.json, retrievers.json, corpus_collected.json, corpus_selected.json,
  selection.json, context.json, report.md, stats.json

What it does NOT record (limitation, not an oversight):
  the chunk stages inside site-packages — EmbeddingsFilter
  (context/compression.py:135, k defaults to 20 from langchain_classic),
  max_results=10 (skills/context_manager.py:63), generation-time context
  assembly, and the searx/duckduckgo/arxiv retrievers (they run inside the
  library; only our `custom` retriever's vast side is wrapped here).
  Those stages are marked "not_instrumented" in stats.json with file:line
  reasons instead of being simulated.
"""

import functools
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKDIR = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(WORKDIR))

RUNS_ENV = "RUN_TRACE_DIR"


def new_run_id(query: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in query[:30]).strip("_")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slug or 'run'}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def component_versions() -> dict:
    versions = {"python": sys.version.split()[0]}
    try:
        from importlib.metadata import version as pkg_version
        versions["gpt_researcher"] = pkg_version("gpt-researcher")
    except Exception as exc:  # not installed as a dist? record, don't crash
        versions["gpt_researcher"] = f"unknown ({type(exc).__name__})"
    for name in ("vast_local_retriever.py", "run_research.py",
                 "retriever_timeout.py", "reasoning_effort.py",
                 "sync_config.py"):
        p = WORKDIR / name
        versions[f"sha256:{name}"] = _sha256_file(p) if p.exists() else "missing"
    return versions


def sanitize_config(cfg: dict) -> dict:
    """Drop anything shaped like a credential; keep model/threshold/routing keys."""
    out = {}
    for key, value in cfg.items():
        kl = key.lower()
        if any(t in kl for t in ("key", "token", "secret", "password", "cookie")):
            out[key] = "<redacted>"
        else:
            out[key] = value
    return out


class RunTracer:
    def __init__(self, query: str, depth: str, root: str | Path):
        self.run_id = new_run_id(query)
        self.root = Path(root) if str(root) not in ("1", "true") else WORKDIR / "runs"
        self.dir = self.root / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.write("run.json", {
            "run_id": self.run_id,
            "started_at_utc": _utcnow(),
            "query": query,
            "depth": depth,
            "config_sanitized": sanitize_config(self._read_config()),
            "components": component_versions(),
        })

    def _read_config(self) -> dict:
        try:
            return json.loads((WORKDIR / "config.json").read_text())
        except OSError:
            return {"config.json": "unreadable"}

    def write(self, name: str, obj) -> Path:
        path = self.dir / name
        if isinstance(obj, str):
            path.write_text(obj, encoding="utf-8")
        else:
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        return path

    def record(self, name: str, obj) -> Path:
        return self.write(name, obj)


def doc_id(source: str, url: str) -> str:
    return f"{source}:{hashlib.sha1(url.encode()).hexdigest()[:12]}"


def hit_to_record(hit, verdict: str | None = None) -> dict:
    rec = {
        "doc_id": doc_id(getattr(hit, "source", "?"), getattr(hit, "url", "")),
        "source": getattr(hit, "source", ""),
        "url": getattr(hit, "url", ""),
        "title": getattr(hit, "title", ""),
        "chars": len(getattr(hit, "raw_content", "") or ""),
        "raw_content": getattr(hit, "raw_content", "") or "",
    }
    if verdict is not None:
        rec["selection_verdict"] = verdict
    return rec


def install_probe_wrapping(tracer: RunTracer):
    """Wrap OUR probe functions so per-retriever outcomes are logged.

    Runtime-only rebinding of `vast_local_retriever.SOURCE_PROBES` (same
    reversible pattern as reasoning_effort.py). Delegates to the real
    functions; output is unchanged, only observed. Returns an uninstall
    callable. Never touches site-packages: the searx/duckduckgo/arxiv
    retrievers run inside the library and are NOT covered — see module
    docstring.
    """
    import asyncio
    import vast_local_retriever as vast

    originals = dict(vast.SOURCE_PROBES)
    outcomes: list[dict] = []

    def make_wrapper(name, fn):
        @functools.wraps(fn)
        async def wrapper(query):
            started = time.monotonic()
            try:
                hits = await fn(query)
                outcomes.append({
                    "retriever": "custom", "probe": name,
                    "status": "ok", "count": len(hits),
                    "elapsed_s": round(time.monotonic() - started, 2),
                    "urls": [h.url for h in hits],
                })
                return hits
            except Exception as exc:
                outcomes.append({
                    "retriever": "custom", "probe": name,
                    "status": f"error:{type(exc).__name__}",
                    "detail": str(exc)[:300],
                    "elapsed_s": round(time.monotonic() - started, 2),
                    "urls": [],
                })
                raise
        return wrapper

    for name, fn in originals.items():
        vast.SOURCE_PROBES[name] = make_wrapper(name, fn)

    def uninstall():
        for name, fn in originals.items():
            vast.SOURCE_PROBES[name] = fn
        tracer.write("retrievers.json", {
            "note": "vast-side probes only; searx/duckduckgo/arxiv run "
                    "inside site-packages (see module docstring).",
            "outcomes": outcomes,
        })

    return uninstall


def trace_select_hits(tracer: RunTracer, hits: list) -> list:
    """Snapshot corpus before/after the REAL _select_hits; log verdicts."""
    import vast_local_retriever as vast

    before = [hit_to_record(h) for h in hits]
    tracer.write("corpus_collected.json", {
        "count": len(before), "items": before,
    })
    selected = vast._select_hits(hits)
    kept_ids = {id(h) for h in selected}
    seen: set[str] = set()
    verdicts: list[dict] = []
    for h in hits:
        if not h.url or h.url in seen:
            verdict = "dropped_dupe"
        elif id(h) in kept_ids:
            verdict = "kept"
        else:
            verdict = "dropped_cut"
        if h.url and h.url not in seen:
            seen.add(h.url)
        verdicts.append({"doc_id": doc_id(h.source, h.url),
                         "url": h.url, "verdict": verdict})
    tracer.write("corpus_selected.json", {
        "count": len(selected),
        "items": [hit_to_record(h, "kept") for h in selected],
    })
    tracer.write("selection.json", {
        "selector": "vast_local_retriever._select_hits "
                    "(dedup by URL, cut at MAX_RESULTS, no scoring)",
        "kept_count": len(selected),
        "verdicts": verdicts,
    })
    return selected
