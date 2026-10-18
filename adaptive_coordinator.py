#!/usr/bin/env python3
"""Adaptive research coordinator: plan -> collect -> assess -> close gaps.

Real coordinator logic, deterministic at its boundaries. Everything the
outside world provides (search/fetch/assess/write/audit/clock) is injected;
the coordinator itself is NEVER mocked in tests — it is the unit under test.

Round discipline (each round recorded: target gaps, ops, new evidence,
coverage delta, insufficiencies, decision):
  1. recover plan / evidence / pending from state (never trusts memory only);
  2. assess coverage + contradictions via the injected assessor
     (default: no evaluations -> insufficiency preserved, never fabricated);
  3. prioritise gaps by impact x expected gain (assessor hints, stable order);
  4. select specific ops (gap_query / alt_channel / read_source), varying the
     channel when the previous attempt on that gap failed or added nothing;
  5. execute within budget/time/round limits (run_budget + controlled clock);
  6. incorporate (distinct excerpts of one URL preserved; corpus never
     silently swapped; external content has no authority over the rules);
  7. persist atomically + checkpoint; decide continue/end with an explicit
     motive SEPARATE from coverage status and from the semantic verdict.

GPT Researcher (installed 0.16.0, site-packages/gpt_researcher) is only ever
encapsulated: at most ONE conduct_research() as the initial sweep, never
repeated with the original question — later rounds use targeted ops
(gap queries, alternate channels, specific source reads) and keep the
accumulated material. Offline tests inject fakes; the real-path wiring lives
in the production entrypoint (gpt_researcher_integration._adaptive_main).

Stop motives: criteria_ok | saturation | rounds | budget | time | blocked |
failure. Saturation with pending gaps is partial. Legacy flow_end is never
used here and never proves completeness. No fabricated ops for counters:
recorded ops == executed ops. Tokens/costs are measured only from real data,
otherwise recorded as "unknown".
"""
from __future__ import annotations

import hashlib
import time

import adaptive_planner as _planner
import adaptive_state as _state
import coverage_ledger as _ledger
import depth_profiles as _profiles
import run_budget as _run_budget

try:
    import run_checkpoint as _checkpoint
except ImportError:  # pragma: no cover - stdlib test path always has it
    _checkpoint = None

CHANNELS = ("web", "github", "arxiv", "youtube")

ADAPTIVE_ROUNDS = {"light": 2, "medium": 3, "hard": 4, "deep": 6}
ADAPTIVE_MODEL_CALLS = {"light": 8, "medium": 16, "hard": 32, "deep": 64}


class TransportError(RuntimeError):
    """Boundary failure (search/fetch/model transport) — never favourable."""


def resolve_adaptive(profile: str = "light",
                     overrides: dict | None = None) -> dict:
    """Resolved adaptive config: depth profile + independent round/model/time
    knobs. Records every applied value for the run record."""
    ov = dict(overrides or {})
    adaptive = {}
    for key in ("max_rounds", "max_model_calls", "max_ops_per_round",
                "time_s", "concurrency"):
        if key in ov:
            try:
                adaptive[key] = int(ov[key])
            except (TypeError, ValueError):
                raise ValueError(f"[ADAPTIVE] override {key} must be integer")
    depth_ov = {k: v for k, v in ov.items()
                if k in _profiles.ALLOWED_OVERRIDES}
    resolved = _profiles.resolve(profile, depth_ov)
    canonical = resolved["profile"]
    resolved["max_rounds"] = adaptive.get("max_rounds",
                                          ADAPTIVE_ROUNDS[canonical])
    resolved["max_model_calls"] = adaptive.get(
        "max_model_calls", ADAPTIVE_MODEL_CALLS[canonical])
    resolved["max_ops_per_round"] = adaptive.get(
        "max_ops_per_round", resolved["DEEP_RESEARCH_BREADTH"])
    resolved["time_s"] = adaptive.get("time_s",
                                      resolved["budget"].get("time_s", 600))
    resolved["concurrency"] = adaptive.get(
        "concurrency", resolved["DEEP_RESEARCH_CONCURRENCY"])
    if resolved["max_rounds"] < 0 or resolved["max_model_calls"] < 0:
        raise ValueError("[ADAPTIVE] max_rounds/max_model_calls must be >= 0")
    if resolved["concurrency"] < 1:
        raise ValueError("[ADAPTIVE] concurrency must be >= 1")
    resolved["adaptive"] = True
    return resolved


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8",
                                              "replace")).hexdigest()[:16]


