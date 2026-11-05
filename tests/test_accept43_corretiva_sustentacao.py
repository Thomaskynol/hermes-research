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
    ev0 = led.evaluate("review", "covered",
                       "Declara Review the final plan visually e Code Review com side-by-side diffs.",
                       "corpus", [{"url": C}, {"url": X}], "c")
    st["evaluations"] = [dict(ev0)]
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

    def test_absence_without_own_doc_yields_no_anchors(self):
        """Remediação 🔴2: ausência sem doc próprio utilizável dava âncoras
        estrangeiras; o correto é sem-evidência (gap), nunca pacote alheio."""
        evidence = {
            self.CONFIG: ("# river-config-pack\nriver-config-pack extends river-market "
                          "with planning templates, structured scaffolds "
                          "and remote sync commands."),
        }
        sentence = ("LACUNA nos excertos avaliados: river-market documenta apenas "
                    "instalação.")
        anchors, _text = sr._select_evidence(["river-market"], sentence, evidence, [])
        self.assertEqual(anchors, [], anchors)

    def test_positive_two_package_claim_keeps_both_anchors(self):
        """Guarda: afirmação positiva legítima sobre 2 pacotes ancora ambos
        (anti-fusão só vale p/ ausência)."""
        evidence = {
            self.MARKET: ("# river-market\nriver-market installs from local directories."),
            self.CONFIG: ("# river-config-pack\nriver-config-pack extends river-market "
                          "with planning templates."),
        }
        sentence = (f"river-market instala pacotes e river-config-pack estende a lista "
                    f"({self.MARKET}) ({self.CONFIG}).")
        anchors, _text = sr._select_evidence(["river-market"], sentence, evidence, [])
        self.assertEqual(set(anchors), {self.MARKET, self.CONFIG}, anchors)


