#!/usr/bin/env python3
"""Adaptive research loop, offline (deterministic doubles at the boundaries).

The COORDINATOR is always the real code under test — never mocked. Only its
boundaries are faked: model frontier (plan JSON), search/fetch (in-memory
corpus, controlled failures), assessor (explicit marker evaluations),
writer/auditor (deterministic), clock (controlled, no sleeps).

Two question types: tool COMPARISON (six harbor lamp tools) and EXPLANATORY
investigation (estuary tide delay). No fixture-name rules anywhere: scenarios
are synthetic harbor/estuary domains.

Run: python3 -m pytest tests/test_adaptive_research.py -q
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_planner as apl
import adaptive_state as ast_

LOCAL_URL = "https://example.com/docs/{}"


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden during adaptive tests")


sys.addaudithook(offline_guard)


# ---------------------------------------------------------------- fakes

class FakeModel:
    """Callable model frontier returning canned plans. Modes: valid (first
    call garbage -> exercises the limited repair), always_invalid, presatisfied."""

    def __init__(self, plans: dict, mode: str = "valid"):
        self.plans = plans
        self.mode = mode
        self.calls = 0
        self.prompts = []

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        self.prompts.append(prompt)
        if self.mode == "always_invalid":
            return "not json at all {{{"
        if self.mode == "presatisfied":
            p = dict(self.plans["default"])
            p["pre_satisfied"] = ["c1"]
            return json.dumps(p)
        if self.mode == "valid" and self.calls == 1:
            return "```json\n" + json.dumps(self.plans["default"]) + "\n```"
        for key, plan in self.plans.items():
            if key != "default" and key in prompt:
                return json.dumps(plan)
        return json.dumps(self.plans["default"])


class FakeCorpus:
    """In-memory search/fetch. transport_fail: urls whose fetch raises.
    search_fail_on: call numbers (1-based) whose search raises."""

    def __init__(self, docs: dict, transport_fail=(), search_fail_on=()):
        self.docs = dict(docs)
        self.transport_fail = set(transport_fail)
        self.search_fail_on = set(search_fail_on)
        self.search_calls = []
        self.fetch_calls = []
        self.failures = []

    def search(self, target: str, channel: str = "web"):
        self.search_calls.append((target, channel))
        if len(self.search_calls) in self.search_fail_on:
            raise ac.TransportError("simulated transport failure (search)")
        out = []
        for url in self.docs:
            out.append({"url": url, "title": url.rsplit("/", 1)[-1],
                        "snippet": str(self.docs[url])[:200]})
        return out

    def fetch(self, url: str):
        self.fetch_calls.append(url)
        if url in self.transport_fail:
            self.failures.append(url)
            raise ac.TransportError(f"simulated transport failure: {url}")
        if url not in self.docs:
            raise ac.TransportError(f"unknown url: {url}")
        return self.docs[url]


class FakeClock:
    def __init__(self, step: float = 0.0):
        self.t = [0.0]
        self.step = step
        self.calls = 0

    def __call__(self):
        self.calls += 1
        self.t[0] += self.step
        return self.t[0]

    def advance(self, dt: float):
        self.t[0] += dt


def marker_assessor(blocked_for=(), discoveries=()):
    """Explicit evaluations from COVER:/PARTIAL:/CONTRA:/NEG: markers in the
    obtained text. blocked_for: criterion ids reported blocked when their
    mapped url fetch failed (closure knowledge, as a model assessor with
    attempt history would have)."""
    def assess(plan, evidence, qualification):
        evals = []
        for crit in plan.get("criteria", []):
            cid = crit["id"]
            hits = [(u, t) for u, t in evidence.items() if f"COVER:{cid}" in t]
            if hits:
                url = hits[0][0]
                evals.append({"criterion_id": cid, "state": "covered",
                              "justification": f"marker evidence in {url}",
                              "origin": "marker audit",
                              "references": [{"url": url, "excerpt": f"COVER:{cid}"}]})
                continue
            parts = [(u, t) for u, t in evidence.items() if f"PARTIAL:{cid}" in t]
            if parts:
                url = parts[0][0]
                evals.append({"criterion_id": cid, "state": "partial",
                              "justification": f"only part of {cid} evidenced",
                              "origin": "marker audit",
                              "references": [{"url": url, "excerpt": f"PARTIAL:{cid}"}]})
                continue
            contras = [u for u, t in evidence.items() if f"CONTRA:{cid}" in t]
            if len(contras) >= 2 or (len(contras) == 1 and len(evidence) >= 2):
                evals.append({"criterion_id": cid, "state": "contradictory",
                              "justification": "sources disagree on " + cid,
                              "origin": "marker audit",
                              "references": [{"url": u, "excerpt": f"CONTRA:{cid}"}
                                             for u in contras] or
                                            [{"url": next(iter(evidence)),
                                              "excerpt": "context"}]})
                continue
            negs = [(u, t) for u, t in evidence.items() if f"NEG:{cid}" in t]
            if negs:
                url = negs[0][0]
                evals.append({"criterion_id": cid, "state": "covered",
                              "justification": f"absence of {cid} sustained by full listing",
                              "origin": "negative_conclusion",
                              "references": [{"url": url, "excerpt": f"NEG:{cid}"}]})
                continue
            if cid in blocked_for:
                evals.append({"criterion_id": cid, "state": "blocked",
                              "justification": "fetch failed twice; access failure, not absence",
                              "origin": "fetch_attempt",
                              "references": []})
                continue
        for eid, ecrit in discoveries:
            for u, t in evidence.items():
                if f"NEW:{eid}" in t:
                    if evals:
                        evals[0].setdefault("propose_entity", None)
                        evals[0]["propose_entity"] = {
                            "entity": {"id": eid, "label": eid},
                            "criteria": [ecrit]}
                    break
        return evals
    return assess


def fake_writer(view):
    cov = view.get("question_coverage", {})
    lines = [f"# {view['question']}", ""]
    for crit in cov.get("criteria", []):
        lines.append(f"## {crit.get('label')} [{crit.get('state')}]")
        lines.append(crit.get("justification") or "-")
    if cov.get("gaps"):
        lines.append("PENDING: " + ",".join(g["criterion_id"] for g in cov["gaps"]))
    text = "\n".join(lines)
    return text, {"included_urls": sorted(view.get("evidence", {})),
                  "cuts": "none"}


def fake_auditor_approved(report, evidence):
    return {"enabled": True, "verdict_state": "aceito", "accepted": True,
            "claims": 1, "summary": {"sustained": 1}}


def fake_auditor_off(report, evidence):
    return {"enabled": False, "verdict_state": "não revisado semanticamente",
            "accepted": False}


def fake_auditor_incomplete(report, evidence):
    return {"enabled": True, "verdict_state": "revisão incompleta",
            "accepted": False, "note": "provider 502"}


# ---------------------------------------------------------------- plans

def comparison_plan(n=6, open_disc=False, pid="cmp-harbor-1"):
    entities = [{"id": f"e{i}", "label": f"harbor lamp tool {i}", "required": True}
                for i in range(1, n + 1)]
    criteria = [{"id": f"c{i}", "label": f"rotation and power of tool {i}",
                 "required": True, "applies_to": [f"e{i}"]}
                for i in range(1, n + 1)]
    return {"plan_id": pid, "version": 1,
            "question": "Compare harbor lamp tools",
            "purpose": "choose a maintainable tool",
            "entities": entities, "criteria": criteria,
            "open_discovery": {"needed": open_disc, "need": "other tools"},
            "initial_paths": ["Compare harbor lamp tools"],
            "restrictions": "none", "premises": []}


def explanatory_plan(pid="exp-tide-1"):
    entities = [{"id": e, "label": e, "required": True} for e in
                ["mechanism", "actors", "data", "alternatives"]]
    criteria = [{"id": f"c-{e}", "label": f"factor {e}", "required": True,
                 "applies_to": [e]} for e in
                ["mechanism", "actors", "data", "alternatives"]]
    return {"plan_id": pid, "version": 1,
            "question": "Explain the estuary tide delay and its consequences",
            "purpose": "understand causes and scenarios",
            "entities": entities, "criteria": criteria,
            "open_discovery": {"needed": False},
            "initial_paths": ["Explain the estuary tide delay and its consequences"],
            "restrictions": "none", "premises": ["qualitative factors suffice"]}


def doc(i, marker=""):
    return LOCAL_URL.format(f"harbor-{i}"), \
        f"Harbor note {i}: lamp rotation, power source. {marker}".strip()


# ---------------------------------------------------------------- tests

class AdaptiveResearch(unittest.TestCase):
    maxDiff = 4000

    def test_a_six_one_partial_semantic_favorable(self):
        urls = {}
        for i in range(1, 7):
            u, t = doc(i, "PARTIAL:c1" if i == 1 else "")
            urls[u] = t
        corp = FakeCorpus(urls)
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(6), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_approved, clock=FakeClock())
        qc = res["question_coverage"]
        self.assertEqual(qc["status"], "partial")
        self.assertFalse(qc["complete"])
        self.assertEqual(qc["proportion"], 0.0)  # partial sustains only itself
        self.assertEqual(len(qc["gaps"]), 6)
        self.assertTrue(res["partial"])
        self.assertTrue(res["semantic"]["accepted"])  # favorable semantic...
        self.assertEqual(qc["status"], "partial")    # ...moves nothing

    def test_b_docs_without_support_stay_incomplete(self):
        corp = FakeCorpus({u: t for u, t in (doc(i) for i in range(1, 7))})
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(6), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(),  # no markers -> no evaluations
            writer_fn=fake_writer, auditor_fn=fake_auditor_off, clock=FakeClock())
        qc = res["question_coverage"]
        self.assertFalse(qc["complete"])
        self.assertEqual(qc["proportion"], 0.0)
        self.assertTrue(all(c["state"] == "uninvestigated" for c in qc["criteria"]))

    def test_c_complete_all_covered(self):
        corp = FakeCorpus({u: t for u, t in
                           (doc(i, f"COVER:c{i}") for i in range(1, 4))})
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(3), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_approved, clock=FakeClock())
        self.assertEqual(res["stop"]["reason"], "criteria_ok")
        self.assertFalse(res["partial"])
        self.assertEqual(res["question_coverage"]["proportion"], 1.0)
        self.assertTrue(res["question_coverage"]["complete"])

    def test_d_gap_resolved_between_rounds(self):
        # explanatory question: mechanism evidenced only after a gap round
        u1 = LOCAL_URL.format("tide-mechanism")
        u2 = LOCAL_URL.format("tide-actors")
        calls = {"n": 0}

        def search(target, channel="web"):
            calls["n"] += 1
            corp.search_calls.append((target, channel))
            if calls["n"] == 1:
                return [{"url": u1}]
            return [{"url": u1}, {"url": u2}]

        docs = {u1: "Tide note: channel shape delays the tide. COVER:c-mechanism",
                u2: "Harbor log: ferry operators adjust schedules. COVER:c-actors"}
        corp = FakeCorpus(docs)
        corp.search = search
        res = ac.run_adaptive(
            "Explain the estuary tide delay and its consequences", profile="light",
            plan={"plan_id": "exp-tide-d", "version": 1,
                  "question": "Explain the estuary tide delay and its consequences",
                  "entities": [{"id": "mechanism", "label": "mechanism", "required": True},
                               {"id": "actors", "label": "actors", "required": True}],
                  "criteria": [{"id": "c-mechanism", "label": "mechanism", "required": True,
                                "applies_to": ["mechanism"]},
                               {"id": "c-actors", "label": "actors", "required": True,
                                "applies_to": ["actors"]}],
                  "initial_paths": ["Explain the estuary tide delay and its consequences"]},
            search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_rounds": 3})
        gap_rounds = [r for r in res["rounds"] if r["kind"] == "gap"]
        self.assertTrue(gap_rounds, "expected at least one gap round")
        self.assertIn("c-actors", gap_rounds[0]["target_gaps"])
        self.assertEqual(res["question_coverage"]["proportion"], 1.0)
        self.assertEqual(res["stop"]["reason"], "criteria_ok")
        deltas = [r["delta"] for r in gap_rounds]
        self.assertTrue(any((d or 0) > 0 for d in deltas))
        for r in res["rounds"]:
            for key in ("target_gaps", "ops", "new_evidence", "delta",
                        "insufficiencies", "decision"):
                self.assertIn(key, r)
        ops = [o for r in res["rounds"] for o in r["ops"]]
        self.assertEqual(len(ops), len(corp.search_calls) * 1)  # no fabricated ops
        self.assertIn(u2, res["report"]["selection"]["included_urls"])

    def test_e_persistent_gap_partial_stop_rounds(self):
        u1, t1 = doc(1, "COVER:c1")
        bad = LOCAL_URL.format("harbor-blocked")
        corp = FakeCorpus({u1: t1, bad: "unreachable"}, transport_fail=(bad,))
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(2), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(blocked_for=("c2",)), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_rounds": 2, "max_ops_per_round": 1})
        qc = res["question_coverage"]
        by_id = {c["id"]: c for c in qc["criteria"]}
        self.assertEqual(by_id["c2"]["state"], "blocked")
        self.assertTrue(res["partial"])
        self.assertIn(res["stop"]["reason"], ("rounds", "budget", "time", "saturation"))
        self.assertTrue(any(g["criterion_id"] == "c2" for g in qc["gaps"]))
        # channel varies after flat attempts (no indefinite repetition)
        gap_ops = [r["ops"] for r in res["rounds"] if r["kind"] == "gap"]
        self.assertTrue(gap_ops)
        self.assertTrue(all(o["outcome"] in ("failed", "duplicate", "nogain")
                            for ops in gap_ops for o in ops))

    def test_f_open_discovery_new_candidate(self):
        u1, t1 = doc(1, "COVER:c1 NEW:e7")
        corp = FakeCorpus({u1: t1,
                           LOCAL_URL.format("harbor-7"): "New tool note. COVER:c-e7"})
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(1, open_disc=True), search_fn=corp.search,
            fetch_fn=corp.fetch,
            assess_fn=marker_assessor(
                discoveries=[("e7", {"id": "c-e7", "label": "tool 7 evidence",
                                     "required": True})]),
            writer_fn=fake_writer, auditor_fn=fake_auditor_off, clock=FakeClock())
        self.assertEqual(len(res["plan_versions"]), 2)
        ids = [e["id"] for e in res["plan"]["entities"]]
        self.assertIn("e1", ids)  # user requirement preserved
        self.assertIn("e7", ids)  # new candidate incorporated
        ref_urls = [r["url"] for r in res["question_coverage"]["references"]]
        self.assertIn(LOCAL_URL.format("harbor-7"), ref_urls)

    def test_g_contradiction_investigated_uncertain(self):
        u1 = LOCAL_URL.format("tide-a")
        u2 = LOCAL_URL.format("tide-b")
        u3 = LOCAL_URL.format("tide-c")
        corp = FakeCorpus({u1: "Gauge A: delay is two hours. CONTRA:c-mechanism",
                           u2: "Gauge B: delay is twenty minutes. CONTRA:c-mechanism",
                           u3: "Review: gauges disagree; cause unclear. CONTRA:c-mechanism"})
        res = ac.run_adaptive(
            "Explain the estuary tide delay and its consequences", profile="light",
            plan={"plan_id": "exp-tide-g", "version": 1,
                  "question": "Explain the estuary tide delay and its consequences",
                  "entities": [{"id": "mechanism", "label": "mechanism", "required": True}],
                  "criteria": [{"id": "c-mechanism", "label": "mechanism", "required": True,
                                "applies_to": ["mechanism"]}],
                  "initial_paths": ["Explain the estuary tide delay and its consequences"]},
            search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_rounds": 2})
        qc = res["question_coverage"]
        self.assertEqual(qc["criteria"][0]["state"], "contradictory")
        self.assertTrue(res["partial"])
        # divergence is a finding with uncertainty, not a silent cover
        self.assertNotEqual(qc["status"], "covered")

    def test_h_saturation_without_inflating(self):
        urls = {}
        for i in range(1, 4):
            u, t = doc(i, f"COVER:c{i}" if i < 3 else "")
            urls[u] = t
        # third doc repeats the first two forever: no new material for c3
        seen = {"n": 0}

        def search(target, channel="web"):
            seen["n"] += 1
            corp.search_calls.append((target, channel))
            return [{"url": u} for u in urls]
        corp = FakeCorpus(urls)
        corp.search = search
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(3), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_rounds": 4, "max_ops_per_round": 1})
        self.assertEqual(res["stop"]["reason"], "saturation")
        self.assertTrue(res["partial"])  # pending gap: saturation != complete
        self.assertEqual(res["question_coverage"]["proportion"], 2 / 3)
        total_ops = sum(len(r["ops"]) for r in res["rounds"])
        self.assertEqual(total_ops, len(corp.search_calls))  # nothing fabricated
        self.assertEqual(res["consumption"]["docs"], 3)  # duplicates never inflate

    def test_i1_round_limit_with_controlled_clock(self):
        corp = FakeCorpus({u: t for u, t in (doc(i) for i in range(1, 3))})
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(2), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_rounds": 0})
        self.assertEqual(res["stop"]["reason"], "rounds")
        self.assertTrue(res["partial"])
        self.assertEqual(len([r for r in res["rounds"] if r["kind"] == "gap"]), 0)

    def test_i2_time_limit_with_controlled_clock(self):
        corp = FakeCorpus({u: t for u, t in (doc(i) for i in range(1, 3))})
        clock = FakeClock(step=6.0)
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(2), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=clock,
            overrides={"max_rounds": 5, "time_s": 10})
        self.assertEqual(res["stop"]["reason"], "time")
        self.assertTrue(res["partial"])
        self.assertGreater(clock.calls, 0)  # clock really drove the stop; no sleeps

    def test_i3_model_call_budget(self):
        corp = FakeCorpus({u: t for u, t in (doc(i) for i in range(1, 2))})
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(1), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_off, clock=FakeClock(),
            overrides={"max_model_calls": 0})
        self.assertEqual(res["stop"]["reason"], "budget")
        self.assertTrue(res["partial"])

    def test_j_invalid_plan_never_favourable(self):
        corp = FakeCorpus({u: t for u, t in (doc(1, "COVER:c1"),)})
        model = FakeModel({"default": comparison_plan(1)}, mode="always_invalid")
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            model_client=model, search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_approved, clock=FakeClock())
        self.assertEqual(res["stop"]["reason"], "failure")
        self.assertTrue(res["partial"])
        self.assertEqual(res["question_coverage"]["status"], "unevaluated")
        self.assertFalse(res["question_coverage"]["complete"])
        self.assertEqual(model.calls, 2)  # one repair attempt, counted

    def test_j2_presatisfied_plan_rejected(self):
        corp = FakeCorpus({})
        model = FakeModel({"default": comparison_plan(1)}, mode="presatisfied")
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            model_client=model, search_fn=corp.search, fetch_fn=corp.fetch,
            clock=FakeClock())
        self.assertEqual(res["stop"]["reason"], "failure")
        self.assertFalse(res["question_coverage"]["complete"])

    def test_j3_transport_failure_never_covers(self):
        corp = FakeCorpus({LOCAL_URL.format("harbor-1"): "x"},
                         transport_fail=(LOCAL_URL.format("harbor-1"),))
        res = ac.run_adaptive(
            "Compare harbor lamp tools", profile="light",
            plan=comparison_plan(1), search_fn=corp.search, fetch_fn=corp.fetch,
            assess_fn=marker_assessor(), writer_fn=fake_writer,
            auditor_fn=fake_auditor_approved, clock=FakeClock(),
            overrides={"max_rounds": 1})
        states = [c["state"] for c in res["question_coverage"]["criteria"]]
        self.assertNotIn("covered", states)
        self.assertNotIn("partial", states)
        self.assertTrue(res["partial"])

    def test_k_checkpoint_resume_no_loss_no_repetition(self):
        u1, t1 = doc(1, "COVER:c1")
        u2, t2plain = doc(2)
        u2t2 = "Harbor note 2: lamp rotation, power source. COVER:c2"
        corp = FakeCorpus({u1: t1, u2: t2plain})
        with tempfile.TemporaryDirectory() as tmp:
            first = ac.run_adaptive(
                "Compare harbor lamp tools", profile="light",
                plan=comparison_plan(2), search_fn=corp.search, fetch_fn=corp.fetch,
                assess_fn=marker_assessor(), writer_fn=fake_writer,
                auditor_fn=fake_auditor_off, clock=FakeClock(),
                run_dir=tmp, run_id="run-k",
                overrides={"max_rounds": 0})
            self.assertEqual(first["stop"]["reason"], "rounds")
            self.assertTrue(first["partial"])  # c2 still open
            # simulate a crash mid-op: inject an in-progress op, then resume
            st = ast_.load(tmp, "run-k")
            st["pending_ops"].append({"op_id": "crashed-1", "kind": "gap_query",
                                      "channel": "web", "target": "x",
                                      "criterion_id": "c2", "status": "in-progress"})
            ast_.save(tmp, st)
            corp2 = FakeCorpus({u1: t1, u2: u2t2})
            second = ac.run_adaptive(
                "Compare harbor lamp tools", profile="light", resume=True,
                search_fn=corp2.search, fetch_fn=corp2.fetch,
                assess_fn=marker_assessor(), writer_fn=fake_writer,
                auditor_fn=fake_auditor_off, clock=FakeClock(),
                run_dir=tmp, run_id="run-k",
                overrides={"max_rounds": 3})
            # completed work kept: c1 still covered; u1 revalidated (duplicate,
            # not double-counted), u2's new excerpt incorporated
            by_id = {c["id"]: c["state"]
                     for c in second["question_coverage"]["criteria"]}
            self.assertEqual(by_id["c1"], "covered")
            self.assertEqual(by_id["c2"], "covered")
            self.assertEqual(second["question_coverage"]["proportion"], 1.0)
            self.assertEqual(second["stop"]["reason"], "criteria_ok")
            self.assertEqual(len(second["rounds"]), len(first["rounds"]) + 1)
            reloaded = ast_.load(tmp, "run-k")
            statuses = [o.get("status") for o in reloaded["pending_ops"]]
            self.assertNotIn("in-progress", statuses)
            self.assertIn("interrupted", statuses)
            self.assertEqual(len(reloaded["segments"]), 3)  # u1, u2, u2-new
            self.assertEqual(len(corp2.fetch_calls), 2)  # only the gap round

    def test_l_semantic_dimensions_independent(self):
        def one_run(auditor):
            u1, t1 = doc(1, "COVER:c1")
            u2, t2 = doc(2)
            corp = FakeCorpus({u1: t1, u2: t2})
            return ac.run_adaptive(
                "Compare harbor lamp tools", profile="light",
                plan=comparison_plan(2), search_fn=corp.search, fetch_fn=corp.fetch,
                assess_fn=marker_assessor(), writer_fn=fake_writer,
                auditor_fn=auditor, clock=FakeClock(),
                overrides={"max_rounds": 1})
        blocks = [one_run(a)["question_coverage"] for a in
                  (fake_auditor_off, fake_auditor_incomplete, fake_auditor_approved)]
        for b in blocks:
            b.pop("run_id", None)  # identity differs; content must not
            self.assertEqual(b["status"], "partial")
            self.assertEqual(b["proportion"], 0.5)
        self.assertEqual(blocks[0], blocks[1])
        self.assertEqual(blocks[1], blocks[2])

    def test_m_cli_wiring_legacy_untouched(self):
        src = (ROOT / "gpt_researcher_integration.py").read_text()
        tree = ast.parse(src)
        self.assertIn("--mode", src)
        self.assertIn("adaptive", src)
        self.assertIn("run_adaptive", src)
        self.assertIn("quick_search", src)  # targeted ops, not repeated full runs
        # legacy path still parses via the untouched ledger CLI contract
        import coverage_ledger as qc
        q, d, p = qc.parse_coverage_cli(["my question"])
        self.assertEqual((q, d, p), ("my question", "light", None))
        # exactly two conduct_research() call sites: legacy + one adaptive sweep
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "conduct_research"]
        self.assertEqual(len(calls), 2)

    def test_n_persisted_states_complete(self):
        corp = FakeCorpus({u: t for u, t in (doc(1, "COVER:c1"),)})
        with tempfile.TemporaryDirectory() as tmp:
            rd = str(Path(tmp) / "run-n")
            res = ac.run_adaptive(
                "Compare harbor lamp tools", profile="light",
                plan=comparison_plan(1), search_fn=corp.search, fetch_fn=corp.fetch,
                assess_fn=marker_assessor(), writer_fn=fake_writer,
                auditor_fn=fake_auditor_off, clock=FakeClock(),
                run_dir=rd, run_id="run-n")
            for name in ("state.json", "report.md", "result.json"):
                self.assertTrue((Path(rd) / name).is_file(), name)
            self.assertFalse(list(Path(rd).glob("*.tmp-*")))  # atomic writes
            state = json.loads((Path(rd) / "state.json").read_text())
            for key in ("run_id", "question", "config_applied", "plan",
                        "plan_versions", "evidence", "segments", "evaluations",
                        "rounds", "consumption", "pending_ops", "stop"):
                self.assertIn(key, state)
            self.assertIn(res["stop"]["reason"],
                          ("criteria_ok", "saturation", "rounds", "budget",
                           "time", "blocked", "failure"))
            self.assertNotEqual(res["stop"]["reason"],
                                res["question_coverage"]["status"])
            for r in state["rounds"]:
                for key in ("target_gaps", "ops", "new_evidence", "delta",
                            "insufficiencies", "decision"):
                    self.assertIn(key, r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