def classify_hit(state: dict, url: str, text: str) -> str:
    """new_useful | confirmed | duplicate | nogain (no fabrication).

    Distinct excerpts of one URL are preserved as separate segments; the
    ledger-facing evidence map concatenates them with a separator.
    """
    text = text or ""
    if not text.strip():
        return "nogain"
    digest = _content_hash(text)
    prior = [s for s in state["segments"] if s.get("url") == url]
    if any(s.get("sha") == digest for s in prior):
        return "duplicate"
    if prior:
        return "new_useful"  # same URL, distinct excerpt -> preserved
    for seg in state["segments"]:
        if seg.get("sha") == digest and seg.get("url") != url:
            return "confirmed"  # independent URL, same bytes
    known_texts = {s.get("excerpt", "") for s in state["segments"]}
    if text in known_texts:
        return "duplicate"
    return "new_useful"


def incorporate(state: dict, url: str, text: str, op_id: str,
                round_no: int, qualification: dict | None = None) -> str:
    """Add obtained material; returns the classification. Duplicates are
    reported, not stored twice; distinct excerpts accumulate."""
    kind = classify_hit(state, url, text or "")
    if kind in ("new_useful", "confirmed"):
        state["segments"].append({
            "url": url, "excerpt": text, "sha": _content_hash(text or ""),
            "op_id": op_id, "round": round_no,
        })
        prev = state["evidence"].get(url, "")
        state["evidence"][url] = (prev + "\n--- segment ---\n" + text
                                  if prev else text)
        if qualification is not None:
            state["qualification"][url] = dict(qualification)
        state["consumption"]["docs"] += 1
    return kind


def _gap_hints(evaluation: dict) -> tuple[float, float]:
    try:
        impact = float(evaluation.get("impact", 1))
    except (TypeError, ValueError):
        impact = 1.0
    try:
        gain = float(evaluation.get("expected_gain", 1))
    except (TypeError, ValueError):
        gain = 1.0
    return max(0.0, impact), max(0.0, gain)


def prioritize_gaps(gaps: list[dict]) -> list[dict]:
    """Order by impact x expected gain (stable; no name-based rules)."""
    scored = []
    for i, gap in enumerate(gaps):
        impact, gain = _gap_hints(gap)
        scored.append((-impact * gain, i, gap))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [g for _, _, g in scored]


def select_ops(state: dict, gaps: list[dict], cap: int) -> list[dict]:
    """One specific op per top gap; vary channel after failed/flat attempts."""
    ops = []
    for gap in gaps[:max(0, cap)]:
        cid = gap.get("criterion_id", "")
        attempts = state["attempts"].get(cid, [])
        last_channel = attempts[-1].get("channel") if attempts else None
        last_outcome = attempts[-1].get("outcome") if attempts else None
        unfetched = [c for c in state["discovery"].get("candidates", [])
                     if c not in state["evidence"]]
        if unfetched and (attempts and last_outcome in ("failed", "nogain")):
            kind, channel = "read_source", (last_channel or CHANNELS[0])
            target = unfetched[0]
        elif not attempts:
            kind, channel = "gap_query", CHANNELS[0]
            target = f"{state['question']} — {gap.get('label', cid)}"
        elif last_outcome in ("failed", "nogain", "duplicate"):
            idx = (CHANNELS.index(last_channel) + 1) % len(CHANNELS) \
                if last_channel in CHANNELS else 1
            kind, channel = "alt_channel", CHANNELS[idx]
            target = f"{state['question']} — {gap.get('label', cid)}"
        else:
            kind, channel = "gap_query", (last_channel or CHANNELS[0])
            target = f"{state['question']} — {gap.get('label', cid)}"
        op_id = f"r{len(state['rounds'])}-{cid}-{len(attempts)}"
        ops.append({"op_id": op_id, "kind": kind, "channel": channel,
                    "target": target, "criterion_id": cid,
                    "status": "in-progress"})
    return ops


def _default_assess(plan, evidence, qualification) -> list:
    """Default assessor: no evaluations (insufficiency preserved, never mapped
    by heuristics). Real deployments inject a model-backed assessor."""
    return []


