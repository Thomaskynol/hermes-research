"""Granularidade de auditoria B2/B5 (accept21, genérico, sem nomes de produto).

B2: check_support não pode diluir versão por blob multi-bullet: a trava de
versão e a isenção de lacuna valem por bullet (linha), como o diagnose.
B5: verify_support registra qual janela auditou (hashes do texto auditado +
seleção quando presente) e pondera sentence_support quando a citação é do
doc da entidade, convergindo os três sem reescrever auditores.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import verification_report as verify


def _plan():
    return {
        "plan_id": "p", "version": 1,
        "entities": [{"id": "e0", "label": "Widget Alpha",
                      "required": True}],
        "criteria": [{"id": "c0", "label": "compatibilidade",
                      "required": True, "applies_to": ["e0"]}],
    }


DOC_OLD = ("Widget Alpha gerencia planos com revisao e testes. "
           "Release 1.0.150 documentada.")


class B2PerBulletVersionTest(unittest.TestCase):
    def test_mixed_bullets_do_not_dilute_version_miss(self):
        # Bullet 1 declara desconhecimento (isenção legítima); bullet 2
        # afirma a versão concreta ausente no doc. Por blob, o "desconhecida"
        # do bullet 1 isenta o blob inteiro; por linha, o bullet 2 falha.
        text = ("- Compatibilidade com a versao 9.9.9 desconhecida: "
                "sem mencao no documento [1]\n"
                "- Suporta a versao 9.9.9 com estabilidade [1]")
        res = verify.check_support(
            text, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": DOC_OLD}, _plan())
        # converge com diagnose (1 unsupported na linha concreta)
        self.assertGreaterEqual(len(res["unsupported"]), 1, res)
        self.assertLess(res["supported"], res["claims"], res)

    def test_single_bullet_controls_unchanged(self):
        ok_text = "Widget Alpha gerencia planos com revisao [1]."
        res = verify.check_support(
            ok_text, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": DOC_OLD}, _plan())
        self.assertEqual(res["supported"], 1, res)
        bad_text = "Widget Alpha suporta a versao 9.9.9 [1]."
        res2 = verify.check_support(
            bad_text, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": DOC_OLD}, _plan())
        self.assertEqual(res2["supported"], 0, res2)


class B5WindowAndWeightingTest(unittest.TestCase):
    def _state(self, report, audit):
        # Relatório entregue real: corpo com [n] + tabela §7 com URLs, para
        # que extract_references encontre citações verificáveis.
        full = (report + "\n\n## 7. Fontes\n\n"
                "| # | URL |\n|---|---|\n"
                "| [1] | https://ex.example/doc |\n")
        return {
            "run_id": "t",
            "plan": _plan(),
            "evidence": {"https://ex.example/doc": DOC_OLD},
            "qualification": {},
            "counters": {"documents": {
                "used_in_synthesis": ["https://ex.example/doc"]}},
            "report": {"markdown": full,
                       "numbers": {"1": "https://ex.example/doc"}},
        }, audit

    def test_verify_support_records_audit_window(self):
        report = "Widget Alpha gerencia planos com revisao [1]."
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [{"id": 0, "verdict": "sustained"}],
                 "accepted": True}
        state, _audit = self._state(report, audit)
        dim = verify.verify_support(
            state, state["report"]["markdown"], audit)
        self.assertIn("audit_window", dim["evidence"], dim["evidence"])
        window = dim["evidence"]["audit_window"]
        self.assertIn("doc_hashes", window, window)
        self.assertIn("https://ex.example/doc",
                      window["doc_hashes"], window)

    def test_verify_support_weights_sentence_version_miss(self):
        # Semântica sustenta, mas a frase cita o doc da entidade com
        # versão ausente: os três devem convergir para falha/parcial,
        # não "ok" só porque a citação resolve.
        report = "Widget Alpha suporta a versao 9.9.9 [1]."
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [{"id": 0, "verdict": "sustained"}],
                 "accepted": True}
        state, _audit = self._state(report, audit)
        dim = verify.verify_support(
            state, state["report"]["markdown"], audit)
        sent = verify.check_support(
            report, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": DOC_OLD}, _plan())
        self.assertEqual(sent["supported"], 0, sent)
        # ponderação: verify_support não pode ficar "ok" quando a
        # sentença (doc da entidade) acusa versão ausente
        self.assertNotEqual(dim["status"], "ok", dim)
        joined = " ".join(dim.get("notes", [])).lower()
        self.assertTrue("sentence" in joined or "vers" in joined,
                        dim.get("notes"))

    def test_generic_overlap_does_not_force_fail(self):
        # Frase genérica sem versão/entidade nomeada: ponderação não
        # pode transformar "ok" em falha (preserva verificação existente).
        plan_empty = {"plan_id": "p", "entities": [], "criteria": []}
        state = {
            "run_id": "t",
            "evidence": {"https://used.example/doc": "substantive text here",
                         "https://table.example/other": "other text here"},
            "qualification": {},
            "counters": {"documents": {
                "used_in_synthesis": ["https://used.example/doc"]}},
            "report": {"markdown": (
                "## 1. Síntese\n\nAfirmação com citação [1].\n\n"
                "## 7. Fontes\n\n"
                "| # | URL |\n|---|---|\n"
                "| [1] | https://used.example/doc |\n"
                "| [2] | https://table.example/other |\n")},
        }
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [], "accepted": True}
        dim = verify.verify_support(
            state, state["report"]["markdown"], audit)
        # sem entidades e sem numbers persistidos: sem ponderação agressiva
        self.assertNotEqual(dim["status"], "failed", dim)


if __name__ == "__main__":
    unittest.main()
