"""FIX E (genus5): gap queries lideradas pela entidade do gap.

Diagnose: _short_gap_query montava a query a partir da PRIMEIRA entidade
do applies_to (sempre e1/Django) e ignorava gap["entity_id"]; gaps de celula
de e3/Flask emitiam queries Django-led e nunca traziam URL oficial Flask.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("gap entity tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def state():
    return {
        "question": "Compare Django FastAPI Flask?",
        "plan": {
            "entities": [
                {"id": "e1", "label": "Django"},
                {"id": "e2", "label": "FastAPI"},
                {"id": "e3", "label": "Flask"},
            ],
            "criteria": [{"id": "c1", "label": "roteamento",
                          "required": True,
                          "applies_to": ["e1", "e2", "e3"]}],
        },
        "evidence": {},
        "attempts": {},
        "discovery": {"open": True, "candidates": []},
        "rounds": [],
    }


class GapEntityLedTest(unittest.TestCase):
    def test_cell_gap_leads_with_own_entity_not_first_applies(self):
        st = state()
        q = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "roteamento",
                 "entity_id": "e3"})
        self.assertTrue(q.split()[0].lower() == "flask",
                        f"query deveria liderar com Flask, veio: {q!r}")
        self.assertNotIn("django", q.lower().split()[:1])

    def test_no_entity_id_keeps_first_applies_behavior(self):
        st = state()
        q = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "roteamento"})
        self.assertTrue(q.split()[0].lower() == "django",
                        f"sem entity_id o comportamento nao muda: {q!r}")

    def test_unknown_entity_id_falls_back_without_crash(self):
        st = state()
        q = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "roteamento",
                 "entity_id": "ex"})
        self.assertTrue(q.split()[0].lower() == "django",
                        f"entity_id desconhecido usa fallback: {q!r}")
        q2 = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "roteamento",
                 "entity_id": ""})
        self.assertTrue(q2.split()[0].lower() == "django")


if __name__ == "__main__":
    unittest.main()
