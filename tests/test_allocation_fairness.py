#!/usr/bin/env python3
"""Allocation fairness (genus8): repeated no-gain must not monopolize slots.

Symptom: ``prioritize_gaps`` ordered by static impact x gain (the ledger
never sets either, so every gap scores 1x1 = plan order) and ``select_ops``
truncated the interleaved expansion to ``cap`` every round. Result: the
same top-3 criteria repeated with delta 0.0 while c4-c10 never got an op
(genus8 r1-r3 all targeted [c1,c2,c3]; every query Django-led, e2/e3 and
c4-c10 starved despite budget remaining).

Fix: attempts decay priority (unexplored outranks repeatedly-failed),
sub-gaps order by least-tried cell, attempts recorded per cell. Priority
is respected: useful gain resets the decay, and with no attempts the
legacy order is bit-identical.

Offline: stdlib only + audithook blocking network.
Run: python3 -m unittest tests.test_allocation_fairness -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("allocation fairness tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac  # noqa: E402


def fairness_state(ncrit=5, entities=("e1", "e2")):
    return {
        "question": "Compare Alpha Beta?",
        "plan": {
            "entities": [{"id": e, "label": e.capitalize()}
                         for e in entities],
            "criteria": [{"id": f"c{i}", "label": f"dimensao {i}",
                          "required": True, "per_candidate": True,
                          "applies_to": list(entities), "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}
                         for i in range(1, ncrit + 1)],
        },
        "evidence": {},
        "attempts": {},
        "discovery": {"open": True, "candidates": []},
        "evaluations": [],
        "rounds": [],
    }


def gaps(ncrit=5):
    return [{"criterion_id": f"c{i}", "label": f"dimensao {i}",
             "state": "insufficient", "justification": "nao investigado",
             "next": "investigar criterio obrigatorio"}
            for i in range(1, ncrit + 1)]


def fail(state, cid, eid=None, n=1, outcome="failed"):
    for _ in range(n):
        att = {"channel": "web", "outcome": outcome}
        if eid is not None:
            att["entity_id"] = eid
        state["attempts"].setdefault(cid, []).append(att)


class PrioritizeDecayTest(unittest.TestCase):
    def test_legacy_order_without_state(self):
        ordered = ac.prioritize_gaps(gaps(5))
        self.assertEqual([g["criterion_id"] for g in ordered],
                         ["c1", "c2", "c3", "c4", "c5"])

    def test_repeated_failure_yields_to_unexplored(self):
        st = fairness_state()
        fail(st, "c1", n=2)
        fail(st, "c2", n=2)
        ordered = ac.prioritize_gaps(gaps(5), st)
        first2 = [g["criterion_id"] for g in ordered[:2]]
        self.assertNotIn("c1", first2)
        self.assertNotIn("c2", first2)
        self.assertEqual(set(first2), {"c3", "c4"})

    def test_useful_gain_resets_decay(self):
        st = fairness_state()
        fail(st, "c1", n=3)
        fail(st, "c2", n=3)
        # c1 produced useful gain last: decay reset, outranks c2 which is
        # still on 3 consecutive failures. Unexplored c3-c5 keep the lead
        # (breadth first at equal base score).
        st["attempts"]["c1"].append(
            {"channel": "web", "outcome": "new_useful"})
        ordered = ac.prioritize_gaps(gaps(5), st)
        ids = [g["criterion_id"] for g in ordered]
        self.assertEqual(ids[:3], ["c3", "c4", "c5"])
        self.assertLess(ids.index("c1"), ids.index("c2"),
                        f"ganho util deveria resetar o decaimento: {ids}")

    def test_fewer_attempts_breaks_ties(self):
        st = fairness_state()
        fail(st, "c1", n=1)
        ordered = ac.prioritize_gaps(gaps(5), st)
        # c2-c5 unexplored (0 attempts) outrank c1 (1 failure).
        self.assertNotEqual(ordered[0]["criterion_id"], "c1")


class EntityRotationTest(unittest.TestCase):
    def test_second_sub_leads_with_untried_entity(self):
        st = fairness_state(ncrit=1)
        ops = ac.select_ops(st, gaps(1), 1)
        self.assertEqual(len(ops), 1)
        self.assertTrue(ops[0]["target"].lower().startswith("e1"),
                        f"primeiro sub lidera com e1: {ops[0]['target']!r}")
        fail(st, "c1", eid="e1")
        ops2 = ac.select_ops(st, gaps(1), 1)
        self.assertTrue(ops2[0]["target"].lower().startswith("e2"),
                        f"apos e1 tentada, lidera com e2: {ops2[0]['target']!r}")

    def test_ops_carry_entity_id(self):
        st = fairness_state(ncrit=1)
        ops = ac.select_ops(st, gaps(1), 2)
        self.assertEqual({o.get("entity_id") for o in ops}, {"e1", "e2"})

    def test_cell_attempts_do_not_leak_across_cells(self):
        st = fairness_state(ncrit=1)
        fail(st, "c1", eid="e1", n=2)
        consec_e2, total_e2 = ac._gap_attempt_stats(st, "c1", "e2")
        self.assertEqual((consec_e2, total_e2), (0, 0))
        consec_e1, total_e1 = ac._gap_attempt_stats(st, "c1", "e1")
        self.assertEqual((consec_e1, total_e1), (2, 2))


class RoundSimulationTest(unittest.TestCase):
    """Controlled genus8 shape: 5 criteria x 2 entities, cap 2, always fail.

    Old code targeted [c1, c2] every round. Fixed code must reach every
    criterion within 3 rounds and never serve one 3x while another gets 0.
    """

    def test_all_criteria_reached_no_monopoly(self):
        st = fairness_state()
        seen: dict[str, int] = {}
        for rnd in range(4):
            ordered = ac.prioritize_gaps(gaps(5), st)
            ops = ac.select_ops(st, ordered, 2)
            self.assertLessEqual(len(ops), 2, "cap respeitado")
            for op in ops:
                cid = op["criterion_id"]
                seen[cid] = seen.get(cid, 0) + 1
                fail(st, cid, eid=op.get("entity_id"))
        for i in range(1, 6):
            self.assertIn(f"c{i}", seen,
                          f"c{i} nunca mirado em 4 rounds: {seen}")
        self.assertLessEqual(max(seen.values()) - min(seen.values()), 1,
                             f"monopolio entre rounds: {seen}")

    def test_entities_share_slots(self):
        st = fairness_state(ncrit=2)
        ents = set()
        for _ in range(2):
            ordered = ac.prioritize_gaps(gaps(2), st)
            for op in ac.select_ops(st, ordered, 2):
                ents.add(op.get("entity_id"))
                fail(st, op["criterion_id"], eid=op.get("entity_id"))
        self.assertEqual(ents, {"e1", "e2"},
                         f"e2 faminta apesar de budget: {ents}")


if __name__ == "__main__":
    unittest.main()
