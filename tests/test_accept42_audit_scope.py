#!/usr/bin/env python3
"""accept42 itens 1-4 — gates de scope e contadores honestos (genérico).

1. Polaridade: frase interop com negação/limite ou modalidade não-factual
   nunca recebe "integração testada" (teto partial/LACUNA); afirmação
   positiva legítima que cita teste continua "integração testada".
2. Co-mencção ≠ teste: "integração testada" exige verbo de integração/
   teste na frase OU evidência de execução no doc; senão "documentado
   (sem teste executado)" (mera menção ao host + plugin não fecha interop).
3. Complementaridade inferida (relation_ok False) nunca vira integração
   testada; enumeração de candidatos do plano nunca entra no canal
   declared_inference.
4. Contadores honestos: claims_judged_quorum (veredito final, sem
   review_incomplete) separado de claims_reviewed (tentativa);
   "integralmente revisadas" só quando judged==claims; denominadores
   de quórum em nota. Offline, sem rede, sem run real.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept42 audit scope test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

URL = "https://example.com/widget-ambos"
URL_NOVERB = "https://example.com/widget-catalogo"
DOC = ("Widget Alpha e Widget Beta tem integracao testada no fluxo "
       "combinado com teste executado de uso conjunto.")
PLAN_2 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True},
                       {"id": "e1", "label": "Widget Beta",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True, "applies_to": ["e0", "e1"],
                        "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

NEG = ("Widget Alpha e Widget Beta tem integracao testada no fluxo "
       "combinado, sem prova de integracao no documento, "
       "que permanece LACUNA [1].")
POS = ("Widget Alpha e Widget Beta tem integracao testada documentada "
       "em teste executado de uso conjunto [1].")


def _scopes(res):
    decl = res.get("declared_inference") or []
    return " | ".join(str((d or {}).get("scope", "")) for d in decl)


class PolarityGateTest(unittest.TestCase):
    def test_negation_caps_integration_scope(self):
        res = verify.check_support(NEG, {1: URL}, {URL: DOC}, PLAN_2)
        scopes = _scopes(res)
        self.assertNotIn("integração testada", scopes, res)

    def test_legit_positive_keeps_integration_scope(self):
        res = verify.check_support(POS, {1: URL}, {URL: DOC}, PLAN_2)
        scopes = _scopes(res)
        self.assertIn("integração testada", scopes, res)


URL_P = "https://example.com/plannotator-doc"
DOC_P = ("Plannotator oferece fluxo de planejamento configurado para o "
         "plugin OpenCode com comandos de revisao manual.")
PLAN_HOST = {"plan_id": "p", "version": 1,
             "entities": [{"id": "e0", "label": "Plannotator",
                           "required": True},
                          {"id": "e1", "label": "OpenCode",
                           "required": True}],
             "criteria": [{"id": "c0", "label": "compatibilidade",
                           "required": True, "applies_to": ["e0", "e1"],
                           "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}
SENT_HOST = ("Plannotator oferece fluxo de planejamento configurado para "
             "o plugin OpenCode [1].")
SENT_TESTED = ("Widget Alpha e Widget Beta tem integracao testada "
               "documentada em teste executado de uso conjunto [7].")


class CoMentionVsTestTest(unittest.TestCase):
    def test_host_mention_without_test_verb_is_documented(self):
        res = verify.check_support(
            SENT_HOST, {1: URL_P}, {URL_P: DOC_P}, PLAN_HOST)
        scopes = _scopes(res)
        self.assertNotIn("integração testada", scopes, res)
        self.assertIn("documentado (sem teste executado)", scopes, res)
        self.assertEqual(res["supported"], 1, res)

    def test_tested_integration_claim_keeps_scope(self):
        res = verify.check_support(
            SENT_TESTED, {7: URL}, {URL: DOC}, PLAN_2)
        scopes = _scopes(res)
        self.assertIn("integração testada", scopes, res)
        self.assertEqual(res["supported"], 1, res)


DOC_NOVERB = ("Widget Alpha e Widget Beta foram revisados no catalogo "
              "com comparativo de recursos.")
SENT_INTEGRALMENTE = ("Widget Alpha e Widget Beta foram integralmente "
                      "revisados [1].")
SENT_INTEGRACAO = ("Integracao testada entre Widget Alpha e Widget Beta "
                   "no fluxo combinado [1].")


class InteropVerbFamilyTest(unittest.TestCase):
    def test_integralmente_is_not_integration_verb(self):
        res = verify.check_support(
            SENT_INTEGRALMENTE, {1: URL_NOVERB}, {URL_NOVERB: DOC_NOVERB},
            PLAN_2)
        scopes = _scopes(res)
        self.assertNotIn("integração testada", scopes, res)
        self.assertIn("documentado (sem teste executado)", scopes, res)
        self.assertEqual(res["supported"], 1, res)

    def test_integracao_keeps_integration_scope(self):
        res = verify.check_support(
            SENT_INTEGRACAO, {1: URL}, {URL: DOC}, PLAN_2)
        scopes = _scopes(res)
        self.assertIn("integração testada", scopes, res)
        self.assertEqual(res["supported"], 1, res)


URL_A2 = "https://example.com/widget-alpha"
URL_B2 = "https://example.com/widget-beta"
DOC_A2 = ("Widget Alpha gerencia planos com revisao e testes. "
          "Release 1.0.150 documentada.")
DOC_B2 = ("Widget Beta executa buscas e preenche formularios. "
          "Release 2.0.10 documentada.")
SENT_COMPL = ("Widget Alpha gerencia planos [1] \u2014 INFER\u00caNCIA: "
              "uso complementar com Widget Beta para fluxo combinado [2].")

URL_CAT = "https://example.com/catalogo"
DOC_CAT = ("Catalogo: Widget Alpha gerencia planos; Widget Beta revisa "
           "codigo; Widget Gamma executa testes; todos listados com links.")
PLAN_3 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True},
                       {"id": "e1", "label": "Widget Beta",
                        "required": True},
                       {"id": "e2", "label": "Widget Gamma",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True,
                        "applies_to": ["e0", "e1", "e2"],
                        "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}
SENT_ENUM = ("Os candidatos do plano sao Widget Alpha, Widget Beta e "
             "Widget Gamma listados no catalogo [1].")


def _entries_for(res, sentence):
    return [d for d in (res.get("declared_inference") or [])
            if (d or {}).get("sentence") == sentence]


class InferredComplementarityTest(unittest.TestCase):
    def test_relation_without_proof_never_integration(self):
        res = verify.check_support(
            SENT_COMPL, {1: URL_A2, 2: URL_B2},
            {URL_A2: DOC_A2, URL_B2: DOC_B2}, PLAN_2)
        scopes = _scopes(res)
        self.assertNotIn("integração testada (interoperabilidade citada)",
                         scopes, res)
        decl = _entries_for(res, SENT_COMPL)
        self.assertTrue(decl, res)
        self.assertFalse(any(d.get("relation_ok") for d in decl), decl)

    def test_plan_enumeration_never_enters_declared_inference(self):
        res = verify.check_support(
            SENT_ENUM, {1: URL_CAT}, {URL_CAT: DOC_CAT}, PLAN_3)
        self.assertEqual(_entries_for(res, SENT_ENUM), [], res)
        self.assertEqual(res["supported"], 1, res)


def _quorum_audit(n_incomplete=24):
    verdicts = [{"id": f"c{i}", "verdict": "review_incomplete"}
                for i in range(n_incomplete)]
    verdicts.append({"id": f"c{n_incomplete}", "verdict": "sustained"})
    return {
        "enabled": True, "claims": n_incomplete + 1,
        "claims_reviewed": n_incomplete + 1, "accepted": False,
        "verdict_state": "revisão incompleta", "verdicts": verdicts,
        "summary": {"votes": 3, "technical_failure_votes": 72,
                    "coverage": {"counts": {"blocks_total": 14,
                                            "blocks_processed": 14,
                                            "blocks_incomplete": 0}}},
    }


class QuorumCountersTest(unittest.TestCase):
    def test_review_separates_judged_from_reviewed(self):
        audit = _quorum_audit(24)
        dim = verify.verify_review({}, audit)
        ev = dim["evidence"]
        self.assertEqual(ev["claims_reviewed"], 25, ev)
        self.assertEqual(ev["claims_judged_quorum"], 1, ev)
        self.assertFalse(ev["accepted"], ev)
        self.assertEqual(ev["verdict_state"], "revisão incompleta", ev)
        self.assertEqual(dim["status"], "partial", dim)
        joined = " ".join(dim.get("notes", []))
        self.assertIn("75", joined, dim.get("notes"))
        self.assertIn("72", joined, dim.get("notes"))

    def test_support_requires_quorum_for_fully_reviewed(self):
        audit = {"enabled": True, "claims": 2, "claims_reviewed": 2,
                 "accepted": True,
                 "verdicts": [{"id": "a", "verdict": "review_incomplete"},
                              {"id": "b", "verdict": "sustained"}],
                 "summary": {"votes": 3, "technical_failure_votes": 0}}
        state = {
            "run_id": "t",
            "plan": {"plan_id": "p", "entities": [], "criteria": []},
            "evidence": {"https://ex.example/doc":
                         "Texto sobre o tema com conteudo suficiente."},
            "qualification": {},
            "counters": {"documents": {"used_in_synthesis":
                                       ["https://ex.example/doc"]}},
            "report": {"markdown": "Afirmação com citação [1].",
                       "numbers": {"1": "https://ex.example/doc"}},
        }
        dim = verify.verify_support(
            state, state["report"]["markdown"], audit)
        self.assertEqual(dim["evidence"]["claims_judged_quorum"], 1,
                         dim["evidence"])
        self.assertEqual(dim["status"], "partial", dim)
        joined = " ".join(dim.get("notes", [])).lower()
        self.assertIn("integralmente revisadas", joined, dim.get("notes"))


if __name__ == "__main__":
    unittest.main()
