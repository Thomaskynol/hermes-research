#!/usr/bin/env python3
"""Divergências auditores — mesma entrada nos 3 auditores (genérico, sem nomes).

1. URL evidência sem [N]: diagnose extrai só [N], verify extrai URLs
   (extract_references/Classify) → uncited vs unknown/failed. Unificar.
2. LACUNA: diagnose sustenta após premissa entidade, sem gate versão
   exata/família nem literal citado que check aplica → diagnose passa,
   verificador falha. Espelhar gates.
3. Ponderação: isenta qualquer _is_user_premise, mas check reprova
   premissa funcional sem fonte da versão → misses vazio com support ok
   vs versão exata ausente. Regra estreita (numérico sustenta, funcional
   reprova) também na ponderação.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("divergencias test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

try:
    from scripts import citation_audit as ca
except ImportError:
    import citation_audit as ca  # type: ignore

A = "https://ex.example/a"
OUTSIDE = "https://outside.example/doc"
DOC_A = ("Widget Alpha gerencia planos com revisao e testes. "
         "Release 1.0.150 documentada.")
DOC_MIN = ("Widget Alpha requer versão mínima 1.0.0 para planejamento "
           "e revisao.")
PLAN_1 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True, "applies_to": ["e0"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

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


class Div1BareEvidenceUrlTest(unittest.TestCase):
    # Mesma entrada: [1] dentro + markdown evidência fora (sem [N]).
    # Verify falha unknown; diagnose deve falhar igual (não uncited).
    REPORT_NEG = ("Widget Alpha gerencia planos com revisao [1], "
                  "veja [guia](https://outside.example/doc) para detalhes "
                  "adicionais sobre o tema abordado aqui.")
    REPORT_POS = ("Widget Alpha gerencia planos com revisao [1], "
                  "veja [guia](https://ex.example/a) para detalhes "
                  "adicionais sobre o tema abordado aqui.")

    def test_negative_verify_fails_unknown(self):
        dim = verify.verify_support(
            _state(self.REPORT_NEG, {"1": A}, {A: DOC_A}),
            self.REPORT_NEG, dict(OK_AUDIT))
        self.assertEqual(dim["status"], "failed", dim["evidence"])
        self.assertIn(ca.normalize_url(OUTSIDE),
                      dim["evidence"].get("citations_unknown", []),
                      dim["evidence"])

    def test_negative_diagnose_fails_same_entry(self):
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": self.REPORT_NEG + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("fora do corpus",
                      out["unsupported_items"][0]["reason"], out)

    def test_positive_same_entry_sustains_both(self):
        dim = verify.verify_support(
            _state(self.REPORT_POS, {"1": A}, {A: DOC_A}),
            self.REPORT_POS, dict(OK_AUDIT))
        self.assertNotEqual(dim["status"], "failed", dim["evidence"])
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": self.REPORT_POS + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out)
        self.assertGreaterEqual(out["supported"], 1, out)


class Div2LacunaGatesTest(unittest.TestCase):
    # Mesma entrada: LACUNA com versão exata ausente no doc.
    NEG = ("LACUNA: Widget Alpha compatível com versão 2.1.4 não "
           "verificado no excerto consultado [1].")
    # Positiva: lacuna com isenção (versão desconhecida declarada).
    POS = ("LACUNA: compatibilidade com 2.1.4 desconhecida nos "
           "excertos consultados [1].")

    def test_negative_check_fails_version(self):
        res = verify.check_support(self.NEG, {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 0, res)
        self.assertIn("versão exata",
                      res["unsupported"][0]["reason"].lower(), res)

    def test_negative_diagnose_fails_same_entry(self):
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": self.NEG + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("versão exata",
                      out["unsupported_items"][0]["reason"].lower(), out)

    def test_negative_verify_support_fails_same_entry(self):
        dim = verify.verify_support(
            _state(self.NEG, {"1": A}, {A: DOC_A}),
            self.NEG, dict(OK_AUDIT))
        # verify_support pondera sentença (B5) ou base: não pode ser ok
        self.assertNotEqual(dim["status"], "ok", dim["evidence"])

    def test_positive_lacuna_gap_sustains_both(self):
        res = verify.check_support(self.POS, {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 1, res)
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": self.POS + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out)

    def test_negative_lacuna_literal_missing_same_entry(self):
        # LACUNA cita literal ausente no doc → ambos reprovam.
        sent = ('LACUNA: Widget Alpha sem "opcao-magica-xyz" '
                'no excerto consultado [1].')
        res = verify.check_support(sent, {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res["supported"], 0, res)
        self.assertIn("literal",
                      res["unsupported"][0]["reason"].lower(), res)
        import diagnose_run as diag
        st = {"plan": PLAN_1, "evidence": {A: DOC_A},
              "report": {"markdown": sent + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("literal",
                      out["unsupported_items"][0]["reason"].lower(), out)


class Div3NarrowPremiseWeightingTest(unittest.TestCase):
    NUMERIC = ("Widget Alpha requer versão mínima 1.0.0; a versão "
               "instalada 2.1.4 [contexto informado pelo usuário] "
               "atende ao mínimo [1].")
    FUNCTIONAL = ("Widget Alpha é compatível com a versão instalada "
                  "2.1.4 [contexto informado pelo usuário] [1].")

    def test_check_numeric_sustains_functional_fails(self):
        res_num = verify.check_support(
            self.NUMERIC, {1: A}, {A: DOC_MIN}, PLAN_1)
        self.assertEqual(res_num["supported"], 1, res_num)
        res_fun = verify.check_support(
            self.FUNCTIONAL, {1: A}, {A: DOC_A}, PLAN_1)
        self.assertEqual(res_fun["supported"], 0, res_fun)
        self.assertIn("versão exata",
                      res_fun["unsupported"][0]["reason"].lower(), res_fun)

    def test_diagnose_numeric_sustains_functional_fails(self):
        import diagnose_run as diag
        st_num = {"plan": PLAN_1, "evidence": {A: DOC_MIN},
                  "report": {"markdown": self.NUMERIC + "\n",
                             "numbers": {"1": A}}}
        self.assertEqual(diag.synthesis_audit(st_num)["unsupported"], 0,
                         diag.synthesis_audit(st_num))
        st_fun = {"plan": PLAN_1, "evidence": {A: DOC_A},
                  "report": {"markdown": self.FUNCTIONAL + "\n",
                             "numbers": {"1": A}}}
        out = diag.synthesis_audit(st_fun)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("versão exata",
                      out["unsupported_items"][0]["reason"].lower(), out)

    def test_verify_weighting_narrow_same_entries(self):
        # Numérica: support ok, sem misses.
        dim_num = verify.verify_support(
            _state(self.NUMERIC, {"1": A}, {A: DOC_MIN}),
            self.NUMERIC, dict(OK_AUDIT))
        self.assertNotEqual(dim_num["status"], "failed",
                            dim_num["evidence"])
        self.assertFalse(dim_num["evidence"].get("sentence_misses"),
                         dim_num["evidence"])
        # Funcional sem fonte da versão: não pode ser ok, misses com
        # versão exata ausente (regra estreita, não isenção ampla).
        dim_fun = verify.verify_support(
            _state(self.FUNCTIONAL, {"1": A}, {A: DOC_A}),
            self.FUNCTIONAL, dict(OK_AUDIT))
        self.assertNotEqual(dim_fun["status"], "ok", dim_fun["evidence"])
        misses = dim_fun["evidence"].get("sentence_misses") or []
        self.assertTrue(misses, dim_fun["evidence"])
        self.assertTrue(any("versão exata" in str(m.get("reason", "")).lower()
                            or "versao exata" in str(m.get("reason", "")).lower()
                            for m in misses), dim_fun["evidence"])


if __name__ == "__main__":
    unittest.main()
