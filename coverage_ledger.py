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
          "covered", "contradictory", "blocked", "not_applicable")

#: Fixed coverage formula, persisted next to every computed block. Never
#: rewrite it to raise a percentage: changing the plan requires a new
#: registered plan version, and the denominator stays fixed per version.
#: ``not_applicable`` cells (per-candidate cells whose documented scope
#: excludes the axis, with scope-delimiting evidence) are excluded from
#: the denominator, listed separately in ``na``/``na_cells``, never hidden
#: and never counted as covered.
COVERAGE_DEFINITION = ("covered required (criterion, entity) cells / "
                      "(total required cells minus not_applicable cells "
                      "with scope evidence); not_applicable cells listed "
                      "separately, never counted as covered")

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
        if c.get("required", True):
            _desc = c.get("description", c.get("definition", ""))
            if not isinstance(_desc, str) or not _desc.strip():
                raise ValueError(
                    f"[COVERAGE] criterion {cid!r} requires a non-empty "
                    f"'description' (or 'definition'): 1-2 operational "
                    f"sentences stating what counts as evidence for the "
                    f"axis; the planner must provide it, label-only is "
                    f"rejected fail-closed")
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



def _gap_next(ledger: "Ledger", crit: dict, entry: dict) -> str:
    """Próximo passo específico por lacuna a partir do estado.

    Genérico ("investigar critério obrigatório") só quando nada mais se
    sabe; com entidades insuficientes identificadas, cita a entidade e a
    fonte própria (coletada: reler seções por dimensão; ausente: buscar
    fonte que mencione o nome no corpo). Sem IDs crus: usa rótulos.
    """
    try:
        applies = crit.get("applies_to") or []
        applies = [applies] if isinstance(applies, str) else list(applies)
        req = ledger._required_entity_ids()
        emap = {e.get("id"): e for e in ledger.plan.get("entities", [])
                if isinstance(e, dict)}
        pending = [eid for eid in applies
                   if eid in req and ledger._evals.get(
                       (crit["id"], eid), {}).get("state",
                                                  "uninvestigated")
                   in ("insufficient", "uninvestigated", "blocked")]
        if pending:
            bits = []
            for eid in pending[:4]:
                ent = emap.get(eid) or {}
                label = str(ent.get("label") or eid)
                src = (ent.get("source_url") or "").strip()
                if src and src in (ledger._evidence or {}):
                    bits.append(f"ler a fonte própria de {label} "
                                f"({src}) nas seções da dimensão")
                elif src:
                    bits.append(f"coletar a fonte própria de {label} "
                                f"({src}) e avaliar a célula")
                else:
                    bits.append(f"buscar fonte própria que mencione "
                                f"{label} no corpo e avaliar a célula")
            return "; ".join(bits)
    except Exception:
        pass
    return ("investigar critério obrigatório; "
            "tentativas anteriores preservadas acima")


