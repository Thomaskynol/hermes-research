#!/usr/bin/env python3
"""Missão 3 — 3 contratos (genérico, sem nomes de produto).

1. [N] resolve: verify_support resolve citação in-text [N] via
   state[report][numbers] (mesmo _n_to_url de check_support) antes de
   extract_references; unknown = [N] sem URL + URL fora do corpus;
   reason "citação fora do corpus" nos dois auditores; gate vazio:
   claims==0 com refs válidas não diz "Sem citações verificáveis".
2. Versão-premissa: comparação numérica contra mínimo declarado =
   sustentada (premissa+corpus); compat funcional/integração sem fonte
   que mencione a versão = LACUNA (versão exata ausente no doc).
3. Complementaridade: trava interop para qualquer claim com >=2
   entidades (com ou sem marcador): integração testada (doc com >=2
   entidades -> supported); complementaridade plausível (âncoras ok em
   docs separados -> declared/LACUNA explícita, não unsupported
   genérico); resto unsupported.

Positivo + negativo pela MESMA entrada real
(check_support/verify_support/diagnose).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("missao3 test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

try:
    from scripts import citation_audit as ca
except ImportError:
    import citation_audit as ca  # type: ignore

A = "https://ex.example/a"
B = "https://ex.example/b"
OUTSIDE = "https://outside.example/doc"

DOC_A = ("Widget Alpha gerencia planos com revisao e testes. "
         "Release 1.0.150 documentada.")
DOC_B = ("Widget Beta executa buscas e preenche formularios. "
         "Release 2.0.10 documentada.")
DOC_BOTH = ("Widget Alpha gerencia planos e integra com Widget Beta "
            "via interface documentada para uso combinado.")
DOC_MIN = ("Widget Alpha requer versão mínima 1.0.0 para planejamento "
           "e revisao.")

PLAN_1 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True, "applies_to": ["e0"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

PLAN_2 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True},
                       {"id": "e1", "label": "Widget Beta",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True, "applies_to": ["e0", "e1"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

OK_AUDIT = {"enabled": True, "claims": 1, "claims_reviewed": 1,
            "verdicts": [{"id": 0, "verdict": "sustained"}],
            "accepted": True}


def _state(report, numbers, evidence, audit=None):
    return {"run_id": "t", "plan": PLAN_1, "evidence": evidence,
            "qualification": {},
            "counters": {"documents": {
                "used_in_synthesis": list(evidence)[:1]}},
            "report": {"markdown": report, "numbers": numbers},
            "semantic": audit or dict(OK_AUDIT)}


class BracketResolveTest(unittest.TestCase):
    def test_bracket_valid_resolves(self):
        report = "Widget Alpha gerencia planos com revisao [1]."
        dim = verify.verify_support(
            _state(report, {"1": A}, {A: DOC_A}), report, dict(OK_AUDIT))
        self.assertGreaterEqual(
            dim["evidence"].get("citations_resolved", 0), 1,
            dim["evidence"])
        self.assertEqual(dim["evidence"].get("citations_unknown"), [],
                         dim["evidence"])
        self.assertNotEqual(dim["status"], "failed", dim)

    def test_bracket_without_url_is_unknown_fail(self):
        report = "Widget Alpha gerencia planos com revisao [99]."
        dim = verify.verify_support(
            _state(report, {"1": A}, {A: DOC_A}), report, dict(OK_AUDIT))
        self.assertTrue(
            any("99" in str(u)
                for u in dim["evidence"].get("citations_unknown", [])),
            dim["evidence"])
        self.assertEqual(dim["status"], "failed", dim)

    def test_bracket_url_outside_corpus_is_unknown(self):
        report = "Widget Alpha gerencia planos com revisao [1]."
        dim = verify.verify_support(
            _state(report, {"1": OUTSIDE}, {A: DOC_A}), report,
            dict(OK_AUDIT))
        self.assertIn(ca.normalize_url(OUTSIDE),
                      dim["evidence"].get("citations_unknown", []),
                      dim["evidence"])
        self.assertEqual(dim["status"], "failed", dim)

    def test_empty_report_is_not_run(self):
        dim = verify.verify_support(
            _state("Sem citações.", {}, {}), "Sem citações.",
            {"enabled": False})
        self.assertEqual(dim["status"], "not_run", dim)
        self.assertTrue(any("citações verificáveis" in str(n).lower()
                            for n in dim.get("notes", [])), dim)

    def test_zero_claims_with_valid_refs_is_not_empty(self):
        report = "Widget Alpha gerencia planos com revisao [1]."
        audit = {"enabled": True, "claims": 0, "claims_reviewed": 0,
                 "verdicts": [], "accepted": True}
        dim = verify.verify_support(
            _state(report, {"1": A}, {A: DOC_A}, audit), report, audit)
        self.assertNotEqual(dim["status"], "not_run", dim)
        self.assertFalse(any("citações verificáveis" in str(n).lower()
                             for n in dim.get("notes", [])), dim)

    def test_check_support_unmapped_number_reason(self):
        res = verify.check_support(
            "Widget Alpha gerencia planos com revisao [9].",
            {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 0, res)
        self.assertEqual(res["unsupported"][0]["reason"],
                         "citação fora do corpus", res)

    def test_check_support_outside_corpus_url_reason(self):
        res = verify.check_support(
            "Widget Alpha gerencia planos com revisao [9].",
            {9: OUTSIDE}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 0, res)
        self.assertEqual(res["unsupported"][0]["reason"],
                         "citação fora do corpus", res)

    def test_diagnose_unmapped_number_reason(self):
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": "Widget Alpha gerencia planos "
                                     "com revisao [9].\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("fora do corpus",
                      out["unsupported_items"][0]["reason"], out)


class VersionPremiseTest(unittest.TestCase):
    NUMERIC = ("Widget Alpha requer versão mínima 1.0.0; a versão "
               "instalada 2.1.4 [contexto informado pelo usuário] "
               "atende ao mínimo [1].")
    FUNCTIONAL = ("Widget Alpha é compatível com a versão instalada "
                  "2.1.4 [contexto informado pelo usuário] [1].")

    def test_numeric_comparison_against_minimum_is_sustained(self):
        res = verify.check_support(
            self.NUMERIC, {1: A}, {A: DOC_MIN}, PLAN_1)
        self.assertEqual(res["supported"], 1, res)

    def test_functional_compat_without_source_version_fails(self):
        res = verify.check_support(
            self.FUNCTIONAL, {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 0, res)
        self.assertEqual(res["unsupported"][0]["reason"],
                         "versão exata ausente no doc", res)

    def test_diagnose_numeric_sustained_functional_fails(self):
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_MIN},
              "report": {"markdown": self.NUMERIC + "\n",
                         "numbers": {"1": A}}}
        self.assertEqual(diag.synthesis_audit(st)["unsupported"], 0,
                         diag.synthesis_audit(st))
        st2 = {"plan": PLAN_1, "evidence": {A: DOC_A},
               "report": {"markdown": self.FUNCTIONAL + "\n",
                          "numbers": {"1": A}}}
        out = diag.synthesis_audit(st2)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("versão exata",
                      out["unsupported_items"][0]["reason"].lower(), out)

    def test_writer_prompt_uses_narrow_version_rule(self):
        import adaptive_coordinator as ac
        prompts = []

        def model(prompt):
            prompts.append(prompt)
            return "texto"

        write = ac.make_model_writer(model)
        write({"question": "q", "plan": PLAN_1,
               "evidence": {A: DOC_A},
               "question_coverage": {}, "stop": {}, "rounds": []})
        prompt = prompts[0]
        self.assertIn("premissa", prompt.lower())
        # regra estreita: comparação numérica vs mínimo = sustentada;
        # funcional sem fonte com a versão = LACUNA
        self.assertIn("mínimo", prompt.lower(), prompt[:2000])
        # instrução geral rejeitada não pode reaparecer
        self.assertNotIn("conclusão que dependa deles é LACUNA", prompt)


class InteropLockTest(unittest.TestCase):
    SENTENCE = ("Widget Alpha gerencia planos e integra com Widget Beta "
                "para uso combinado [1][2].")

    def test_separate_docs_is_declared_lacuna_not_generic(self):
        res = verify.check_support(
            self.SENTENCE, {1: A, 2: B}, {A: DOC_A, B: DOC_B}, PLAN_2)
        self.assertEqual(res["supported"], 0, res)
        reason = res["unsupported"][0]["reason"].lower()
        self.assertTrue("interoperabilidade" in reason
                        or "integra" in reason, res)
        self.assertNotIn(res["unsupported"][0]["reason"],
                         ("sem sobreposição",
                          "entidade não mencionada no doc"), res)
        scopes = [str((d or {}).get("scope", "")).lower()
                  for d in (res.get("declared") or [])]
        scopes += [str((d or {}).get("scope", "")).lower()
                   for d in (res.get("declared_inference") or [])]
        self.assertTrue(any("lacuna" in s for s in scopes), res)

    def test_interop_doc_sustains(self):
        res = verify.check_support(
            "Widget Alpha gerencia planos e integra com Widget Beta "
            "para uso combinado [1].",
            {1: A}, {A: DOC_BOTH}, PLAN_2)
        self.assertEqual(res["supported"], 1, res)

    def test_diagnose_separate_docs_is_interop_not_generic(self):
        import diagnose_run as diag
        st = {"plan": PLAN_2, "evidence": {A: DOC_A, B: DOC_B},
              "report": {"markdown": self.SENTENCE + "\n",
                         "numbers": {"1": A, "2": B}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        reason = out["unsupported_items"][0]["reason"].lower()
        self.assertTrue("interoperabilidade" in reason
                        or "integra" in reason, out)

    def test_diagnose_interop_doc_sustains(self):
        import diagnose_run as diag
        st = {"plan": PLAN_2, "evidence": {A: DOC_BOTH},
              "report": {"markdown": "Widget Alpha gerencia planos e "
                                     "integra com Widget Beta para uso "
                                     "combinado [1].\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out)


if __name__ == "__main__":
    unittest.main()
