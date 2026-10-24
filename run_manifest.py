#!/usr/bin/env python3
"""Run manifest: what executed, with which config/code/models/artifacts.

Honesty rules (modelagem §14):
* simulated/offline runs are explicitly marked (``simulated: true``) — never
  presented as real network/model operations;
* models are recorded by DECLARED NAME only; credential-like keys are redacted;
* unmeasured tokens/costs stay ``"unknown"``, never 0;
* own-module hashes make the executed code identifiable.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

OWN_MODULES = (
    "adaptive_coordinator.py", "adaptive_state.py", "adaptive_planner.py",
    "coverage_ledger.py", "research_counters.py", "quantitative.py",
    "report_renderer.py", "verification_report.py", "run_manifest.py",
    "depth_profiles.py", "run_budget.py", "semantic_review.py",
    "gpt_researcher_integration.py", "agent_reach.py", "academic_search.py",
)

_SECRET_HINTS = ("key", "token", "secret", "password", "authorization",
                 "credential", "cookie")


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _module_path(name: str) -> Path | None:
    module = sys.modules.get(name.removesuffix(".py"))
    if module is not None and getattr(module, "__file__", None):
        return Path(module.__file__)
    candidate = Path(__file__).resolve().parent / name
    return candidate if candidate.is_file() else None


def module_hashes() -> dict:
    """sha256 of each own module actually present (missing ones are omitted)."""
    hashes = {}
    for name in OWN_MODULES:
        path = _module_path(name)
        if path is None or not path.is_file():
            continue
        try:
            hashes[name] = _sha256_bytes(path.read_bytes())
        except OSError:
            continue
    return hashes


def _sanitize(value):
    """Recursively redact credential-like keys; values stay as declared names."""
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if any(hint in str(key).lower() for hint in _SECRET_HINTS):
                clean[key] = "[redacted]"
            else:
                clean[key] = _sanitize(item)
        return clean
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _models(model_info) -> dict:
    if model_info is None:
        return {"declared": "unknown"}
    if isinstance(model_info, str):
        return {"declared": model_info or "unknown"}
    if isinstance(model_info, dict):
        return _sanitize(model_info)
    return {"declared": str(model_info)}


def _artifacts(run_dir: Path, artifacts) -> list[dict]:
    if not artifacts:
        return []
    items = []
    if isinstance(artifacts, dict):
        pairs = list(artifacts.items())
    else:
        pairs = [(Path(str(a)).name, a) for a in artifacts]
    for name, raw_path in pairs:
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = run_dir / path
        entry = {"name": str(name), "path": str(path)}
        try:
            data = path.read_bytes()
            entry["sha256"] = _sha256_bytes(data)
            entry["bytes"] = len(data)
            entry["exists"] = True
        except OSError:
            entry["exists"] = False
        items.append(entry)
    return items


def _consumption(state: dict) -> dict:
    consumption = dict(state.get("consumption") or {})
    for key in ("tokens", "cost_usd"):
        if consumption.get(key) in (None, 0, 0.0):
            # Not measured on this path: unknown, never a fake zero.
            consumption[key] = "unknown"
    consumption.setdefault("tokens", "unknown")
    consumption.setdefault("cost_usd", "unknown")
    return consumption


def build_manifest(run_dir, state: dict, *, resolved: dict,
                   model_info=None, environment: dict | None = None,
                   artifacts=None) -> dict:
    """Build the manifest dict (also used by tests without writing)."""
    env = dict(environment or {})
    if "simulated" not in env or not isinstance(env["simulated"], bool):
        raise ValueError("[MANIFEST] environment must declare simulated: "
                         "true|false (offline runs are marked, never hidden)")
    directory = Path(run_dir)
    return {
        "run_id": state.get("run_id", ""),
        "question": state.get("question", ""),
        "mode": state.get("mode", "adaptive"),
        "profile": state.get("profile", ""),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "generated_at": _utcnow(),
        "simulated": env["simulated"],
        "config_applied": dict(state.get("config_applied") or {}),
        "resolved": dict(resolved or {}),
        "models": _models(model_info),
        "environment": {**_sanitize(env),
                        "simulated": env["simulated"],
                        "python": sys.version.split()[0]},
        "module_hashes": module_hashes(),
        "artifacts": _artifacts(directory, artifacts),
        "consumption": _consumption(state),
        "stop": dict(state.get("stop") or {}),
        "counters": (state.get("counters") or {}).get("counts", "unknown"),
        "cwd": os.getcwd(),
    }


def write_manifest(run_dir, state: dict, *, resolved: dict,
                   model_info=None, environment: dict | None = None,
                   artifacts=None) -> Path:
    """Write manifest.json atomically; returns its path."""
    directory = Path(run_dir)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(directory, state, resolved=resolved,
                              model_info=model_info, environment=environment,
                              artifacts=artifacts)
    path = directory / "manifest.json"
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1,
                            sort_keys=True))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path
