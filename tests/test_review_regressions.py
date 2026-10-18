"""Independent offline regressions for adaptive research HEAD 981c030.

Copy this file into the project's tests/ directory. Run with:
    python -m unittest discover -s tests -p test_review_regressions.py -v

These tests state desired behavior. Failures against 981c030 demonstrate
review findings; they do not change the supplied implementation.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Independent review is offline")


sys.addaudithook(deny_network)

import adaptive_coordinator as ac
import adaptive_state as st
import coverage_ledger as cl
import run_budget as rb


URL = "https://example.org/evidence/one"
OTHER = "https://example.org/evidence/two"


def plan(n=1):
    return {
        "plan_id": "independent-review", "version": 1,
        "entities": [{"id": f"e{i}", "required": True} for i in range(n)],
        "criteria": [{"id": f"c{i}", "label": f"criterion {i}",
                      "required": True, "applies_to": [f"e{i}"]}
                     for i in range(n)],
        "initial_paths": ["initial review query"],
    }


def qual(text):
    return {"status": "usable", "usable_text": text, "excluded": False}


def evaluation(cid="c0", url=URL, entity_id=None):
    result = {"criterion_id": cid, "state": "covered",
              "justification": "Explicit assessment of the obtained evidence",
              "origin": "review boundary", "references": [{"url": url}]}
    if entity_id is not None:
        result["entity_id"] = entity_id
    return result


def writer(view):
    return "A bounded review report", {"included_urls": [], "cuts": "test boundary"}


def auditor(report, evidence):
    return {"enabled": False, "accepted": False}


class ReviewRegressions(unittest.TestCase):
    def test_r01_one_entity_does_not_cover_shared_criterion_for_six(self):
        p = plan(6)
        p["criteria"] = [{"id": "shared", "required": True,
                          "applies_to": [f"e{i}" for i in range(6)]}]
        ledger = cl.Ledger(p)
        ledger.set_corpus({URL: "Evidence about entity e0 only"},
                          {URL: qual("Evidence about entity e0 only")})
        ledger.evaluate("shared", "covered", "Evidence for e0", "manual review",
                        [{"url": URL}], entity_id="e0")
        block = ledger.compute()
        self.assertFalse(block["complete"], json.dumps(block))

    def test_r02_nineteen_of_twenty_mandatory_is_partial(self):
        result = ac.run_adaptive(
            "Answer twenty mandatory criteria", plan=plan(20),
            search_fn=lambda *_: [{"url": URL}],
            fetch_fn=lambda _: "Obtained facts for criteria zero through eighteen",
            assess_fn=lambda *_: [evaluation(f"c{i}") for i in range(19)],
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0,
        )
        self.assertFalse(result["question_coverage"]["complete"])
        self.assertTrue(result["partial"], json.dumps({
            "coverage": result["question_coverage"]["proportion"],
            "stop": result["stop"], "partial": result["partial"]}))

    def test_r03_zero_model_allowance_prevents_planner_transport(self):
        calls = []
        def model(prompt):
            calls.append(prompt)
            return json.dumps(plan())
        ac.run_adaptive(
            "A question", model_client=model, search_fn=lambda *_: [],
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0,
            overrides={"max_model_calls": 0},
        )
        self.assertEqual(len(calls), 0, "Planner ran despite zero model allowance")

    def test_r04_model_accounting_includes_assessment_write_and_audit(self):
        calls = []
        def transport(stage):
            calls.append(stage)
        def model(prompt):
            transport("plan")
            return json.dumps(plan())
        def assess(*_):
            transport("assessment")
            return []
        def write(view):
            transport("write")
            return writer(view)
        def audit(report, evidence):
            transport("audit")
            return auditor(report, evidence)
        result = ac.run_adaptive(
            "A question", model_client=model, search_fn=lambda *_: [],
            assess_fn=assess, writer_fn=write, auditor_fn=audit,
            clock=lambda: 0.0, overrides={"max_rounds": 0},
        )
        self.assertEqual(result["consumption"]["model_calls"], len(calls),
                         f"Actual boundary calls: {calls}")

    def test_r05_error_payload_is_not_usable_evidence(self):
        _, qualification = ac._coerce_payload(
            {"status": "error", "text": "HTTP 403 Forbidden"}, URL)
        self.assertTrue(qualification["excluded"], str(qualification))

    def test_r06_empty_evidence_cannot_justify_covered(self):
        ledger = cl.Ledger(plan())
        ledger.set_corpus({URL: ""}, {URL: qual("")})
        with self.assertRaises(ValueError):
            ledger.evaluate("c0", "covered", "A claim", "manual review",
                            [{"url": URL}])

    def test_r07_read_source_reads_target_without_searching(self):
        state = st.new_state("A question")
        searches, fetched = [], []
        def search(target, channel):
            searches.append(target)
            return [{"url": OTHER}]
        def fetch(url):
            fetched.append(url)
            return "Actual obtained source text"
        op = {"op_id": "read-1", "kind": "read_source", "channel": "web",
              "target": URL, "criterion_id": "c0", "status": "in-progress"}
        resolved = ac.resolve_adaptive("light")
        ac._execute_ops(state, [op], search, fetch, rb.Budget(resolved["budget"]),
                        resolved, lambda: 0.0, 0.0, None, 0)
        self.assertEqual(searches, [], f"read_source searched {searches}")
        self.assertEqual(fetched, [URL])

    def test_r08_real_interruption_recovers_completed_collection(self):
        fetches, crashed = [], [False]
        def search(*_):
            return [{"url": URL}, {"url": OTHER}]
        def fetch(url):
            fetches.append(url)
            if url == OTHER and not crashed[0]:
                crashed[0] = True
                raise KeyboardInterrupt("Simulated actual mid-collection interruption")
            return "Obtained evidence for " + url
        def assess(_plan, evidence, _qualification):
            return [evaluation()] if URL in evidence else []
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyboardInterrupt):
                ac.run_adaptive(
                    "A question", plan=plan(), search_fn=search, fetch_fn=fetch,
                    assess_fn=assess, writer_fn=writer, auditor_fn=auditor,
                    clock=lambda: 0.0, run_dir=tmp, run_id="interrupted-review",
                    overrides={"max_rounds": 1})
            ac.run_adaptive(
                "A question", resume=True, search_fn=search, fetch_fn=fetch,
                assess_fn=assess, writer_fn=writer, auditor_fn=auditor,
                clock=lambda: 0.0, run_dir=tmp, run_id="interrupted-review",
                overrides={"max_rounds": 1})
        self.assertEqual(fetches.count(URL), 1,
                         f"Already completed source silently fetched again: {fetches}")

    def test_r09_unique_source_budget_is_enforced(self):
        urls = [URL, OTHER, "https://example.org/evidence/three"]
        result = ac.run_adaptive(
            "A question", plan=plan(),
            search_fn=lambda *_: [{"url": u} for u in urls],
            fetch_fn=lambda url: "Different evidence at " + url,
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0,
            overrides={"budget_unique_sources": 1, "max_rounds": 0})
        obtained = result["consumption"]["docs"]
        self.assertLessEqual(obtained, 1, f"Obtained {obtained} sources with limit 1")

    def test_r10_identical_bytes_do_not_prove_independent_confirmation(self):
        state = st.new_state("A question")
        ac.incorporate(state, URL, "Identical syndicated story", "op-1", 0)
        result = ac.incorporate(state, OTHER, "Identical syndicated story", "op-2", 0)
        self.assertNotEqual(result, "confirmed",
                            "Second URL with identical bytes is not proof of independence")

    def test_r11_planner_transport_failure_produces_partial_result(self):
        def failing_model(prompt):
            raise ac.TransportError("Simulated provider failure")
        result = ac.run_adaptive(
            "A question", model_client=failing_model,
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0)
        self.assertTrue(result["partial"])
        self.assertEqual(result["stop"]["reason"], "failure")

    def test_r12_assessor_failure_preserves_result_and_obtained_evidence(self):
        def failing_assessor(*_):
            raise ac.TransportError("Simulated assessment provider failure")
        with tempfile.TemporaryDirectory() as tmp:
            result = ac.run_adaptive(
                "A question", plan=plan(), search_fn=lambda *_: [{"url": URL}],
                fetch_fn=lambda _: "Already obtained evidence",
                assess_fn=failing_assessor, writer_fn=writer, auditor_fn=auditor,
                clock=lambda: 0.0, run_dir=tmp)
            self.assertTrue(result["partial"])
            self.assertIn(URL, st.load(tmp)["evidence"])

    def test_r13_default_required_items_cannot_disappear_on_plan_update(self):
        first = plan()
        first["entities"][0].pop("required")
        first["criteria"][0].pop("required")
        state = st.new_state("A question")
        st.record_plan_version(state, first, "Initial plan, required by default")
        replacement = plan()
        replacement["entities"][0]["id"] = "replacement-entity"
        replacement["criteria"][0]["id"] = "replacement-criterion"
        replacement["criteria"][0]["applies_to"] = ["replacement-entity"]
        with self.assertRaises(ValueError):
            st.record_plan_version(state, replacement, "Drop original requirements")

    def test_r14_failed_planner_attempts_remain_accounted(self):
        calls = []
        def invalid_model(prompt):
            calls.append(prompt)
            return "invalid json"
        result = ac.run_adaptive(
            "A question", model_client=invalid_model,
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["consumption"]["model_calls"], len(calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
