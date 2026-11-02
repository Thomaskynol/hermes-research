"""Assessor selection prioritizes open entity x dimension cells and
carries later lots into the next rounds (accept17 residual: 53 usable
docs never evaluated — JSON ceiling + prefix-ordered lots that 3 rounds
never reach).

Controlled cases: with a tight json_budget, the first call must prefer
docs about the entity with open cells, and the second call must carry
the previously-cut open docs before repeating already-sent ones.
Limits (max_docs, json_budget, model calls) are never raised.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("selection budget test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def plan():
    return {
        "plan_id": "p", "version": 1,
        "entities": [
            {"id": "e0", "label": "AlphaWidget", "required": True},
            {"id": "e1", "label": "BetaGadget", "required": True},
        ],
        "criteria": [
            {"id": "c0", "label": "custo de licenca",
             "required": True, "applies_to": ["e0", "e1"], "description": "Eixo custo de licenca: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c1", "label": "revisao de codigo",
             "required": True, "applies_to": ["e0", "e1"], "description": "Eixo revisao de codigo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": [],
    }


def evidence():
    ev = {}
    for i in range(12):
        ev[f"https://example.org/alpha/{i}"] = (
            f"AlphaWidget custo de licenca MIT documentado ({i}). "
            f"detalhes sobre alphawidget " * 4)
    for i in range(12):
        ev[f"https://example.org/beta/{i}"] = (
            f"BetaGadget revisao de codigo documentada ({i}). "
            f"detalhes sobre betagadget " * 4)
    return ev


def covered_e1():
    out = []
    for cid in ("c0", "c1"):
        out.append({"criterion_id": cid, "entity_id": "e1",
                    "state": "covered", "justification": "j",
                    "origin": "stub",
                    "references": [{"url": "https://example.org/beta/0"}]})
    return out


class OpenCellPriorityTest(unittest.TestCase):
    def test_open_entity_docs_come_first(self):
        assess = ac.make_model_assessor(lambda prompt: "[]",
                                        max_docs=24, excerpt_chars=100,
                                        json_budget=4000)
        assess.set_previous_evaluations(covered_e1())
        assess(plan(), evidence(), {}, {})
        urls = assess.last_selection["urls"]
        alpha = [u for u in urls if "/alpha/" in u]
        beta = [u for u in urls if "/beta/" in u]
        self.assertTrue(alpha, "docs da entidade em aberto devem ser "
                              "selecionados primeiro")
        if beta:
            first_beta = min(urls.index(u) for u in beta)
            last_alpha = max(urls.index(u) for u in alpha)
            self.assertLess(last_alpha, first_beta)

    def test_cut_lot_is_carried_into_next_round(self):
        assess = ac.make_model_assessor(lambda prompt: "[]",
                                        max_docs=24, excerpt_chars=100,
                                        json_budget=1500)
        assess.set_previous_evaluations(covered_e1())
        assess(plan(), evidence(), {}, {})
        first = list(assess.last_selection["urls"])
        self.assertTrue(first)
        assess(plan(), evidence(), {}, {})
        second = list(assess.last_selection["urls"])
        self.assertTrue(second)
        # Lote posterior carrega o restante: nenhuma repetição enquanto
        # houver material não enviado sobre a entidade em aberto.
        self.assertEqual(set(first) & set(second), set())
        alpha_pos = [second.index(u) for u in second if "/alpha/" in u]
        beta_pos = [second.index(u) for u in second if "/beta/" in u]
        self.assertTrue(alpha_pos, "lote posterior retoma o material aberto")
        if beta_pos:
            self.assertLess(max(alpha_pos), min(beta_pos),
                            f"aberto antes do restante: {second}")

    def test_limits_are_respected(self):
        assess = ac.make_model_assessor(lambda prompt: "[]",
                                        max_docs=6, excerpt_chars=100,
                                        json_budget=4000)
        assess.set_previous_evaluations(covered_e1())
        assess(plan(), evidence(), {}, {})
        self.assertLessEqual(len(assess.last_selection["urls"]), 6)

    def test_no_prior_evals_keeps_stable_order(self):
        urls = [f"https://example.org/doc/{i}" for i in range(8)]
        ev = {u: f"content about {u} alphawidget" for u in urls}
        assess = ac.make_model_assessor(lambda prompt: "[]", max_docs=5)
        assess(plan(), ev, {}, {})
        self.assertEqual(len(assess.last_selection["urls"]), 5)


if __name__ == "__main__":
    unittest.main()
