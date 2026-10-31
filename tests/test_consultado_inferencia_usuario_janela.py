#!/usr/bin/env python3
"""Foco: consultado vs mencionado, inferencia por premissas, fato usuario, janela.

Generico, sem nomes de produto. Caminho real: check_support / verify_support /
diagnose.synthesis_audit + citation_audit + renderer.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("focused test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify
import report_renderer as renderer

try:
    from scripts import citation_audit as ca
except ImportError:
    import citation_audit as ca  # type: ignore

PLAN_1 = {"plan_id": "p", "version": 1,
          "entities": [{"id": "e0", "label": "Widget Alpha",
                        "required": True}],
          "criteria": [{"id": "c0", "label": "compatibilidade",
                        "required": True, "applies_to": ["e0"]}]}

DOC_ALPHA = ("Widget Alpha gerencia planos com revisao e testes. "
             "Release 1.0.150 documentada.")
DOC_BETA = ("Widget Beta executa buscas e preenche formularios. "
            "Release 2.0.10 documentada.")
DOC_BOTH = ("Widget Alpha gerencia planos e integra com Widget Beta "
            "via interface documentada para uso combinado.")


class ConsultadoVsMencionadoTest(unittest.TestCase):
    def test_outside_preservada_como_literal_nao_registra(self):
        numbers = {"https://ex.example/doc": 1}
        text = 'Veja "https://outside.example/a" aqui [1].'
        _text, outside = renderer._rewrite_refs(text, numbers, set())
        # URL dentro de literal citado e preservada: nao e citacao fora
        self.assertEqual(outside, [], outside)
        self.assertIn("https://outside.example/a", _text)

    def test_normalize_aspas_curvas(self):
        self.assertEqual(ca.normalize_url("https://ex.example/x”"),
                         ca.normalize_url("https://ex.example/x"))
        self.assertEqual(ca.normalize_url("“https://ex.example/x”"),
                         "https://ex.example/x")

    def test_classify_npx_e_in_code(self):
        r1 = {"format": "bare", "snippet": "run npx -y pacote",
              "in_code": False, "spoken": None}
        self.assertEqual(ca.classify_reference(r1), "in_command")
        r2 = {"format": "bare",
              "snippet": "veja `https://ex.example/x` aqui",
              "in_code": True, "spoken": None}
        self.assertEqual(ca.classify_reference(r2), "in_command")
        r3 = {"format": "markdown", "snippet": "[guia](https://ex.example/x)",
              "in_code": True, "spoken": None}
        self.assertEqual(ca.classify_reference(r3), "evidence")

    def test_verify_support_so_evidence_pondera_unknown(self):
        report = ("Widget Alpha gerencia planos com revisao [1].\n\n"
                  "- render: sintese citou URL fora do corpus e foi removida: "
                  "https://outside.example/foo\n\n"
                  "Veja https://outside.example/bar para detalhes.\n\n"
                  "## 7. Fontes\n\n"
                  "| # | URL |\n|---|---|\n"
                  "| [1] | https://ex.example/doc |\n")
        state = {"run_id": "t", "plan": PLAN_1,
                 "evidence": {"https://ex.example/doc": DOC_ALPHA},
                 "qualification": {},
                 "counters": {"documents": {
                     "used_in_synthesis": ["https://ex.example/doc"]}},
                 "report": {"markdown": report,
                            "numbers": {"1": "https://ex.example/doc"}}}
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [{"id": 0, "verdict": "sustained"}],
                 "accepted": True}
        dim = verify.verify_support(state, report, audit)
        # mencoes utilitarias + linhas de nota propria nao viram unknown
        self.assertEqual(dim["evidence"].get("citations_unknown"), [],
                         dim["evidence"])
        self.assertNotEqual(dim["status"], "failed", dim)


class InferenciaPorPremissasTest(unittest.TestCase):
    def _plan2(self):
        return {"plan_id": "p", "version": 1,
                "entities": [{"id": "e0", "label": "Widget Alpha",
                              "required": True},
                             {"id": "e1", "label": "Widget Beta",
                              "required": True}],
                "criteria": [{"id": "c0", "label": "compatibilidade",
                              "required": True,
                              "applies_to": ["e0", "e1"]}]}

    def test_combinacao_sem_interop_nao_sustenta(self):
        plan = self._plan2()
        sentence = ("Widget Alpha gerencia planos [1] — INFERÊNCIA: "
                    "combina com Widget Beta sem sobreposição [2].")
        res = verify.check_support(
            sentence, {1: "https://ex.example/a",
                       2: "https://ex.example/b"},
            {"https://ex.example/a": DOC_ALPHA,
             "https://ex.example/b": DOC_BETA}, plan)
        # ancora sozinha nao sustenta; exige citacao de interoperabilidade
        self.assertEqual(res["supported"], 0, res)
        self.assertEqual(len(res["unsupported"]), 1, res)
        reason = res["unsupported"][0]["reason"].lower()
        self.assertTrue("interoperabilidade" in reason or "lacuna" in reason
                        or "integra" in reason, reason)
        # vira inferencia declarada, nunca supported por ancora
        self.assertTrue(res.get("declared_inference"), res)

    def test_combinacao_com_interop_documentada_sustenta(self):
        plan = self._plan2()
        sentence = ("Widget Alpha gerencia planos [1] — INFERÊNCIA: "
                    "integra com Widget Beta [1].")
        res = verify.check_support(
            sentence, {1: "https://ex.example/a"},
            {"https://ex.example/a": DOC_BOTH}, plan)
        self.assertEqual(res["supported"], 1, res)

    def test_diagnose_marca_complementaridade_plausivel(self):
        import diagnose_run as diag
        plan = self._plan2()
        state = {"plan": plan,
                 "evidence": {"https://ex.example/a": DOC_ALPHA,
                              "https://ex.example/b": DOC_BETA},
                 "report": {
                     "markdown": ("Widget Alpha gerencia planos [1] — "
                                  "INFERÊNCIA: combina com Widget Beta "
                                  "sem sobreposição [2].\n"),
                     "numbers": {"1": "https://ex.example/a",
                                 "2": "https://ex.example/b"}}}
        out = diag.synthesis_audit(state)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertTrue(
            "interoperabilidade" in out["unsupported_items"][0]["reason"].lower()
            or "integra" in out["unsupported_items"][0]["reason"].lower(),
            out["unsupported_items"])


class FatoUsuarioTest(unittest.TestCase):
    def test_corpus_exclui_user_context(self):
        st = {"evidence": {"https://ex.example/doc": "texto util",
                           "user://context/installed_opencode_version": "2.1.4"},
              "qualification": {"https://ex.example/doc": {},
                                "user://context/installed_opencode_version": {
                                    "usable_text": "2.1.4"}}}
        corp = verify._corpus(st)
        self.assertNotIn("user://context/installed_opencode_version", corp)

    def test_renderer_corpus_exclui_user_context(self):
        st = {"evidence": {"https://ex.example/doc": "texto util",
                           "user://context/k": "2.1.4"},
              "counters": {}}
        corp = renderer._corpus(st)
        self.assertNotIn("user://context/k", corp)

    def test_premissa_usuario_explicita_nao_e_lacuna_automatica(self):
        doc = ("Widget Alpha gerencia planos com revisao. "
               "Release 1.0.150 documentada.")
        sentence = ("Widget Alpha gerencia planos [1] "
                    "(versão instalada 2.1.4 "
                    "[contexto informado pelo usuário]).")
        res = verify.check_support(
            sentence, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": doc}, PLAN_1)
        # premissa explicita do usuario + doc da entidade: nao falha como
        # versao ausente automatica
        self.assertEqual(res["supported"], 1, res)

    def test_gate_tag_exata_vs_familia(self):
        # doc so tem familia V2; frase com tag exata 2.1.4 sem isenção falha
        # como tag exata, nao como familia
        res_exact = verify.check_support(
            "Widget Alpha suporta a versão 2.1.4 [1].",
            {1: "https://ex.example/doc"},
            {"https://ex.example/doc":
             "Widget Alpha suporta OpenCode V2 com revisao."}, PLAN_1)
        self.assertEqual(res_exact["supported"], 0, res_exact)
        r_exact = res_exact["unsupported"][0]["reason"]
        # frase com familia V2 presente no doc passa
        res_fam = verify.check_support(
            "Widget Alpha suporta OpenCode V2 [1].",
            {1: "https://ex.example/doc"},
            {"https://ex.example/doc":
             "Widget Alpha suporta OpenCode V2 com revisao."}, PLAN_1)
        self.assertEqual(res_fam["supported"], 1, res_fam)
        self.assertNotEqual(r_exact.lower(), "sem sobreposição")


class JanelaContextoTest(unittest.TestCase):
    def test_sintese_cita_janela_e_lacuna_tem_escopo(self):
        report = "Nenhum excerto menciona custo [1]."
        state = {"run_id": "t", "plan": PLAN_1,
                 "evidence": {"https://ex.example/doc": DOC_ALPHA,
                              "https://ex.example/outro": DOC_BETA},
                 "qualification": {},
                 "counters": {"documents": {
                     "used_in_synthesis": ["https://ex.example/doc"]}},
                 "report": {"markdown": report + "\n\n## 7. Fontes\n\n"
                            "| # | URL |\n|---|---|\n"
                            "| [1] | https://ex.example/doc |\n",
                            "numbers": {"1": "https://ex.example/doc"},
                            "selection": {
                                "included_urls": ["https://ex.example/doc"],
                                "chars": 1200,
                                "cuts": "janela de relevancia teste"}}}
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [{"id": 0, "verdict": "sustained"}],
                 "accepted": True}
        dim = verify.verify_support(
            state, state["report"]["markdown"], audit)
        win = dim["evidence"].get("audit_window") or {}
        # sintese cita a janela do writer
        self.assertTrue(win.get("writer_included_urls")
                        or win.get("selection_urls"), win)
        # lacuna carrega escopo de janela vs global
        sent = verify.check_support(
            report, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": DOC_ALPHA}, PLAN_1)
        self.assertTrue(sent.get("declared"), sent)
        scope = str((sent["declared"][0] or {}).get("scope") or "").lower()
        self.assertTrue("janela" in scope or "window" in scope
                        or "excerto" in scope, sent)

    def test_so_links_exige_diff_excerto_fulltext(self):
        doc = ("Links: https://a.example/x https://b.example/y "
               "Widget Alpha gerencia planos com revisao.")
        report = ("Widget Alpha só lista links [1].")
        sent = verify.check_support(
            report, {1: "https://ex.example/doc"},
            {"https://ex.example/doc": doc}, PLAN_1)
        win = sent.get("audit_window") or {}
        # antes de concluir "só links", auditoria registra diff
        # excerto vs full-text (ou janela auditada)
        self.assertTrue("excerpt" in str(win).lower()
                        or "janela" in str(win).lower()
                        or "window" in str(win).lower()
                        or "full" in str(win).lower(), sent)


if __name__ == "__main__":
    unittest.main()
