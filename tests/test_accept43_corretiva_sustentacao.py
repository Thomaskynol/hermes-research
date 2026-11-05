"""Corretiva accept43 — sustentação/avaliação/claim3 (T1–T4, TDD RED primeiro).

Genérico, sem literais de produto: fixtures "River" sintéticas, offline
(rede proibida inclusive 8082). Cada teste demonstra um defeito no código
atual pelo motivo esperado; a correção deve fazê-los passar sem enfraquecer
os controles que continuam rejeitando (cobertos pelos testes *_negativos).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adaptive_coordinator as ac
import adaptive_state
import coverage_ledger as cl
import report_renderer as rr
import semantic_review as sr
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("corretiva tests forbid network, including 8082")


sys.addaudithook(offline)
A = "https://github.com/acme/river-review"
B = "https://github.com/team/river-plan"
C = "https://github.com/team/river-deploy"
X = "https://example.com/river-blog"


def plan3():
    return {"plan_id": "rivers", "version": 1,
            "entities": [{"id": "host", "label": "RiverHost", "required": True},
                         {"id": "a", "label": "River Review (acme)",
                          "source_url": A, "discovered": True, "required": True},
                         {"id": "b", "label": "River Plan", "source_url": B,
                          "discovered": True, "required": True},
                         {"id": "c", "label": "River Deploy", "source_url": C,
                          "discovered": True, "required": True}],
            "criteria": [{"id": "review", "label": "Revisão de código", "required": True,
                          "description": "Revisão documentada por candidato.",
                          "per_candidate": True,
                          "applies_to": ["a", "b", "c"]}]}


def state3():
    st = adaptive_state.new_state("Compare extensões para revisão no RiverHost.")
    st["plan"] = plan3()
    st["evidence"] = {A: "# River Review\nPerforms automated code review with confidence scoring.",
                      B: "# River Plan\nDocumented plan review and interactive questions.",
                      C: "# River Deploy\nReview the final plan visually in reviewable sections.",
                      X: "River blog: Code Review side-by-side diffs and syntax-highlighted editors."}
    st["qualification"] = {u: {"status": "usable", "excluded": False, "usable_text": t}
                           for u, t in st["evidence"].items()}
    return st


def covered_state3():
    st = state3()
    led = cl.Ledger(st["plan"], run_id=st["run_id"])
    led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
    led.evaluate("review", "covered",
                 "Declara Review the final plan visually e Code Review com side-by-side diffs.",
                 "corpus", [{"url": C}, {"url": X}], "c")
    st["question_coverage"] = led.compute()
    st["report"] = {"selection": {"included_urls": [A, B, C]},
                    "numbers": {"1": A, "2": B, "3": C}}
    return st


class T1RescopeRewritesToSingleEntityScope(unittest.TestCase):
    """§1: rescope copia a sentença-limite multi-entidade para a célula e
    filtra refs p/ só covering — a célula uni-entidade publica frase de 3
    entidades com 1 ref. Correção: reescrever ao escopo uni-entidade."""

    def test_rescoped_justification_names_only_target_entity(self):
        st = covered_state3()
        md = ("- INFERÊNCIA de sobreposição parcial em revisão entre River Review (acme), "
              "River Plan e River Deploy, porque o primeiro documenta revisão automatizada, "
              "o segundo documenta review de código e o terceiro tem apenas revisão visual de "
              "plano demonstrada nos excertos enviados e sem base equivalente de code review "
              "detalhada [3], por isso não afirmar mesma profundidade entre eles.")
        block = ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: C})
        self.assertIsNotNone(block, st.get("notes"))
        cell = next(c for c in block["criteria"] if c["id"] == "review")
        ev = (cell.get("entity_evaluations") or {}).get("c") or {}
        self.assertEqual(ev.get("state"), "partial", ev)
        just = ev.get("justification", "")
        self.assertIn("apenas revisão visual", just, ev)
        self.assertNotIn("River Review (acme)", just, ev)
        self.assertNotIn("River Plan", just, ev)
        self.assertEqual([r.get("url") for r in (ev.get("references") or [])], [C], ev)

    def test_outside_excerpt_ref_not_published_as_bare_excerpt_citation(self):
        st = covered_state3()
        crit = next(c for c in st["question_coverage"]["criteria"] if c["id"] == "review")
        ev = (crit.get("entity_evaluations") or {}).get("c") or {}
        nums = {rr._norm(u): n for n, u in
                [(1, A), (2, B), (3, C), (4, X)]}
        refs = rr._refs(ev, nums, {"not_investigated": "não investigado"}, set(), [A, B, C])
        # X está fora de included_urls: nunca publicado como excerto nu.
        self.assertIn("[4]", refs, ev)
        self.assertNotIn(", [4]", ", ".join(
            r for r in refs.split(", ") if "fora dos excertos" not in r), refs)


class T2aNumericPremiseWithFunctionalLacuna(unittest.TestCase):
    """§2: comparação numérica válida (premissa + mínimo declarado) com
    LACUNA funcional explícita vira unsupported/interop. Correção: canal
    que aceita numérico+premissa+LACUNA como partial declarada."""

    PLAN = {"plan_id": "p", "version": 1,
            "entities": [{"id": "e0", "label": "RiverHost", "required": False},
                         {"id": "e1", "label": "River Plan", "source_url": B, "required": True}],
            "criteria": [{"id": "c0", "label": "compatibilidade", "required": True,
                          "description": "Eixo compatibilidade."}]}
    DOC = ("# River Plan\nRequires RiverHost V2 2.1.2+. "
           "Documented plan review and interactive questions.")
    SENT = ("O River Plan declara Requires RiverHost V2 2.1.2+; contra a versão "
            "instalada 2.1.4 do contexto controlado há INFERÊNCIA numérica de mínimo "
            "atendido, sem fonte de compatibilidade funcional com 2.1.4 "
            "(LACUNA de integração [1]).")

    def test_numeric_premise_with_lacuna_is_partial_not_unsupported(self):
        res = vr.check_support(self.SENT, {1: B}, {B: self.DOC}, self.PLAN)
        bad = [u for u in (res.get("unsupported") or [])
               if "interoperabilidade" in str(u.get("reason", ""))]
        self.assertEqual(bad, [], res)
        self.assertEqual(res.get("unsupported"), [], res)
        # Canal LACUNA: ausência sustentada pela consulta, com escopo de
        # janela — nunca unsupported/interop.
        scopes = " | ".join(str(d.get("scope", ""))
                            for d in (res.get("declared") or []))
        self.assertIn("janela", scopes, res)

    def test_invented_version_without_premise_still_rejected(self):
        sent = ("O River Plan declara compatibilidade funcional com 9.9.9 "
                "e integração testada. [1]")
        res = vr.check_support(sent, {1: B}, {B: self.DOC}, self.PLAN)
        self.assertTrue(res.get("unsupported"), res)


class T2bOwnReadmeFactIsSupported(unittest.TestCase):
    """§2: fato próprio positivo no excerto (README da entidade) vira
    'entidade não mencionada' por atribuição frouxa + entidade espúria.
    Correção: fato próprio no excerto = supported; ausências = LACUNA."""

    PLAN = {"plan_id": "p", "version": 1,
            "entities": [{"id": "e0", "label": "RiverHost", "required": False},
                         {"id": "e1", "label": "River Review (acme)",
                          "source_url": A, "required": True},
                         {"id": "e2", "label": "River Code Flow",
                          "source_url": "https://github.com/team/river-code-flow",
                          "required": True}],
            "criteria": [{"id": "c0", "label": "revisão", "required": True,
                          "description": "Eixo revisão."}]}
    DOC_A = ("# River Review\nRiver Review performs automated code review "
             "on pull requests with confidence scoring.")
    DOC_OTHER = ("# River Code Flow\nRiver Code Flow models code review flows.")
    # Prosa sem o decorador "(acme)": rótulo estrito decorado nunca casa.
    SENT = ("O River Review declara performs automated code review "
            "on pull requests com confidence scoring [1].")

    def test_own_readme_positive_fact_is_supported(self):
        res = vr.check_support(self.SENT, {1: A},
                               {A: self.DOC_A,
                                "https://github.com/team/river-code-flow": self.DOC_OTHER},
                               self.PLAN)
        self.assertEqual(res.get("unsupported"), [], res)
        self.assertEqual(res.get("supported"), 1, res)

    def test_foreign_doc_attribution_still_rejected(self):
        res = vr.check_support(self.SENT, {1: "https://github.com/team/river-code-flow"},
                               {A: self.DOC_A,
                                "https://github.com/team/river-code-flow": self.DOC_OTHER},
                               self.PLAN)
        self.assertTrue(res.get("unsupported"), res)


class T3OutsideWindowChain(unittest.TestCase):
    """§3: [blog do autor válido e substantivo] obtido e avaliado, mas fora
    de included_urls; publicado como excerto nu perde o alcance.
    Correção: fora-da-janela nunca publicado como excerto; sinal difuso
    registrado como parcial alternativo, não apagado."""

    def test_blog_ref_outside_selection_marked_not_bare(self):
        st = covered_state3()
        crit = next(c for c in st["question_coverage"]["criteria"] if c["id"] == "review")
        ev = (crit.get("entity_evaluations") or {}).get("c") or {}
        nums = {rr._norm(u): n for n, u in
                [(1, A), (2, B), (3, C), (4, X)]}
        refs = rr._refs(ev, nums, {"not_investigated": "não investigado"}, set(), [A, B, C])
        self.assertIn("[4]", refs, ev)
        bare = [r for r in refs.split(", ") if r.strip() == "[4]"]
        self.assertEqual(bare, [], refs)


class T4ClaimPackagingWithoutFusion(unittest.TestCase):
    """§4: LACUNA isolada verdadeira sobre um pacote vira unsupported porque
    o empacotamento funde evidência de pacote distinto. Correção:
    empacotamento por entidade, sem fusão."""

    MARKET = "https://github.com/team/river-market"
    CONFIG = "https://github.com/team/river-config-pack"

    def test_lacuna_about_one_package_does_not_anchor_foreign_doc(self):
        sr.reset_state_for_tests() if hasattr(sr, "reset_state_for_tests") else None
        evidence = {
            self.MARKET: ("# river-market\nriver-market installs from local directories "
                          "or remote URLs with update and list commands."),
            self.CONFIG: ("# river-config-pack\nriver-config-pack extends river-market "
                          "with planning templates, structured scaffolds "
                          "and remote sync commands."),
        }
        sentence = ("LACUNA nos excertos avaliados: river-market documenta apenas "
                    "instalação; sem trecho que estabeleça planejamento próprio.")
        anchors, _text = sr._select_evidence(["river-market"], sentence, evidence, [])
        self.assertIn(self.MARKET, anchors, anchors)
        self.assertNotIn(self.CONFIG, anchors, anchors)


if __name__ == "__main__":
    unittest.main()
