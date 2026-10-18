#!/usr/bin/env python3
"""Question coverage ledger (first increment).

Separates QUESTION coverage from SEMANTIC approval:

- semantic_review.py answers "does the report say what the evidence says?"
  (fields ``coverage_complete`` / ``dropped_incomplete`` there are about
  claim extraction, and are preserved untouched).
- this module answers "was everything the QUESTION asked about actually
  investigated, and where is the usable evidence for each point?".

A semantic approval NEVER implies question coverage: a report can be fully
sustained by its citations while leaving mandatory sub-questions
uninvestigated. The two dimensions are recorded side by side, never merged.

Rules enforced here (structure only — never semantic truth):

- URL / mention / raw text is NOT coverage. Six entities with documents does
  NOT cover criteria: ``covered`` requires an explicit evaluation traceable
  to usable evidence (approved qualification, not excluded).
- A nonexistent reference, or evidence the qualification excluded, cannot
  cover (attempting it raises instead of silently recording).
- ``partial`` only sustains its own scope; it never counts as covered.
- Access failure is NOT absence: it maps to ``blocked``, never to a
  negative conclusion.
- A well-sustained NEGATIVE conclusion (``origin="negative_conclusion"``
  with usable references showing the absence) CAN cover.
- The ledger validates structure (stable ids, states, justification +
  origin + resolvable references). It never claims semantic truth.

No network, no model calls, stdlib only.
"""
from __future__ import annotations

import json
from pathlib import Path

STATES = ("uninvestigated", "insufficient", "partial",
          "covered", "contradictory", "blocked")

#: Pipeline stages tracked as observed counts (never inferred).
STAGES = ("discovered", "obtained", "qualified",
          "analyzed", "used", "cited")

#: Keys that would declare fulfilment in advance. A plan describes the work
#: EXPECTED, never its completion — any of these anywhere in a plan rejects it.
_PRE_SATISFIED_KEYS = frozenset({
    "pre_satisfied", "presatisfied", "pre-satisfied",
    "pre_completed", "precompleted", "pre-completed",
    "already_satisfied", "already-covered", "already_covered",
    "already_satisfied", "satisfied",
})

#: Result fields that do not belong in a plan (they are computed, not asked).
_RESULT_KEYS = frozenset({
    "status", "complete", "proportion", "question_coverage",
})


def _norm_key(key: str) -> str:
    return str(key).strip().lower().replace("-", "_")


def _reject_pre_satisfied(node, where: str = "plan") -> None:
    """Recursively reject any pre-satisfaction declaration in a plan."""
    if isinstance(node, dict):
        for key, value in node.items():
            nk = _norm_key(key)
            if nk in _PRE_SATISFIED_KEYS:
                raise ValueError(
                    f"[COVERAGE] plan rejected: {where} declares {key!r} — "
                    "a plan describes expected work, never fulfilment")
            if where == "plan" and nk in _RESULT_KEYS:
                raise ValueError(
                    f"[COVERAGE] plan rejected: {where} contains result "
                    f"field {key!r} — status/complete/proportion are computed")
            _reject_pre_satisfied(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _reject_pre_satisfied(item, f"{where}[{i}]")


def validate_plan(plan: dict) -> dict:
    """Validate a coverage plan dict. Returns it unchanged. Raises ValueError."""
    if not isinstance(plan, dict):
        raise ValueError("[COVERAGE] plan must be a JSON object")
    _reject_pre_satisfied(plan)
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id.strip():
        raise ValueError("[COVERAGE] plan needs a non-empty 'plan_id'")
    entities = plan.get("entities")
    criteria = plan.get("criteria")
    if not isinstance(entities, list) or not entities:
        raise ValueError("[COVERAGE] plan needs a non-empty 'entities' list")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("[COVERAGE] plan needs a non-empty 'criteria' list")
    seen_e, seen_c = set(), set()
    for e in entities:
        if not isinstance(e, dict):
            raise ValueError("[COVERAGE] each entity must be an object")
        eid = e.get("id")
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError("[COVERAGE] each entity needs a stable non-empty 'id'")
        if eid in seen_e:
            raise ValueError(f"[COVERAGE] duplicate entity id {eid!r}")
        seen_e.add(eid)
    for c in criteria:
        if not isinstance(c, dict):
            raise ValueError("[COVERAGE] each criterion must be an object")
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("[COVERAGE] each criterion needs a stable non-empty 'id'")
        if cid in seen_c:
            raise ValueError(f"[COVERAGE] duplicate criterion id {cid!r}")
        seen_c.add(cid)
        applies = c.get("applies_to", None)
        if applies is not None:
            if not isinstance(applies, list) or not applies:
                raise ValueError(
                    f"[COVERAGE] criterion {cid!r}: 'applies_to' must be a "
                    "non-empty entity-id list or be omitted")
            for eid in applies:
                if eid not in seen_e:
                    raise ValueError(
                        f"[COVERAGE] criterion {cid!r} applies to "
                        f"unknown entity {eid!r}")
    return plan


def load_coverage_plan(source: str) -> dict:
    """Load a plan from a JSON file path or an inline JSON string.

    Raises ValueError on unreadable/invalid content or pre-satisfaction.
    """
    raw = None
    candidate = Path(source)
    if candidate.is_file():
        raw = candidate.read_text(encoding="utf-8")
    else:
        raw = source
    try:
        plan = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"[COVERAGE] plan is not valid JSON: {exc}")
    return validate_plan(plan)


