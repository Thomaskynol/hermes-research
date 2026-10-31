"""Citação x entidade (accept17 residual: writer citava [4][5]/[5][4] em
bloco onde só um doc tratava da entidade).

Contrato: numa frase que nomeia a entidade, cada número citado deve
resolver para um doc que menciona a entidade; citação conjuntiva frouxa
é removida quando resta ao menos uma citação que sustenta — e mantida
quando removê-la mascararia a lacuna (a auditoria continua a sinalizar).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("citation test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

PLAN = {"plan_id": "p", "version": 1,
        "entities": [{"id": "e0", "label": "AlphaWidget", "required": True},
                     {"id": "e1", "label": "BetaGadget", "required": True}],
        "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                      "applies_to": ["e0", "e1"]}]}

DOC_ALPHA = "AlphaWidget planner: comandos de planejamento e revisão."
DOC_GENERIC = "OpenCode plugins review: produtividade e testes em geral."


def numbers():
    return {1: "https://example.org/alpha",
            2: "https://example.org/generic"}


def evidence():
    return {"https://example.org/alpha": DOC_ALPHA,
            "https://example.org/generic": DOC_GENERIC}


class TightenCitationsTest(unittest.TestCase):
    def test_conjunctive_loose_cite_is_removed(self):
        text = "AlphaWidget oferece planejamento [1][2]."
        tightened, notes = verify._tighten_citations(
            text, numbers(), evidence(), PLAN)
        self.assertEqual(tightened, "AlphaWidget oferece planejamento [1].")
        self.assertTrue(notes)

    def test_single_loose_cite_is_kept_for_audit(self):
        text = "BetaGadget revisa código [2]."
        tightened, notes = verify._tighten_citations(
            text, numbers(), evidence(), PLAN)
        self.assertEqual(tightened, text)
        self.assertEqual(notes, [])

    def test_claim_without_entity_is_untouched(self):
        text = "Recursos gerais de produtividade [1][2]."
        tightened, notes = verify._tighten_citations(
            text, numbers(), evidence(), PLAN)
        self.assertEqual(tightened, text)

    def test_all_sustaining_cites_are_kept(self):
        ev = {"https://example.org/alpha":
              DOC_ALPHA + " Também usado com BetaGadget.",
              "https://example.org/generic":
              "BetaGadget review: testes e revisão no BetaGadget."}
        text = "BetaGadget revisa código [1][2]."
        tightened, _ = verify._tighten_citations(
            text, numbers(), ev, PLAN)
        self.assertEqual(tightened, text)

    def test_unknown_number_is_kept_for_audit(self):
        text = "AlphaWidget oferece planejamento [1][9]."
        tightened, _ = verify._tighten_citations(
            text, numbers(), evidence(), PLAN)
        self.assertEqual(tightened, text)


class WriterPromptTest(unittest.TestCase):
    def test_prompt_requires_entity_matching_cites(self):
        import adaptive_coordinator as ac
        prompts = []

        def model(prompt):
            prompts.append(prompt)
            return "texto"

        write = ac.make_model_writer(model)
        write({"question": "q", "plan": PLAN, "evidence": evidence(),
               "question_coverage": {}, "stop": {}, "rounds": []})
        self.assertIn("entidade", prompts[0].lower())
        self.assertTrue(
            "apenas" in prompts[0].lower() and "cada" in prompts[0].lower(),
            "prompt deve exigir citação por documento que contém a entidade")


if __name__ == "__main__":
    unittest.main()
