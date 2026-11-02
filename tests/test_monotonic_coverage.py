"""Monotonic coverage: assessor cannot downgrade without new evidence.

Regression from real run uvrun3 (2026-10-24): round 1 assessed c1 as
covered; round 2 brought no new evidence (ops failed/nogain) yet the
assessor re-stated c1 as partial and c2 as insufficient, and the
coordinator applied the downgrade. Coverage must be monotonic unless the
new evaluation cites material incorporated after the previous assessment.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("monotonic coverage test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL_OLD = "https://example.org/old-source"
URL_NEW = "https://example.org/new-source"


def make_plan():
    return {
        "plan_id": "monotonic", "version": 1,
        "entities": [{"id": "e0", "required": True}],
        "criteria": [{"id": "c0", "label": "criterion 0",
                      "required": True, "applies_to": ["e0"], "description": "Eixo criterion 0: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        "initial_paths": ["query"],
    }


def qual(text):
    return {"status": "usable", "excluded": False, "usable_text": text}


def assessor_with(state_value, url):
    def assess(plan, evidence, qualification, attempts=None):
        return [{"criterion_id": "c0", "entity_id": "e0", "state": state_value,
                 "justification": "stub", "origin": "stub",
                 "references": [{"url": url}]}]
    return assess


def fresh_state():
    state = state_api.new_state("monotonic question")
    state["plan"] = make_plan()
    state["evidence"] = {URL_OLD: "old text with substance"}
    state["qualification"] = {URL_OLD: qual("old text with substance")}
    return state


class MonotonicCoverageTest(unittest.TestCase):
    def test_downgrade_without_new_evidence_is_rejected(self):
        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, assessor_with("covered", URL_OLD),
                         ledger, resolved)
        self.assertEqual(
            [e for e in state["evaluations"]
             if e.get("criterion_id") == "c0"][0]["state"], "covered")
        # Round 2: same corpus, assessor changes its mind -> must be kept.
        ac._assess_round(state, assessor_with("partial", URL_OLD),
                         ledger, resolved)
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"][0]
        self.assertEqual(kept["state"], "covered")
        self.assertTrue(any("downgrade without new evidence rejected" in str(n)
                            for n in state["notes"]))
        # The ledger (which feeds proportion/block) must also keep covered:
        # uvrun5 showed evaluations kept but block regressing to 0.0.
        self.assertEqual(ledger.state_of("c0", "e0"), "covered")
        self.assertEqual(ledger.compute()["proportion"], 1.0)

    def test_downgrade_citing_new_evidence_is_applied(self):
        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, assessor_with("covered", URL_OLD),
                         ledger, resolved)
        # Round 2 brings genuinely new material that corrects the record.
        state["evidence"][URL_NEW] = "new text contradicting the old excerpt"
        state["qualification"][URL_NEW] = qual("new text")
        ac._assess_round(state, assessor_with("partial", URL_NEW),
                         ledger, resolved)
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"][0]
        self.assertEqual(kept["state"], "partial")

    def test_upgrade_without_new_evidence_is_allowed(self):
        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, assessor_with("partial", URL_OLD),
                         ledger, resolved)
        ac._assess_round(state, assessor_with("covered", URL_OLD),
                         ledger, resolved)
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"][0]
        self.assertEqual(kept["state"], "covered")

    def test_contradictory_is_not_a_downgrade(self):
        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, assessor_with("covered", URL_OLD),
                         ledger, resolved)
        ac._assess_round(state, assessor_with("contradictory", URL_OLD),
                         ledger, resolved)
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"][0]
        self.assertEqual(kept["state"], "contradictory")


if __name__ == "__main__":
    unittest.main()