def parse_coverage_cli(args: list[str]) -> tuple[str, str, str | None]:
    """Parse ``query [depth] [--coverage-plan <json|path>]`` retro-compatibly.

    Returns (query, depth, plan_source|None). Raises ValueError on misuse.
    """
    query, depth, plan_source = None, "light", None
    positional: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--coverage-plan":
            if plan_source is not None:
                raise ValueError("[COVERAGE] duplicate --coverage-plan")
            if i + 1 >= len(args):
                raise ValueError("[COVERAGE] --coverage-plan needs a value")
            plan_source = args[i + 1]
            i += 2
        elif tok.startswith("--coverage-plan="):
            if plan_source is not None:
                raise ValueError("[COVERAGE] duplicate --coverage-plan")
            plan_source = tok.split("=", 1)[1]
            if not plan_source:
                raise ValueError("[COVERAGE] --coverage-plan needs a value")
            i += 1
        elif tok.startswith("--"):
            raise ValueError(f"[COVERAGE] unknown flag {tok!r}")
        else:
            positional.append(tok)
            i += 1
    if not positional:
        raise ValueError("[COVERAGE] missing query")
    query = positional[0]
    if len(positional) > 1:
        depth = positional[1]
    if len(positional) > 2:
        raise ValueError("[COVERAGE] too many positional args "
                         "(expected: query [depth])")
    return query, depth, plan_source


def empty_question_coverage(run_id: str = "") -> dict:
    """Unevaluated block used when no plan was given.

    No heuristics: proportion is None (not 0.0), nothing is declared.
    """
    return {
        "status": "unevaluated",
        "complete": False,
        "plan_id": None,
        "plan_version": None,
        "run_id": run_id or "",
        "proportion": None,
        "criteria": [],
        "gaps": [],
        "references": [],
        "observed_counts": {stage: 0 for stage in STAGES},
        "note": ("sem plano de cobertura: pergunta não avaliada; "
                 "nenhuma heurística aplicada"),
    }


def summarize(block: dict) -> str:
    """One-line user-facing summary with a pointer to the audited text."""
    status = block.get("status", "unevaluated")
    label = {"covered": "coberta", "partial": "parcial",
             "unevaluated": "não avaliada"}.get(status, status)
    prop = block.get("proportion")
    prop_s = "null" if prop is None else f"{prop:.2f}"
    gaps = block.get("gaps") or []
    return (f"[COVERAGE] pergunta {label}: status={status} "
            f"proportion={prop_s} complete={bool(block.get('complete'))} "
            f"plan={block.get('plan_id')} run={block.get('run_id')} "
            f"gaps={len(gaps)} "
            f"(rastreio: bloco question_coverage no artefato _depth.json)")