def _default_writer(view: dict) -> tuple[str, dict]:
    """Deterministic synthesis by plan criteria (no model needed)."""
    lines = [f"# {view['question']}", ""]
    cov = view.get("question_coverage", {})
    lines.append(f"Coverage: {cov.get('status', '?')} "
                 f"(proportion={cov.get('proportion')}) — "
                 f"stop: {view.get('stop', {}).get('reason', '?')}.")
    lines.append("")
    for crit in cov.get("criteria", []):
        refs = "; ".join(r.get("url", "") for r in crit.get("references", []))
        lines.append(f"## {crit.get('label', crit.get('id'))} "
                     f"[{crit.get('state')}]")
        lines.append(crit.get("justification") or "not investigated.")
        if refs:
            lines.append(f"Refs: {refs}")
        lines.append("")
    gaps = cov.get("gaps", [])
    if gaps:
        lines.append("Insufficient / pending: " +
                     ", ".join(g.get("criterion_id", "?") for g in gaps))
    return "\n".join(lines), {"included_urls": sorted(view.get("evidence", {})),
                              "cuts": "none (template writer uses full corpus)"}


def _default_auditor(report: str, evidence: dict) -> dict:
    """Real-path auditor: lazy semantic_review with its quorum/tie/failure
    protections. Never hides question gaps (recorded separately)."""
    try:
        import semantic_review as _sr
    except ImportError:
        return {"enabled": False,
                "verdict_state": "não revisado semanticamente",
                "accepted": False,
                "note": "semantic_review unavailable; question gaps kept"}
    try:
        result = _sr.review_report(report, dict(evidence or {}), enabled=True)
    except Exception as exc:  # failure is visible, never favourable
        return {"enabled": True, "verdict_state": "revisão incompleta",
                "accepted": False, "note": f"auditor failure: {exc}"}
    return result


def _assess_round(state: dict, assess_fn, ledger) -> tuple[list, dict]:
    """Feed the ledger with the REAL corpus/qualification, apply ONLY the
    assessor's explicit evaluations, compute the block. Returns (evals, block).
    The coordinator never maps evidence to criteria itself."""
    ledger.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
    evals = assess_fn(state["plan"], dict(state["evidence"]),
                      dict(state["qualification"])) or []
    applied = []
    for ev in evals:
        if not isinstance(ev, dict) or "criterion_id" not in ev:
            continue
        try:
            ledger.evaluate(ev["criterion_id"], ev.get("state", "insufficient"),
                            ev.get("justification", ""), ev.get("origin", ""),
                            ev.get("references", []), ev.get("entity_id"))
            applied.append(ev)
        except (ValueError, KeyError):
            # Invalid evaluation (e.g. unresolvable ref): preserved as an
            # insufficiency signal, never forced into coverage.
            state["notes"].append(
                f"assessor evaluation for {ev.get('criterion_id')} rejected "
                f"({ev.get('state')}): kept as insufficiency")
    # Open discovery: the assessor (model in production) may propose entities
    # the plan did not know. The coordinator only applies them as a new,
    # validated plan version — user requirements never shrink (enforced).
    for ev in evals:
        proposal = (ev or {}).get("propose_entity")
        if proposal and state["discovery"]["open"]:
            _apply_discovery(state, ledger, proposal, ev)
    block = ledger.compute()
    return applied, block


def _apply_discovery(state: dict, ledger, proposal: dict, ev: dict) -> None:
    """Incorporate a newly discovered candidate as a tracked entity."""
    try:
        import copy as _copy
        entity = proposal.get("entity") or {}
        criteria = proposal.get("criteria") or []
        eid = entity.get("id")
        if not isinstance(eid, str) or not eid.strip():
            return
        if any(e.get("id") == eid for e in state["plan"].get("entities", [])):
            return  # already tracked: no duplicate, no version spam
        new_plan = _copy.deepcopy(state["plan"])
        new_plan.setdefault("entities", []).append({
            "id": eid, "label": entity.get("label", eid),
            "required": True})
        for c in criteria:
            if isinstance(c, dict) and c.get("id"):
                c = dict(c)
                c.setdefault("applies_to", [eid])
                new_plan.setdefault("criteria", []).append(c)
        from coverage_ledger import validate_plan as _validate
        _validate(new_plan)
        _state.record_plan_version(
            state, new_plan,
            f"open discovery: candidate {eid} from {ev.get('criterion_id')}")
        # Rebuild the ledger on the new plan, re-applying prior evaluations
        # against the same corpus (references re-validated, never trusted).
        fresh = _ledger.Ledger(new_plan, run_id=state["run_id"])
        fresh.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
        kept = []
        for prev in state.get("evaluations", []):
            try:
                fresh.evaluate(prev["criterion_id"], prev.get("state", "insufficient"),
                               prev.get("justification", ""), prev.get("origin", ""),
                               prev.get("references", []), prev.get("entity_id"))
                kept.append(prev)
            except (ValueError, KeyError):
                pass
        state["evaluations"] = kept
        ledger.plan = fresh.plan
        ledger._evals = fresh._evals
        ledger._evidence = fresh._evidence
        ledger._qualification = fresh._qualification
        ledger._counts = fresh._counts
        ledger.version = fresh.version
    except (ValueError, KeyError, TypeError) as exc:
        state["notes"].append(f"discovery proposal rejected: {exc}")


