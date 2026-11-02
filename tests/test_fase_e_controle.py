#!/usr/bin/env python3
"""Fase E — controle: persistência da diversidade (F1), regra de
complementaridade no writer (F2) e vocabulário do resumo de seleção (F3).

Genérico (AlphaWidget/BetaGadget/Widget Gamma, sem literais de produto).
Offline: model stub `lambda prompt: "[]"` + construtores reais
(adaptive_state.new_state, make_model_assessor/writer, _assess_round).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("fase E test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state
import coverage_ledger as cl


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def dim_doc(label, dim, i):
    body = (f"{label} guia geral. {dim} documentado nesta fonte ({i}). ")
    for j in range(48):
        body += (f"secao {j} da fonte {i}: {label} documenta {dim} "
                 f"no cenario {j} com exemplos, parametros e observacoes "
                 f"praticas de uso. ")
    return body


def cell_plan():
    return {
        "plan_id": "div", "version": 1, "question": "q",
        "entities": [
            {"id": "eA", "label": "AlphaWidget", "required": True},
        ],
        "criteria": [
            {"id": "c3", "label": "planejamento",
             "required": True, "applies_to": ["eA"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c4", "label": "implementacao",
             "required": True, "applies_to": ["eA"], "description": "Eixo implementacao: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["q"],
    }


class DiversityPersistedTest(unittest.TestCase):
    """F1: a nota de diversidade do lote sai do atributo volátil
    (assess.last_selection) para o registro persistido em
    state["assessments"] (alcançável por Grep no state.json)."""

    def _round(self, plan, evidence):
        st = adaptive_state.new_state("fase e f1")
        st["plan"] = plan
        st["evidence"] = dict(evidence)
        st["qualification"] = {u: qual(t) for u, t in evidence.items()}
        assess = ac.make_model_assessor(lambda prompt: "[]")
        ledger = cl.Ledger(plan)
        ac._assess_round(st, assess, ledger, None)
        return st

    def test_reorder_engaged_persists_diversity_marker(self):
        plan = cell_plan()
        evidence = {}
        for i in range(10):
            evidence[f"https://example.org/c3/{i}"] = dim_doc(
                "AlphaWidget", "planejamento", i)
        for i in range(2):
            evidence[f"https://example.org/c4/{i}"] = dim_doc(
                "AlphaWidget", "implementacao", i)
        st = self._round(plan, evidence)
        rec = st["assessments"][-1]
        self.assertIn("diversidade", str(rec.get("cuts") or ""),
                      f"lote por diversidade engajado deve persistir no "
                      f"registro: {rec}")

    def test_no_gain_persists_without_marker(self):
        plan = cell_plan()
        url = "https://example.org/solo/0"
        st = self._round(
            plan, {url: dim_doc("AlphaWidget", "planejamento", 0)})
        rec = st["assessments"][-1]
        self.assertEqual(rec["selection"], [url], rec)
        self.assertNotIn("diversidade", str(rec.get("cuts") or ""),
                         f"sem reordenação, sem marcador (seleção antiga "
                         f"mantida corretamente): {rec}")


class WriterComplementarityTest(unittest.TestCase):
    """F2: o writer recebe a regra de complementaridade — inferência
    prudente marcada+citada, nunca integração testada."""

    def _view(self, evidence):
        st = adaptive_state.new_state("fase e f2")
        st["plan"] = cell_plan()
        st["evidence"] = dict(evidence)
        st["question_coverage"] = {"criteria": []}
        return st

    def test_prompt_carries_complementarity_rule(self):
        seen = {}

        def fake_writer(prompt):
            seen["prompt"] = prompt
            return "relatório sintético"

        write = ac.make_model_writer(fake_writer)
        text, _ = write(self._view(
            {"https://example.org/a/0":
             dim_doc("AlphaWidget", "planejamento", 0)}))
        self.assertTrue(text.strip())
        low = seen["prompt"].lower()
        self.assertIn("complementar", low,
                      "writer deve instruir a inferência prudente de "
                      "combinação/sobreposição (complementaridade)")
        self.assertIn("inferência", low,
                      "complementaridade exige marca INFERÊNCIA")
        self.assertIn("integração testada", low,
                      "complementaridade nunca afirma integração testada")

    def test_marked_cited_inference_passes_to_synthesis(self):
        url_a = "https://example.org/a/0"
        url_b = "https://example.org/b/0"
        body = ("INFERÊNCIA: combinação prudente de AlphaWidget e "
                f"BetaGadget no fluxo; premissas em [{url_a}] [{url_b}]; "
                f"limites: sem prova de integração testada.")
        write = ac.make_model_writer(lambda prompt: body)
        text, _ = write(self._view(
            {url_a: dim_doc("AlphaWidget", "planejamento", 0),
             url_b: dim_doc("BetaGadget", "planejamento", 1)}))
        self.assertIn("INFERÊNCIA", text,
                      "inferência marcada+citada chega ao texto da síntese")
        self.assertIn(url_a, text)
        self.assertIn(url_b, text)


class SelectionSummaryWordingTest(unittest.TestCase):
    """F3: o resumo de seleção por candidato distingue 'apenas menções
    em lista/catálogo' (nomeado sem fonte própria) de 'sem documento
    que o nomeie' (ausência total) — mecanismo genérico, sem literais."""

    def _prompt_for(self, entities, evidence):
        seen = {}

        def fake_writer(prompt):
            seen["prompt"] = prompt
            return "relatório sintético"

        write = ac.make_model_writer(fake_writer)
        plan = {"plan_id": "f3", "version": 1, "question": "q",
                "entities": entities,
                "criteria": [{"id": "c1", "label": "axis", "required": True,
                              "per_candidate": True,
                              "applies_to": [e["id"] for e in entities], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": ["q"]}
        view = {"question": "q", "plan": plan,
                "evidence": dict(evidence), "user_context": {},
                "question_coverage": {"criteria": []}, "stop": {},
                "rounds": [], "evaluations": [],
                "unexplored_alternatives": [], "substitutions": [],
                "semantic_rank": []}
        write(view)
        return seen["prompt"]

    def test_listing_only_says_mentions_not_unnamed(self):
        catalog = ("Catalogo de ferramentas: Widget Alpha gerencia planos; "
                   "Widget Beta revisa codigo; ambos listados com links. " * 4)
        garden = ("Guia de jardinagem: rega e poda sem codigo alheio. " * 20)
        prompt = self._prompt_for(
            [{"id": "w1", "label": "Widget Alpha", "required": True,
              "discovered": True,
              "source_url": "https://example.org/widget-alpha"}],
            {"https://example.org/catalogo": catalog,
             "https://example.org/jardim": garden})
        low = prompt.lower()
        self.assertIn("apenas menções", low,
                      "candidato nomeado só em listagem não pode sair como "
                      "não-nomeado")
        self.assertNotIn("sem documento que o nomeie", low,
                         "forma forte reservada à ausência total de menção")

    def test_truly_unnamed_keeps_stronger_wording(self):
        garden = ("Guia de jardinagem: rega e poda sem codigo alheio. " * 20)
        prompt = self._prompt_for(
            [{"id": "w9", "label": "Widget Gamma", "required": True,
              "discovered": True}],
            {"https://example.org/jardim": garden})
        self.assertIn("sem documento que o nomeie", prompt.lower(),
                      "ausência total de menção mantém a forma forte")

    def test_unverifiable_status_never_claims_absence(self):
        ent = {"id": "w9", "label": "Widget Gamma", "required": True,
               "discovered": True}
        for bad in ({}, {"https://example.org/x": ""},):
            st, _ = ac._candidate_corpus_status(bad, ent)
            self.assertNotIn("sem documento que o nomeie", st.lower(),
                             f"estado não verificável não pode afirmar "
                             f"ausência: {bad!r}")
        st, _ = ac._candidate_corpus_status(
            {"https://example.org/jardim": "texto"}, "nao-um-dict")
        self.assertNotIn("sem documento que o nomeie", st.lower(),
                         "entidade inválida não pode afirmar ausência")


if __name__ == "__main__":
    unittest.main()