class Ledger:
    """Explicit per-criterion evaluations against a validated plan."""

    def __init__(self, plan: dict, run_id: str = "") -> None:
        self.plan = validate_plan(plan)
        self.run_id = run_id or ""
        self.version = plan.get("version", 1)
        self._evidence: dict[str, str] = {}
        self._qualification: dict[str, dict] = {}
        self._counts: dict[str, int] = {s: 0 for s in STAGES}
        self._evals: dict[str, dict] = {}  # criterion_id -> evaluation

    # -- corpus / qualification feed (real, existing) ---------------------

    def set_corpus(self, evidence: dict[str, str],
                   qualification: dict[str, dict] | None = None) -> None:
        """Feed obtained material + its qualification (no analysis here)."""
        self._evidence = dict(evidence or {})
        self._qualification = dict(qualification or {})

    def set_observed_counts(self, counts: dict[str, int]) -> None:
        for stage in STAGES:
            if stage in (counts or {}):
                try:
                    self._counts[stage] = max(0, int(counts[stage]))
                except (TypeError, ValueError):
                    continue

    # -- evaluation -------------------------------------------------------

    def _resolves(self, ref: dict) -> tuple[bool, str]:
        """A reference sustains coverage only if it points at usable evidence."""
        url = ref.get("url", ref.get("doc_id", ""))
        if not isinstance(url, str) or not url:
            return False, "referência sem url/doc_id"
        if url not in self._evidence:
            return False, f"referência inexistente no corpus: {url[:80]}"
        qual = self._qualification.get(url)
        if qual is None:
            return False, (f"referência sem qualificação: {url[:80]} "
                           "(não avaliada, não cobre)")
        if qual.get("excluded"):
            return False, (f"evidência excluída pela qualificação "
                           f"({qual.get('status', '?')}): {url[:80]}")
        if not (qual.get("usable_text") or "").strip():
            if qual.get("status") not in ("usable", "partial"):
                return False, (f"evidência insuficiente "
                               f"({qual.get('status', '?')}): {url[:80]}")
        return True, ""

    def evaluate(self, criterion_id: str, state: str, justification: str,
                 origin: str, references: list[dict] | None = None,
                 entity_id: str | None = None) -> dict:
        """Record one explicit evaluation. Raises on structural problems.

        ``covered``/``partial`` require justification + origin + at least one
        reference resolvable to usable (non-excluded) evidence. Other states
        keep justification (+ optional attempt references, failures included).
        """
        crit = next((c for c in self.plan["criteria"]
                     if c["id"] == criterion_id), None)
        if crit is None:
            raise KeyError(f"[COVERAGE] unknown criterion {criterion_id!r}")
        if state not in STATES:
            raise ValueError(f"[COVERAGE] unknown state {state!r}; "
                             f"expected one of {STATES}")
        if entity_id is not None:
            applies = crit.get("applies_to", None)
            known = {e["id"] for e in self.plan["entities"]}
            if entity_id not in known:
                raise ValueError(f"[COVERAGE] unknown entity {entity_id!r}")
            if applies is not None and entity_id not in applies:
                raise ValueError(
                    f"[COVERAGE] criterion {criterion_id!r} does not apply "
                    f"to entity {entity_id!r}")
        refs = list(references or [])
        if state == "uninvestigated":
            self._evals.pop(criterion_id, None)
            return {"criterion_id": criterion_id, "state": state}
        if not (justification or "").strip():
            raise ValueError("[COVERAGE] evaluation needs a justification "
                             "(lacunas e tentativas são preservadas, não omitidas)")
        if not (origin or "").strip():
            raise ValueError("[COVERAGE] evaluation needs an origin "
                             "(de onde veio a justificativa)")
        if state in ("covered", "partial"):
            if not refs:
                raise ValueError(
                    f"[COVERAGE] {state} exige referência a material obtido "
                    "(URL/menção/texto sozinho não cobre)")
            if origin.strip().lower() in ("access_failure", "access-failure",
                                          "fetch_error", "timeout"):
                raise ValueError("[COVERAGE] falha de acesso não cobre "
                                 "nem sustenta parcial — use 'blocked'")
            for ref in refs:
                ok, why = self._resolves(ref if isinstance(ref, dict) else {})
                if not ok:
                    raise ValueError(f"[COVERAGE] não cobre: {why}")
        self._evals[criterion_id] = {
            "criterion_id": criterion_id,
            "entity_id": entity_id,
            "state": state,
            "justification": justification,
            "origin": origin,
            "references": refs,
        }
        return dict(self._evals[criterion_id])

    # -- computation ------------------------------------------------------

    def _required(self) -> list[dict]:
        return [c for c in self.plan["criteria"] if c.get("required", True)]

    def state_of(self, criterion_id: str) -> str:
        return self._evals.get(criterion_id, {}).get("state", "uninvestigated")

    def compute(self) -> dict:
        """Build the persistable ``question_coverage`` block (no fabrication).

        Denominator = every applicable mandatory criterion, including
        blocked/uninvestigated ones. Numerator = covered only.
        """
        required = self._required()
        total = len(required)
        covered_n = sum(1 for c in required
                        if self.state_of(c["id"]) == "covered")
        if total == 0:
            proportion = None
            complete = False
            status = "partial"
        else:
            proportion = covered_n / total
            complete = covered_n == total
            status = "covered" if complete else "partial"
        criteria_out, gaps, refs_out = [], [], []
        for c in self.plan["criteria"]:
            ev = self._evals.get(c["id"], {})
            state = ev.get("state", "uninvestigated")
            entry = {
                "id": c["id"],
                "label": c.get("label", c["id"]),
                "required": bool(c.get("required", True)),
                "applies_to": c.get("applies_to", None),
                "state": state,
                "justification": ev.get("justification", ""),
                "origin": ev.get("origin", ""),
                "entity_id": ev.get("entity_id", None),
                "references": ev.get("references", []),
            }
            criteria_out.append(entry)
            for r in ev.get("references", []):
                refs_out.append({"criterion_id": c["id"], **r})
            if entry["required"] and state != "covered":
                gaps.append({
                    "criterion_id": c["id"],
                    "label": entry["label"],
                    "state": state,
                    "justification": entry["justification"] or "não investigado",
                    "next": ("investigar critério obrigatório; "
                             "tentativas anteriores preservadas acima"),
                })
        return {
            "status": status,
            "complete": complete,
            "plan_id": self.plan.get("plan_id"),
            "plan_version": self.version,
            "run_id": self.run_id,
            "proportion": proportion,
            "criteria": criteria_out,
            "gaps": gaps,
            "references": refs_out,
            "observed_counts": dict(self._counts),
        }

    # -- persistence (never mix runs) -------------------------------------

    def to_json(self) -> dict:
        return {"run_id": self.run_id,
                "plan": self.plan,
                "evidence": dict(self._evidence),
                "qualification": {k: dict(v) for k, v in
                                  self._qualification.items()},
                "evaluations": list(self._evals.values()),
                "observed_counts": dict(self._counts)}

    @classmethod
    def from_json(cls, payload: dict, run_id: str | None = None) -> "Ledger":
        if not isinstance(payload, dict):
            raise ValueError("[COVERAGE] payload must be an object")
        saved_run = payload.get("run_id", "")
        if run_id is not None and saved_run != run_id:
            raise ValueError(
                f"[COVERAGE] run mismatch: payload is run {saved_run!r}, "
                f"asked for {run_id!r} — runs never mix")
        ledger = cls(payload.get("plan", {}), run_id=saved_run)
        # Corpus travels with the payload so recovery re-validates each
        # reference against the same material (never trusted blindly).
        ledger.set_corpus(payload.get("evidence", {}) or {},
                          payload.get("qualification", {}) or {})
        ledger.set_observed_counts(payload.get("observed_counts", {}) or {})
        for ev in payload.get("evaluations", []) or []:
            if ev.get("state") == "uninvestigated":
                continue
            ledger.evaluate(ev["criterion_id"], ev["state"],
                            ev.get("justification", ""),
                            ev.get("origin", ""),
                            ev.get("references", []),
                            ev.get("entity_id"))
        return ledger