class Ledger:
    """Explicit per-criterion evaluations against a validated plan.

    Unit of evaluation is the applicable pair (criterion_id, entity_id):
    a criterion applying to N entities needs N covered pairs. Global
    criteria (no applies_to) need one. Single-entity criteria accept the
    evaluation with or without the explicit entity_id for retro-compat.
    Aggregate evaluations (entity_id None) never cover a multi-entity
    criterion on their own; per-entity evidence is required.
    """

    def __init__(self, plan: dict, run_id: str = "") -> None:
        self.plan = validate_plan(plan)
        self.run_id = run_id or ""
        self.version = plan.get("version", 1)
        self._evidence: dict[str, str] = {}
        self._qualification: dict[str, dict] = {}
        self._counts: dict[str, int] = {s: 0 for s in STAGES}
        # (criterion_id, entity_id|None) -> evaluation
        self._evals: dict[tuple, dict] = {}

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

    def _na_cell_ok(self, crit: dict, entity_id: str | None) -> bool:
        applies = crit.get("applies_to", None)
        if not isinstance(applies, list) or len(applies) < 2:
            return False
        if not entity_id:
            return False
        ent = next((e for e in self.plan.get("entities", [])
                    if isinstance(e, dict) and e.get("id") == entity_id),
                   None)
        return bool(ent is not None and ent.get("discovered")
                    and ent.get("required", True))

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
        status = str(qual.get("status", "") or "").strip().lower()
        if status in ("error", "failed", "fetch_error", "timeout",
                      "access_failure", "access-failure"):
            return False, (f"evidência de erro não sustenta cobertura "
                           f"({qual.get('status', '?')}): {url[:80]}")
        # Empty usable text never sustains covered/partial, whatever the
        # declared status is (a status=usable with empty text is incoherent
        # and must not cover). shortcut: sem texto útil, sem cobertura.
        if not (qual.get("usable_text") or "").strip():
            return False, (f"evidência vazia/insuficiente "
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
        if state == "not_applicable" and not self._na_cell_ok(crit,
                                                              entity_id):
            raise ValueError(
                f"[COVERAGE] not_applicable for ({criterion_id!r}, "
                f"{entity_id!r}) rejected: it only holds for a "
                f"per-candidate cell (criterion applying to several "
                f"entities) of a discovered+required entity — global or "
                f"single-entity criteria with N/A are insufficient, never "
                f"scope exclusions")
        refs = list(references or [])
        key = (criterion_id, entity_id)
        if state == "uninvestigated":
            self._evals.pop(key, None)
            # Retro-compat: clearing without entity also clears the
            # entity-less entry for single-entity criteria.
            if entity_id is None:
                for k in [k for k in self._evals if k[0] == criterion_id]:
                    self._evals.pop(k, None)
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
        self._evals[key] = {
            "criterion_id": criterion_id,
            "entity_id": entity_id,
            "state": state,
            "justification": justification,
            "origin": origin,
            "references": refs,
        }
        return dict(self._evals[key])

    # -- computation ------------------------------------------------------

    def _required(self) -> list[dict]:
        return [c for c in self.plan["criteria"] if c.get("required", True)]

    def _required_entity_ids(self) -> set[str]:
        """Entities that count toward coverage.

        Discovery may version more candidates than the question asks for
        (accept9: 12 entities -> 83 cells, 1 covered). Extra candidates stay
        tracked (``required: false``) but never inflate the denominator.
        """
        return {e.get("id") for e in self.plan.get("entities", [])
                if isinstance(e, dict) and e.get("required", True)}

    def state_of(self, criterion_id: str, entity_id=None) -> str:
        if entity_id is not None:
            return self._evals.get(
                (criterion_id, entity_id), {}).get("state", "uninvestigated")
        # Overall state for the criterion: covered only when every
        # applicable required pair is covered.
        crit = next((c for c in self.plan["criteria"]
                     if c["id"] == criterion_id), None)
        if crit is None:
            return "uninvestigated"
        applies = crit.get("applies_to", None)
        if applies:
            applies = [applies] if isinstance(applies, str) else list(applies)
            req = self._required_entity_ids()
            applies = [e for e in applies if e in req] or None
        if not applies:
            for (cid, _), ev in self._evals.items():
                if cid == criterion_id and ev.get("state") == "covered":
                    return "covered"
            direct = self._evals.get((criterion_id, None), {})
            if direct:
                return direct.get("state", "uninvestigated")
            others = [ev for (cid, _), ev in self._evals.items()
                      if cid == criterion_id]
            if others:
                return others[0].get("state", "uninvestigated")
            return "uninvestigated"
        if len(applies) == 1:
            eid = applies[0]
            for key in ((criterion_id, eid), (criterion_id, None)):
                st = self._evals.get(key, {}).get("state")
                if st:
                    return st
            return "uninvestigated"
        pairs = [self._evals.get((criterion_id, eid), {}).get("state",
                 "uninvestigated") for eid in applies]
        # Out-of-scope cells never decide the criterion state.
        eff = [s for s in pairs if s != "not_applicable"]
        if not eff:
            return "not_applicable"
        if all(s == "covered" for s in eff):
            return "covered"
        if any(s == "covered" for s in eff):
            return "partial"
        for s in eff:
            if s != "uninvestigated":
                return s
        return "uninvestigated"

    def _covered_pairs(self, crit: dict) -> tuple[int, int]:
        """Return (covered_pairs, total_pairs) for one criterion."""
        applies = crit.get("applies_to", None)
        if applies:
            applies = [applies] if isinstance(applies, str) else list(applies)
            req = self._required_entity_ids()
            applies = [e for e in applies if e in req] or None
        if not applies:
            total = 1
            covered = 1 if self.state_of(crit["id"]) == "covered" else 0
            return covered, total
        if len(applies) == 1:
            total = 1
            eid = applies[0]
            covered = 1 if (self._evals.get((crit["id"], eid), {}).get(
                "state") == "covered" or self._evals.get(
                    (crit["id"], None), {}).get("state") == "covered") else 0
            return covered, total
        total = len(applies)
        covered = sum(1 for eid in applies if self._evals.get(
            (crit["id"], eid), {}).get("state") == "covered")
        return covered, total

    def _na_required_cells(self) -> list[dict]:
        """Required per-candidate cells marked out of scope (never hidden).

        Only cells of required criteria on required entities count: they
        are the ones excluded from the denominator. Each entry carries
        its justification + references so the exclusion stays auditable.
        """
        req_entities = self._required_entity_ids()
        out = []
        for (cid, eid), ev in self._evals.items():
            if ev.get("state") != "not_applicable" or eid is None:
                continue
            crit = next((c for c in self.plan["criteria"]
                         if c["id"] == cid), None)
            if crit is None or not crit.get("required", True):
                continue
            if eid not in req_entities:
                continue
            out.append({
                "criterion_id": cid,
                "entity_id": eid,
                "justification": ev.get("justification", ""),
                "references": ev.get("references", []),
            })
        out.sort(key=lambda d: (d["criterion_id"], d["entity_id"] or ""))
        return out

    def cell_counts(self) -> tuple[int, int]:
        """(covered, total) required cells — single source of the formula.

        The denominator is every applicable (criterion, entity) pair of the
        current plan version; it never shrinks to raise the proportion.
        (``not_applicable`` cells are subtracted in ``compute()``, where
        the exclusion is exposed as ``na``/``na_cells``.)
        """
        covered_n = 0
        total = 0
        for c in self._required():
            cov, tot = self._covered_pairs(c)
            covered_n += cov
            total += tot
        return covered_n, total

    def compute(self) -> dict:
        """Build the persistable ``question_coverage`` block (no fabrication).

        Denominator = every applicable (criterion, entity) pair for
        mandatory criteria, including blocked/uninvestigated ones, MINUS
        ``not_applicable`` cells (excluded, listed in ``na``/``na_cells``).
        Numerator = covered pairs only. A shared criterion is covered
        only when every in-scope entity in applies_to has a covering
        evaluation.

        The formula is fixed (``COVERAGE_DEFINITION``): it is never changed
        to improve the percentage. A plan change must be registered as a new
        version (see ``plan_version_record``) so the new denominator is
        visible in the artifact.
        """
        covered_n, total = self.cell_counts()
        na_cells = self._na_required_cells()
        na = len(na_cells)
        denom = total - na
        if total == 0:
            proportion = None
            complete = False
            status = "partial"
        elif denom == 0:
            # Every required cell out of scope: nothing left to cover.
            proportion = 1.0
            complete = True
            status = "covered"
        else:
            proportion = covered_n / denom
            complete = covered_n == denom
            status = "covered" if complete else "partial"
        criteria_out, gaps, refs_out = [], [], []
        for c in self.plan["criteria"]:
            state = self.state_of(c["id"])
            # Representative evaluation for display: prefer an explicit
            # per-entity eval, else the aggregate one.
            ev = {}
            applies = c.get("applies_to", None)
            all_applies = applies
            if applies:
                applies = [eid for eid in applies if eid in self._required_entity_ids()]
            if applies and len(applies) > 1:
                for eid in applies:
                    cand = self._evals.get((c["id"], eid))
                    if cand and (not ev or cand.get("state") == "covered"):
                        ev = cand
                        if cand.get("state") != "covered":
                            break
                if not ev:
                    ev = self._evals.get((c["id"], None), {})
            elif applies and len(applies) == 1:
                ev = self._evals.get((c["id"], applies[0]),
                                     self._evals.get((c["id"], None), {}))
            else:
                for (cid, _), cand in self._evals.items():
                    if cid == c["id"]:
                        ev = cand
                        break
            entity_states = None
            _req_applies = [e for e in (applies or [])
                            if e in self._required_entity_ids()]
            if _req_applies and len(_req_applies) > 1:
                entity_states = {eid: self._evals.get(
                    (c["id"], eid), {}).get("state", "uninvestigated")
                    for eid in _req_applies}
            entry = {
                "id": c["id"],
                "label": c.get("label", c["id"]),
                "required": bool(c.get("required", True)),
                "applies_to": c.get("applies_to", None),
                "per_candidate": bool(c.get("per_candidate")),
                "state": state,
                "justification": ev.get("justification", ""),
                "origin": ev.get("origin", ""),
                "entity_id": ev.get("entity_id", None),
                "references": ev.get("references", []),
            }
            if entity_states is not None:
                entry["entity_states"] = entity_states
            if applies:
                entry["entity_evaluations"] = {
                    eid: dict(self._evals.get((c["id"], eid), {})) for eid in applies}
            entry["na_cells"] = [nc for nc in na_cells
                                 if nc["criterion_id"] == c["id"]]
            criteria_out.append(entry)
            for (cid, _), cand in self._evals.items():
                if cid == c["id"]:
                    for r in cand.get("references", []):
                        refs_out.append({"criterion_id": c["id"], **r})
            if entry["required"] and state not in ("covered",
                                                      "not_applicable"):
                # Gaps por célula acionável (G1): entidade versionada por
                # descoberta com source_url própria e célula ainda sem
                # cobertura ganha um gap endereçado à célula — o select_ops
                # vira read_source direto da fonte, sem depender de a query
                # genérica do critério redescobri-la. Chaves novas
                # (entity_id/entity_label/source_url) são aditivas: leitores
                # antigos que só olham criterion_id seguem funcionando.
                # Dedup §6/parada: quando os gaps específicos por célula
                # cobrem TODAS as pendências do critério, o genérico é
                # suprimido (prefere o específico; contagem sem dupla do
                # mesmo next). Se resta pendência sem fonte própria
                # (ex.: entidade sem source_url), o genérico é mantido
                # para não perder cobertura (G1b: e0 sem fonte + e1 com
                # fonte → genérico + célula).
                _cell_gaps: list = []
                try:
                    _emap = {e.get("id"): e for e in
                             self.plan.get("entities", []) if isinstance(e, dict)}
                    for _eid in all_applies or []:
                        _ent = _emap.get(_eid) or {}
                        if not (_ent.get("required", True)
                                or _ent.get("discovered")):
                            continue  # fora da seleção e sem descoberta:
                            # sem célula (substituída/explorada)
                        _src = (_ent.get("source_url") or "").strip()
                        if not _src or _src in (self._evidence or {}):
                            continue
                        _cell = (self._evals.get((c["id"], _eid)) or {}).get(
                            "state", "uninvestigated")
                        if _cell not in ("uninvestigated", "insufficient",
                                         "blocked"):
                            continue
                        _cell_gaps.append({
                            "criterion_id": c["id"],
                            "entity_id": _eid,
                            "entity_label": _ent.get("label", _eid),
                            "source_url": _src,
                            "label": entry["label"],
                            "state": _cell,
                            "justification": (
                                f"célula ({c['id']}, {_eid}) ainda sem "
                                f"cobertura; fonte própria: {_src[:80]}"),
                            "next": "ler a fonte própria da entidade",
                        })
                except Exception:
                    pass
                try:
                    _req_ids = self._required_entity_ids()
                    _pending = [eid for eid in (applies or [])
                                if eid in _req_ids and (self._evals.get(
                                    (c["id"], eid)) or {}).get(
                                    "state", "uninvestigated") in (
                                    "uninvestigated", "insufficient",
                                    "blocked")]
                    _covered_by_cells = {g.get("entity_id")
                                         for g in _cell_gaps}
                    _fully_covered = bool(_cell_gaps) and bool(_pending) and all(
                        eid in _covered_by_cells for eid in _pending)
                except Exception:
                    _fully_covered = bool(_cell_gaps) and not _pending
                if _cell_gaps and _fully_covered:
                    gaps.extend(_cell_gaps)
                else:
                    gaps.append({
                        "criterion_id": c["id"],
                        "label": entry["label"],
                        "state": state,
                        "justification": entry["justification"] or "não investigado",
                        "next": _gap_next(self, c, entry),
                    })
                    gaps.extend(_cell_gaps)
        return {
            "status": status,
            "complete": complete,
            "plan_id": self.plan.get("plan_id"),
            "plan_version": self.version,
            "run_id": self.run_id,
            "definition": COVERAGE_DEFINITION,
            "numerator": covered_n,
            "denominator": denom,
            "na": na,
            "na_cells": na_cells,
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


def plan_version_record(plan: dict) -> dict:
    """Denominator fields every ``plan_versions`` record must expose.

    ``adaptive_state`` appends each plan version; it should merge these
    fields into the record so a denominator change is visible in the
    persisted artifact::

        state["plan_versions"].append({**plan_version_record(plan), ...})

    ``cells`` is the same count ``Ledger.compute()`` uses as denominator
    (required criteria x applicable required entities). The formula is
    fixed: it is never rewritten to raise a percentage — changing the plan
    requires a new registered version, which is what makes the change
    visible.
    """
    ledger = Ledger(plan)
    _, total = ledger.cell_counts()
    return {
        "criteria_count": len(ledger._required()),
        "entities_required": len(ledger._required_entity_ids()),
        "cells": total,
    }


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
