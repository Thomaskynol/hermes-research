#!/usr/bin/env python3
"""LACUNA x citação: quote ausente no doc citado não sustenta (accept21).

Frase LACUNA com literal entre aspas/backticks ou número de versão cuja
citação resolve para doc do corpus mas sem overlap do quote falha — só
resolubilidade não basta. LACUNA sem quote ou com overlap passa.
Vereditos diferenciam corpus/doc: "citação fora do corpus",
"literal/versão ausente no doc citado".
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("lacuna quote gate test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

URL = "https://example.org/docs/v2ex-like"
PLAN = {"plan_id": "p", "version": 1,
        "entities": [{"id": "e0", "label": "Ferramenta Y",
                      "required": True}],
        "criteria": [{"id": "c0", "label": "feature", "required": True,
                      "applies_to": ["e0"], "description": "Eixo feature: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

DOC_PLAIN = ("Pagina de discussao geral sobre configuracao, sem flags "
             "de player e sem literais de codigo.")
DOC_WITH_FLAG = ('Pagina com trecho `"desktop_use_new_history_manager":true` '
                 "e discussao geral.")


class LacunaQuoteGateTest(unittest.TestCase):
    def test_lacuna_quote_absent_fails(self):
        sentence = ('LACUNA — Documentado: o excerto contém apenas '
                    '`"desktop_use_new_history_manager":true` [1].')
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: DOC_PLAIN}, PLAN)
        self.assertEqual(result["supported"], 0, result)
        self.assertEqual(len(result["unsupported"]), 1)
        self.assertIn("literal",
                      result["unsupported"][0]["reason"])

    def test_lacuna_no_quote_passes(self):
        sentence = ("Nenhum excerto do corpus em [1] afirma ou nega "
                    "compatibilidade.")
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: DOC_PLAIN}, PLAN)
        self.assertEqual(result["supported"], 1, result)
        self.assertEqual(result["unsupported"], [])

    def test_lacuna_quote_present_passes(self):
        sentence = ('LACUNA — Documentado: o excerto contém apenas '
                    '`"desktop_use_new_history_manager":true` [1].')
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: DOC_WITH_FLAG}, PLAN)
        self.assertEqual(result["supported"], 1, result)
        self.assertEqual(result["unsupported"], [])

    def test_lacuna_version_absent_fails(self):
        sentence = ('LACUNA: o excerto contém apenas `"foo":true` '
                    "e cita a versão 9.9.9 [1].")
        doc = ('Pagina com trecho `"foo":true` e discussao geral, '
               "sem versao citada.")
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: doc}, PLAN)
        self.assertEqual(result["supported"], 0, result)
        self.assertIn("versão",
                      result["unsupported"][0]["reason"])

    def test_lacuna_version_gap_still_passes(self):
        sentence = ("Compatibilidade com a versão 2.1.4 desconhecida: "
                    "sem menção no documento [1].")
        doc = ("Ferramenta Y gerencia planos e compatibilidade "
               "com versões do editor desconhecida sem menção detalhada.")
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: doc}, PLAN)
        self.assertEqual(result["supported"], 1, result)

    def test_lacuna_unmapped_citation_is_corpus_miss(self):
        sentence = "Nenhum excerto do corpus em [9] afirma compatibilidade."
        result = verify.check_support(sentence, {9: "https://x.example/y"},
                                      {URL: DOC_PLAIN}, PLAN)
        self.assertEqual(result["supported"], 0, result)
        self.assertIn("corpus",
                      result["unsupported"][0]["reason"])

    def test_short_label_stays_exempt(self):
        sentence = "`cand-x`: **insufficient** — sem revisão demonstrada [1]."
        result = verify.check_support(sentence, {URL: 1},
                                      {URL: DOC_PLAIN}, PLAN)
        self.assertEqual(result["supported"], 1, result)


if __name__ == "__main__":
    unittest.main()
