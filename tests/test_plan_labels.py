#!/usr/bin/env python3
"""Entity-label normalization (offline).

Run: python3 -m unittest tests.test_plan_labels
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_planner as ap


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


if __name__ == "__main__":
    unittest.main()
