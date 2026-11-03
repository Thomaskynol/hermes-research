#!/usr/bin/env python3
"""Fase G — evidência selecionada chega à célula (PT critério × EN fonte).

Dois mecanismos gerais, sem nomes de produto:

(a) ponte PT→EN cobre o vocabulário de dimensão do produto
    (planejamento/implementação/testes/revisão/compatibilidade/
    dependências/custos/manutenção/funcionalidades): um rótulo PT
    encontra a seção EN do documento;
(b) ``_shown`` registra o par (url, célula) apenas quando o EXCERTO
    enviado contém a menção da entidade e o termo da dimensão — não
    todas as células pedidas. Sem isso o reenvio focado (accept32) fica
    morto e uma célula cuja seção ficou fora da janela nunca volta.

Fluxo normal: ``make_model_assessor`` real + cliente dublê que só
registra prompts (sem rede). Entradas sintéticas genéricas.
"""
import json as _json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("fase g selection test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def material(prompt):
    marker = "Material selecionado: "
    return _json.JSONDecoder().raw_decode(
        prompt[prompt.index(marker) + len(marker):])[0]


def excerpt_of(prompt, url):
    return [it.get("excerpt", "") for it in material(prompt)
            if isinstance(it, dict) and it.get("url") == url]


class PtEnDimensionBridgeTest(unittest.TestCase):
    """Rótulo PT do critério encontra a dimensão EN no corpo."""

    def test_planning_and_review_labels_hit_english_body(self):
        ent = {"id": "e1", "label": "AlphaWidget", "required": True}
        text = ("AlphaWidget is a code review helper with planning "
                "workflow, implementation notes, automated testing and "
                "compatibility guidance.")
        cases = {
            "planejamento": "planning",
            "implementação": "implementation",
            "testes": "testing",
            "revisão de código": "review",
            "compatibilidade": "compatibility",
        }
        for label, expected in cases.items():
            toks = ac._norm_tokens(label, min_len=4)
            toks.extend(t for t in ac._expand_terms_en(toks)
                        if len(t) >= 4)
            self.assertTrue(
                ac._cell_locality_hit(text, ent, toks,
                                      generic=frozenset(), rare_ok=True),
                f"rótulo {label!r} não alcançou {expected!r}: {toks}")

    def test_generic_word_alone_still_does_not_prove_dimension(self):
        """Ponte não transforma menção genérica em suporte de dimensão."""
        ent = {"id": "e1", "label": "AlphaWidget", "required": True}
        text = "AlphaWidget release notes and installation instructions."
        toks = ac._norm_tokens("revisão de código", min_len=4)
        toks.extend(t for t in ac._expand_terms_en(toks) if len(t) >= 4)
        self.assertFalse(ac._cell_locality_hit(
            text, ent, toks, generic=frozenset(), rare_ok=True))


class ShownPairIsExcerptLevelTest(unittest.TestCase):
    """Célula só conta como exibida quando o excerto a mostra."""

    def _plan(self, with_implementation=True):
        crit = [
            {"id": "c1", "label": "planejamento", "required": True,
             "applies_to": ["e1"], "description": "d1"},
        ]
        if with_implementation:
            crit.insert(0, {"id": "c0", "label": "implementação",
                            "required": True, "applies_to": ["e1"],
                            "description": "d0"})
        return {
            "plan_id": "g", "version": 1, "question": "q",
            "entities": [{"id": "e1", "label": "AlphaWidget",
                          "required": True}],
            "criteria": crit,
            "initial_paths": ["q"],
        }

    def _doc(self, planning_at):
        filler = ("implementation notes and release details. " * 12)
        if planning_at == "near":
            return ("AlphaWidget planning workflow with gates and stages. "
                    + filler + "unrelated maintenance prose. " * 15)
        return ("AlphaWidget " + filler
                + "unrelated maintenance prose. " * 15
                + "planning workflow with gates and stages. ")

    def _assess(self, doc, with_implementation=True):
        prompts = []

        def fake_client(prompt):
            prompts.append(prompt)
            return "[]"

        assess = ac.make_model_assessor(
            fake_client, max_docs=1, excerpt_chars=300)
        plan = self._plan(with_implementation=with_implementation)
        assess(plan, {"https://example.org/a": doc},
               {"https://example.org/a": qual(doc)})
        return assess, plan, prompts

    def test_excerpt_marks_only_visible_cells(self):
        """O helper marca a célula vista no excerto, não todas as pedidas."""
        plan = self._plan()
        excerpt = ("AlphaWidget implementation notes and release details. "
                   "No such section in this window.")
        got = ac._excerpt_shown_cells(excerpt, plan)
        self.assertIn(("c0", "e1"), got,
                      f"implementação visível deve ser marcada: {got}")
        self.assertNotIn(("c1", "e1"), got,
                         f"planejamento fora do excerto não pode ser "
                         f"marcado como exibido: {got}")

    def test_excerpt_marks_both_when_both_visible(self):
        plan = self._plan()
        excerpt = ("AlphaWidget planning workflow and implementation "
                   "notes in the same window.")
        got = ac._excerpt_shown_cells(excerpt, plan)
        self.assertEqual(got, {("c0", "e1"), ("c1", "e1")}, got)

    def test_visible_section_is_not_resent(self):
        url = "https://example.org/a"
        doc = self._doc("near")
        assess, plan, prompts = self._assess(
            doc, with_implementation=False)
        first = excerpt_of(prompts[-1], url)
        self.assertTrue(first)
        self.assertIn("planning", first[0].lower())
        assess(plan, {url: doc}, {url: qual(doc)})
        # O doc já enviado pode voltar no lote (contexto), mas sem foco
        # de reenvio: o par (url,célula) já foi exibido no excerto.
        self.assertNotIn("resend-foco",
                         str((assess.last_selection or {}).get("cuts")),
                         "par (url,célula) já exibido no excerto não "
                         "deve consumir reenvio focado")


if __name__ == "__main__":
    unittest.main()
