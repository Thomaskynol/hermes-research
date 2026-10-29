#!/usr/bin/env python3
"""Sentence-level support audit (check_support), offline.

The synthesis is never rewritten: each cited sentence is mapped back to the
cited document and checked for real overlap / entity mention. Paraphrase is
accepted (>=35% content words or >=2 rare shared words), a version claim on
a doc that only carries another version is not, and a doc that never names
the entity does not sustain the sentence.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("support check test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

URL = "https://example.org/docs/one"
URL2 = "https://example.org/docs/two"
PLAN = {"plan_id": "p", "version": 1,
        "entities": [{"id": "e0", "label": "Ferramenta Y",
                      "required": True}],
        "criteria": [{"id": "c0", "label": "feature", "required": True,
                      "applies_to": ["e0"]}]}

PARAPHRASE_SENTENCE = "O projeto exige Node 18 e instala via npm [1]."
PARAPHRASE_DOC = "Requirements: Node.js 18+; install with npm. License: MIT."

VERSION_SENTENCE = "A API V2 é a única versão suportada [1]."
VERSION_DOC = "Version 0.3.2 of the library; no newer release exists."


class CheckSupportTest(unittest.TestCase):
    def test_legit_paraphrase_is_supported(self):
        result = verify.check_support(
            PARAPHRASE_SENTENCE + " Frase informativa sem citação.",
            {URL: 1}, {URL: PARAPHRASE_DOC}, PLAN)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["claims"], 1)
        self.assertEqual(result["supported"], 1)
        self.assertEqual(result["uncited"], 1)
        self.assertEqual(result["unsupported"], [])

    def test_other_version_is_unsupported(self):
        result = verify.check_support(
            VERSION_SENTENCE, {1: URL}, {URL: VERSION_DOC}, PLAN)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["supported"], 0)
        self.assertEqual(len(result["unsupported"]), 1)
        self.assertEqual(result["unsupported"][0]["citations"], [1])
        self.assertEqual(result["unsupported"][0]["reason"],
                         "sem sobreposição")

    def test_entity_missing_from_cited_doc_is_unsupported(self):
        sentence = "A Biblioteca Alfa oferece suporte completo e estável [1]."
        doc = "Suporte completo e estável para muitas ferramentas."
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e0", "label": "Biblioteca Alfa",
                              "required": True}],
                "criteria": [{"id": "c0", "label": "feature",
                              "required": True, "applies_to": ["e0"]}]}
        result = verify.check_support(sentence, {URL: 1}, {URL: doc}, plan)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["unsupported"][0]["reason"],
                         "entidade não mencionada no doc")

    def test_half_supported_is_partial(self):
        text = PARAPHRASE_SENTENCE + " " + VERSION_SENTENCE
        result = verify.check_support(
            text, {URL: 1, URL2: 2},
            {URL: PARAPHRASE_DOC, URL2: VERSION_DOC}, PLAN)
        self.assertEqual(result["claims"], 2)
        self.assertEqual(result["supported"], 1)
        self.assertEqual(len(result["unsupported"]), 1)
        self.assertEqual(result["status"], "partial")

    def test_no_citations_is_unknown(self):
        result = verify.check_support("Sem nenhuma citação.", {URL: 1},
                                      {URL: PARAPHRASE_DOC}, PLAN)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["claims"], 0)
        self.assertEqual(result["uncited"], 1)

    def test_lacuna_declaration_over_consulted_doc_is_sustained(self):
        sentence = ("Nenhum excerto do corpus em [1] afirma ou nega "
                    "compatibilidade.")
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: PARAPHRASE_DOC}, PLAN)
        self.assertEqual(result["claims"], 1)
        self.assertEqual(result["supported"], 1)
        self.assertEqual(result["unsupported"], [])
        self.assertEqual(len(result["declared"]), 1)

    def test_lacuna_declaration_with_unresolved_citation_fails(self):
        sentence = "Nenhum excerto do corpus em [9] afirma compatibilidade."
        result = verify.check_support(sentence, {9: "https://x.example/y"},
                                      {URL: PARAPHRASE_DOC}, PLAN)
        self.assertEqual(result["supported"], 0)
        self.assertEqual(len(result["unsupported"]), 1)

    def test_inference_marked_claim_audits_factual_anchor(self):
        sentence = ("`License MIT` — fonte: [1] — INFERÊNCIA autorizada: "
                    "licença sem custo de licença.")
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: PARAPHRASE_DOC}, PLAN)
        self.assertEqual(result["supported"], 1)
        self.assertEqual(result["unsupported"], [])

    def test_pure_inference_without_anchor_still_fails(self):
        sentence = "INFERÊNCIA: provavelmente é grátis e sem limites [1]."
        doc = "Um texto longo sobre instalação e configuração detalhada."
        result = verify.check_support(sentence, {URL: 1}, {URL: doc}, PLAN)
        self.assertEqual(result["supported"], 0)
        self.assertEqual(len(result["unsupported"]), 1)

    def test_vacuous_prefix_falls_back_to_full_sentence(self):
        sentence = ("- **Sobreposição provável (INFERÊNCIA, não fato):** "
                    "ambos tocam plan e submit_plan [1].")
        self.assertEqual(verify._factual_anchor(sentence), sentence)

    def test_substantive_anchor_is_kept(self):
        sentence = ("`License MIT` — fonte: [1] — INFERÊNCIA autorizada: "
                    "licença sem custo.")
        anchor = verify._factual_anchor(sentence)
        self.assertNotEqual(anchor, sentence)
        self.assertIn("License MIT", anchor)


if __name__ == "__main__":
    unittest.main()
