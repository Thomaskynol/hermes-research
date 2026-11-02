"""Planejador preserva eixos per_candidate; colapso gera aviso observável.

Genérico, offline, sem rede/8082 (audithook).
"""
import sys
import unittest

sys.path.insert(0, "/home/thomaskyn/Projetos/hermes-research-dev")

import adaptive_coordinator as ac
import adaptive_planner as planner


class PerCandidatePromptTest(unittest.TestCase):
    def test_prompt_shows_both_criterion_shapes(self):
        prompt = planner.build_plan_prompt("Descubra e compare cinco plugins?")
        self.assertIn('"per_candidate": true', prompt)
        self.assertIn("MUST carry", prompt)

    def test_collapsed_plan_warns(self):
        plan = {"open_discovery": {"needed": True}, "candidate_target": 5,
                "criteria": [{"id": "c1", "label": "x", "required": True}]}
        warn = ac._collapsed_per_candidate_warning(plan)
        self.assertTrue(warn and "global" in warn)

    def test_healthy_plan_silent(self):
        plan = {"open_discovery": {"needed": True}, "candidate_target": 5,
                "criteria": [{"id": "c1", "required": True},
                             {"id": "c2", "required": True,
                              "per_candidate": True}]}
        self.assertIsNone(ac._collapsed_per_candidate_warning(plan))


if __name__ == "__main__":
    unittest.main()