def run_adaptive(question: str, *, profile: str = "light",
                 plan: dict | None = None, plan_source: str | dict | None = None,
                 purpose: str = "", constraints: dict | None = None,
                 model_client=None, search_fn=None, fetch_fn=None,
                 assess_fn=None, writer_fn=None, auditor_fn=None,
                 clock=None, budget=None, run_dir=None, run_id: str = "",
                 overrides: dict | None = None,
                 checkpoint=None, resume: bool = False) -> dict:
    """Execute the adaptive loop. All external effects are injected.

    resume=True continues a persisted run_dir state (checkpoint): completed
    work is kept (duplicates detected, never double-counted), interrupted ops
    were marked 'interrupted' by load(), and no second run/plan/config mixes
    in (question + run_id verified).

    Returns the final result (also persisted in run_dir when given).
    Raises nothing for domain outcomes (they become stop motives); raises
    ValueError only for programming/config misuse.
    """
    now = clock or time.monotonic
    t_start = now()
    resolved = resolve_adaptive(profile, overrides)
    budget_given = budget is not None
    if budget is None:
        budget = _run_budget.Budget(resolved.get("budget"), profile=resolved["profile"])
    if resume and run_dir is not None:
        try:
            state = _state.load(run_dir, run_id or None)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"[ADAPTIVE] resume found no usable state: {exc}")
        if state.get("question", "") != question:
            raise ValueError("[ADAPTIVE] resume question differs from stored "
                             "state — runs never mix")
        if state.get("mode") != "adaptive":
            raise ValueError("[ADAPTIVE] stored state is not adaptive")
        resolved = dict(state.get("config_applied") or {})
        if not resolved:
            resolved = resolve_adaptive(profile, overrides)
        # Resume keeps the stored run/plan/config (never mixes). The only
        # accepted change is an explicit limit extension, recorded as such.
        if overrides:
            allowed = {"max_rounds", "time_s", "max_model_calls", "max_ops_per_round"}
            for key in overrides:
                if key not in allowed:
                    raise ValueError(
                        f"[ADAPTIVE] resume only accepts limit extensions "
                        f"{sorted(allowed)}; got {key!r}")
                try:
                    new_val = int(overrides[key])
                except (TypeError, ValueError):
                    raise ValueError(f"[ADAPTIVE] override {key} must be integer")
            for key in allowed & set(overrides):
                old = resolved.get(key)
                resolved[key] = int(overrides[key])
                state["notes"].append(
                    f"resume extended {key}: {old} -> {resolved[key]} (recorded, "
                    f"not silent)")
        if not budget_given:
            budget = _run_budget.Budget(resolved.get("budget"),
                                        profile=resolved.get("profile", profile))
            # Resume inherits consumed budget (no pierced ceiling across runs).
            cons = state.get("consumption", {})
            try:
                budget.reseed({"queries": cons.get("queries", 0),
                               "extractions": cons.get("fetches", 0),
                               "unique_sources": len(state.get("evidence", {}))})
            except Exception:
                pass
        state["notes"].append("resumed from checkpoint; completed work kept, "
                              "interrupted ops marked, no silent repetition")
        plan, plan_meta = state["plan"], state.get("plan_meta", {})
        if plan is None:
            raise ValueError("[ADAPTIVE] stored state has no plan to resume")
        ledger = _ledger.Ledger(plan, run_id=state["run_id"])
        ledger.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
        kept = []
        for prev in state.get("evaluations", []):
            try:
                ledger.evaluate(prev["criterion_id"], prev.get("state", "insufficient"),
                                prev.get("justification", ""), prev.get("origin", ""),
                                prev.get("references", []), prev.get("entity_id"))
                kept.append(prev)
            except (ValueError, KeyError):
                pass
        state["evaluations"] = kept
        block = ledger.compute()
        prev_proportion = block.get("proportion")
        if checkpoint is None and _checkpoint is not None:
            checkpoint = _checkpoint.Checkpoint(run_dir)
        assess = assess_fn or _default_assess
        write = writer_fn or _default_writer
        audit = auditor_fn or _default_auditor
        stop = _resume_loop(state, ledger, assess, write, audit, resolved,
                            budget, search_fn, fetch_fn, now, t_start,
                            checkpoint, run_dir, block, prev_proportion)
        return stop
    state = _state.new_state(question, run_id=run_id, profile=resolved["profile"],
                             config={k: resolved[k] for k in
                                     ("profile", "report_type", "MAX_ITERATIONS",
                                      "DEEP_RESEARCH_BREADTH", "DEEP_RESEARCH_DEPTH",
                                      "DEEP_RESEARCH_CONCURRENCY", "TOTAL_WORDS",
                                      "vast_max", "yt_live", "max_rounds",
                                      "max_model_calls", "max_ops_per_round",
                                      "time_s", "concurrency", "budget")})
    if checkpoint is None and run_dir is not None and _checkpoint is not None:
        checkpoint = _checkpoint.Checkpoint(run_dir)
    if run_dir is not None:
        _state.save(run_dir, state)

    # -- plan -------------------------------------------------------------
    try:
        if plan is not None:
            plan, plan_meta = _planner.plan_from_explicit(plan)
        elif plan_source is not None:
            plan, plan_meta = _planner.plan_from_explicit(plan_source)
        elif model_client is not None:
            plan, plan_meta = _planner.generate_plan(
                question, model_client, purpose, constraints)
        else:
            raise _planner.PlanError(
                "[PLAN] no plan and no model_client — cannot invent one")
    except _planner.PlanError as exc:
        state["stop"] = {"reason": "failure", "partial": True,
                         "detail": f"plan failed: {exc}"}
        state["notes"].append(f"plan failure (no fictitious plan): {exc}")
        if run_dir is not None:
            _state.save(run_dir, state)
        return _finalize(state, resolved, budget, None, None, None,
                         t_start, now, run_dir)
    state["consumption"]["model_calls"] += int(plan_meta.get("model_calls", 0))
    _state.record_plan_version(state, plan, plan_meta.get("repair_log", [""])[0]
                               if plan_meta.get("repair_log") else "plan adopted")
    state["plan_meta"] = plan_meta
    disc = (plan.get("open_discovery") or {})
    state["discovery"]["open"] = bool(disc.get("needed", False))
    if run_dir is not None:
        _state.save(run_dir, state)

    ledger = _ledger.Ledger(plan, run_id=state["run_id"])
    assess = assess_fn or _default_assess
    write = writer_fn or _default_writer
    audit = auditor_fn or _default_auditor

    # -- initial collection (ONE sweep; later rounds are targeted ops) ------
    initial_queries = list((plan.get("initial_paths") or [question])) or [question]
    init_ops = [{"op_id": f"init-{i}", "kind": "initial", "channel": CHANNELS[0],
                 "target": q, "criterion_id": "", "status": "in-progress"}
                for i, q in enumerate(initial_queries)]
    _execute_ops(state, init_ops, search_fn, fetch_fn, budget, resolved, now,
                 t_start, checkpoint, round_no=0)
    applied, block = _assess_round(state, assess, ledger)
    state["evaluations"] = applied
    prev_proportion = block.get("proportion")
    state["rounds"].append({
        "round": 0, "kind": "initial",
        "target_gaps": [], "ops": _summarize_ops(state, init_ops),
        "new_evidence": len(state["segments"]),
        "coverage": {"status": block["status"], "proportion": prev_proportion},
        "delta": None, "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
        "decision": "assessed initial sweep",
    })
    state["consumption"]["rounds"] = 1
    if checkpoint is not None:
        try:
            checkpoint.note_query_done("initial-sweep",
                                       n_sources=len(state["evidence"]))
        except Exception:
            pass
    if run_dir is not None:
        _state.save(run_dir, state)

    # -- adaptive rounds ----------------------------------------------------
    return _resume_loop(state, ledger, assess, write, audit, resolved,
                        budget, search_fn, fetch_fn, now, t_start,
                        checkpoint, run_dir, block, prev_proportion)


