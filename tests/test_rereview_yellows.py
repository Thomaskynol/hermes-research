#!/usr/bin/env python3
"""Re-review yellows (4) — regression tests, generic (Widget Alpha/Beta)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

URL_A = "https://example.com/widget-alpha"
URL_B = "https://example.com/widget-beta"
URL_C = "https://example.com/widget-gamma"
DOC_A = ("Widget Alpha is a planning helper. It does planning with gates. "
         "Scope: planning only.")
DOC_B = ("Widget Beta is a plugin marketplace. It distributes plugins via a "
         "catalog. Scope: acquisition and distribution.")


def qual(url, text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


class PromotionDiscardNotesTest(unittest.TestCase):
    def test_incompatible_evaluations_logged_not_silent(self):
        import adaptive_coordinator as ac
        import coverage_ledger as ledger_mod
        plan = ledger_mod.validate_plan({
            "plan_id": "promo", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": False, "discovered": True,
                          "source_url": URL_A}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["w1"]}],
            "candidate_target": 2,
        })
        st = {"plan": plan, "question": "q",
              "discovery": {"open": True, "candidates": []},
              "evidence": {URL_A: DOC_A},
              "qualification": {URL_A: qual(URL_A, DOC_A)},
              "evaluations": [], "run_id": "t",
              "rounds": [{"round": 0}, {"round": 1}], "notes": [],
              "plan_versions": [], "attempts": {},
              "consumption": {"model_calls": 0, "rounds": 0},
              "unexplored_alternatives": []}
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("c1", "partial", "Widget Alpha documentado em fonte",
                     "selected_material", [{"url": URL_A}], "w1")
        valid = dict(led._evals[("c1", "w1")])
        invalid = {"criterion_id": "cZ", "entity_id": "w1",
                   "state": "covered", "justification": "fantasma",
                   "origin": "selected_material",
                   "references": [{"url": URL_A}]}
        st["evaluations"] = [valid, invalid]
        self.assertTrue(ac._promote_evaluated(st, led))
        notes = " | ".join(str(n) for n in st.get("notes", []))
        self.assertIn("descart", notes.lower(), notes)
        self.assertIn("1", notes, notes)
        self.assertIn("cZ", notes, notes)


class GapDedupTest(unittest.TestCase):
    def test_generic_plus_cell_gaps_deduped(self):
        import coverage_ledger as ledger_mod
        plan = ledger_mod.validate_plan({
            "plan_id": "g", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True,
                          "source_url": URL_C}],
            "criteria": [{"id": "c1", "label": "Eixo", "required": True,
                          "per_candidate": True,
                          "applies_to": ["w1"]}],
        })
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus({}, {})
        led.evaluate("c1", "insufficient", "sem material sobre Widget Alpha",
                     "selected_material", None, "w1")
        block = led.compute()
        gaps = [g for g in block["gaps"] if g.get("criterion_id") == "c1"]
        self.assertEqual(len(gaps), 1, gaps)
        self.assertEqual(gaps[0].get("entity_id"), "w1", gaps)


class NaCellLabelTest(unittest.TestCase):
    def test_na_cells_use_label_not_raw_id(self):
        from report_renderer import render_report
        plan = {"plan_id": "p",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True}],
                "criteria": [{"id": "c1", "label": "Eixo Um",
                              "required": True, "applies_to": ["w1"]}]}
        block = {"status": "partial", "proportion": 0.0, "numerator": 0,
                 "denominator": 1, "na": 1,
                 "na_cells": [{"criterion_id": "c1", "entity_id": "w1",
                               "justification": "fora de escopo"}],
                 "definition": "d",
                 "criteria": [{"id": "c1", "label": "Eixo Um",
                               "required": True, "applies_to": ["w1"],
                               "state": "not_applicable",
                               "justification": "fora de escopo",
                               "origin": "o", "entity_id": "w1",
                               "references": [],
                               "na_cells": [{"criterion_id": "c1",
                                             "entity_id": "w1",
                                             "justification":
                                             "fora de escopo"}]}],
                 "gaps": [], "references": [], "observed_counts": {}}
        state = {"question": "q", "plan": plan,
                 "question_coverage": block,
                 "report": {"numbers": {}, "selection": {}},
                 "evidence": {}, "notes": []}
        out = render_report(state, synthesis_text="texto",
                            verifications=None)
        self.assertIn("Widget Alpha", out, out[:4000])
        self.assertNotIn("- **N/A** w1:", out, out)


class DeclaredInferencePartialStatusTest(unittest.TestCase):
    def test_only_complementary_inferences_is_partial_not_failed(self):
        import verification_report as verify
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e0", "label": "Widget Alpha",
                              "required": True},
                             {"id": "e1", "label": "Widget Beta",
                              "required": True}],
                "criteria": [{"id": "c0", "label": "compatibilidade",
                              "required": True,
                              "applies_to": ["e0", "e1"]}]}
        sent = ("Widget Alpha gerencia planos [1] \u2014 INFER\u00caNCIA: "
                "uso complementar com Widget Beta para fluxo combinado [2].")
        res = verify.check_support(
            sent, {1: URL_A, 2: URL_B},
            {URL_A: DOC_A, URL_B: DOC_B}, plan)
        self.assertTrue(res.get("partial_declared"), res)
        self.assertEqual(res.get("supported"), 0, res)
        self.assertEqual(res.get("status"), "partial", res)


if __name__ == "__main__":
    unittest.main()