class TRemedicaoReviewer(unittest.TestCase):
    """Passe de remediação do gate reviewer (1 correção por causa)."""

    def test_multi_entity_without_safe_rewrite_falls_to_partial(self):
        """🔴1: frase multi-entidade sem reescrita segura não pode manter
        covered superestimado — cai p/ partial com alcance, refs do escopo."""
        st = covered_state3()
        md = ("- INFERÊNCIA de sobreposição limitada em revisão e código entre "
              "River Review (acme), River Plan e River Deploy [1][3].")
        block = ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: C})
        self.assertIsNotNone(block, st.get("notes"))
        cell = next(c for c in block["criteria"] if c["id"] == "review")
        ev = (cell.get("entity_evaluations") or {}).get("c") or {}
        self.assertEqual(ev.get("state"), "partial", ev)
        self.assertIn("River Deploy", ev.get("justification", ""), ev)
        urls = [r.get("url") for r in (ev.get("references") or [])]
        self.assertNotIn(X, urls, ev)
        for u in urls:
            self.assertIn(u, [A, B, C], ev)

    def test_ordinal_swapped_clauses_stay_with_their_entity(self):
        """Ordinal trocado: cláusula de outra entidade nunca veste o alvo."""
        st = covered_state3()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("review", "covered", "Plan com review documentado.",
                     "corpus", [{"url": B}, {"url": X}], "b")
        st["question_coverage"] = led.compute()
        md = ("- INFERÊNCIA de sobreposição em revisão e código entre River Review (acme) "
              "e River Plan, porque o primeiro documenta revisão automatizada de pull "
              "requests [1] e o segundo tem apenas revisão visual de plano limitada "
              "aos excertos [2].")
        block = ac._rescope_cells_to_excerpts(st, md, {1: A, 2: B, 3: X})
        self.assertIsNotNone(block, st.get("notes"))
        cell = next(c for c in block["criteria"] if c["id"] == "review")
        ev = (cell.get("entity_evaluations") or {}).get("b") or {}
        self.assertEqual(ev.get("state"), "partial", ev)
        just = ev.get("justification", "")
        self.assertIn("apenas revisão visual", just, ev)
        self.assertNotIn("revisão automatizada", just, ev)

    def test_ordinal_resolves_by_textual_order_not_plan_order(self):
        """Guarda: enumeração textual manda, nunca a ordem do plano."""
        st = covered_state3()
        ents = st["plan"]["entities"]
        st["plan"]["entities"] = [e for e in ents if e.get("id") not in ("a", "b", "c")] \
            + [e for e in ents if e.get("id") == "c"] \
            + [e for e in ents if e.get("id") == "a"] \
            + [e for e in ents if e.get("id") == "b"]
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
        self.assertNotIn("River Review (acme)", just, ev)
        self.assertNotIn("River Plan", just, ev)

    def test_bare_window_mold_without_lacuna_context_is_not_absence(self):
        """🟡 moldes isolados (sem fonte/trecho) sem lacuna/excertos nem marca
        líder não desviam prosa p/ declared."""
        self.assertFalse(vr.is_lacuna_declaration(
            "River Plan publica pacotes de qualquer fonte, sem fonte única oficial."), )
        self.assertFalse(sr._is_absence_claim(
            "River Plan publica pacotes de qualquer fonte, sem fonte única oficial."), )
        self.assertTrue(vr.is_lacuna_declaration(
            "River Plan: LACUNA de planejamento sem fonte que a mencione [1]."), )
        self.assertTrue(sr._is_absence_claim(
            "LACUNA nos excertos: River Plan sem trecho sobre o eixo [1]."), )

    def test_lacuna_premise_rejects_foreign_doc_sharing_two_tokens(self):
        """🟡 premissa LACUNA exige regra estrita: doc de outro dono no plano
        que só compartilha 2 tokens não é premissa da entidade."""
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e8", "label": "River Guide",
                              "source_url": "https://github.com/team/river-guide",
                              "required": True},
                             {"id": "e9", "label": "River Notes", "required": True}],
                "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                              "description": "Eixo."}]}
        foreign = "https://github.com/team/river-guide"
        corpus = {foreign: ("River workflows and release notes describe planning.")}
        sent = ("LACUNA nos excertos avaliados: River Notes sem trecho que "
                "demonstre planejamento próprio [1].")
        res = vr.check_support(sent, {1: foreign}, corpus, plan)
        self.assertTrue(res.get("unsupported"), res)
        self.assertIn("entidade não mencionada",
                      str((res.get("unsupported") or [{}])[0].get("reason")), res)

    def test_cognate_overlap_does_not_borrow_foreign_doc(self):
        """🟡 negativo com plano não-relacionado: cognatos + 2 tokens soltos
        não fazem doc de outro dono sustentar afirmação sobre esta entidade."""
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e8", "label": "River Plan",
                              "source_url": "https://github.com/team/river-plan",
                              "required": True},
                             {"id": "e9", "label": "River Notes", "required": True}],
                "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                              "description": "Eixo."}]}
        foreign = "https://github.com/team/river-plan"
        corpus = {foreign: ("River workflows and release notes describe "
                            "the plan detailed equivalent screens.")}
        sent = ("River Notes mostra plano detalhado equivalente [1].")
        res = vr.check_support(sent, {1: foreign}, corpus, plan)
        self.assertTrue(res.get("unsupported"), res)
        self.assertIn("entidade não mencionada",
                      str((res.get("unsupported") or [{}])[0].get("reason")), res)

    def test_homonym_full_form_does_not_borrow(self):
        """Guarda: forma cheia curta nunca casa composto maior e vice-versa."""
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "ea", "label": "River Alpha",
                              "source_url": "https://github.com/team/river-alpha",
                              "required": True},
                             {"id": "eb", "label": "River Alphabeta",
                              "source_url": "https://github.com/team/river-alphabeta",
                              "required": True}],
                "criteria": [{"id": "c0", "label": "revisão", "required": True,
                              "description": "Eixo."}]}
        doc_b = "River Alphabeta models extended review flows."
        sent = "River Alpha declara recurso próprio de revisão [1]."
        res = vr.check_support(
            sent, {1: "https://github.com/team/river-alphabeta"},
            {"https://github.com/team/river-alphabeta": doc_b,
             "https://github.com/team/river-alpha": "River Alpha declara recurso próprio."},
            plan)
        self.assertTrue(res.get("unsupported"), res)

    def test_reconciliation_notes_carry_separate_synthesis_scope(self):
        """🟡 texto da nota estável (sem sha inline); alcance histórico em
        linha separada da seção de notas."""
        st = covered_state3()
        st["report"]["synthesis_sha"] = "dbcf44eb069f" + "c126dde7313a7a27"
        out = rr.render_report(st, synthesis_text=("INFERÊNCIA de complementaridade entre "
                                                  "River Review (acme) e River Plan, "
                                                  "com limite declarado. Ver."),
                               verifications=None)
        for line in out.splitlines():
            if line.startswith("- Nota:"):
                self.assertNotRegex(line, r"síntese [0-9a-f]{12}", line)
        self.assertRegex(out, r"reconciliação referem-se à síntese [0-9a-f]+", out)


