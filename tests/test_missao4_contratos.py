#!/usr/bin/env python3
"""Missão 4 — 3 contratos v2 (genérico, sem nomes de produto).

v2-1 inferência positiva: POS doc-interop (menciona ambas) -> supported
  + declared (premissas+limites); NEG docs separados -> declared/LACUNA
  explícita (não unsupported genérico); extrapolação (integração testada /
  ausência de conflitos sem fonte) -> rejeitado. Espelhado nos 3 auditores
  com canal declared. `logo` não é marcador de inferência. Versão numérica
  vs funcional preservada.
v2-2 consistência entrega: §8 reflete verificação final (two-pass ou rótulo);
  sem "sem citações verificáveis" com refs válidas; numbers estável, cited
  coerente; sem duplicação de notas em re-render.
v2-3 identidade/atribuição: eid derivado e-* ignorado, forma cheia com
  fronteira; refs de evaluation exigem identidade (_identity_matches +
  _singleton_rare); _rank_unfetched desempata por identidade, não substring.

Positivo + negativo pela MESMA entrada real nos 3 auditores.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("missao4 test is offline")


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


def _state(report, numbers, evidence, audit=None, plan=None):
    return {"run_id": "t", "plan": plan or PLAN_2, "evidence": evidence,
            "qualification": {},
            "counters": {"documents": {
                "used_in_synthesis": list(evidence)[:1]}},
            "report": {"markdown": report, "numbers": numbers},
            "semantic": audit or dict(OK_AUDIT)}


class InferencePositiveTest(unittest.TestCase):
    POS = ("Widget Alpha gerencia planos e integra com Widget Beta "
           "para uso combinado [1].")
    NEG = ("Widget Alpha gerencia planos e integra com Widget Beta "
           "para uso combinado [1][2].")

    def test_pos_interop_check_supported_and_declared(self):
        res = verify.check_support(
            self.POS, {1: A}, {A: DOC_BOTH}, PLAN_2)
        self.assertEqual(res["supported"], 1, res)
        scopes = [str((d or {}).get("scope", "")).lower()
                  for d in (res.get("declared") or [])]
        scopes += [str((d or {}).get("scope", "")).lower()
                   for d in (res.get("declared_inference") or [])]
        self.assertTrue(scopes, res)
        self.assertTrue(any("integra" in s or "interop" in s for s in scopes),
                        res)

    def test_pos_interop_diagnose_declared(self):
        import diagnose_run as diag
        st = {"plan": PLAN_2, "evidence": {A: DOC_BOTH},
              "report": {"markdown": self.POS + "\n",
                         "numbers": {"1": A}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 0, out)
        self.assertGreaterEqual(out["supported"], 1, out)
        self.assertIn("declared", out, out)
        self.assertTrue(out["declared"], out)

    def test_pos_interop_verify_no_misses(self):
        dim = verify.verify_support(
            _state(self.POS, {"1": A}, {A: DOC_BOTH}),
            self.POS, dict(OK_AUDIT))
        self.assertNotEqual(dim["status"], "failed", dim["evidence"])
        self.assertFalse(dim["evidence"].get("sentence_misses"),
                         dim["evidence"])

    def test_neg_separate_is_declared_lacuna_not_generic(self):
        res = verify.check_support(
            self.NEG, {1: A, 2: B}, {A: DOC_A, B: DOC_B}, PLAN_2)
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
        self.assertTrue(any("lacuna" in s or "complementar" in s
                            or "plaus" in s for s in scopes), res)

    def test_neg_separate_diagnose_declared_not_generic(self):
        import diagnose_run as diag
        st = {"plan": PLAN_2, "evidence": {A: DOC_A, B: DOC_B},
              "report": {"markdown": self.NEG + "\n",
                         "numbers": {"1": A, "2": B}}}
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        reason = out["unsupported_items"][0]["reason"].lower()
        self.assertTrue("interoperabilidade" in reason
                        or "integra" in reason, out)
        self.assertIn("declared", out, out)
        self.assertTrue(out["declared"], out)

    def test_neg_separate_verify_not_ok(self):
        dim = verify.verify_support(
            _state(self.NEG, {"1": A, "2": B}, {A: DOC_A, B: DOC_B}),
            self.NEG, dict(OK_AUDIT))
        self.assertNotEqual(dim["status"], "ok", dim["evidence"])

    def test_extrapolation_without_source_rejected(self):
        # Integração testada / ausência de conflitos afirmadas sem doc-interop.
        for sent in (
            "Widget Alpha e Widget Beta têm integração testada sem "
            "conflitos [1][2].",
            "Widget Alpha e Widget Beta não apresentam conflitos de "
            "integração [1][2].",
        ):
            res = verify.check_support(
                sent, {1: A, 2: B}, {A: DOC_A, B: DOC_B}, PLAN_2)
            self.assertEqual(res["supported"], 0,
                             f"extrapolação deveria falhar: {sent} {res}")
            import diagnose_run as diag
            st = {"plan": PLAN_2, "evidence": {A: DOC_A, B: DOC_B},
                  "report": {"markdown": sent + "\n",
                             "numbers": {"1": A, "2": B}}}
            out = diag.synthesis_audit(st)
            self.assertEqual(out["unsupported"], 1, f"{out} {sent}")

    def test_logo_is_not_inference_marker(self):
        self.assertFalse(verify._has_inference_marker(
            "Widget Alpha gerencia planos, logo integra com Widget Beta."))
        # `logo` não desvia para o ramo marcado: trava interop decide.
        sent = ("Widget Alpha gerencia planos, logo integra com Widget Beta "
                "[1][2].")
        res = verify.check_support(
            sent, {1: A, 2: B}, {A: DOC_A, B: DOC_B}, PLAN_2)
        self.assertEqual(res["supported"], 0, res)
        self.assertIn("interoperabilidade",
                      res["unsupported"][0]["reason"].lower(), res)

    def test_version_numeric_vs_functional_preserved(self):
        numeric = ("Widget Alpha requer versão mínima 1.0.0; a versão "
                   "instalada 2.1.4 [contexto informado pelo usuário] "
                   "atende ao mínimo [1].")
        functional = ("Widget Alpha é compatível com a versão instalada "
                      "2.1.4 [contexto informado pelo usuário] [1].")
        res_num = verify.check_support(
            numeric, {1: A}, {A: DOC_MIN}, PLAN_2)
        self.assertEqual(res_num["supported"], 1, res_num)
        res_fun = verify.check_support(
            functional, {1: A}, {A: DOC_A}, PLAN_2)
        self.assertEqual(res_fun["supported"], 0, res_fun)
        self.assertIn("versão exata",
                      res_fun["unsupported"][0]["reason"].lower(), res_fun)


class DeliveryConsistencyTest(unittest.TestCase):
    def test_no_false_not_run_with_valid_refs(self):
        report = "Widget Alpha gerencia planos com revisao [1]."
        audit = {"enabled": True, "claims": 0, "claims_reviewed": 0,
                 "verdicts": [], "accepted": True}
        dim = verify.verify_support(
            _state(report, {"1": A}, {A: DOC_A}, audit), report, audit)
        self.assertNotEqual(dim["status"], "not_run", dim)
        self.assertFalse(any("citações verificáveis" in str(n).lower()
                             for n in dim.get("notes", [])), dim)

    def test_annex_reflects_final_verification(self):
        import report_renderer as renderer
        state = {"run_id": "t", "question": "q", "profile": "medium",
                 "plan": PLAN_2, "evidence": {A: DOC_A},
                 "qualification": {},
                 "counters": {"documents": {
                     "used_in_synthesis": [A]}},
                 "question_coverage": {"status": "partial",
                                      "proportion": 0.5,
                                      "criteria": []},
                 "stop": {"reason": "rounds", "partial": True},
                 "rounds": [], "notes": []}
        final_ver = {"dimensions": {
            "execution": {"dimension": "execution", "status": "ok",
                          "evidence": {}, "notes": []},
            "question": {"dimension": "question", "status": "partial",
                         "evidence": {}, "notes": []},
            "review": {"dimension": "review", "status": "partial",
                       "evidence": {}, "notes": []},
            "support": {"dimension": "support", "status": "ok",
                        "evidence": {"citations": 1}, "notes": []}},
            "overall": "partial"}
        md1 = renderer.render_report(
            state, synthesis_text="Widget Alpha gerencia planos [1].",
            verifications=final_ver)
        self.assertIn("| support | ok |", md1, md1[md1.find("8. Anexo"):md1.find("8. Anexo")+800])
        self.assertNotIn("sem citações verificáveis", md1.lower())
        n1 = dict(getattr(renderer.render_report, "last_numbers", {}))
        md2 = renderer.render_report(
            state, synthesis_text="Widget Alpha gerencia planos [1].",
            verifications=final_ver)
        n2 = dict(getattr(renderer.render_report, "last_numbers", {}))
        self.assertEqual(n1, n2, (n1, n2))
        # sem duplicação de notas em re-render (two-pass idempotente)
        tighten = [n for n in (state.get("notes") or [])
                   if "citação ajustada" in str(n).lower()]
        self.assertEqual(len(tighten), len(set(tighten)), state.get("notes"))

    def test_numbers_stable_and_cited_coherent(self):
        import report_renderer as renderer
        state = {"run_id": "t", "question": "q", "profile": "medium",
                 "plan": PLAN_2, "evidence": {A: DOC_A, B: DOC_B},
                 "qualification": {},
                 "counters": {},
                 "question_coverage": {"status": "partial",
                                      "proportion": 0.5, "criteria": []},
                 "stop": {"reason": "rounds", "partial": True},
                 "rounds": [], "notes": []}
        ver = {"dimensions": {
            "execution": {"dimension": "execution", "status": "ok",
                          "evidence": {}, "notes": []},
            "question": {"dimension": "question", "status": "partial",
                         "evidence": {}, "notes": []},
            "review": {"dimension": "review", "status": "partial",
                       "evidence": {}, "notes": []},
            "support": {"dimension": "support", "status": "ok",
                        "evidence": {}, "notes": []}},
            "overall": "partial"}
        renderer.render_report(
            state, synthesis_text="Widget Alpha https://ex.example/a e "
                                  "Widget Beta https://ex.example/b.",
            verifications=ver)
        numbers = dict(getattr(renderer.render_report, "last_numbers", {}))
        cited = list(getattr(renderer.render_report, "last_cited_urls", []))
        self.assertEqual(len(numbers), 2, numbers)
        self.assertEqual(len(cited), 2, cited)


class IdentityAttributionTest(unittest.TestCase):
    def test_derived_eid_ignored(self):
        # eid derivado e-* sozinho não é menção; forma cheia do label é.
        ent_label, ent_id = "Widget Alpha", "e-alpha"
        self.assertFalse(
            verify._entity_mentioned(ent_label, ent_id,
                                     "veja e-alpha para detalhes"),
            "eid derivado não pode sustentar identidade sozinho")
        self.assertTrue(
            verify._entity_mentioned(ent_label, ent_id,
                                     "Widget Alpha gerencia planos"))
        self.assertFalse(
            verify._entity_mentioned("Widget Alpha", "e0",
                                     "veja e0 para detalhes"))

    def test_entity_mentioned_requires_full_form_boundary(self):
        self.assertFalse(
            verify._entity_mentioned("Widget Alpha", "x-alpha",
                                     "Widget Alphabeta gerencia coisas"),
            "prefixo de palavra maior não é forma cheia")
        self.assertTrue(
            verify._entity_mentioned("Widget Alpha", "x-alpha",
                                     "Widget Alpha gerencia planos"))

    def test_evaluation_refs_require_identity(self):
        import adaptive_coordinator as ac
        ent = {"id": "e-alpha", "label": "Widget Alpha"}
        bodies = [DOC_A, DOC_B]
        # DOC_A é sobre Alpha; DOC_B não menciona Alpha.
        self.assertTrue(
            ac._identity_matches(ent, DOC_A,
                                 single_ok=ac._singleton_rare(ent, bodies)))
        self.assertFalse(
            ac._identity_matches(ent, DOC_B,
                                 single_ok=ac._singleton_rare(ent, bodies)))
        # helper geral: refs de evaluation exigem identidade
        self.assertTrue(hasattr(ac, "_evaluation_refs_have_identity"),
                        "coordinator deve expor validação de identidade p/ refs")
        state = {"evidence": {A: DOC_A, B: DOC_B},
                 "qualification": {}}
        self.assertTrue(ac._evaluation_refs_have_identity(
            state, ent, [{"url": A}]))
        self.assertFalse(ac._evaluation_refs_have_identity(
            state, ent, [{"url": B}]))

    def test_rank_unfetched_identity_not_url_substring(self):
        import adaptive_coordinator as ac
        state = {"plan": PLAN_2, "question": "q"}
        gap = {"criterion_id": "c0", "entity_id": "e0",
               "label": "compatibilidade Widget Alpha"}
        cands = ["https://ex.example/alphabet-soup",
                 "https://ex.example/alpha-guide"]
        ranked = ac._rank_unfetched(state, cands, gap)
        self.assertEqual(ranked[0], "https://ex.example/alpha-guide",
                         ranked)

    def test_misattribution_mechanism_generic(self):
        # Doc sobre Beta citado para Alpha deve falhar; doc sobre Alpha passa.
        res_ok = verify.check_support(
            "Widget Alpha gerencia planos com revisao [1].",
            {1: A}, {A: DOC_A}, PLAN_2)
        self.assertEqual(res_ok["supported"], 1, res_ok)
        res_bad = verify.check_support(
            "Widget Alpha gerencia planos com revisao [1].",
            {1: B}, {B: DOC_B}, PLAN_2)
        self.assertEqual(res_bad["supported"], 0, res_bad)
        self.assertIn("entidade", res_bad["unsupported"][0]["reason"].lower(),
                      res_bad)

    def test_identity_prefix_only_is_not_match(self):
        # Fronteira: "Widget Alphabeta" não é a forma cheia "Widget Alpha"
        # (mesmo conceito de _entity_mentioned). Positivo + negativo pela
        # mesma entrada.
        import adaptive_coordinator as ac
        ent = {"id": "e-alpha", "label": "Widget Alpha"}
        bodies = [DOC_A, DOC_B]
        single_ok = ac._singleton_rare(ent, bodies)
        self.assertTrue(
            ac._identity_matches(ent, DOC_A, single_ok=single_ok))
        self.assertFalse(
            ac._identity_matches(
                ent, "Widget Alphabeta gerencia coisas",
                single_ok=single_ok),
            "prefixo de palavra maior não é forma cheia")
        # Doc só com prefixo não sustenta ref: cai em insufficiency
        # (o demote de covered/partial segue do helper False).
        state = {"evidence": {A: "Widget Alphabeta gerencia coisas"},
                 "qualification": {}}
        self.assertFalse(ac._evaluation_refs_have_identity(
            state, ent, [{"url": A}]))

    def test_evaluation_refs_url_slug_alone_is_not_identity(self):
        # Slug da URL não basta: o corpo decide (alinha a
        # _entity_corpus_docs, que usa só o corpo). Mesma entrada, só o
        # corpo muda.
        import adaptive_coordinator as ac
        ent = {"id": "e-alpha", "label": "Widget Alpha"}
        slug_url = "https://ex.example/widget-alpha/overview"
        state_neg = {"evidence": {slug_url: DOC_B}, "qualification": {}}
        self.assertFalse(ac._evaluation_refs_have_identity(
            state_neg, ent, [{"url": slug_url}]),
            "slug da URL sem menção no corpo não é identidade")
        state_pos = {"evidence": {slug_url: DOC_A}, "qualification": {}}
        self.assertTrue(ac._evaluation_refs_have_identity(
            state_pos, ent, [{"url": slug_url}]))


if __name__ == "__main__":
    unittest.main()