def _resume_loop(state: dict, ledger, assess, write, audit, resolved: dict,
                 budget, search_fn, fetch_fn, now, t_start, checkpoint,
                 run_dir, block: dict, prev_proportion) -> dict:
    """Shared gap-round loop for fresh and resumed runs."""
    stop = None
    while len(state["rounds"]) - 1 < resolved["max_rounds"]:
        elapsed = now() - t_start
        open_gaps = block.get("gaps", [])
        # Explicit round/time motives (orçamento genérico não os esconde).
        if len(state["rounds"]) - 1 >= resolved["max_rounds"]:
            stop = {"reason": "rounds", "partial": bool(open_gaps),
                    "detail": f"max_rounds={resolved['max_rounds']} consumed"}
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        if elapsed >= resolved["time_s"]:
            stop = {"reason": "time", "partial": bool(open_gaps),
                    "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        novelty = _novelty(state)
        decision = _profiles.decide_stop(
            aspects_covered=block.get("proportion"),
            novelty_last_rounds=novelty,
            budget={"rounds_used": len(state["rounds"]) - 1,
                    "rounds_budget": resolved["max_rounds"],
                    "time_used_s": elapsed, "time_budget_s": resolved["time_s"]},
            blocked=_all_blocked(block),
            gaps=[g.get("criterion_id") for g in open_gaps])
        stop = _map_stop(decision, block, state, resolved, budget,
                         elapsed, now, t_start)
        if stop is not None:
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        ordered = prioritize_gaps(open_gaps)
        ops = select_ops(state, ordered, resolved["max_ops_per_round"])
        if not ops:
            stop = {"reason": "saturation", "partial": bool(open_gaps),
                    "detail": "no selectable ops for open gaps"}
            break
        for op in ops:
            state["pending_ops"].append(op)
        _execute_ops(state, ops, search_fn, fetch_fn, budget, resolved, now,
                     t_start, checkpoint, round_no=len(state["rounds"]))
        applied, block = _assess_round(state, assess, ledger)
        state["evaluations"] = applied
        new_prop = block.get("proportion")
        delta = (_prop_delta(prev_proportion, new_prop))
        prev_proportion = new_prop
        state["rounds"].append({
            "round": len(state["rounds"]), "kind": "gap",
            "target_gaps": [o["criterion_id"] for o in ops],
            "ops": _summarize_ops(state, ops),
            "new_evidence": len(state["segments"]),
            "coverage": {"status": block["status"], "proportion": new_prop},
            "delta": delta, "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
            "decision": "continue",
        })
        state["consumption"]["rounds"] += 1
        if checkpoint is not None:
            try:
                checkpoint.note_learning(
                    f"round {len(state['rounds']) - 1}: {block['status']} "
                    f"{new_prop} delta={delta}")
            except Exception:
                pass
        if run_dir is not None:
            _state.save(run_dir, state)

    if stop is None:  # max_rounds consumed by the loop guard
        open_gaps = block.get("gaps", [])
        stop = {"reason": "rounds", "partial": bool(open_gaps),
                "detail": f"max_rounds={resolved['max_rounds']} consumed"}
    state["stop"] = stop
    if run_dir is not None:
        _state.save(run_dir, state)
    return _finalize(state, resolved, budget, block, write, audit,
                     t_start, now, run_dir)


def _prop_delta(old, new) -> float | None:
    if old is None or new is None:
        return None
    try:
        return round(float(new) - float(old), 4)
    except (TypeError, ValueError):
        return None


def _novelty(state: dict) -> float:
    """Fraction of new findings in the last round (low = repetition)."""
    if not state["rounds"]:
        return 1.0
    last = state["rounds"][-1]
    ops = last.get("ops", [])
    if not ops:
        return 1.0
    useful = sum(1 for o in ops if o.get("outcome") in ("new_useful", "confirmed"))
    return useful / max(1, len(ops))


def _all_blocked(block: dict) -> bool:
    crits = block.get("criteria", [])
    if not crits:
        return False
    return all(c.get("state") == "blocked" for c in crits if c.get("required", True))


def _map_stop(decision: dict, block: dict, state: dict, resolved: dict,
              budget, elapsed: float, now, t_start) -> dict | None:
    """Translate decide_stop + hard limits into an explicit motive."""
    open_gaps = block.get("gaps", [])
    pending = bool(open_gaps)
    reason = decision.get("stop_reason")
    if reason == "coverage":
        return {"reason": "criteria_ok", "partial": False,
                "detail": f"proportion={block.get('proportion')}"}
    if reason == "novelty":
        return {"reason": "saturation", "partial": pending,
                "detail": f"novelty={_novelty(state):.2f} with "
                          f"{len(open_gaps)} gaps pending"}
    if reason == "blocked":
        return {"reason": "blocked", "partial": pending,
                "detail": "all required criteria blocked"}
    if reason == "budget":
        if elapsed >= resolved["time_s"]:
            return {"reason": "time", "partial": pending,
                    "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
        return {"reason": "budget", "partial": pending,
                "detail": f"rounds/time budget consumed "
                          f"(elapsed={elapsed:.1f}s)"}
    if state["consumption"]["model_calls"] >= resolved["max_model_calls"] and pending:
        return {"reason": "budget", "partial": True,
                "detail": f"max_model_calls={resolved['max_model_calls']}"}
    if state["consumption"]["queries"] >= int(
            resolved.get("budget", {}).get("queries", 0) or 0) and \
            int(resolved.get("budget", {}).get("queries", 0) or 0) > 0 and pending:
        return {"reason": "budget", "partial": True,
                "detail": "query budget consumed"}
    if budget is not None and budget.exhausted() and pending:
        return {"reason": "budget", "partial": True,
                "detail": str(budget.exhausted())}
    if elapsed >= resolved["time_s"]:
        return {"reason": "time", "partial": pending,
                "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
    if reason == "continue":
        return None
    return None


def _summarize_ops(state: dict, ops: list[dict]) -> list[dict]:
    return [{"op_id": o.get("op_id"), "kind": o.get("kind"),
             "channel": o.get("channel"), "target": o.get("target"),
             "outcome": o.get("outcome", "unknown"),
             "new": o.get("outcome") in ("new_useful", "confirmed")}
            for o in ops]


def _execute_ops(state: dict, ops: list[dict], search_fn, fetch_fn, budget,
                 resolved: dict, now, t_start, checkpoint, round_no: int) -> None:
    """Run ops sequentially within limits (concurrency recorded; the offline
    path executes sequentially — no fabricated parallelism)."""
    for op in ops:
        if now() - t_start >= resolved["time_s"]:
            op["status"], op["outcome"] = "failed", "time"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "time"})
            continue
        if not budget.spend("queries"):
            op["status"], op["outcome"] = "failed", "budget"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "budget"})
            continue
        state["consumption"]["queries"] += 1
        state["consumption"]["ops"] += 1
        try:
            hits = _run_search(search_fn, op)
        except TransportError as exc:
            op["status"], op["outcome"] = "failed", "failed"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "failed",
                 "note": str(exc)[:200]})
            state["notes"].append(f"op {op['op_id']} transport failure: {exc}")
            continue
        best = "nogain"
        for hit in (hits or [])[:resolved["vast_max"]]:
            url = hit.get("url") if isinstance(hit, dict) else hit
            if not isinstance(url, str) or not url:
                continue
            if url in state["evidence"] and not state["discovery"]["open"]:
                pass
            if not budget.spend("extractions"):
                state["notes"].append(f"op {op['op_id']}: extraction budget hit")
                break
            try:
                payload = _run_fetch(fetch_fn, op, url)
            except TransportError as exc:
                state["consumption"]["fetches"] += 1
                state["notes"].append(
                    f"op {op['op_id']} fetch failure for {url[:80]}: {exc}")
                best = "failed" if best == "nogain" else best
                continue
            text, qual = _coerce_payload(payload, url)
            state["consumption"]["fetches"] += 1
            outcome = incorporate(state, url, text, op["op_id"], round_no,
                                  qualification=qual)
            if checkpoint is not None and outcome in ("new_useful", "confirmed"):
                try:
                    checkpoint.note_source(url, source=op.get("channel", ""),
                                           content=text)
                except Exception:
                    pass
            if outcome == "new_useful":
                best = "new_useful"
            elif outcome == "confirmed" and best != "new_useful":
                best = "confirmed"
            elif outcome == "duplicate" and best == "nogain":
                best = "duplicate"
            # open discovery: unknown candidates enter the pool, and (when the
            # plan allows) become new tracked entities via plan versioning
            if state["discovery"]["open"] and url not in [
                    c for c in state["discovery"]["candidates"]]:
                state["discovery"]["candidates"].append(url)
        op["status"] = "done" if best != "failed" else "failed"
        op["outcome"] = best
        state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
            {"channel": op.get("channel"), "outcome": best})
        for pending in state["pending_ops"]:
            if pending.get("op_id") == op.get("op_id"):
                pending["status"] = op["status"]
                pending["outcome"] = best


