#!/usr/bin/env python3
"""Question coverage ledger + integration path (offline, synthetic only).

Synthetic generic fixtures (harbor-light maintenance domain); no real
plugins/vendors/licenses touched, no network, no model, no sync_config.
Run: python3 -m pytest tests/test_question_coverage.py -q
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import coverage_ledger as qc
import depth_profiles as dp


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden during question-coverage tests")


sys.addaudithook(offline_guard)


def make_plan(n=6, plan_id="plan-harbor-1"):
    entities = [{"id": f"e{i}", "label": f"harbor section {i}",
                 "required": True} for i in range(1, n + 1)]
    criteria = [{"id": f"c{i}", "label": f"criterion {i}", "required": True,
                 "applies_to": [f"e{i}"]} for i in range(1, n + 1)]
    return {"plan_id": plan_id, "version": 1,
            "entities": entities, "criteria": criteria}


def doc(i):
    return f"https://example.com/docs/harbor-{i}"


def qual_ok(text):
    return {"status": "usable", "reason": "synthetic usable",
            "usable_text": text, "excluded": False}


def qual_excluded(status="insufficient"):
    return {"status": status, "reason": "synthetic excluded",
            "usable_text": "", "excluded": True}


def corpus(n=6, excluded=()):
    ev, q = {}, {}
    for i in range(1, n + 1):
        text = (f"Harbor section {i}: lamp rotation period, power source and "
                f"maintenance log entries for audit {i}.")
        ev[doc(i)] = text
        q[doc(i)] = qual_excluded() if i in excluded else qual_ok(text)
    return ev, q


def ref(i, excerpt="lamp rotation period"):
    return {"url": doc(i), "excerpt": excerpt, "version": "2026-10-18"}


class QuestionCoverage(unittest.TestCase):
    def test_a_six_entities_one_partial(self):
        plan = make_plan(6)
        ev, q = corpus(6)
        block, ratio = qc.build_run_question_coverage(
            plan=plan, run_id="run-a", evidence=ev, qualification=q,
            discovered_urls=[doc(i) for i in range(1, 7)],
            evaluations=[{"criterion_id": "c1", "state": "partial",
                          "justification": "rotation period found; power "
                                           "source still missing",
                          "origin": "manual audit of doc 1",
                          "references": [ref(1)]}])
        self.assertEqual(block["status"], "partial")
        self.assertFalse(block["complete"])
        self.assertEqual(ratio, 0.0)  # partial sustains only its scope
        by_id = {c["id"]: c for c in block["criteria"]}
        self.assertEqual(by_id["c1"]["state"], "partial")
        rest = [by_id[f"c{i}"]["state"] for i in range(2, 7)]
        self.assertEqual(rest, ["uninvestigated"] * 5)
        # partial sustains only its scope: all six still need work
        self.assertEqual(len(block["gaps"]), 6)

    def test_b_docs_without_evaluation_stay_incomplete(self):
        plan = make_plan(6)
        ev, q = corpus(6)  # all six entities HAVE documents
        block, ratio = qc.build_run_question_coverage(
            plan=plan, run_id="run-b", evidence=ev, qualification=q,
            discovered_urls=[doc(i) for i in range(1, 7)])
        # docs != criteria covered: no evaluation -> incomplete preserved
        self.assertFalse(block["complete"])
        self.assertEqual(block["status"], "partial")
        self.assertEqual(ratio, 0.0)
        self.assertEqual(len(block["gaps"]), 6)
        self.assertTrue(all(c["state"] == "uninvestigated"
                            for c in block["criteria"]))

    def test_c_all_mandatory_sufficient_is_complete(self):
        plan = make_plan(3)
        ev, q = corpus(3)
        evals = [{"criterion_id": f"c{i}", "state": "covered",
                  "justification": f"section {i} fully evidenced",
                  "origin": "manual audit", "references": [ref(i)]}
                 for i in range(1, 4)]
        block, ratio = qc.build_run_question_coverage(
            plan=plan, run_id="run-c", evidence=ev, qualification=q,
            discovered_urls=[doc(i) for i in range(1, 4)],
            evaluations=evals)
        self.assertEqual(block["status"], "covered")
        self.assertTrue(block["complete"])
        self.assertEqual(ratio, 1.0)
        self.assertEqual(block["gaps"], [])

    def test_d_sustained_negative_conclusion_covers(self):
        plan = make_plan(2)
        text = ("Harbor section 1 log: no foghorn installed in this section; "
                "absence confirmed by full equipment list.")
        ev = {doc(1): text, doc(2): "Harbor section 2 lamp details."}
        q = {doc(1): qual_ok(text), doc(2): qual_ok(ev[doc(2)])}
        ledger = qc.Ledger(plan, run_id="run-d")
        ledger.set_corpus(ev, q)
        ledger.evaluate("c1", "covered",
                        justification="equipment list is complete and shows "
                                      "no foghorn in section 1",
                        origin="negative_conclusion",
                        references=[ref(1, excerpt="no foghorn installed")])
        block = ledger.compute()
        by_id = {c["id"]: c for c in block["criteria"]}
        self.assertEqual(by_id["c1"]["state"], "covered")
        self.assertEqual(block["proportion"], 0.5)
        self.assertFalse(block["complete"])

    def test_e_missing_excluded_insufficient_never_cover(self):
        plan = make_plan(2)
        ev, q = corpus(2, excluded=(2,))
        ledger = qc.Ledger(plan, run_id="run-e")
        ledger.set_corpus(ev, q)
        with self.assertRaises(ValueError):  # nonexistent reference
            ledger.evaluate("c1", "covered", justification="j",
                            origin="manual audit",
                            references=[{"url": "https://example.com/docs/nope"}])
        with self.assertRaises(ValueError):  # excluded evidence
            ledger.evaluate("c2", "covered", justification="j",
                            origin="manual audit", references=[ref(2)])
        with self.assertRaises(ValueError):  # unqualified url, no refs at all
            ledger.evaluate("c1", "covered", justification="j",
                            origin="manual audit", references=[])
        self.assertEqual(ledger.state_of("c1"), "uninvestigated")
        self.assertEqual(ledger.state_of("c2"), "uninvestigated")

    def test_f_contradictory_blocked_keep_insufficiency(self):
        plan = make_plan(3)
        ev, q = corpus(3)
        ledger = qc.Ledger(plan, run_id="run-f")
        ledger.set_corpus(ev, q)
        ledger.evaluate("c1", "contradictory",
                        justification="doc 1 and doc 2 disagree on period",
                        origin="manual audit", references=[ref(1), ref(2)])
        ledger.evaluate("c2", "blocked",
                        justification="archive fetch failed twice (HTTP 403); "
                                      "access failure, not absence",
                        origin="fetch_attempt",
                        references=[{"url": doc(2),
                                     "excerpt": "403 Forbidden on fetch",
                                     "version": "2026-10-18"}])
        with self.assertRaises(ValueError):  # access failure must not cover
            ledger.evaluate("c3", "covered", justification="j",
                            origin="access_failure", references=[ref(3)])
        block = ledger.compute()
        self.assertEqual(block["status"], "partial")
        self.assertFalse(block["complete"])
        self.assertEqual(block["proportion"], 0.0)
        states = {c["id"]: c["state"] for c in block["criteria"]}
        self.assertEqual(states, {"c1": "contradictory", "c2": "blocked",
                                  "c3": "uninvestigated"})
        self.assertEqual(len(block["gaps"]), 3)

    def test_g_no_plan_is_unevaluated_null(self):
        block, ratio = qc.build_run_question_coverage(
            plan=None, run_id="run-g", evidence={doc(1): "text"},
            discovered_urls=[doc(1)])
        self.assertEqual(block["status"], "unevaluated")
        self.assertIsNone(block["proportion"])
        self.assertIsNone(ratio)
        self.assertFalse(block["complete"])
        self.assertEqual(block["criteria"], [])
        query, depth, plan_source = qc.parse_coverage_cli(["my question"])
        self.assertEqual((query, depth, plan_source),
                         ("my question", "light", None))
        query, depth, plan_source = qc.parse_coverage_cli(
            ["my question", "deep", "--coverage-plan", "p.json"])
        self.assertEqual((query, depth, plan_source),
                         ("my question", "deep", "p.json"))

    def test_h_semantic_approval_never_clears_gaps(self):
        plan = make_plan(2)
        ev, q = corpus(2)
        for semantic in ({"verdict_state": "aceito", "accepted": True},
                         {"verdict_state": "não revisado semanticamente",
                          "accepted": False}):
            with self.subTest(semantic=semantic["verdict_state"]):
                block, _ = qc.build_run_question_coverage(
                    plan=plan, run_id="run-h", evidence=ev, qualification=q,
                    discovered_urls=[doc(1), doc(2)], semantic=semantic)
                self.assertEqual(block["status"], "partial")
                self.assertFalse(block["complete"])
                self.assertEqual(len(block["gaps"]), 2)  # gaps stay visible

    def test_i_serialization_recovery_never_mixes_runs(self):
        plan = make_plan(2)
        ev, q = corpus(2)
        a = qc.Ledger(plan, run_id="run-i-A")
        a.set_corpus(ev, q)
        a.evaluate("c1", "covered", justification="j", origin="manual audit",
                   references=[ref(1)])
        payload = json.loads(json.dumps(a.to_json()))
        b = qc.Ledger.from_json(payload, run_id="run-i-A")
        self.assertEqual(b.compute(), a.compute())
        with self.assertRaises(ValueError):
            qc.Ledger.from_json(payload, run_id="run-i-B")  # runs never mix
        c = qc.Ledger(plan, run_id="run-i-B")
        self.assertEqual(c.state_of("c1"), "uninvestigated")  # isolated

    def test_j_integrated_path_emits_question_coverage_artifact(self):
        plan = make_plan(2)
        ev, q = corpus(2)
        report = ("Harbor notes. Source: https://example.com/docs/harbor-1 "
                  "covers rotation.")
        block, ratio = qc.build_run_question_coverage(
            plan=plan, run_id="run-j", evidence=ev, qualification=q,
            discovered_urls=[doc(1), doc(2)], report_text=report,
            evaluations=[{"criterion_id": "c1", "state": "covered",
                          "justification": "rotation evidenced",
                          "origin": "manual audit", "references": [ref(1)]}],
            semantic={"verdict_state": "aceito com ressalvas",
                      "accepted": False})
        # same artifact the integration persists inside _depth.json
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "run-j_depth.json"
            artifact.write_text(json.dumps(
                {"run_id": "run-j", "stop_reason": "flow_end",
                 "question_coverage": block}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            reloaded = json.loads(artifact.read_text(encoding="utf-8"))
        qcb = reloaded["question_coverage"]
        for key in ("status", "complete", "plan_id", "proportion",
                    "criteria", "gaps", "references", "observed_counts"):
            self.assertIn(key, qcb)
        self.assertEqual(qcb["plan_id"], "plan-harbor-1")
        self.assertEqual(qcb["observed_counts"]["discovered"], 2)
        self.assertEqual(qcb["observed_counts"]["cited"], 1)
        # integrated wiring present in the real entrypoint (AST, no import
        # of its network hooks)
        src = (ROOT / "gpt_researcher_integration.py").read_text()
        tree = ast.parse(src)
        self.assertIn("--coverage-plan", src)
        self.assertIn("question_coverage", src)
        self.assertIn("build_run_question_coverage", src)
        # final decision uses the real measurement, never fictitious 1.0/0.5
        self.assertNotIn("aspects_covered=1.0 if not _gaps else 0.5", src)
        unknown = dp.decide_stop(aspects_covered=None,
                                 novelty_last_rounds=0.0, gaps=[])
        self.assertNotEqual(unknown.get("stop_reason"), "coverage")
        measured = dp.decide_stop(aspects_covered=ratio,
                                  novelty_last_rounds=0.0, gaps=["c2"])
        self.assertEqual(measured["stop_reason"], "continue")

    def test_plan_rejects_pre_satisfied(self):
        plan = make_plan(1)
        plan["pre_satisfied"] = ["c1"]
        with self.assertRaises(ValueError):
            qc.validate_plan(plan)
        plan2 = make_plan(1)
        plan2["criteria"][0]["satisfied"] = True
        with self.assertRaises(ValueError):
            qc.validate_plan(plan2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
