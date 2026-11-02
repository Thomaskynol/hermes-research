"""Bind per_candidate criteria when no discovery is expected (genus2 bug).

genus2: 3 predefined required entities, per_candidate criteria with
applies_to None, open_discovery.needed=False. Nothing ever bound them,
so the criteria stayed global and the assessor's per-entity evaluations
were dropped (denominator 10 instead of 3*8+2=26).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("bind test is offline")


sys.addaudithook(deny_network)

import adaptive_coordinator as ac


def make_plan(discovery_needed=False):
    return {
        "plan_id": "bind-test", "version": 1,
        "entities": [{"id": f"e{i}", "label": f"E{i}", "required": True, "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}
                     for i in range(1, 4)],
        "criteria": [
            {"id": "c1", "label": "dim one", "required": True,
             "per_candidate": True, "description": "Eixo dim one: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c2", "label": "dim two", "required": True,
             "per_candidate": True, "description": "Eixo dim two: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "cg", "label": "global synthesis", "required": True, "description": "Eixo global synthesis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["q"],
        "open_discovery": {"needed": discovery_needed},
        "candidate_target": 3,
    }


def writer(view):
    return "report", {"included_urls": [], "cuts": "test"}


def auditor(report, evidence):
    return {"enabled": False, "accepted": False}


def assessor(plan, evidence, qualification, attempts=None):
    out = []
    for c in plan["criteria"]:
        for eid in (c.get("applies_to") or [None]):
            out.append({"criterion_id": c["id"], "entity_id": eid,
                        "state": "partial", "justification": "stub",
                        "origin": "stub", "references": []})
    return out


class BindPredefinedTest(unittest.TestCase):
    def test_no_discovery_expected_binds_to_all_required(self):
        result = ac.run_adaptive(
            "Compare A, B, C", plan=make_plan(discovery_needed=False),
            model_client=None, search_fn=lambda *_: [],
            fetch_fn=lambda _: "text", assess_fn=assessor,
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0,
            overrides={"max_rounds": 0})
        qc = result["question_coverage"]
        # 2 per_candidate x 3 entities + 1 global = 7 cells.
        self.assertEqual(qc["denominator"], 7,
                         f"per_candidate stayed global: {qc}")
        for c in qc["criteria"]:
            if c["id"] in ("c1", "c2"):
                self.assertEqual(len(c.get("entity_states", {})), 3)

    def test_discovery_open_leaves_unbound_for_extension(self):
        result = ac.run_adaptive(
            "Discover five", plan=make_plan(discovery_needed=True),
            model_client=None, search_fn=lambda *_: [],
            fetch_fn=lambda _: "text", assess_fn=assessor,
            writer_fn=writer, auditor_fn=auditor, clock=lambda: 0.0,
            overrides={"max_rounds": 0})
        qc = result["question_coverage"]
        # Discovery will extend per new candidate; adoption must not
        # pre-bind the anchor set (denominator stays 3 globals).
        self.assertEqual(qc["denominator"], 3,
                         f"adoption pre-bound discovery plan: {qc}")


if __name__ == "__main__":
    unittest.main()