def _run_search(search_fn, op: dict) -> list:
    if search_fn is None:
        return []
    try:
        return search_fn(op["target"], op.get("channel", "web")) or []
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(f"search failed: {exc}")


def _run_fetch(fetch_fn, op: dict, url: str):
    if fetch_fn is None:
        raise TransportError("no fetch_fn injected (offline: nothing to read)")
    try:
        return fetch_fn(url)
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(f"fetch failed for {url[:80]}: {exc}")


def _coerce_payload(payload, url: str) -> tuple[str, dict | None]:
    """Accept str | {text,...} payloads. Qualification is recorded, never
    invented: unknown payloads get a minimal usable record only when they
    carry non-empty text, otherwise excluded."""
    if isinstance(payload, str):
        text = payload
        qual = {"status": "usable", "reason": "injected corpus text",
                "usable_text": text, "excluded": False} if text.strip() else \
            {"status": "empty", "reason": "empty payload", "usable_text": "",
             "excluded": True}
        return text, qual
    if isinstance(payload, dict):
        text = payload.get("text", "") or ""
        qual = {k: payload[k] for k in ("status", "reason", "usable_text",
                                       "excluded") if k in payload}
        if "excluded" not in qual:
            qual["excluded"] = not bool(text.strip())
        qual.setdefault("usable_text", text if not qual["excluded"] else "")
        qual.setdefault("status", "usable" if text.strip() else "empty")
        return text, qual
    return "", {"status": "empty", "reason": "unrecognised payload",
                "usable_text": "", "excluded": True}


