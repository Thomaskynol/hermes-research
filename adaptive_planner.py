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
import re

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
        '"candidate_target": 5, '
        '"initial_paths": ["..."], "restrictions": "...", "premises": ["..."]}\n'
        "Rules: every user requirement must appear as a required entity or "
        "criterion (nothing may disappear silently); named entities are tracked "
        "individually; open-ended requests set open_discovery.needed=true and "
        "must NOT invent candidate names; criteria that apply only to some "
        "entities list them in applies_to (omit applies_to when global).\n"
        "candidate_target is how many candidates the question asks to compare "
        "(integer, e.g. 'five plugins' -> 5; 5 when the question names no "
        "count): discovery beyond it stays tracked but out of coverage.\n"
        "Criteria that must hold for EACH discovered candidate (features, "
        "dependencies, costs, maintenance, limitations, compatibility) declare "
        "\"per_candidate\": true and omit applies_to until the candidates are "
        "known: every discovered candidate is added to them automatically. "
        "Synthesis criteria (combinations, overlaps, source recency, "
        "documented vs inferred) stay global (no per_candidate). Criteria "
        "about the FORM of the answer itself (e.g. 'separate documented "
        "features from inferences') declare \"synthesis\": true: they are "
        "assessed against the delivered synthesis text (separation markers "
        "plus real corpus citations, partial at most), never against "
        "excerpts.\n"
        "Entity labels: use the EXACT name of the product/repo/plugin (e.g. "
        "'opencode-planner'), exactly as it appears in the source. Never a "
        "description, never a sentence, never 'owner repo' glued together. "
        "If the exact name is unknown, use the name as it appears in the "
        "source; never invent a name.\n"
        "Entities must be concrete things NAMED in the question or in the "
        "provided context. Never create placeholder entities for items still "
        "to be discovered ('candidate 1', 'unknown', 'to be discovered'): a "
        "discovery obligation is a criterion (e.g. 'identify N candidates'), "
        "and criteria about the discovered set omit applies_to (global).\n"
        "initial_paths are short web search queries (2-6 words), never local "
        "file paths; include at least one query aimed at the discovery need. "
        "Nem todo candidato precisa cobrir todo eixo: a cobertura é "
        "avaliada por célula (critério × candidato); quando o escopo "
        "documentado do candidato exclui o eixo, a célula pode ser marcada "
        "not_applicable com justificativa que cite a evidência "
        "delimitadora de escopo. Mantenha per_candidate, candidate_target "
        "e a proibição de placeholders."
    )


def is_placeholder_label(label) -> bool:
    """True when a label names something still to be discovered.

    accept7: the planner emitted entities like 'plugin candidato 1 (nome a
    descobrir via discovery)'; criteria applied to them, so 50 cells could
    never be covered and their wording leaked into search queries. A
    discovery obligation is a criterion, never a placeholder entity.
    """
    t = str(label or "").strip().lower()
    if not t:
        return False
    if "?" in t:
        return True
    return any(m in t for m in (
        "a descobrir", "nome a descobrir", "a definir",
        "to be discovered", "to discover", "unknown", "tbd"))


def normalize_entity_label(label, source_url: str = "") -> str:
    """Return the entity's exact name from a possibly composite label.

    Discovery can join owner + repo or wrap the name in a sentence
    (accept11: 'dzianisv plugin-testing'). Callers that know the entity's
    source_url should pass it: the repo of a github.com URL is authoritative
    when the label carries owner and repo. A plain name ('Plannotator') is
    returned untouched. This never invents a name — it only extracts the one
    already present in the label/source.
    """
    original = str(label or "").strip()
    m = re.match(r"https?://(?:www\.)?github\.com/([^/?#\s]+)/([^/?#\s]+)",
                 str(source_url or "").strip(), re.IGNORECASE)
    repo = m.group(2) if m else ""
    if repo.endswith(".git"):
        repo = repo[:-4]
    if repo:
        owner = m.group(1)
        tokens = re.findall(r"[A-Za-z0-9._-]+", original.lower())
        if repo.lower() in tokens and owner.lower() in tokens:
            return repo
    if re.fullmatch(r"[^\s/]+/[^\s/]+", original):
        return original.split("/", 1)[1]
    if len(original.split()) > 6:
        compounds = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*",
                                            original)
                     if "-" in t or "_" in t]
        if compounds:
            candidate = compounds[-1].strip("._-")
            if candidate:
                return candidate
    return original or repo


def drop_placeholder_entities(plan: dict, meta: dict) -> dict:
    """Remove placeholder entities; rewrite applies_to; keep the plan valid.

    Never drops the last entity (a plan without entities is invalid): in
    that case the plan is left untouched and the issue is noted.
    """
    entities = [e for e in plan.get("entities") or [] if isinstance(e, dict)]
    keep, dropped = [], []
    for e in entities:
        (dropped if is_placeholder_label(e.get("label") or e.get("id"))
         else keep).append(e)
    if not dropped or not keep:
        if dropped:
            meta["repair_log"].append(
                "placeholder entities kept: dropping all would leave no "
                "entity")
        return plan
    drop_ids = {e.get("id") for e in dropped}
    candidate = dict(plan)
    candidate["entities"] = keep
    criteria = []
    for c in plan.get("criteria") or []:
        if not isinstance(c, dict):
            criteria.append(c)
            continue
        applies = c.get("applies_to")
        if applies:
            seq = [applies] if isinstance(applies, str) else list(applies)
            rest = [x for x in seq if x not in drop_ids]
            c = dict(c)
            if rest:
                c["applies_to"] = rest
            else:
                c.pop("applies_to", None)
        criteria.append(c)
    candidate["criteria"] = criteria
    try:
        candidate = _ledger.validate_plan(candidate)
    except ValueError as exc:
        meta["repair_log"].append(
            f"placeholder drop skipped (plan invalid afterwards): {exc}")
        return plan
    meta["repairs"] = meta.get("repairs", 0) + 1
    meta["repair_log"].append(
        "dropped placeholder entities (discovery obligation stays a "
        "criterion): " + ", ".join(str(e.get("id")) for e in dropped))
    return candidate


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
    plan = drop_placeholder_entities(plan, meta)
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
