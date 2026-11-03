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

    def test_entity_name_is_identity_not_dimension_evidence(self):
        """O nome 'opencode-review' não prova a dimensão revisão."""
        ent = {"id": "e1", "label": "opencode-review", "required": True}
        toks = ac._norm_tokens("revisão de código", min_len=4)
        toks.extend(t for t in ac._expand_terms_en(toks) if len(t) >= 4)
        self.assertFalse(ac._cell_locality_hit(
            "opencode-review is a plugin.", ent, toks,
            generic=frozenset(), rare_ok=True),
            "o rótulo da entidade não pode marcar a célula sozinho")
        self.assertFalse(ac._cell_locality_hit(
            "OpenCode Review is a plugin.", ent, toks,
            generic=frozenset(), rare_ok=True),
            "a forma espaçada do rótulo também é identidade")
        self.assertTrue(ac._cell_locality_hit(
            "opencode-review adds a code review workflow.", ent, toks,
            generic=frozenset(), rare_ok=True),
            "uma ocorrência fora do rótulo é evidência visível")

    def test_shared_label_token_does_not_mark_every_dimension(self):
        """'Melhoria' compartilhado não prova planejamento nem revisão."""
        plan = {
            "plan_id": "g3", "version": 1, "question": "q",
            "entities": [{"id": "e1", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [
                {"id": "c2", "label": "Melhoria de planejamento",
                 "required": True, "applies_to": ["e1"]},
                {"id": "c3", "label": "Melhoria de revisão",
                 "required": True, "applies_to": ["e1"]},
            ],
            "initial_paths": ["q"],
        }
        got = ac._excerpt_shown_cells(
            "AlphaWidget melhoria de qualidade.", plan)
        self.assertEqual(got, set(), got)

    def test_accented_body_matches_accent_stripped_term(self):
        ent = {"id": "e1", "label": "AlphaWidget", "required": True}
        toks = ac._norm_tokens("revisão de código", min_len=4)
        toks.extend(t for t in ac._expand_terms_en(toks) if len(t) >= 4)
        self.assertTrue(ac._cell_locality_hit(
            "AlphaWidget revisão de código.", ent, toks,
            generic=frozenset(), rare_ok=True))

    def test_plural_inflection_matches(self):
        ent = {"id": "e1", "label": "AlphaWidget", "required": True}
        toks = ac._norm_tokens("revisão de código", min_len=4)
        toks.extend(t for t in ac._expand_terms_en(toks) if len(t) >= 4)
        self.assertTrue(ac._cell_locality_hit(
            "AlphaWidget publishes code reviews.", ent, toks,
            generic=frozenset(), rare_ok=True))
        tests = ac._norm_tokens("testes", min_len=4)
        tests.extend(t for t in ac._expand_terms_en(tests) if len(t) >= 4)
        self.assertTrue(ac._cell_locality_hit(
            "AlphaWidget has a test suite.", ent, tests,
            generic=frozenset(), rare_ok=True))

    def test_expanded_terms_match_whole_words_only(self):
        """'featured' não prova funcionalidades; 'maintainers' não prova manutenção."""
        ent = {"id": "e1", "label": "AlphaWidget", "required": True}
        func = ac._norm_tokens("funcionalidades", min_len=4)
        func.extend(t for t in ac._expand_terms_en(func) if len(t) >= 4)
        self.assertFalse(ac._cell_locality_hit(
            "AlphaWidget is featured in a list.", ent, func,
            generic=frozenset(), rare_ok=True))
        maint = ac._norm_tokens("manutenção", min_len=4)
        maint.extend(t for t in ac._expand_terms_en(maint) if len(t) >= 4)
        self.assertFalse(ac._cell_locality_hit(
            "AlphaWidget maintainers are listed.", ent, maint,
            generic=frozenset(), rare_ok=True))


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

    def _assess(self, doc, with_implementation=True, excerpt_chars=300):
        prompts = []

        def fake_client(prompt):
            prompts.append(prompt)
            return "[]"

        assess = ac.make_model_assessor(
            fake_client, max_docs=1, excerpt_chars=excerpt_chars)
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

    def test_section_outside_excerpt_triggers_focused_resend(self):
        """Seção fora do 1º excerto volta pelo reenvio focado (accept32)."""
        url = "https://example.org/a"
        filler = "filler " * 20
        doc = (
            "AlphaWidget is a widget. " + filler
            + "License MIT. " + filler
            + "Version 1.0. " + filler
            + "Install with npm. " + filler
            + "Price free. " + filler
            + "Maintainers active. " + filler
            + "AlphaWidget planning workflow with gates. " + "tail " * 20
        )
        assess, plan, prompts = self._assess(
            doc, with_implementation=False, excerpt_chars=100)
        first = excerpt_of(prompts[-1], url)
        self.assertTrue(first)
        self.assertNotIn("planning", first[0].lower(),
                         f"1º excerto não deveria conter a seção: {first[0]!r}")
        assess(plan, {url: doc}, {url: qual(doc)})
        cuts = str((assess.last_selection or {}).get("windows"))
        self.assertIn("resend-foco", cuts,
                      f"célula fora do excerto deve disparar reenvio: {cuts}")
        second = excerpt_of(prompts[-1], url)
        self.assertTrue(second)
        self.assertIn("planning", second[0].lower(),
                      f"2º excerto deve conter a seção reenviada: {second[0]!r}")

    def test_boolean_rare_map_does_not_silence_marking(self):
        """Bool no lugar do mapa não pode zerar silenciosamente o _shown."""
        plan = self._plan()
        excerpt = "AlphaWidget implementation notes and release details."
        got = ac._excerpt_shown_cells(excerpt, plan, True)
        self.assertIn(("c0", "e1"), got, got)


class EntityRotationTest(unittest.TestCase):
    """Com teto pequeno, a entidade menos servida vem primeiro."""

    def _plan(self):
        return {
            "plan_id": "g2", "version": 1, "question": "q",
            "entities": [
                {"id": "e1", "label": "AlphaWidget", "required": True},
                {"id": "e2", "label": "BetaWidget", "required": True},
            ],
            "criteria": [
                {"id": "c1", "label": "planejamento", "required": True,
                 "applies_to": ["e1"], "description": "d1"},
                {"id": "c2", "label": "implementação", "required": True,
                 "applies_to": ["e2"], "description": "d2"},
            ],
            "initial_paths": ["q"],
        }

    def test_second_call_rotates_to_unserved_entity(self):
        c_url = "https://example.org/c"
        a_url = "https://example.org/a"
        b_url = "https://example.org/b"
        first_docs = {
            c_url: "AlphaWidget planning workflow with gates.",
        }
        all_docs = {
            c_url: "AlphaWidget planning workflow with gates.",
            a_url: ("AlphaWidget planning workflow with gates. "
                    "AlphaWidget planning AlphaWidget planning."),
            b_url: "BetaWidget implementation notes and release details.",
        }
        prompts = []

        def fake_client(prompt):
            prompts.append(prompt)
            return "[]"

        assess = ac.make_model_assessor(
            fake_client, max_docs=1, excerpt_chars=300)
        plan = self._plan()
        assess(plan, first_docs,
               {u: qual(t) for u, t in first_docs.items()})
        first = [it["url"] for it in material(prompts[-1])]
        self.assertEqual(first, [c_url], first)
        assess(plan, all_docs,
               {u: qual(t) for u, t in all_docs.items()})
        second = [it["url"] for it in material(prompts[-1])]
        # e1 já teve célula exibida; a rotação deve servir e2 antes de
        # outro doc não enviado de e1 (antes da correção vinha /a).
        self.assertEqual(second, [b_url], second)


if __name__ == "__main__":
    unittest.main()
