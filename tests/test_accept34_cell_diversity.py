#!/usr/bin/env python3
"""accept34 M-A/M-B — lote por diversidade de células + isenção do writer.

M-A (sem aumentar tetos): no assembly do lote, priorizar células
required abertas sem cobertura/ref (sem repetir par url×célula já
exibido junto), dentro dos mesmos tetos (max_docs 24, excerpt 1200,
json 12000). Inclui resend servindo primeiro células required abertas
(não entidade fora do teto) quando houver contenção.

Casos-âncora accept33 (originais preservados; aqui cópia identificada
em tests/fixtures/accept33_c9e6.json + sintéticos genéricos sem
literais de produto):
(a) c9×e6: doc próprio contém a dimensão (seção de requisitos/
    dependências no rodapé) mas a janela perde;
(b) lote com N células abertas e teto 12k corta o prefixo e deixa
    células sem cobertura (padrão c3×e3/c4×e3);
(c) writer: versão exata ausente no doc citado exige isenção
    explícita (casos #1-#3) e nenhum literal indevido (caso #4).

Fluxo normal com construtores reais (adaptive_state.new_state —
stop/report são dicts, nunca None). Sem hardcode de nomes de
plugins/fontes: só tokens do plano/pergunta + kind-words genéricas.
"""
import json as _json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept34 diversity test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state

FIX = ROOT / "tests" / "fixtures" / "accept33_c9e6.json"
DOC_URL = "https://github.com/anomalyco/opencode-sdk-js"


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def excerpts_of(prompt, url):
    marker = "Material selecionado: "
    items, _ = _json.JSONDecoder().raw_decode(
        prompt[prompt.index(marker) + len(marker):])
    return [it.get("excerpt", "") for it in items
            if isinstance(it, dict) and it.get("url") == url]


class ExcerptKeepsDependencySectionTest(unittest.TestCase):
    """(a) c9×e6: seção de dependências do doc próprio retida na janela."""

    def test_frozen_dependency_tail_survives_windowing(self):
        fix = _json.loads(FIX.read_text(encoding="utf-8"))
        plan, evidence = fix["plan"], fix["evidence"]
        text = evidence[DOC_URL]
        self.assertIn("Requirements", text,
                      "cópia congelada deve conter a seção de dependências")
        seen = {}

        def fake_client(prompt):
            seen.setdefault("prompts", []).append(prompt)
            return "[]"

        st = adaptive_state.new_state("pergunta congelada accept33")
        self.assertIsInstance(st.get("stop"), dict)
        self.assertIsInstance(st.get("report"), dict)
        assess = ac.make_model_assessor(fake_client)
        assess(plan, {DOC_URL: text}, {DOC_URL: qual(text)})
        excerpt = excerpts_of(seen["prompts"][-1], DOC_URL)[0]
        self.assertLessEqual(len(excerpt), 1200, len(excerpt))
        self.assertIn(
            "TypeScript", excerpt,
            "janela deve reter a seção de dependências do doc próprio "
            "(c9×e6: 'Requirements/TypeScript >= 4.9' no rodapé, fora do head)")