def build_run_question_coverage(*, plan: dict | None, run_id: str,
                                evidence: dict[str, str] | None = None,
                                qualification: dict[str, dict] | None = None,
                                discovered_urls: list | None = None,
                                report_text: str = "",
                                evaluations: list[dict] | None = None,
                                semantic: dict | None = None) -> tuple[dict, float | None]:
    """Integrated path used by gpt_researcher_integration.py (and tests).

    Feeds the ledger with the REAL corpus/qualification/traceability, applies
    only EXPLICIT evaluations (the flow itself never maps evidence to
    criteria, so insufficiency is preserved), and returns
    (question_coverage_block, coverage_ratio_or_None).

    ``semantic`` (verdict_state/accepted/...) is recorded as context only:
    approval there never clears question gaps.
    """
    evidence = dict(evidence or {})
    qualification = dict(qualification or {})
    urls = [u for u in (discovered_urls or []) if isinstance(u, str)]
    if plan is None:
        block = empty_question_coverage(run_id)
        block["observed_counts"] = _observe(evidence, urls, report_text)
        if semantic is not None:
            block["semantic_context"] = {
                "verdict_state": semantic.get("verdict_state"),
                "accepted": semantic.get("accepted"),
                "note": ("contexto apenas — aprovação semântica não "
                         "implica cobertura da pergunta"),
            }
        return block, None
    ledger = Ledger(plan, run_id=run_id)
    ledger.set_corpus(evidence, qualification)
    ledger.set_observed_counts(_observe(evidence, urls, report_text))
    for ev in evaluations or []:
        ledger.evaluate(ev["criterion_id"], ev.get("state", "insufficient"),
                        ev.get("justification", ""), ev.get("origin", ""),
                        ev.get("references", []), ev.get("entity_id"))
    block = ledger.compute()
    if semantic is not None:
        block["semantic_context"] = {
            "verdict_state": semantic.get("verdict_state"),
            "accepted": semantic.get("accepted"),
            "note": ("contexto apenas — aprovação semântica não "
                     "implica cobertura da pergunta"),
        }
    ratio = block["proportion"]
    return block, (None if ratio is None else float(ratio))


def _observe(evidence: dict[str, str], urls: list[str],
             report_text: str) -> dict[str, int]:
    """Stage counts from real material only (analyzed/used stay 0: the flow
    performs no evidence→criterion mapping — shortcut: sem essa análise,
    insuficiência é preservada; upgrade quando houver avaliação explícita)."""
    obtained = sum(1 for t in evidence.values()
                   if isinstance(t, str) and t.strip())
    cited = sum(1 for u in set(urls) if u and u in (report_text or ""))
    return {
        "discovered": len(set(urls)),
        "obtained": obtained,
        "qualified": len(evidence),
        "analyzed": 0,
        "used": 0,
        "cited": cited,
    }
