#!/usr/bin/env python3
"""Anti-ausencia-falsa no writer (complementaridade): RED->GREEN.

Generico (AlphaWidget/BetaGadget, sem literais de produto/entidades).
Offline: audithook bloqueia rede; writer/model stub; sem 8082.
Nao toca tetos/orcamento/thresholds do verifier.

Contrato: antes de redigir 'sem funcionalidade/documentacao atribuivel'
para um candidato na secao de combinacao/sobreposicao, o writer deve
conferir o estado funcional acumulado (evaluations partial/covered com
refs); havendo, afirma apenas ausencia de base de combinacao/
sobreposicao, nunca de funcionalidade. Sem evaluations que sustentem
funcionalidade, a LACUNA de ausencia fica preservada, sem forcar covered.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("false-absence test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


class AntiFalseAbsenceGuidanceTest(unittest.TestCase):
    """Regra anti-ausencia-falsa no guidance + prompt do writer."""

    def test_guidance_forbids_false_absence(self):
        g = ac._writer_complementarity_guidance().lower()
        self.assertIn("partial", g,
                      "regra deve citar o estado funcional acumulado "
                      "(partial)")
        self.assertIn("covered", g,
                      "regra deve citar o estado funcional acumulado "
                      "(covered)")
        self.assertIn("combina", g,
                      "havendo funcionalidade, ausencia e SO de base de "
                      "combinacao/sobreposicao")
        self.assertIn("nunca", g,
                      "regra deve proibir afirmar ausencia de "
                      "funcionalidade nesse caso")
        self.assertIn("funcionalidade", g,
                      "o que nunca se nega havendo evaluations e a "
                      "funcionalidade")

    def test_prompt_carries_anti_absence_rule(self):
        seen = {}

        def fake_writer(prompt):
            seen["prompt"] = prompt
            return "relatorio sintetico"

        write = ac.make_model_writer(fake_writer)
        view = {"question": "q",
                "plan": {"entities": [], "criteria": []},
                "evidence": {"https://example.org/a/0": "AlphaWidget guia "
                             + ("geral. " * 500)},
                "question_coverage": {"criteria": []},
                "evaluations": [
                    {"criterion_id": "cF", "entity_id": "eA",
                     "state": "partial",
                     "justification": "funcionalidade documentada",
                     "references": [{"url": "https://example.org/a/0"}]}]}
        write(view)
        low = seen["prompt"].lower()
        self.assertIn("partial", low,
                      "prompt do writer deve levar a regra anti-ausencia "
                      "quando ha evaluations")
        self.assertIn("covered", low)
        self.assertIn("combina", low)
        self.assertIn("nunca", low)

    def test_genuine_absence_keeps_lacuna_without_forcing_covered(self):
        g = ac._writer_complementarity_guidance().lower()
        self.assertIn("lacuna", g,
                      "sem evaluations que sustentem funcionalidade, a "
                      "LACUNA de ausencia fica preservada")
        # Nunca forcar covered: a palavra covered so aparece como condicao
        # do estado acumulado, nunca como ordem de elevar/forcá-lo.
        self.assertNotIn("eleve", g,
                         "regra nunca ordena elevar para covered")
        self.assertNotIn("converta", g,
                         "regra nunca ordena converter para covered")
        self.assertNotIn("force", g.replace("sem forçar", "").replace(
            "sem forcar", ""),
            "regra nunca ordena forcar covered (fora da ressalva "
            "'sem forcar')")


if __name__ == "__main__":
    unittest.main()
