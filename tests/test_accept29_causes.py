#!/usr/bin/env python3
"""accept29 causas-raiz — testes de contrato genéricos (sem nomes de produto).

Widget Alpha/Beta seguem a convenção do repo; nenhum nome de plugin/fonte
real. Cada teste falha antes do fix (TDD RED) e passa depois.

D1 descoberta aberta sem conjunto exigido: plataforma/contexto não consome
   candidate_target; descoberto entra candidate (required=False) até prova;
   avaliado promove a slot vazio; fraco sem doc próprio é substituível.
A2 aceite: prompt do writer declara descoberta≠seleção + regra de
   LACUNA com causa; conjunto sem 5º selecionado nunca sem ressalva.
R3 restrições: override de harness marca source=harness (user só com
   exigência explícita); stop rounds solitário registrado como
   não-justificado; dimensionamento proporcional registrado antes do run.
C4 critérios: (a) INFERÊNCIA com premissas em fontes distintas conta
   partial declarada com limites (nunca integração testada sem
   doc-interop); (b) contribuição documentada ao eixo conta partial sem
   exigir geração/execução autônoma.
E5 editorial no gerador: numeração única (síntese rebaixada), resíduos em
   anexo técnico, next específico por gap, conclusão aponta §5, tabela por
   rótulo (nunca id cru).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept29 test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import coverage_ledger as ledger_mod
import verification_report as verify

URL_A = "https://example.com/widget-alpha"
URL_B = "https://example.com/widget-beta"
DOC_A = ("Widget Alpha is a planning helper. It does planning with gates. "
         "Scope: planning only.")
DOC_B = ("Widget Beta is a plugin marketplace. It distributes plugins via a "
         "catalog. Scope: acquisition and distribution; it does not implement "
         "planning, implementation, testing or code review itself.")


def qual(url, text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def base_state(plan, evidence):
    return {
        "plan": plan, "question": plan.get("question", "q"),
        "discovery": {"open": True, "candidates": []},
        "evidence": dict(evidence),
        "qualification": {u: qual(u, t) for u, t in evidence.items()},
        "evaluations": [], "run_id": "accept29-tdd",
        "rounds": [{"round": 0}, {"round": 1}], "notes": [],
        "plan_versions": [], "attempts": {},
        "consumption": {"model_calls": 0, "rounds": 0},
        "unexplored_alternatives": [],
    }


class DiscoveryCapTest(unittest.TestCase):
    def test_platform_entity_not_counted_in_cap(self):
        """Plataforma/contexto (required sem discovered, fora do escopo
        per_candidate) não consome candidate_target: slot segue livre."""
        plan = ledger_mod.validate_plan({
            "plan_id": "plat", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget Platform",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True}],
            "candidate_target": 1,
        })
        st = base_state(plan, {URL_A: DOC_A})
        st["discovery"]["candidates"] = [URL_A]
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._apply_discovery(
            st, led,
            {"entity": {"id": "w1", "label": "Widget Alpha", "url": URL_A},
             "criteria": []},
            {"criterion_id": "c1"})
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w1")
        self.assertTrue(new.get("required", False),
                        f"plataforma consumiu o slot: {st['plan']['entities']}")

    def test_discovery_without_collected_source_stays_candidate(self):
        """Sem fonte própria coletada+mencionada, descoberto entra
        candidate (required=False) — verificação adiada não admite."""
        plan = ledger_mod.validate_plan({
            "plan_id": "cand", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget Platform",
                          "required": True}],
            "candidate_target": 2,
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True}],
        })
        st = base_state(plan, {})
        st["discovery"]["candidates"] = []
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._apply_discovery(
            st, led,
            {"entity": {"id": "w9", "label": "Widget Nine"}, "criteria": []},
            {"criterion_id": "c1"})
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w9")
        self.assertFalse(new.get("required", True),
                         f"admissão sem fonte: {st['plan']['entities']}")

    def test_evaluated_candidate_promoted_to_empty_slot(self):
        """Candidate com 1ª covered/partial e slot vazio promove a
        required (slot preenchível, nunca LACUNA congelada)."""
        plan = ledger_mod.validate_plan({
            "plan_id": "promo", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": False, "discovered": True,
                          "source_url": URL_A}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["w1"]}],
            "candidate_target": 2,
        })
        st = base_state(plan, {URL_A: DOC_A})
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("c1", "partial", "Widget Alpha documentado em fonte",
                     "selected_material", [{"url": URL_A}], "w1")
        st["evaluations"] = [dict(led._evals[("c1", "w1")])]
        self.assertTrue(ac._promote_evaluated(st, led),
                        f"slot vazio não preenchido: {st['plan']['entities']}")
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w1")
        self.assertTrue(new.get("required", False), new)


class WriterSelectionRuleTest(unittest.TestCase):
    def test_prompt_declares_discovery_vs_selection(self):
        """Prompt declara: menção em listagem = descoberta; seleção exige
        fonte própria + célula investigada; sem 5º selecionado, LACUNA com
        causa — nunca conjunto parcial sem ressalva."""
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        write = ac.make_model_writer(fake_client, max_chars=2400)
        plan = {"plan_id": "p", "version": 1, "question": "q",
                "entities": [
                    {"id": "w1", "label": "Widget Alpha", "required": True,
                     "discovered": True, "source_url": URL_A},
                    {"id": "w2", "label": "Widget Beta", "required": True,
                     "discovered": True}],
                "criteria": [{"id": "c1", "label": "axis", "required": True,
                              "per_candidate": True,
                              "applies_to": ["w1", "w2"]}],
                "candidate_target": 2}
        block = {"criteria": [], "gaps": []}
        view = {"question": "q", "plan": plan,
                "evidence": {URL_A: DOC_A}, "user_context": {},
                "question_coverage": block, "stop": {}, "rounds": [],
                "evaluations": [], "unexplored_alternatives": [],
                "substitutions": [], "semantic_rank": []}
        write(view)
        prompt = seen.get("prompt", "")
        low = prompt.lower()
        self.assertIn("descoberta", low, prompt[:2000])
        self.assertIn("fonte própria", low, prompt[:4000])
        self.assertIn("lacuna", low, prompt[:4000])


class RoundsSourceTest(unittest.TestCase):
    def test_override_is_harness_unless_user_demands(self):
        """Flag de harness (--max-rounds do operador) marca
        source=harness; user só com exigência explícita na pergunta."""
        r_harness = ac.resolve_adaptive("medium", {"max_rounds": 3})
        self.assertEqual(r_harness.get("max_rounds_source"), "harness",
                         r_harness)
        r_user = ac.resolve_adaptive("medium", {"max_rounds": 3},
                                     user_demands_rounds=True)
        self.assertEqual(r_user.get("max_rounds_source"), "user", r_user)
        r_default = ac.resolve_adaptive("medium", None)
        self.assertEqual(r_default.get("max_rounds_source"), "default",
                         r_default)

    def test_proportional_sizing_recorded(self):
        """Dimensionamento proporcional: tetos autorizados + células/gaps
        geram conta registrada (não comparabilidade)."""
        suggestion = ac.proportional_max_rounds(
            {"queries": 30, "extractions": 120, "model_calls": 16,
             "time_s": 1800},
            {"cells": 40, "gaps_open": 15})
        self.assertGreaterEqual(suggestion["max_rounds"], 4, suggestion)
        self.assertIn("conta", suggestion, suggestion)

    def test_lone_rounds_stop_flagged_unjustified(self):
        """Stop rounds com gaps abertos e demais tetos com folga = parcial
        não-justificado no detalhe (nunca justificável por
        comparabilidade)."""

        def search(target, channel="web"):
            return [{"url": URL_A, "title": URL_A, "snippet": "s"}]

        def fetch(url):
            return DOC_A

        def assess(plan, evidence, qualification):
            return []

        def writer(view):
            return "# t\ntexto sem cobertura", {"included_urls": [],
                                                "cuts": "none"}

        def auditor(report, evidence):
            return {"enabled": False, "verdict_state": "não revisado",
                    "accepted": False}

        import time as _t
        res = ac.run_adaptive(
            "Compare widgets", profile="light",
            plan={"plan_id": "b", "version": 1,
                  "question": "Compare widgets",
                  "entities": [{"id": "e0", "label": "Widget",
                                "required": True}],
                  "criteria": [{"id": "c1", "label": "axis", "required": True,
                                "applies_to": ["e0"]}],
                  "initial_paths": ["Compare widgets"]},
            search_fn=search, fetch_fn=fetch, assess_fn=assess,
            writer_fn=writer, auditor_fn=auditor, clock=_t.monotonic,
            overrides={"max_rounds": 1, "max_ops_per_round": 1})
        self.assertEqual(res["stop"]["reason"], "rounds", res["stop"])
        self.assertTrue(res["stop"].get("partial"), res["stop"])
        detail = str(res["stop"].get("detail", ""))
        self.assertIn("source=harness", detail, detail)
        for token in ("nico vinculante", "o-justificada", "comparabilidade"):
            self.assertIn(token, detail, detail)


class InferencePartialTest(unittest.TestCase):
    PLAN_2 = {"plan_id": "p", "version": 1,
              "entities": [{"id": "e0", "label": "Widget Alpha",
                            "required": True},
                           {"id": "e1", "label": "Widget Beta",
                            "required": True}],
              "criteria": [{"id": "c0", "label": "compatibilidade",
                            "required": True,
                            "applies_to": ["e0", "e1"]}]}

    def test_premises_in_distinct_docs_count_partial_declared(self):
        """Premissas em fontes distintas = partial declarada com limites
        explícitos; só alegação de integração testada exige doc-interop."""
        sent = ("Widget Alpha gerencia planos [1] \u2014 INFER\u00caNCIA: "
                "uso complementar com Widget Beta para fluxo combinado [2].")
        res = verify.check_support(
            sent, {1: URL_A, 2: URL_B},
            {URL_A: DOC_A, URL_B: DOC_B}, self.PLAN_2)
        decl = res.get("declared_inference") or []
        self.assertTrue(decl, res)
        scopes = " | ".join(str((d or {}).get("scope", "")) for d in decl)
        low = scopes.lower()
        self.assertIn("partial declarada", low, scopes)
        self.assertNotIn("integração testada (interoperabilidade citada)",
                         scopes, scopes)
        partial = res.get("partial_declared") or []
        self.assertTrue(partial, res)

    def test_interop_claim_without_interop_doc_rejected(self):
        """Alegação de integração testada sem doc que mencione ≥2
        entidades nunca é supported."""
        sent = ("Widget Alpha e Widget Beta operam de forma integrada "
                "e testada no fluxo combinado [1] [2].")
        res = verify.check_support(
            sent, {1: URL_A, 2: URL_B},
            {URL_A: DOC_A, URL_B: DOC_B}, self.PLAN_2)
        self.assertEqual(res["supported"], 0, res)


class TestsAxisPromptTest(unittest.TestCase):
    def test_contribution_counts_partial_without_autonomous_demo(self):
        """Eixo de melhoria: contribuição documentada conta partial sem
        exigir geração/execução autônoma; sem hipótese frágil."""
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "[]"

        assess = ac.make_model_assessor(fake_client)
        plan = {"plan_id": "p", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True, "discovered": True}],
                "criteria": [{"id": "c1", "label": "eixo", "required": True,
                              "per_candidate": True,
                              "applies_to": ["w1"]}]}
        try:
            assess(plan, {URL_A: DOC_A}, {URL_A: qual(URL_A, DOC_A)})
        except Exception:
            pass
        prompt = seen.get("prompt", "")
        low = prompt.lower()
        self.assertIn("contribuição documentada", low, prompt[:6000])
        self.assertIn("autônoma", low, prompt[:6000])


class EditorialRendererTest(unittest.TestCase):
    def test_synthesis_headings_demoted_to_unique_numbering(self):
        """Síntese com '## N' é rebaixada: numeração única do renderer."""
        from report_renderer import render_report
        state = {"question": "q",
                 "plan": {"plan_id": "p", "entities": [], "criteria": []},
                 "question_coverage": {"status": "partial", "proportion": 0.1,
                                       "numerator": 1, "denominator": 10,
                                       "criteria": [], "gaps": []},
                 "report": {"numbers": {}, "selection": {}},
                 "evidence": {}, "notes": []}
        out = render_report(state,
                            synthesis_text="## 3. Achados internos\ntexto",
                            verifications=None)
        self.assertEqual(out.count("## 1."), 1, out[:800])
        self.assertNotIn("\n## 3. Achados internos", out, out[:800])
        self.assertIn("\n### 3. Achados internos", out, out[:800])

    def test_debug_notes_go_to_annex_not_limits(self):
        """Resíduos internos (boost/reconcile/markers) vão ao anexo
        técnico, nunca às Notas da execução."""
        from report_renderer import render_report
        state = {"question": "q", "profile": "deep",
                 "plan": {"plan_id": "p", "entities": [], "criteria": []},
                 "question_coverage": {"status": "partial", "proportion": 0.1,
                                       "numerator": 1, "denominator": 10,
                                       "criteria": [], "gaps": []},
                 "report": {"numbers": {}, "selection": {}},
                 "evidence": {},
                 "notes": ["semantic boost: seleção [a] sob ordem [b]",
                           "nota voltada ao usuário"]}
        out = render_report(state, synthesis_text="texto",
                            verifications=None)
        limits = out.split("5. Limitações")[1].split("## 6.")[0] \
            if "5. Limitações" in out else out
        self.assertNotIn("semantic boost", limits, limits[:2000])
        self.assertIn("semantic boost", out, out[-3000:])

    def test_conclusion_points_to_limits_and_labels_mapped(self):
        """§6 referencia §5 (sem relistar) e tabela usa rótulo, não id."""
        from report_renderer import render_report
        plan = {"plan_id": "p",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True}],
                "criteria": [{"id": "c1", "label": "Eixo Um",
                              "required": True, "applies_to": ["w1"]}]}
        block = {"status": "partial", "proportion": 0.0, "numerator": 0,
                 "denominator": 1, "na": 0, "na_cells": [], "definition": "d",
                 "criteria": [{"id": "c1", "label": "Eixo Um",
                               "required": True, "applies_to": ["w1"],
                               "state": "insufficient",
                               "justification": "sem material",
                               "origin": "o", "entity_id": None,
                               "references": [],
                               "entity_states": {"w1": "insufficient"},
                               "na_cells": []}],
                 "gaps": [{"criterion_id": "c1", "label": "Eixo Um",
                           "state": "insufficient",
                           "justification": "sem material",
                           "next": "ler a fonte própria de Widget Alpha"}],
                 "references": [], "observed_counts": {}}
        state = {"question": "q", "plan": plan,
                 "question_coverage": block,
                 "report": {"numbers": {}, "selection": {}},
                 "evidence": {}, "notes": []}
        out = render_report(state, synthesis_text="texto",
                            verifications=None)
        self.assertIn("Widget Alpha", out, out[:4000])
        self.assertNotIn("| w1 |", out, out)
        tail = out.split("## 6.")[1] if "## 6." in out else out
        self.assertNotIn("ler a fonte própria de Widget Alpha", tail,
                         tail[:2000])

    def test_gap_next_names_entity_source(self):
        """Next genérico vira específico: cita entidade/fonte própria."""
        plan = {"plan_id": "g", "version": 1,
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True, "discovered": True,
                              "source_url": URL_A}],
                "criteria": [{"id": "c1", "label": "Eixo", "required": True,
                              "per_candidate": True,
                              "applies_to": ["w1"]}]}
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus({URL_A: DOC_A}, {URL_A: qual(URL_A, DOC_A)})
        led.evaluate("c1", "insufficient", "sem material sobre Widget Alpha",
                     "selected_material", None, "w1")
        block = led.compute()
        gaps = [g for g in block["gaps"]
                if g.get("criterion_id") == "c1"]
        self.assertTrue(gaps, block)
        self.assertTrue(any("Widget Alpha" in str(g.get("next", ""))
                            or "fonte própria" in str(g.get("next", ""))
                            for g in gaps),
                        [g.get("next") for g in gaps])

    def test_gap_next_keeps_long_source_url_whole(self):
        """URL de fonte própria >80 chars sai inteira (sem corte)."""
        long_url = ("https://example.com/t/widget-alpha-com-nome-bem-"
                    "longo-para-passar-de-oitenta-caracteres/1234?tl=pt_BR")
        self.assertGreater(len(long_url), 80)
        plan = {"plan_id": "g2", "version": 1,
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True, "discovered": True,
                              "source_url": long_url}],
                "criteria": [{"id": "c1", "label": "Eixo", "required": True,
                              "per_candidate": True,
                              "applies_to": ["w1"]}]}
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus({long_url: DOC_A}, {long_url: qual(long_url, DOC_A)})
        led.evaluate("c1", "insufficient", "sem material sobre Widget Alpha",
                     "selected_material", None, "w1")
        block = led.compute()
        gaps = [g for g in block["gaps"]
                if g.get("criterion_id") == "c1"]
        self.assertTrue(gaps, block)
        self.assertTrue(any(long_url in str(g.get("next", ""))
                            for g in gaps),
                        [g.get("next") for g in gaps])


if __name__ == "__main__":
    unittest.main()
