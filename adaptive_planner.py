#!/usr/bin/env python3
"""Adaptive planner: NL question -> validated coverage plan (offline-safe).

The plan describes the work EXPECTED, never its fulfilment. Validation reuses
``coverage_ledger.validate_plan`` (stable ids, non-empty entities/criteria,
``applies_to`` pointing at known entities, rejection of pre-satisfaction /
result fields). This module adds NOTHING semantic: it obtains a structured
candidate from an injectable model frontier, repairs it in a limited,
counted and logged way, and validates it. Any failure raises PlanError and
never becomes a fictitious valid plan.

Model frontier interface (injectable, offline-mockable):
  - a callable ``model_client(prompt) -> str`` returning the raw text, or
  - an object with ``.generate(prompt) -> str``.

No network, no library imports here: stdlib only.
"""
from __future__ import annotations

import hashlib
import json

import coverage_ledger as _ledger

PLAN_SCHEMA_VERSION = 1
MAX_REPAIRS = 1  # limited repair: strip fences, then at most one re-ask


class PlanError(ValueError):
    """Raised when no valid plan can be produced (never a fictitious plan)."""


def _call_model(model_client, prompt: str) -> tuple[str, int]:
    """Invoke the frontier once. Returns (raw_text, 1 call)."""
    if callable(model_client):
        return str(model_client(prompt)), 1
    generate = getattr(model_client, "generate", None)
    if callable(generate):
        return str(generate(prompt)), 1
    raise PlanError("[PLAN] model_client must be callable or expose .generate()")


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    return t


def _coerce_json(raw: str) -> dict:
    """Parse raw model text into a dict (fences tolerated once)."""
    try:
        obj = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, TypeError) as exc:
        raise PlanError(f"[PLAN] model output is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        raise PlanError("[PLAN] model output must be a JSON object (the plan)")
    return obj


def build_plan_prompt(question: str, purpose: str = "",
                      constraints: dict | None = None) -> str:
    """Generic planning prompt. No fixture/actor names: the model discovers."""
    hints = ""
    if constraints:
        try:
            hints = f"\nRestrictions/premises (must be preserved in the plan): {json.dumps(constraints, ensure_ascii=False)[:1000]}"
        except (TypeError, ValueError):
            hints = ""
    return (
        "You plan a research investigation. Return ONLY a JSON object.\n"
        f"Question: {question}\n"
        f"Purpose: {purpose or 'answer the question with verifiable evidence'}{hints}\n"
        "Required JSON shape:\n"
        '{"plan_id": "short-slug", "version": 1, '
        '"question": "<the question verbatim>", '
        '"purpose": "<what the answer will be used for>", '
        '"entities": [{"id": "e1", "label": "...", "required": true}], '
        '"criteria": [{"id": "c1", "label": "...", "required": true, '
        '"applies_to": ["e1"]}], '
        '"open_discovery": {"needed": true/false, "need": "..."}, '
        '"initial_paths": ["..."], "restrictions": "...", "premises": ["..."]}\n'
        "Rules: every user requirement must appear as a required entity or "
        "criterion (nothing may disappear silently); named entities are tracked "
        "individually; open-ended requests set open_discovery.needed=true and "
        "must NOT invent candidate names; criteria that apply only to some "
        "entities list them in applies_to (omit applies_to when global)."
    )


def generate_plan(question: str, model_client, purpose: str = "",
                  constraints: dict | None = None) -> tuple[dict, dict]:
    """Generate + validate a plan. Returns (plan, meta).

    meta = {repairs, repair_log, prompt_sha, model_calls}. Raises PlanError
    when the frontier output cannot be repaired into a valid plan.
    """
    if not (question or "").strip():
        raise PlanError("[PLAN] empty question cannot produce a plan")
    prompt = build_plan_prompt(question, purpose, constraints)
    meta = {"repairs": 0, "repair_log": [],
            "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "model_calls": 0}
    raw, n = _call_model(model_client, prompt)
    meta["model_calls"] += n
    try:
        candidate = _coerce_json(raw)
    except PlanError as first:
        if MAX_REPAIRS < 1:
            raise
        meta["repairs"] += 1
        meta["repair_log"].append(f"parse-failed: {first}; re-asked for JSON only")
        raw2, n2 = _call_model(model_client, prompt + "\nReturn ONLY the JSON object.")
        meta["model_calls"] += n2
        candidate = _coerce_json(raw2)  # raises PlanError when still invalid
    candidate.setdefault("question", question.strip())
    if purpose and not candidate.get("purpose"):
        candidate["purpose"] = purpose
    try:
        plan = _ledger.validate_plan(candidate)
    except ValueError as exc:
        raise PlanError(f"[PLAN] frontier plan invalid: {exc}")
    if not str(plan.get("question", "")).strip():
        raise PlanError("[PLAN] frontier plan dropped the question")
    plan.setdefault("schema_version", PLAN_SCHEMA_VERSION)
    return plan, meta


def plan_from_explicit(source: str | dict) -> tuple[dict, dict]:
    """Use an explicit user plan (--coverage-plan). Validated, never completed."""
    if isinstance(source, dict):
        plan = _ledger.validate_plan(dict(source))
    else:
        plan = _ledger.load_coverage_plan(source)
    meta = {"repairs": 0, "repair_log": ["explicit plan, no model involved"],
            "model_calls": 0}
    plan.setdefault("schema_version", PLAN_SCHEMA_VERSION)
    return plan, meta