class TRemedicaoAttempt2(unittest.TestCase):
    """Segundo passe (attempt 2: 0🔴, 6🟡, 1❓) — 1 correção por causa."""

    SIBLING = "https://github.com/team/river-marketplace"

    def test_package_doc_match_rejects_longer_sibling_slug(self):
        """(1) substring casava URL estrangeira (marketplace vs market) e
        derrotava o anti-fusão: match com fronteira."""
        self.assertFalse(sr._is_package_doc(self.SIBLING, ["river-market"]))
        self.assertTrue(sr._is_package_doc(
            "https://github.com/team/river-market", ["river-market"]))
        evidence = {
            self.SIBLING: ("# river-marketplace\nriver-marketplace extends "
                           "river-market with hosted plugins."),
        }
        anchors, _text = sr._select_evidence(
            ["river-market"],
            "LACUNA nos excertos avaliados: river-market documenta apenas instalação.",
            evidence, [])
        self.assertEqual(anchors, [], anchors)

    def test_window_cooccurrence_requires_same_clause(self):
        """(2) `excertos` incidental noutra oração + `sem fonte` desviava
        prosa positiva: molde e alcance precisam da mesma oração."""
        self.assertFalse(vr.is_lacuna_declaration(
            "O River Plan documenta os excertos avaliados na seção 2, "
            "e declara instalação sem fonte única oficial."))
        self.assertTrue(vr.is_lacuna_declaration(
            "O River Plan declara mínimo atendido, sem fonte de "
            "compatibilidade funcional (LACUNA de integração)."))

    def test_demonstrada_template_aligned_across_gates(self):
        """(3) `sem <dim> demonstrada` era LACUNA num gate e positivo no
        outro: gates alinhados."""
        sent = "`cand-x`: **insufficient** — sem revisão demonstrada [1]."
        self.assertTrue(vr.is_lacuna_declaration(sent))
        self.assertTrue(sr._is_absence_claim(sent))

    def test_monorepo_sibling_doc_is_not_vetoed(self):
        """(4) veto por repo vetava doc próprio de irmãos monorepo (mesmo
        repo_key do requerente): pula veto quando cur == próprio."""
        mono = "https://github.com/team/mono"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "ea", "label": "River Alpha",
                              "source_url": mono, "required": True},
                             {"id": "eb", "label": "River Beta",
                              "source_url": mono, "required": True}],
                "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                              "description": "Eixo."}]}
        corpus = {mono: "Alpha river metrics and dashboards."}
        lac = ("LACUNA nos excertos: River Alpha sem trecho sobre o eixo [1].")
        res = vr.check_support(lac, {1: mono}, corpus, plan)
        self.assertEqual(res.get("supported"), 1, res)
        pos = "River Alpha declara recurso próprio [1]."
        res2 = vr.check_support(pos, {1: mono}, corpus, plan)
        self.assertEqual(res2.get("supported"), 1, res2)

    def test_second_unrelated_version_not_exempted(self):
        """(5) janela de 40 chars isentava 2ª versão não-relacionada: só a
        versão na oração de comparação numérica junto ao marcador."""
        url = "https://github.com/team/river-plan"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e1", "label": "River Plan",
                              "source_url": url, "required": True}],
                "criteria": [{"id": "c0", "label": "compatibilidade", "required": True,
                              "description": "Eixo."}]}
        corpus = {url: ("River Plan requires RiverHost V2 2.1.2+. "
                        "Documented plan review.")}
        sent = ("O River Plan declara mínimo 2.1.2 com mínimo atendido; instalada 2.1.4 "
                "(premissa controlada), 9.9.9 sem fonte "
                "(LACUNA de integração [1]).")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        self.assertTrue(res.get("unsupported"), res)
        self.assertIn("versão exata",
                      str((res.get("unsupported") or [{}])[0].get("reason")), res)


if __name__ == "__main__":
    unittest.main()
