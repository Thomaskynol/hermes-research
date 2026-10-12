#!/usr/bin/env python3
"""Resumable checkpoints for a research run: persist what was already collected.

Problem it solves
-----------------
A deep run collected sources for ~10.5h and lost everything to a crash at the
end: the only artifact left was ``run.json``. Nothing in the run could be
reused, and a retry would have re-fetched every page from scratch.

What this provides
------------------
* ``Checkpoint`` — append-only JSONL per run holding the sources already
  obtained (url + evidence type + content hash, never the content itself:
  re-using a source means reading it from the vast cache, not duplicating a
  50 KB blob in a checkpoint).
* ``completed_queries`` — the queries already answered, so a resumed run does
  not repeat collection it has finished.
* ``resume_plan(ckpt, wanted_queries)`` — which queries still need running and
  which URLs are already available. Identity of sources is preserved (URL is
  the key), so a resumed run never re-collects what it has.

Durability: every append is ``flush`` + ``fsync``, so a hard kill mid-run
leaves a usable file rather than a truncated one.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

CHECKPOINT_NAME = "checkpoint.jsonl"


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:16]


class Checkpoint:
    """Append-only, crash-durable record of a run's collected work."""

    def __init__(self, run_dir: str | Path):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / CHECKPOINT_NAME
        self._lock = threading.Lock()

    def _append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())

    def note_query_done(self, query: str, n_sources: int = 0) -> None:
        self._append({"kind": "query_done", "query": query,
                      "n_sources": int(n_sources)})

    def note_source(self, url: str, *, source: str = "", title: str = "",
                    content: str = "", evidence_type: str = "",
                    chars: int | None = None) -> None:
        """Record that a source was obtained. Content is NOT stored — only its
        hash and size, so resume reads the real bytes from the vast cache."""
        self._append({
            "kind": "source",
            "url": url,
            "source": source,
            "title": title,
            "evidence_type": evidence_type,
            "chars": int(chars if chars is not None else len(content or "")),
            "content_hash": _content_hash(content or ""),
        })

    def note_learning(self, text: str) -> None:
        self._append({"kind": "learning", "text": text})

    # -- read side ---------------------------------------------------------
    def load(self) -> dict:
        """Return {sources, queries_done, learnings} from the JSONL.

        A truncated final line (hard kill mid-write) is skipped rather than
        raising: a checkpoint that survives a crash must also survive its own
        last partial write.
        """
        sources: dict[str, dict] = {}
        queries: list[str] = []
        learnings: list[str] = []
        if not self.path.exists():
            return {"sources": sources, "queries_done": queries,
                    "learnings": learnings}
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue  # partial last line after a crash
                kind = rec.get("kind")
                if kind == "source" and rec.get("url"):
                    sources[rec["url"]] = rec
                elif kind == "query_done" and rec.get("query"):
                    queries.append(rec["query"])
                elif kind == "learning" and rec.get("text"):
                    learnings.append(rec["text"])
        return {"sources": sources, "queries_done": queries,
                "learnings": learnings}


def resume_plan(ckpt: Checkpoint, wanted_queries) -> dict:
    """Decide what a resumed run must still do.

    Returns {already_have_urls, pending_queries, done_queries, learnings}.
    A query already recorded as done is NOT repeated; URLs already obtained are
    reported so the caller can reuse them (identity preserved by URL).
    """
    state = ckpt.load()
    done = set(state["queries_done"])
    pending = [q for q in (wanted_queries or []) if q not in done]
    return {
        "already_have_urls": sorted(state["sources"]),
        "pending_queries": pending,
        "done_queries": sorted(done),
        "learnings": state["learnings"],
    }
