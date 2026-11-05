"""Follow-ups da revisão independente sobre reproduction-c3700bb-live (genérico).

1. `_combination_premises`: trio nomeado com 2 refs (ou par com terceiro
   fantasma via menção frouxa) deve sinalizar a entidade sem fonte, nunca
   listar "N premissas" como se cobrisse todos. Vale para N candidatos.
2. Célula coberta por refs fora dos excertos do writer, limitada pela
   síntese: matriz vai a parcial com o limite (refs só dos excertos).
3. Rótulo único para inferências: relação inferida nunca "documentada".
Offline, sem rede.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adaptive_coordinator as ac
import adaptive_state
import coverage_ledger as cl
import report_renderer as rr
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("follow-up tests forbid network, including 8082")


sys.addaudithook(offline)
A = "https://github.com/acme/river-review"
B = "https://github.com/team/river-plan"
C = "https://github.com/team/river-deploy"
D = "https://github.com/team/river-flow"
X = "https://example.com/river-blog"


def plan():
    return {"plan_id": "rivers", "version": 1,
            "open_discovery": {"needed": True}, "candidate_target": 4,
            "entities": [{"id": "host", "label": "RiverHost", "required": True},
                         {"id": "a", "label": "River Review (acme)",
                          "source_url": A, "discovered": True, "required": True},
                         {"id": "b", "label": "River Plan", "source_url": B,
                          "discovered": True, "required": True},
                         {"id": "c", "label": "River Deploy", "source_url": C,
                          "discovered": True, "required": True},
                         {"id": "d", "label": "River Flow", "source_url": D,
                          "discovered": True, "required": True}],
            "criteria": [{"id": "review", "label": "Revisão de código", "required": True,
                          "description": "Revisão documentada por candidato.",
                          "per_candidate": True,
                          "applies_to": ["a", "b", "c", "d"]}]}


def state():
    st = adaptive_state.new_state("Compare extensões para revisão no RiverHost.")
    st["plan"] = plan()
    st["evidence"] = {A: "# River Review\nPerforms automated code review with confidence scoring.",
                      B: "# River Plan\nDocumented plan review and interactive questions.",
                      C: "# River Deploy\nRiver Deploy deploys packages.",
                      D: "# River Flow\nRiver Flow models workflows.",
                      X: "River blog: Code Review side-by-side diffs and syntax-highlighted editors for questions."}
    st["qualification"] = {u: {"status": "usable", "excluded": False, "usable_text": t}
                           for u, t in st["evidence"].items()}
    return st


def numbers(st):
    for u, t in st["evidence"].items():
        ac._counters.record_obtained(st, u, t, st["qualification"][u])
    raw = rr._numbers(st)
    return {u: raw[rr._norm(u)] for u in (A, B, C, D, X)}


def text_with(st, bullet):
    return bullet


class CombinationPremises(unittest.TestCase):
    def test_pair_with_generic_review_words_lists_pair_only(self):
        st = state()
        n = numbers(st)
        bullet = (f"- INFERÊNCIA de sobreposição parcial entre River Plan e River Flow, porque o "
                  f"primeiro documenta plan review e o segundo documenta code review de fluxo, "
                  f"limite: sem prova conjunta [{n[B]}][{n[D]}].")
        lines = rr._combination_premises(st, bullet)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("River Plan × River Flow", lines[0], lines)
        self.assertNotIn("River Review", lines[0], lines)

    def test_trio_with_two_refs_flags_entity_without_source(self):
        st = state()
        n = numbers(st)
        bullet = (f"- INFERÊNCIA de sobreposição parcial entre River Review (acme), River Plan e "
                  f"River Deploy no eixo revisão [{n[A]}][{n[B]}].")
        lines = rr._combination_premises(st, bullet)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("sem fonte", lines[0], lines)
        self.assertIn("River Deploy", lines[0].split("sem fonte", 1)[1], lines)

    def test_trio_with_three_refs_lists_clean_trio(self):
        st = state()
        n = numbers(st)
        bullet = (f"- INFERÊNCIA de sobreposição parcial entre River Review (acme), River Plan e "
                  f"River Deploy no eixo revisão [{n[A]}][{n[B]}][{n[C]}].")
        lines = rr._combination_premises(st, bullet)
        self.assertEqual(len(lines), 1, lines)
        self.assertNotIn("sem fonte", lines[0], lines)
        self.assertIn("River Review (acme) × River Plan × River Deploy", lines[0], lines)

    def test_four_named_with_four_refs_have_no_missing_source(self):
        st = state()
        n = numbers(st)
        bullet = (f"- INFERÊNCIA de complementaridade entre River Review (acme), River Plan, "
                  f"River Deploy e River Flow em fluxo combinado [{n[A]}][{n[B]}][{n[C]}][{n[D]}].")
        lines = rr._combination_premises(st, bullet)
        self.assertEqual(len(lines), 1, lines)
        self.assertNotIn("sem fonte", lines[0], lines)


DOC_BOTH = ("River Plan offers planning. River Flow models workflows in one catalog.")
SENT_COMENTION = ("River Plan e River Flow constam no catálogo com planejamento e fluxos [1].")
SENT_MARKED = ("INFERÊNCIA de complementaridade entre River Plan e River Flow: "
               "planning and workflows in one catalog [1].")
PLAN_PAIR = {"plan_id": "p", "version": 1,
             "entities": [{"id": "e0", "label": "River Plan", "required": True},
                          {"id": "e1", "label": "River Flow", "required": True}],
             "criteria": [{"id": "c0", "label": "compatibilidade", "required": True,
                           "description": "Eixo compatibilidade."}]}


class InferenceScopeLabel(unittest.TestCase):
    def _scopes(self, res):
        return " | ".join(str((d or {}).get("scope", ""))
                           for d in (res.get("declared_inference") or []))

    def test_comention_without_test_verb_is_unified_inference_scope(self):
        res = vr.check_support(SENT_COMENTION, {1: X.replace("river-blog", "catalogo")},
                               {X.replace("river-blog", "catalogo"): DOC_BOTH}, PLAN_PAIR)
        scopes = self._scopes(res)
        self.assertNotIn("integração testada (interoperabilidade citada)", scopes, res)
        self.assertNotIn("documentado (sem teste executado)", scopes, res)
        self.assertIn("partial declarada", scopes, res)
        self.assertIn("nunca integração testada", scopes, res)
        self.assertEqual(res["supported"], 1, res)
        self.assertTrue(res.get("partial_declared"), res)

    def test_marked_inference_with_interop_doc_is_unified_inference_scope(self):
        res = vr.check_support(SENT_MARKED, {1: X.replace("river-blog", "catalogo")},
                               {X.replace("river-blog", "catalogo"): DOC_BOTH}, PLAN_PAIR)
        scopes = self._scopes(res)
        self.assertNotIn("integração testada (interoperabilidade citada)", scopes, res)
        self.assertNotIn("documentado (sem teste executado)", scopes, res)
        self.assertIn("partial declarada", scopes, res)
        self.assertIn("nunca integração testada", scopes, res)
        self.assertEqual(res["supported"], 1, res)
        self.assertTrue(res.get("partial_declared"), res)


class ExcerptRescope(unittest.TestCase):
    def _covered_state(self):
        st = state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("review", "covered",
                     "Declara Review the final plan visually e Code Review com side-by-side diffs.",
                     "corpus", [{"url": C}, {"url": X}], "c")
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [A, B, C, D]},
                        "numbers": {"1": A, "2": B, "3": X}}
        return st

    def test_covered_cell_limited_by_synthesis_is_rescoped_to_partial(self):
        st = self._covered_state()
        md = ("- INFERÊNCIA de sobreposição parcial em revisão entre River Review (acme), "
              "River Plan e River Deploy, porque o primeiro documenta revisão automatizada, "
              "o segundo documenta review de código e o terceiro tem apenas revisão visual de "
              "plano demonstrada nos excertos enviados e sem base equivalente de code review "
              "detalhada [2], por isso não afirmar mesma profundidade entre eles.")
        block = ac._rescope_cells_to_excerpts(st, md, {1: A, 2: C, 3: X})
        self.assertIsNotNone(block, st.get("notes"))
        cell = next(c for c in block["criteria"] if c["id"] == "review")
        ev = (cell.get("entity_evaluations") or {}).get("c") or {}
        self.assertEqual(ev.get("state"), "partial", ev)
        self.assertNotIn("side-by-side", ev.get("justification", ""), ev)
        self.assertIn("apenas revisão visual", ev.get("justification", ""), ev)
        self.assertEqual([r.get("url") for r in (ev.get("references") or [])], [C], ev)
        self.assertTrue(any("excerpt-scope" in str(n) for n in st.get("notes", [])), st.get("notes"))

    def test_cell_without_synthesis_limit_keeps_covered(self):
        st = self._covered_state()
        md = "- INFERÊNCIA de complementaridade entre River Review (acme) e River Plan [1][2]."
        self.assertIsNone(ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: X}))

    def test_limit_citing_outside_excerpt_does_not_rescope(self):
        st = self._covered_state()
        md = ("- River Plan tem apenas revisão visual de plano nos excertos e sem base de code "
              "review detalhada [3].")
        self.assertIsNone(ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: X}))

    def test_limit_about_other_dimension_does_not_rescope(self):
        st = self._covered_state()
        md = ("- River Deploy contém comando de testes do próprio projeto nos excertos, o que é "
              "evidência sobre o desenvolvimento, e documenta apenas contribuição limitada "
              "sem base equivalente de code review detalhada [2].")
        self.assertIsNone(ac._rescope_cells_to_excerpts(st, md, {1: A, 2: C, 3: X}))

    def test_partial_cell_is_not_rescoped(self):
        st = self._covered_state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        for prev in st.get("evaluations", []):
            try:
                led.evaluate(prev["criterion_id"], prev.get("state", "insufficient"),
                             prev.get("justification", ""), prev.get("origin", ""),
                             prev.get("references", []), prev.get("entity_id"))
            except (ValueError, KeyError):
                pass
        led.evaluate("review", "partial", "Plano parcial.", "corpus", [{"url": B}], "b")
        st["question_coverage"] = led.compute()
        md = ("- River Plan tem apenas revisão visual de plano demonstrada nos excertos enviados "
              "e sem base equivalente de code review detalhada [2].")
        self.assertIsNone(ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: X}))


if __name__ == "__main__":
    unittest.main()