def diversity_plan():
    return {
        "plan_id": "div", "version": 1, "question": "q",
        "entities": [
            {"id": "eA", "label": "AlphaWidget", "required": True},
            {"id": "eB", "label": "BetaGadget", "required": True},
        ],
        "criteria": [
            {"id": "c3", "label": "planejamento",
             "required": True, "applies_to": ["eA", "eB"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c4", "label": "implementacao",
             "required": True, "applies_to": ["eA", "eB"], "description": "Eixo implementacao: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["q"],
    }


def cell_doc(label, i):
    dims = ("planejamento", "implementacao")
    body = (f"{label} guia geral. planejamento e implementacao "
            f"documentados nesta fonte ({i}). ")
    for j in range(48):
        body += (f"secao {j} da fonte {i}: {label} documenta "
                 f"{dims[j % 2]} no cenario {j} com exemplos, parametros "
                 f"e observacoes praticas de uso. ")
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


def dim_doc(label, dim, i, tag):
    body = (f"{label} guia geral. {dim} documentado nesta fonte ({i}). ")
    for j in range(48):
        body += (f"secao {j} da fonte {i}: {label} documenta {dim} "
                 f"no cenario {j} com exemplos, parametros e observacoes "
                 f"praticas de uso. ")
    return body


class BatchDiversityUnderBudgetTest(unittest.TestCase):
    """(b) teto 12k: lote prioriza diversidade de células, não o prefixo
    (padrão accept33 c3×e3/c4×e3: docs da mesma entidade cobrindo uma só
    célula lotam o orçamento e as demais células abertas ficam sem
    cobertura)."""

    def test_tight_budget_covers_distinct_open_cells(self):
        plan = cell_plan()
        evidence = {}
        for i in range(10):
            evidence[f"https://example.org/c3/{i}"] = dim_doc(
                "AlphaWidget", "planejamento", i, "c3")
        for i in range(2):
            evidence[f"https://example.org/c4/{i}"] = dim_doc(
                "AlphaWidget", "implementacao", i, "c4")
        assess = ac.make_model_assessor(lambda prompt: "[]")
        assess(plan, evidence, {})
        urls = list((assess.last_selection or {}).get("urls") or [])
        self.assertLessEqual(len(urls), 24, urls)
        self.assertTrue(
            any("/c4/" in u for u in urls),
            f"teto 12k deve preservar célula aberta distinta, não só o "
            f"prefixo (padrão c3×e3/c4×e3): {urls[:10]}")
        self.assertTrue(any("/c3/" in u for u in urls))


class ResendServesRequiredCellsFirstTest(unittest.TestCase):
    """Resend com contenção: célula required aberta antes de fora do teto."""

    def _base_plan(self, applies):
        return {
            "plan_id": "r", "version": 1, "question": "q",
            "entities": [
                {"id": "eR", "label": "ReqWidget", "required": True},
                {"id": "eO", "label": "OptWidget", "required": False},
            ],
            "criteria": [
                {"id": "c3", "label": "planejamento",
                 "required": True, "applies_to": applies, "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            ],
            "initial_paths": ["q"],
        }

    def _plan(self):
        return self._base_plan(["eR", "eO"])

    def _evals_covering_required(self, opt_url):
        out = []
        for cid in ("cA", "cB"):
            out.append({"criterion_id": cid, "entity_id": "eR",
                        "state": "covered", "justification": "j",
                        "origin": "stub",
                        "references": [{"url": opt_url}]})
        return out

    def _docs(self):
        return {
            "https://example.org/req/0":
                "ReqWidget guia. planejamento documentado nesta fonte. "
                "detalhes sobre a ferramenta. " * 6,
            "https://example.org/opt/0":
                "OptWidget guia. planejamento documentado nesta fonte. "
                "detalhes sobre a ferramenta. " * 6,
        }

    def test_resend_skips_out_of_scope_entity_cell(self):
        plan = self._plan()
        evidence = self._docs()
        resend = ac._resend_for_open_cells(
            plan, evidence, {}, {"https://example.org/opt/0"},
            {}, {}, {})
        cells = {(c, e) for _, c, e in resend}
        self.assertNotIn(
            ("c3", "eO"), cells,
            f"reenvio não serve entidade fora do teto (required=False): "
            f"{resend}")

    def test_assess_order_prefers_required_open_cell(self):
        # Versionamento + contenção: opt exibido antes da célula (cB,eO)
        # existir; required já coberto (reserva suprimida); com max_docs=1
        # o reenvio decide — e deve servir required aberta, nunca a
        # entidade fora do teto.
        opt_url = "https://example.org/opt/0"
        req_url = "https://example.org/req/0"

        def plan_v1():
            return {
                "plan_id": "r", "version": 1, "question": "q",
                "entities": [
                    {"id": "eR", "label": "ReqWidget", "required": True},
                ],
                "criteria": [
                    {"id": "cA", "label": "planejamento",
                     "required": True, "applies_to": ["eR"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                    {"id": "cB", "label": "planejamento",
                     "required": True, "applies_to": ["eR"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                ],
                "initial_paths": ["q"],
            }

        def plan_v2():
            return {
                "plan_id": "r", "version": 2, "question": "q",
                "entities": [
                    {"id": "eR", "label": "ReqWidget", "required": True},
                    {"id": "eO", "label": "OptWidget", "required": False},
                ],
                "criteria": [
                    {"id": "cA", "label": "planejamento",
                     "required": True, "applies_to": ["eR"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                    {"id": "cB", "label": "planejamento",
                     "required": True, "applies_to": ["eR", "eO"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                ],
                "initial_paths": ["q"],
            }

        docs = self._docs()
        # Mesma história no assessor sob teste: opt em _sent sem o par
        # (url,célula), required coberto via avaliações prévias.
        assess2 = ac.make_model_assessor(lambda prompt: "[]", max_docs=1)
        assess2(plan_v1(), {opt_url: docs[opt_url]}, {})
        assess2.set_previous_evaluations(
            self._evals_covering_required(opt_url))
        assess2(plan_v2(), {req_url: docs[req_url], opt_url: docs[opt_url]},
                {})
        urls = list((assess2.last_selection or {}).get("urls") or [])
        self.assertTrue(urls)
        self.assertIn(
            "req", urls[0],
            f"com contenção, célula required aberta primeiro: {urls}")


class WriterVersionExemptionTemplateTest(unittest.TestCase):
    """(c) template do writer: isenção explícita p/ versão/quote (gates
    intactos — rótulo LACUNA sozinho não isenta)."""

    def _view(self):
        st = adaptive_state.new_state("pergunta com versão instalada")
        st["plan"] = diversity_plan()
        st["evidence"] = {"https://example.org/alpha/0":
                          cell_doc("AlphaWidget", 0)}
        st["question_coverage"] = {"criteria": []}
        return st

    def test_prompt_carries_version_gap_exemption_rule(self):
        seen = {}

        def fake_writer(prompt):
            seen["prompt"] = prompt
            return "relatório sintético"

        write = ac.make_model_writer(fake_writer)
        text, _ = write(self._view())
        self.assertTrue(text.strip())
        prompt = seen["prompt"]
        self.assertIn("desconhecida", prompt.lower(),
                      "writer deve instruir isenção explícita quando a "
                      "versão exata não consta do doc citado (casos #1-#3)")
        self.assertIn("sem menção", prompt.lower())
        self.assertIn("fora do corpus", prompt.lower(),
                      "nota metodológica referencia URLs do pedido fora do "
                      "corpus, sem vesti-las de conteúdo citado (caso #4)")

    def test_prompt_forbids_undue_literals(self):
        seen = {}

        def fake_writer(prompt):
            seen["prompt"] = prompt
            return "relatório sintético"

        write = ac.make_model_writer(fake_writer)
        write(self._view())
        self.assertIn("literal", seen["prompt"].lower(),
                      "writer não veste literais que o doc citado não "
                      "contém como conteúdo citado")


if __name__ == "__main__":
    unittest.main()
