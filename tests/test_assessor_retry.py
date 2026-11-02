"""Bounded assessor retry: one transient glitch must not kill a run.

Regression from real run accept5 (2026-10-25): the model returned a
non-list payload once (`assessor must return a JSON list`), the run died
with stop=failure despite 54 banked evaluations and remaining budget.
One retry (budget-counted, noted) tolerates the transient glitch; a
persistent failure still fails honestly (partial preserved, R11/R12).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("assessor retry test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL = "https://example.org/retry-source"


def make_plan():
    return {
        "plan_id": "retry", "version": 1,
        "entities": [{"id": "e0", "required": True}],
        "criteria": [{"id": "c0", "label": "criterion 0",
                      "required": True, "applies_to": ["e0"], "description": "Eixo criterion 0: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        "initial_paths": ["query"],
    }


def qual(text):
    return {"status": "usable", "excluded": False, "usable_text": text}


def fresh_state():
    state = state_api.new_state("retry question")
    state["plan"] = make_plan()
    state["evidence"] = {URL: "substantive text about the topic"}
    state["qualification"] = {URL: qual("substantive text about the topic")}
    return state


def covered_eval():
    return [{"criterion_id": "c0", "entity_id": "e0", "state": "covered",
             "justification": "stub", "origin": "stub",
             "references": [{"url": URL}]}]


class AssessorRetryTest(unittest.TestCase):
    def test_flaky_assessor_retried_once_then_applied(self):
        calls = []

        def flaky(plan, evidence, qualification, attempts=None):
            calls.append(1)
            if len(calls) == 1:
                raise ac.TransportError("assessor must return a JSON list")
            return covered_eval()

        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, flaky, ledger, resolved)
        self.assertEqual(len(calls), 2)
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"][0]
        self.assertEqual(kept["state"], "covered")
        self.assertTrue(any("retrying once" in str(n)
                            for n in state["notes"]))
        # Entry call + retry both counted as boundary calls.
        self.assertEqual(
            state.get("consumption", {}).get("model_calls"), 2)

    def test_persistent_failure_still_fails_honestly(self):
        def broken(plan, evidence, qualification, attempts=None):
            raise ac.TransportError("boom")

        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = ac.resolve_adaptive("light")
        with self.assertRaises(ac.TransportError):
            ac._assess_round(state, broken, ledger, resolved)
        # Exactly one retry, then honest failure (caller maps to partial).
        self.assertTrue(any("retrying once" in str(n)
                            for n in state["notes"]))
        self.assertEqual(
            state.get("consumption", {}).get("model_calls"), 2)

    def test_no_retry_when_budget_exhausted(self):
        calls = []

        def broken(plan, evidence, qualification, attempts=None):
            calls.append(1)
            raise ac.TransportError("boom")

        state = fresh_state()
        ledger = cl.Ledger(state["plan"])
        resolved = dict(ac.resolve_adaptive("light"))
        resolved["max_model_calls"] = 1  # entry call consumes the only one
        with self.assertRaises(ac.TransportError):
            ac._assess_round(state, broken, ledger, resolved)
        self.assertEqual(len(calls), 1)
        self.assertFalse(any("retrying once" in str(n)
                             for n in state["notes"]))


if __name__ == "__main__":
    unittest.main()
