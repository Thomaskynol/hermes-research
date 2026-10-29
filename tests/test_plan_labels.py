#!/usr/bin/env python3
"""Entity-label normalization + stable coverage definition (offline).

Run: python3 -m unittest tests.test_plan_labels
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_planner as ap
import coverage_ledger as cl


class EntityLabelTest(unittest.TestCase):
    def test_github_owner_repo_label_returns_exact_repo(self):
        self.assertEqual(
            ap.normalize_entity_label(
                "dzianisv opencode-plugins",
                "https://github.com/dzianisv/opencode-plugins"),
            "opencode-plugins")

    def test_slash_owner_repo_returns_repo(self):
        self.assertEqual(ap.normalize_entity_label("owner/repo"), "repo")

    def test_plain_name_is_untouched(self):
        self.assertEqual(ap.normalize_entity_label("Plannotator"),
                         "Plannotator")
        # repo matches the URL, but the owner is not in the label: keep it.
        self.assertEqual(
            ap.normalize_entity_label(
                "Plannotator", "https://github.com/someone/Plannotator"),
            "Plannotator")

    def test_long_sentence_label_returns_short_name(self):
        label = "this is the exact plugin name for opencode-planner"
        out = ap.normalize_entity_label(label)
        self.assertTrue(out)
        self.assertLessEqual(len(out.split()), 6)
        self.assertEqual(out, "opencode-planner")

    def test_planner_prompt_states_exact_name_rule(self):
        prompt = ap.build_plan_prompt("compare five plugins")
        self.assertIn("EXACT name", prompt)
        self.assertIn("never 'owner repo'", prompt)


def _plan():
    return {
        "plan_id": "plan-label", "version": 1,
        "entities": [
            {"id": "e1", "label": "alpha", "required": True},
            {"id": "e2", "label": "beta", "required": True},
        ],
        "criteria": [
            {"id": "c1", "label": "feature", "required": True,
             "applies_to": ["e1", "e2"]},
        ],
    }


class CoverageDefinitionTest(unittest.TestCase):
    def test_compute_exposes_definition_numerator_denominator(self):
        url = "https://example.com/docs/alpha"
        text = "alpha feature details, synthetic evidence"
        plan = _plan()
        ledger = cl.Ledger(plan, run_id="run-label")
        ledger.set_corpus({url: text},
                          {url: {"status": "usable", "usable_text": text,
                                 "excluded": False}})
        ledger.evaluate("c1", "covered", justification="feature documented",
                        origin="manual audit",
                        references=[{"url": url, "excerpt": "feature details"}],
                        entity_id="e1")
        block = ledger.compute()
        self.assertEqual(block["definition"], cl.COVERAGE_DEFINITION)
        self.assertEqual(block["numerator"], 1)
        self.assertEqual(block["denominator"], 2)
        self.assertEqual(block["proportion"], 1 / 2)

    def test_plan_version_record_exposes_required_cells(self):
        record = cl.plan_version_record(_plan())
        self.assertEqual(record["criteria_count"], 1)
        self.assertEqual(record["entities_required"], 2)
        self.assertEqual(record["cells"], 2)


if __name__ == "__main__":
    unittest.main()
