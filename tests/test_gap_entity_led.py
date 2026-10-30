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


def pc_state(evals=None):
    """Criterion-scoped producer gap: per_candidate criterion, no entity_id
    (real genus6 shape) + explicit evaluations list."""
    st = state()
    st["plan"]["criteria"] = [{"id": "c1", "label": "roteamento",
                               "required": True, "per_candidate": True,
                               "applies_to": ["e1", "e2", "e3"]}]
    st["evaluations"] = list(evals or [])
    return st


def crit_gap():
    return {"criterion_id": "c1", "label": "roteamento",
            "state": "insufficient", "justification": "nao investigado",
            "next": "investigar criterio obrigatorio"}


class GapPerCandidateExpansionTest(unittest.TestCase):
    """Missing half of Fix E: criterion-scoped gaps (no entity_id, the real
    producer shape) over per_candidate criteria expand into one entity-led
    sub-gap per uncovered applies_to entity."""

    def test_criterion_gap_expands_one_op_per_entity(self):
        st = pc_state()
        ops = ac.select_ops(st, [crit_gap()], 3)
        self.assertEqual(len(ops), 3, f"1 gap x 3 entidades -> 3 ops: {ops}")
        leads = [o["target"].split()[0].lower() for o in ops]
        self.assertEqual(leads, ["django", "fastapi", "flask"],
                         f"cada op lidera com sua entidade: {leads}")

    def test_covered_entity_skipped_and_cap_respected(self):
        st = pc_state([{"criterion_id": "c1", "entity_id": "e2",
                        "state": "covered"}])
        ops = ac.select_ops(st, [crit_gap()], 3)
        leads = [o["target"].split()[0].lower() for o in ops]
        self.assertEqual(leads, ["django", "flask"],
                         f"e2 coberta nao emite sub-gap: {leads}")
        ops1 = ac.select_ops(st, [crit_gap()], 1)
        self.assertEqual(len(ops1), 1, f"cap 1 -> 1 op: {ops1}")
        self.assertEqual(ops1[0]["target"].split()[0].lower(), "django")

    def test_non_per_candidate_gap_stays_single_op(self):
        st = state()  # criterio sem per_candidate
        ops = ac.select_ops(st, [crit_gap()], 3)
        self.assertEqual(len(ops), 1, f"sem per_candidate nao expande: {ops}")
        self.assertEqual(ops[0]["target"].split()[0].lower(), "django")

    def test_cell_gap_with_source_url_stays_read_source(self):
        st = pc_state()
        url = "https://flask.example/docs/routing"
        gap = dict(crit_gap(), entity_id="e3", entity_label="Flask",
                   source_url=url)
        ops = ac.select_ops(st, [gap], 3)
        self.assertEqual(len(ops), 1, f"gap de celula -> 1 op: {ops}")
        self.assertEqual(ops[0]["kind"], "read_source")
        self.assertEqual(ops[0]["target"], url)


def _rr_state():
    """Two per_candidate criteria x [e1, e2] (genus7 shape: c1 monopolized
    the op budget because grouped expansion filled every cap slot)."""
    return {
        "question": "Compare Django FastAPI?",
        "plan": {
            "entities": [
                {"id": "e1", "label": "Django"},
                {"id": "e2", "label": "FastAPI"},
            ],
            "criteria": [
                {"id": "c1", "label": "roteamento",
                 "required": True, "per_candidate": True,
                 "applies_to": ["e1", "e2"]},
                {"id": "c2", "label": "orm",
                 "required": True, "per_candidate": True,
                 "applies_to": ["e1", "e2"]},
            ],
        },
        "evidence": {},
        "attempts": {},
        "discovery": {"open": True, "candidates": []},
        "rounds": [],
        "evaluations": [],
    }


def _rr_gap(cid, label):
    return {"criterion_id": cid, "label": label,
            "state": "insufficient", "justification": "nao investigado",
            "next": "investigar criterio obrigatorio"}


class GapRoundRobinTest(unittest.TestCase):
    """Sub-gaps interleave round-robin ACROSS criteria (breadth): with
    cap=3 and gaps [c1, c2] the ops must be c1-e1, c2-e1, c1-e2 — never
    c1-e1, c1-e2, c2-e1 (grouped expansion let c1 hog the whole budget)."""

    def test_subgaps_interleave_across_criteria(self):
        st = _rr_state()
        ops = ac.select_ops(st, [_rr_gap("c1", "roteamento"),
                                 _rr_gap("c2", "persistencia")], 3)
        self.assertEqual([o["criterion_id"] for o in ops],
                         ["c1", "c2", "c1"],
                         f"round-robin entre criterios, nao agrupado: {ops}")
        leads = [o["target"].split()[0].lower() for o in ops]
        self.assertEqual(leads, ["django", "django", "fastapi"],
                         f"cada op lidera com sua entidade: {leads}")

    def test_fully_covered_criterion_skipped_in_rotation(self):
        st = _rr_state()
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "e1", "state": "covered"},
            {"criterion_id": "c1", "entity_id": "e2", "state": "covered"},
        ]
        ops = ac.select_ops(st, [_rr_gap("c1", "roteamento"),
                                 _rr_gap("c2", "persistencia")], 2)
        self.assertEqual(len(ops), 2, f"c2 aberta -> 2 ops: {ops}")
        self.assertTrue(all(o["criterion_id"] == "c2" for o in ops),
                        f"ambos os ops de c2 (c1 toda coberta): {ops}")
        leads = [o["target"].split()[0].lower() for o in ops]
        self.assertEqual(leads, ["django", "fastapi"],
                         f"cada op lidera com sua entidade: {leads}")


if __name__ == "__main__":
    unittest.main()
