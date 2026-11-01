#!/usr/bin/env python3
"""accept33 — hook proporcional com state REAL (regressão accept32).

Causa-raiz: ``adaptive_state.new_state`` inicializa
``stop={"reason": None, ...}`` e ``report={}`` (nunca None). O guarda
``stop is not None or report is not None`` era portanto sempre True
pós-início → re-adoção M5 morta em runs reais. Os testes M5
(test_accept31_rounds) montavam states sintéticos sem stop/report e
passavam — mock-behavior gap.

Cenário espelho do accept32: base com plano v1 de 0 células escreve
``_proportional_cells=0``; expansão para 50 células com loop iniciado
re-adota max_rounds 3→7 (limites queries=30/extractions=120/
time_s=1800/max_model_calls=16) COM note de trace.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as _state


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


class ProportionalRealStateTest(unittest.TestCase):
    def test_base_zero_cells_records_key_and_trace(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-base")
        resolved = make_resolved()
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(0, 5)))  # 0 células: sem adoção
        self.assertEqual(resolved["max_rounds"], 3)
        self.assertEqual(state.get("_proportional_cells"), 0)
        self.assertTrue(
            any("proporcional" in str(n).lower()
                for n in state.get("notes", [])),
            [str(n)[:120] for n in state.get("notes", [])])

    def test_expansion_readopts_with_real_state(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-exp")
        resolved = make_resolved()
        # Base: plano v1 com 0 células (como o accept32).
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(0, 5))
        self.assertEqual(state.get("_proportional_cells"), 0)
        # Loop iniciou (guarda pós-início ativo com stop/report reais).
        state["rounds"].append({"round": 0})
        notes_before = len(state.get("notes", []))
        # Expansão v1→v15: 0→50 células → proporcional 7 > 3, com folga.
        self.assertTrue(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)),
            [str(n)[:120] for n in state.get("notes", [])])
        self.assertEqual(resolved["max_rounds"], 7, resolved)
        self.assertEqual(resolved.get("max_rounds_source"), "default",
                         resolved)
        self.assertEqual(state["config_applied"].get("max_rounds"), 7)
        self.assertGreater(len(state.get("notes", [])), notes_before)
        self.assertTrue(any("proporcional" in str(n).lower()
                            for n in state.get("notes", [])))

    def test_stable_plan_stays_silent(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-st")
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(0, 5))
        state["rounds"].append({"round": 0})
        ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5))
        notes_before = len(state.get("notes", []))
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)))  # estável: silencioso
        self.assertEqual(resolved["max_rounds"], 7)
        self.assertEqual(len(state.get("notes", [])), notes_before)

    def test_never_after_real_stop(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-stop")
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(0, 5))
        state["rounds"].append({"round": 0})
        state["stop"] = {"reason": "rounds", "partial": True, "detail": "x"}
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)))
        self.assertEqual(resolved["max_rounds"], 3)

    def test_blocked_stop_traces_note(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-blstop")
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(0, 5))
        state["rounds"].append({"round": 0})
        state["stop"] = {"reason": "rounds", "partial": True, "detail": "x"}
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)))
        self.assertEqual(resolved["max_rounds"], 3)
        notes = [str(n) for n in state.get("notes", [])]
        self.assertTrue(
            any("proporcional:" in n and "bloqueado" in n and "stop" in n
                for n in notes), notes)

    def test_blocked_report_traces_note(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-blrep")
        resolved = make_resolved()
        ac._maybe_adopt_proportional_rounds(state, resolved, make_plan(0, 5))
        state["rounds"].append({"round": 0})
        state["report"] = {"verdict": "ok"}
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)))
        self.assertEqual(resolved["max_rounds"], 3)
        notes = [str(n) for n in state.get("notes", [])]
        self.assertTrue(
            any("proporcional:" in n and "bloqueado" in n and "report" in n
                for n in notes), notes)

    def test_legacy_resume_traces_without_adopting(self):
        state = _state.new_state("Compare widgets?", run_id="accept33-leg")
        resolved = make_resolved()
        state["rounds"].append({"round": 0})  # resume sem base de cálculo
        self.assertIsNone(state.get("_proportional_cells"))
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, make_plan(10, 5)))
        self.assertEqual(resolved["max_rounds"], 3)
        notes = [str(n) for n in state.get("notes", [])]
        self.assertTrue(
            any("proporcional:" in n and "resume" in n for n in notes),
            notes)


if __name__ == "__main__":
    unittest.main()
