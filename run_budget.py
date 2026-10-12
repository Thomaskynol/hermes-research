#!/usr/bin/env python3
"""Global per-run budget shared across rounds, branches and concurrent requests.

Why this exists
---------------
The per-request caps in ``vast_local_retriever.py`` (``max_results``,
``yt_live``) bound ONE call. A deep run makes dozens of calls across rounds and
parallel branches, so the caps alone cannot stop a runaway run: measured, a
``deep`` run issued queries for ~10.5h with no aggregate ceiling. This module
adds the missing aggregate ceiling.

Design
------
* One ``Budget`` object per run, created by the entry point from the resolved
  depth profile and installed process-wide (``install``). The vast retriever —
  which runs in the SAME process as the research when started via
  ``vast_local_retriever.__main__`` for the integration tests, and as a separate
  service otherwise — reads it through the HTTP surface (query params carry the
  remaining allowance) or directly (``get()``).
* Counters are monotonic and thread/async-safe (``threading.Lock``): a single
  lock around increments keeps concurrent branches from double-spending.
* ``exhausted()`` names WHICH limit tripped, so the stop reason is explicit
  (``budget:queries``), never a bare "coverage".
* Every counter is observable (``snapshot()``), so a run can record what it
  consumed rather than guess.

Not measured here: token/cost. The library exposes no per-call attribution on
this path (verified: ``researcher.costs`` raises AttributeError), so those
limits stay declared-but-unenforced — ``snapshot`` reports them as
``unenforced`` instead of pretending.
"""
from __future__ import annotations

import os
import threading
import time

# Profile -> default ceilings. 0 means "unbounded".
DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "light": {"time_s": 600, "queries": 12, "unique_sources": 60,
              "extractions": 40, "yt_live_fetches": 4},
    "medium": {"time_s": 1800, "queries": 30, "unique_sources": 150,
               "extractions": 120, "yt_live_fetches": 8},
    "hard": {"time_s": 3600, "queries": 60, "unique_sources": 300,
             "extractions": 250, "yt_live_fetches": 12},
    "deep": {"time_s": 7200, "queries": 120, "unique_sources": 600,
             "extractions": 500, "yt_live_fetches": 20},
}

_LOCK = threading.Lock()
_CURRENT: "Budget | None" = None


class Budget:
    """Aggregate allowance for one run, shared by every branch."""

    def __init__(self, limits: dict | None = None, *, profile: str = ""):
        self.profile = profile
        lim = dict(DEFAULT_LIMITS.get(profile, {}))
        for k, v in (limits or {}).items():
            if k in ("time_s", "queries", "unique_sources", "extractions",
                     "yt_live_fetches"):
                lim[k] = int(v)
        self.limits = lim
        self._used = {k: 0 for k in lim}
        self._start = time.monotonic()
        self._lock = threading.Lock()
        self.stopped_reason: str | None = None

    # -- consumption -------------------------------------------------------
    def spend(self, counter: str, n: int = 1) -> bool:
        """Try to spend n units of ``counter``.

        Returns True if the spend was allowed (within the limit), False if it
        would exceed it. A refused spend does NOT consume: the caller must
        stop that work and let the run finish with what it already has.
        """
        with self._lock:
            if counter not in self._used:
                return True
            limit = self.limits.get(counter, 0)
            if limit and self._used[counter] + n > limit:
                if self.stopped_reason is None:
                    self.stopped_reason = f"budget:{counter}"
                return False
            self._used[counter] += n
            return True

    def note_unique_sources(self, count: int) -> None:
        """Set (not add) the unique-source watermark; dedupe happens upstream."""
        with self._lock:
            if count > self._used.get("unique_sources", 0):
                self._used["unique_sources"] = count

    def elapsed(self) -> float:
        return time.monotonic() - self._start

    # -- queries -----------------------------------------------------------
    def exhausted(self) -> str | None:
        """Name the tripped limit, or None. Time is checked live."""
        with self._lock:
            if self.stopped_reason:
                return self.stopped_reason
            for k, used in self._used.items():
                limit = self.limits.get(k, 0)
                if limit and used >= limit:
                    return f"budget:{k}"
            tlimit = self.limits.get("time_s", 0)
            if tlimit and self.elapsed() >= tlimit:
                return "budget:time_s"
        return None

    def remaining(self, counter: str) -> int:
        """Units left for ``counter`` (large sentinel when unbounded)."""
        with self._lock:
            limit = self.limits.get(counter, 0)
            if not limit:
                return 10**9
            return max(0, limit - self._used.get(counter, 0))

    def snapshot(self) -> dict:
        with self._lock:
            used = dict(self._used)
        snap = {
            "profile": self.profile,
            "limits": dict(self.limits),
            "used": used,
            "elapsed_s": round(self.elapsed(), 1),
            "stop_reason": self.exhausted(),
            "unenforced": ["tokens", "cost_usd"],
        }
        return snap


def install(profile: str, limits: dict | None = None) -> Budget:
    """Create + install the run budget. Idempotent per process."""
    global _CURRENT
    b = Budget(limits, profile=profile)
    with _LOCK:
        _CURRENT = b
    os.environ["RUN_BUDGET_PROFILE"] = profile
    return b


def get() -> "Budget | None":
    return _CURRENT


def snapshot() -> dict:
    b = _CURRENT
    return b.snapshot() if b else {"profile": None, "limits": {}, "used": {},
                                   "elapsed_s": 0.0, "stop_reason": None,
                                   "unenforced": ["tokens", "cost_usd"]}


def reset() -> None:
    """Test helper: drop the installed budget."""
    global _CURRENT
    with _LOCK:
        _CURRENT = None
