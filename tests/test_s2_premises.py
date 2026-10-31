"""S2 sem isenção automática (accept17 residuals).

INFERÊNCIA/LACUNA marcadas precisam de premissas verificáveis: a
premissa existe e está citada (doc citado menciona a entidade quando a
frase a nomeia). Falsos positivos do heurístico corrigidos sem
mascarar a citação frouxa real do writer — os dois casos com testes
que os diferenciam:

- FP rótulo exato: doc sobre "OpenCode Plugin" sustenta frase sobre
  "OpenCode Eclipse Plugin" (2+ tokens distintivos compartilhados).
- FP "versão ausente": frase que declara desconhecimento da versão
  (ex. 2.1.4) não falha por o doc não conter a string cuja ausência é
  o conteúdo da frase.
- Frouxa real: LACUNA nomeando entidade citada contra doc que não a
  menciona continua unsupported (premissa sem doc da entidade).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("s2 test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify

PLAN = {"plan_id": "p", "version": 1,
        "entities": [{"id": "e0", "label": "OpenCode Eclipse Plugin",
                      "required": True}],
        "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                      "applies_to": ["e0"]}]}

DOC_PLUGIN = ("OpenCode Plugin: gerencia planos de implementação com "
              "revisão e testes automatizados.")
DOC_OTHER = ("AlphaWidget planner: comandos de planejamento e revisão "
             "de código.")


class EntityMentionFallbackTest(unittest.TestCase):
    def test_prefix_doc_form_sustains(self):
        ok, reason = verify._sentence_supported(
            set(verify._content_tokens(
                "O OpenCode Eclipse Plugin gerencia planos")),
            DOC_PLUGIN,
            [({"opencode", "eclipse", "plugin"}, "OpenCode Eclipse Plugin",
              "e0")],
            "O OpenCode Eclipse Plugin gerencia planos [1].")
        self.assertTrue(ok, reason)

    def test_single_shared_generic_token_still_rejects(self):
        ok, reason = verify._sentence_supported(
            set(verify._content_tokens("opencode agents executa planos")),
            "opencode-planner: gerencia planos de deploy.",
            [({"opencode", "agents"}, "opencode agents", "e9")],
            "opencode agents executa planos [1].")
        self.assertFalse(ok)
        self.assertEqual(reason, "entidade não mencionada no doc")


class VersionUncertaintyTest(unittest.TestCase):
    def test_declared_unknown_version_does_not_fail_on_absence(self):
        sentence = ("Compatibilidade com a versão 2.1.4 desconhecida: "
                    "sem menção no documento [1].")
        doc = ("OpenCode Eclipse Plugin gerencia planos e compatibilidade "
               "com versões do editor desconhecida sem menção detalhada.")
        result = verify.check_support(
            sentence, {1: "https://example.org/plugin"},
            {"https://example.org/plugin": doc}, PLAN)
        self.assertEqual(result["supported"], 1, result)

    def test_asserted_version_still_requires_doc_match(self):
        result = verify.check_support(
            "A API V2 é a única versão suportada [1].",
            {1: "https://example.org/plugin"},
            {"https://example.org/plugin": DOC_PLUGIN}, PLAN)
        self.assertEqual(result["supported"], 0)

    def test_uncertain_version_skips_absence_gate(self):
        sentence = ("O OpenCode Eclipse Plugin gerencia planos na "
                    "versão 2.1.4 desconhecida [1].")
        doc = ("OpenCode Plugin gerencia planos e revisões; "
               "compatibilidade desconhecida.")
        ok, reason = verify._sentence_supported(
            set(verify._content_tokens(sentence)), doc,
            [({"opencode", "eclipse", "plugin"},
              "OpenCode Eclipse Plugin", "e0")], sentence)
        self.assertTrue(ok, reason)


class LacunaPremiseTest(unittest.TestCase):
    def test_lacuna_citing_entity_doc_is_sustained(self):
        result = verify.check_support(
            "Nenhum excerto declara custos do plugin [1].",
            {1: "https://example.org/plugin"},
            {"https://example.org/plugin": DOC_PLUGIN}, PLAN)
        self.assertEqual(result["supported"], 1, result)
        self.assertEqual(result["declared"][0]["premise_docs"], 1)

    def test_lacuna_citing_foreign_doc_is_unsupported(self):
        result = verify.check_support(
            "Nenhum excerto declara custos do OpenCode Eclipse Plugin [1].",
            {1: "https://example.org/other"},
            {"https://example.org/other": DOC_OTHER}, PLAN)
        self.assertEqual(result["supported"], 0, result)
        self.assertEqual(len(result["unsupported"]), 1)
        self.assertIn("entidade", result["unsupported"][0]["reason"])

    def test_writer_prompt_requires_premise_cites(self):
        import adaptive_coordinator as ac
        prompts = []

        def model(prompt):
            prompts.append(prompt)
            return "texto"

        write = ac.make_model_writer(model)
        write({"question": "q", "plan": PLAN,
               "evidence": {"https://example.org/plugin": DOC_PLUGIN},
               "question_coverage": {}, "stop": {}, "rounds": []})
        self.assertIn("premissa", prompts[0].lower())


class DiagnosePremiseTest(unittest.TestCase):
    def _diag_state(self, line, url, doc):
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        import diagnose_run as diag
        evidence = {"https://example.org/plugin": DOC_PLUGIN,
                    "https://example.org/other": DOC_OTHER}
        evidence[url] = doc
        return diag, {"plan": PLAN, "evidence": evidence,
                      "report": {"numbers": {"1": url},
                                 "markdown": line + "\n"}}

    def test_diagnose_lacuna_with_entity_doc_supported(self):
        diag, st = self._diag_state(
            "Nenhum excerto declara custos do plugin [1].",
            "https://example.org/plugin", DOC_PLUGIN)
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out["unsupported_items"])

    def test_diagnose_lacuna_with_foreign_doc_flagged(self):
        diag, st = self._diag_state(
            "Nenhum excerto declara custos do OpenCode Eclipse Plugin [1].",
            "https://example.org/other", DOC_OTHER)
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1)
        self.assertIn("premissa", out["unsupported_items"][0]["reason"])

    def test_diagnose_uncertain_version_not_version_miss(self):
        diag, st = self._diag_state(
            "O OpenCode Eclipse Plugin gerencia planos na versão 2.1.4 "
            "desconhecida [1].",
            "https://example.org/plugin", DOC_PLUGIN)
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out["unsupported_items"])


if __name__ == "__main__":
    unittest.main()
