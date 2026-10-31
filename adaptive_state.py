#!/usr/bin/env python3
"""Per-run adaptive state: atomic persistence + checkpoint reuse (stdlib only).

One run = one directory, one ``state.json`` written atomically (tmp+rename,
fsync) after every stage: request, applied config, plan + versions, evidence
+ segments, evaluations, round history, consumption, pending ops, stop motive.
``run_checkpoint.Checkpoint`` is reused between stages for crash-durable
collection records; an op interrupted mid-flight is reloaded as
``interrupted`` (explicit treatment, no exactly-once promise).

Runs/plans/configs never mix: load() verifies the run_id.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import research_counters as _counters

STATE_NAME = "state.json"


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_run_id(question: str) -> str:
    seed = f"{time.time_ns()}|{(question or '')[:200]}"
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + \
        hashlib.sha256(seed.encode()).hexdigest()[:6]


def new_state(question: str, run_id: str = "", mode: str = "adaptive",
              profile: str = "light", config: dict | None = None) -> dict:
    """Create the initial in-memory state (not yet persisted)."""
    return {
        "schema": 1,
        "run_id": run_id or new_run_id(question),
        "question": question,
        "mode": mode,
        "profile": profile,
        "created_at": _utcnow(),
        "config_applied": dict(config or {}),
        "plan": None,
        "plan_versions": [],  # [{version, plan_id, at, justification}]
        "plan_meta": {},
        "evidence": {},       # url -> concatenated usable text (segments kept)
        "segments": [],       # [{url, excerpt, sha, at, op_id, round}]
        "qualification": {},  # url -> qualification record
        "evaluations": [],
        "rounds": [],         # round history (see coordinator)
        "consumption": {"queries": 0, "docs": 0, "model_calls": 0,
                        "rounds": 0, "ops": 0, "fetches": 0},
        "pending_ops": [],    # [{op_id, kind, target, status, attempts, ...}]
        "attempts": {},       # criterion_id -> [{channel, outcome, at}]
        "discovery": {"candidates": [], "open": False},
        "gaps": [],
        "counters": _counters.default_counters(),
        "quantitative_specs": [],
        "quantitative": [],
        "verification": {},
        "manifest": {},
        "notes": [],
        "report": {},
        "semantic": {},
        "elapsed_s": 0.0,
        "stop": {"reason": None, "partial": None, "detail": ""},
    }


def _atomic_write(path: Path, payload: dict) -> None:
    """Write JSON atomically: tmp file + fsync + os.replace (no partial)."""
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1,
                            sort_keys=True))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def save(run_dir: str | Path, state: dict) -> Path:
    """Persist state atomically. Returns the state file path."""
    d = Path(run_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / STATE_NAME
    state["updated_at"] = _utcnow()
    _atomic_write(path, state)
    return path


def ensure_defaults(state: dict) -> dict:
    """Fill keys added after older runs (retrocompatible; never destructive)."""
    state.setdefault("gaps", [])
    state.setdefault("embeddings", {"calls": []})
    state.setdefault("quantitative_specs", [])
    state.setdefault("quantitative", [])
    state.setdefault("verification", {})
    state.setdefault("manifest", {})
    _counters.ensure(state)
    return state


def load(run_dir: str | Path, run_id: str | None = None) -> dict:
    """Reload state; verifies run identity; marks interrupted ops explicitly."""
    path = Path(run_dir) / STATE_NAME
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"[STATE] no state in {run_dir}: {exc}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"[STATE] truncated state in {run_dir}: {exc}")
    if not isinstance(state, dict) or "run_id" not in state:
        raise ValueError(f"[STATE] invalid state file in {run_dir}")
    if run_id is not None and state["run_id"] != run_id:
        raise ValueError(
            f"[STATE] run mismatch: file holds {state['run_id']!r}, "
            f"asked for {run_id!r} — runs never mix")
    ensure_defaults(state)
    touched = False
    for op in state.get("pending_ops", []):
        if op.get("status") == "in-progress":
            op["status"] = "interrupted"
            op["note"] = ("op was in-progress when the run stopped; "
                          "outcome unknown, safe to retry (no exactly-once)")
            touched = True
    if touched:
        state.setdefault("notes", []).append(
            f"{_utcnow()} resume: in-progress ops marked interrupted")
    return state


def _required_ids(plan: dict) -> set:
    """Required ids with default True (same default as coverage_ledger)."""
    ids = set()
    for coll in ("entities", "criteria"):
        for item in (plan or {}).get(coll, []) or []:
            if isinstance(item, dict) and item.get("required", True):
                ids.add((coll, item.get("id")))
    return ids


def record_plan_version(state: dict, plan: dict, justification: str) -> None:
    """Attach a plan (first or updated); user requirements never shrink.

    required defaults to True (consistent with coverage_ledger._required).
    Every version stores a snapshot (or delta) so earlier plans can be
    rebuilt: snapshot holds the full plan, required holds the mandatory
    ids, prev holds the previous version number.
    """
    import copy as _copy
    prev_ids = _required_ids(state.get("plan") or {}) if state.get("plan") else set()
    new_ids = _required_ids(plan)
    missing = prev_ids - new_ids
    if missing:
        raise ValueError(
            "[STATE] plan update would silently drop required items "
            f"{sorted(missing)} — user requirements never disappear silently")
    # Version must increase on update; adopt caller's version when it
    # moves forward, else bump.
    prev_v = 0
    if state.get("plan_versions"):
        try:
            prev_v = max(int(v.get("version", 0) or 0)
                         for v in state["plan_versions"])
        except (TypeError, ValueError):
            prev_v = len(state["plan_versions"])
    try:
        want_v = int(plan.get("version", 0) or 0)
    except (TypeError, ValueError):
        want_v = 0
    if state.get("plan") and want_v <= prev_v:
        want_v = prev_v + 1
        plan["version"] = want_v
    elif not state.get("plan") and not want_v:
        want_v = 1
        plan["version"] = want_v
    state["plan"] = plan
    state["plan_versions"].append({
        "version": plan.get("version", len(state["plan_versions"]) + 1),
        "plan_id": plan.get("plan_id"),
        "at": _utcnow(),
        "justification": justification,
        "required": sorted(new_ids),
        "snapshot": _copy.deepcopy(plan),
    })
