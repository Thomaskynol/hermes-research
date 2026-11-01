#!/usr/bin/env python3
"""accept31 M5 — recálculo proporcional na expansão do plano (genérico).

Widget Alpha/Beta/Gamma: plano versionado que expande (15→55 células)
recalcula o proporcional e adota quando há folga; plano estável não
re-adota; sem folga não adota. Nunca reduz, nunca pós-finalização,
fonte segue harness/user/default.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac


def make_plan(n_ent, n_crit):
    return {"plan_id": "p", "version": 1, "question": "q",
            "entities": [{"id": f"w{i}", "label": f"Widget {i}",
                          "required": True} for i in range(n_ent)],
            "criteria": [{"id": f"c{j}", "label": f"axis {j}",
                          "required": True, "per_candidate": True,
                          "applies_to": [f"w{i}" for i in range(n_ent)]}
                         for j in range(n_crit)],
            "initial_paths": ["q"]}


def make_resolved(max_rounds=3, source="default", model_calls=16,
                  queries=30, extractions=120, time_s=1800):
    return {"max_rounds": max_rounds, "max_rounds_source": source,
            "max_model_calls": model_calls,
            "budget": {"queries": queries, "extractions": extractions,
                       "time_s": time_s}}


class ProportionalReadoptTest(unittest.TestCase):
    def test_expanded_plan_adopts(self):
        state = {"rounds": [], "notes": [], "config_applied": {}}
        resolved = make_resolved()
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(3, 5)))  # 15 células: 2 <= 3
        self.assertEqual(resolved["max_rounds"], 3)
        state["rounds"].append({"round": 0})  # loop iniciou
        self.assertTrue(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(11, 5)),  # 55 células → 7
            [str(n)[:100] for n in state.get("notes", [])])
        self.assertEqual(resolved["max_rounds"], 7, resolved)
        self.assertEqual(resolved.get("max_rounds_source"), "default",
                         resolved)
        self.assertEqual(state["config_applied"].get("max_rounds"), 7)
        self.assertTrue(any("proporcional" in str(n).lower()
                            for n in state.get("notes", [])))

    def test_stable_plan_no_readopt(self):
        state = {"rounds": [], "notes": [], "config_applied": {}}
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(3, 5))
        state["rounds"].append({"round": 0})
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(11, 5))
        notes_before = len(state.get("notes", []))
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(11, 5)))  # estável: sem re-adoção
        self.assertEqual(resolved["max_rounds"], 7)
        self.assertEqual(len(state.get("notes", [])), notes_before)

    def test_no_slack_no_adopt(self):
        state = {"rounds": [], "notes": [], "config_applied": {}}
        resolved = make_resolved(queries=6, extractions=12, model_calls=4,
                                 time_s=150)
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(3, 5)))
        state["rounds"].append({"round": 0})
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(11, 5)))  # sem folga: não adota
        self.assertEqual(resolved["max_rounds"], 3, resolved)

    def test_never_after_stop(self):
        state = {"rounds": [], "notes": [], "config_applied": {}}
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(3, 5))
        state["rounds"].append({"round": 0})
        state["stop"] = {"reason": "rounds", "partial": True, "detail": "x"}
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(11, 5)))
        self.assertEqual(resolved["max_rounds"], 3)


if __name__ == "__main__":
    unittest.main()