def _finalize(state: dict, resolved: dict, budget, block: dict | None,
              write, audit, t_start: float, now, run_dir) -> dict:
    """Finalisation is reserved: write + audit always run on what exists.
    Tokens/costs come from real data only, else 'unknown'."""
    consumption = dict(state["consumption"])
    try:
        used = budget.snapshot().get("used", {}) if budget is not None else {}
        consumption["budget_used"] = used
    except Exception:
        consumption["budget_used"] = "unknown"
    consumption["tokens"] = "unknown"  # shortcut: no per-call attribution on
    consumption["cost_usd"] = "unknown"  # this path (run_budget documents it)
    if block is None:
        block = _ledger.empty_question_coverage(state["run_id"])
    view = {"question": state["question"], "plan": state["plan"],
            "evidence": dict(state["evidence"]),
            "question_coverage": block, "stop": state["stop"],
            "rounds": state["rounds"]}
    try:
        report_text, selection = write(view)
    except Exception as exc:
        state["stop"] = {"reason": "failure", "partial": True,
                         "detail": f"writer failed: {exc}"}
        report_text, selection = "", {"included_urls": [], "cuts": str(exc)}
    state["report"] = {"text": report_text,
                       "sha": _content_hash(report_text or ""),
                       "selection": selection,
                       "words": len((report_text or "").split())}
    try:
        semantic = audit(report_text, dict(state["evidence"]))
    except Exception as exc:
        semantic = {"enabled": True, "verdict_state": "revisão incompleta",
                    "accepted": False, "note": f"auditor failure: {exc}"}
    if not isinstance(semantic, dict):
        semantic = {"enabled": True, "verdict_state": "revisão incompleta",
                    "accepted": False, "note": "auditor returned non-dict"}
    # Trace report<->audited text: the verdict belongs to exactly this hash.
    semantic.setdefault("audited_sha", _content_hash(report_text or ""))
    state["semantic"] = semantic
    # Semantic NEVER moves question coverage: the block above is untouched.
    result = {
        "run_id": state["run_id"], "mode": "adaptive",
        "profile": state["profile"], "resolved": resolved,
        "plan": state["plan"], "plan_versions": state["plan_versions"],
        "question_coverage": block, "stop": state["stop"],
        "partial": bool(state["stop"].get("partial", True)) or not block.get("complete", False),
        "rounds": state["rounds"], "consumption": consumption,
        "report": state["report"], "semantic": semantic,
        "elapsed_s": round(now() - t_start, 3),
    }
    if state["stop"].get("reason") == "criteria_ok":
        result["partial"] = False
    if run_dir is not None:
        _state.save(run_dir, state)
        try:
            from pathlib import Path as _P
            (_P(run_dir) / "report.md").write_text(report_text or "", encoding="utf-8")
            import json as _json
            (_P(run_dir) / "result.json").write_text(
                _json.dumps({k: v for k, v in result.items()
                             if k != "resolved"}, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception:
            pass
    return result
