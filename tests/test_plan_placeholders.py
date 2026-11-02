"""Placeholder entities and query hygiene.

Regression from accept7: the auto-planner created entities like
'plugin candidato 1 (nome a descobrir via discovery)' and applied every
comparison criterion to them. Fifty cells could never be covered, and the
placeholder wording leaked into search queries ('... (nome a descobrir via
discovery) melhoria de planejamento ...'), returning npm/package.json junk.
A discovery obligation is a criterion; entities are concrete names.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("placeholder test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_planner as planner
import adaptive_state as state_api


def placeholder_plan():
    return {
        "plan_id": "ph-1", "version": 1, "question": "Compare cinco plugins",
        "entities": [
            {"id": "e1", "label": "plugin candidato 1 (nome a descobrir via discovery)",
             "required": True},
            {"id": "e2", "label": "plugin candidato 2 (nome a descobrir via discovery)",
             "required": True},
            {"id": "e6", "label": "versão instalada do OpenCode", "required": True},
        ],
        "criteria": [
            {"id": "c1", "label": "melhoria de planejamento", "required": True,
             "applies_to": ["e1", "e2"], "description": "Eixo melhoria de planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c2", "label": "compatibilidade", "required": True,
             "applies_to": ["e1", "e6"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c3", "label": "síntese", "required": True, "description": "Eixo síntese: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["~/.config/opencode", "opencode plugins"],
    }


class PlaceholderPlanTest(unittest.TestCase):
    def test_placeholder_entities_dropped_and_applies_rewritten(self):
        meta = {"repairs": 0, "repair_log": []}
        plan = planner.drop_placeholder_entities(placeholder_plan(), meta)
        ids = [e["id"] for e in plan["entities"]]
        self.assertEqual(ids, ["e6"])
        crit = {c["id"]: c for c in plan["criteria"]}
        self.assertNotIn("applies_to", crit["c1"])  # all placeholders gone
        self.assertEqual(crit["c2"]["applies_to"], ["e6"])
        self.assertNotIn("applies_to", crit["c3"])
        self.assertEqual(meta["repairs"], 1)
        self.assertTrue(any("placeholder" in r for r in meta["repair_log"]))

    def test_never_drops_the_last_entity(self):
        plan = {
            "plan_id": "ph-2", "version": 1, "question": "q",
            "entities": [{"id": "e1", "label": "candidato 1 (a descobrir)",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "x", "required": True,
                          "applies_to": ["e1"], "description": "Eixo x: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "initial_paths": ["q"],
        }
        meta = {"repairs": 0, "repair_log": []}
        kept = planner.drop_placeholder_entities(plan, meta)
        self.assertEqual(len(kept["entities"]), 1)
        self.assertTrue(any("no entity" in r for r in meta["repair_log"]))

    def test_generate_plan_applies_the_guard(self):
        def model(_prompt):
            import json
            return json.dumps(placeholder_plan())

        plan, meta = planner.generate_plan("Compare cinco plugins", model)
        self.assertNotIn("e1", [e["id"] for e in plan["entities"]])
        self.assertEqual(meta["repairs"], 1)


class QueryHygieneTest(unittest.TestCase):
    def test_query_label_strips_parentheticals(self):
        self.assertEqual(
            ac._query_label("plugin candidato 1 (nome a descobrir via discovery)"),
            "")  # still a placeholder after stripping
        self.assertEqual(ac._query_label("OpenCode (instalado)"), "OpenCode")

    def test_gap_query_never_uses_placeholder_wording(self):
        st = state_api.new_state(
            "Compare cinco plugins para planejamento no OpenCode")
        st["plan"] = placeholder_plan()
        q = ac._short_gap_query(st, {"criterion_id": "c1",
                                     "label": "melhoria de planejamento"})
        self.assertNotIn("descobrir", q.lower())
        self.assertNotIn("discovery", q.lower())
        self.assertIn("planejamento", q.lower())
        self.assertIn("opencode", q.lower())

    def test_local_paths_are_recognized(self):
        for p in ("~/.config/opencode", "./opencode.json", "/etc/opencode",
                  "../x", "C:\\Users\\x"):
            self.assertTrue(ac._looks_like_local_path(p), p)
        for q in ("opencode plugins", "best plugins for opencode"):
            self.assertFalse(ac._looks_like_local_path(q), q)


if __name__ == "__main__":
    unittest.main()
