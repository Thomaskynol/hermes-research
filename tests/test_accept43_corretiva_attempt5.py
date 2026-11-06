"""Corretiva accept43 attempt5 — itens 1-4 (TDD RED primeiro).

Genérico, sem literais de produto: fixtures "River" sintéticas, offline
(rede proibida inclusive 8082). Cada teste demonstra um defeito do código
atual pelo motivo esperado; a correção deve fazê-los passar sem enfraquecer
os controles que continuam rejeitando (frente 6 = negativos conservados).
"""
import json
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
        raise RuntimeError("attempt5 tests forbid network, including 8082")


sys.addaudithook(offline)

A = "https://github.com/acme/river-review"
B = "https://github.com/team/river-plan"
C = "https://github.com/team/river-deploy"
X = "https://example.com/river-blog"


def plan_rivers():
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


# ── Frente 1 (2a): escrita sem reading + finalização ──────────────────────

class T1FinalizeRefreshesScopeAfterWrite(unittest.TestCase):
    """Escopo examinado deve refletir a seleção do writer após a escrita,
    mesmo quando assessments=[] (sem reading pré-write)."""

    def test_annotate_force_recomputes_after_selection_change(self):
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = plan_rivers()
        st["evidence"] = {A: "River Review docs about review.",
                           B: "River Plan docs about planning."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                   "usable_text": t}
                               for u, t in st["evidence"].items()}
        st["assessments"] = []
        st["reading"] = {"collected_chars": 1000, "excerpted_chars": 0}
        st["report"] = {"selection": {"included_urls": []}}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        ac._annotate_examined_scope(st, block)
        before = " ".join(e.get("examined_scope", "")
                          for e in block.get("criteria") or [])
        self.assertIn("não examinado", before, before)
        # Pós-write: seleção do writer passa a incluir o doc de a.
        st["report"] = {"selection": {"included_urls": [A]}}
        st["reading"] = {"collected_chars": 1000, "excerpted_chars": 500}
        ac._annotate_examined_scope(st, block)
        stale = " ".join(e.get("examined_scope", "")
                         for e in block.get("criteria") or [])
        self.assertIn("não examinado", stale, stale)  # idempotente: congela
        ac._annotate_examined_scope(st, block, force=True)
        fresh = " ".join(e.get("examined_scope", "")
                         for e in block.get("criteria") or [])
        self.assertIn("River Review (acme): excerto examinado", fresh, fresh)


# ── Frente 2 (item 1): multi-entidade com evidência por entidade ──────────

ENUM_SENT = ("- Seleção exigida pelo plano, cada um com fonte própria: "
             "River Review (acme) (https://github.com/acme/river-review), "
             "River Plan (https://github.com/team/river-plan), "
             "River Deploy (https://github.com/team/river-deploy).")


class T2MultiEntityDecomposition(unittest.TestCase):
    """Frase de seleção fundindo 3 pacotes vira 3 claims single-package,
    cada um com packages/anchors próprios (sem fusão, sem reescrita)."""

    def _evidence(self):
        return {A: "# River Review\nPerforms automated code review.",
                B: "# River Plan\nOrganizes tickets by category on a board.",
                C: "# River Deploy\nDeploys from local directories."}

    def test_enumeration_splits_per_package(self):
        if hasattr(sr, "reset_state_for_tests"):
            sr.reset_state_for_tests()
        claims = sr.extract_claims(ENUM_SENT, self._evidence(), generic=True)
        by_pkg = {}
        for c in claims:
            for p in (c.get("packages") or []):
                by_pkg.setdefault(p, []).append(c)
        self.assertEqual(
            {c["id"] for c in claims
             if len(c.get("packages") or []) > 1}, set(), claims)
        self.assertGreaterEqual(len(claims), 3, claims)

    def test_last_item_with_e_conjunction_splits(self):
        """'A (urlA), B (urlB) e C (urlC)': o último item ligado por 'e'
        também vira sub-claim própria (sem fusão do par final)."""
        if hasattr(sr, "reset_state_for_tests"):
            sr.reset_state_for_tests()
        sent = ("Os cinco candidatos exigidos têm fonte primária: "
                "River Review (acme) (https://github.com/acme/river-review), "
                "River Plan (https://github.com/team/river-plan) e "
                "River Deploy (https://github.com/team/river-deploy).")
        evidence = {A: "# River Review\nPerforms automated code review.",
                    B: "# River Plan\nOrganizes tickets.",
                    C: "# River Deploy\nDeploys from local directories."}
        claims = sr.extract_claims(sent, evidence, generic=True)
        self.assertEqual(len(claims), 3, claims)
        for c in claims:
            self.assertEqual(len(c.get("packages") or []), 1, c)

    def test_each_subclaim_carries_only_own_anchors(self):
        if hasattr(sr, "reset_state_for_tests"):
            sr.reset_state_for_tests()
        claims = sr.extract_claims(ENUM_SENT, self._evidence(), generic=True)
        self.assertGreaterEqual(len(claims), 3, claims)
        own_by_key = {"review": A, "plan": B, "deploy": C}
        for c in claims:
            pkgs = c.get("packages") or []
            self.assertEqual(len(pkgs), 1, c)
            lab = str(pkgs[0]).lower()
            own = next((u for key, u in own_by_key.items()
                        if key in lab), None)
            self.assertIsNotNone(own, c)
            for u in (c.get("anchors") or []):
                self.assertEqual(u, own, c)

    def test_relation_sentence_stays_single(self):
        """Guarda: relação entre 2 pacotes não é decomponível (vínculo)."""
        if hasattr(sr, "reset_state_for_tests"):
            sr.reset_state_for_tests()
        sent = ("River Review complementa River Plan porque um revisa código "
                "e o outro organiza tickets "
                f"({A}) ({B}).")
        claims = sr.extract_claims(sent, self._evidence(), generic=True)
        self.assertEqual(len(claims), 1, claims)


# ── Frente 3: atribuição entre pacotes ────────────────────────────────────

class T3AttributionBetweenPackages(unittest.TestCase):
    """Sub-claim de um pacote nunca ancora doc próprio de outro pacote."""

    def test_subclaim_anchors_exclude_foreign_package_doc(self):
        if hasattr(sr, "reset_state_for_tests"):
            sr.reset_state_for_tests()
        evidence = {A: "# River Review\nPerforms automated code review.",
                    B: "# River Plan\nOrganizes tickets by category."}
        sent = ("Seleção: River Review (acme) (https://github.com/acme/river-review), "
                "River Plan (https://github.com/team/river-plan).")
        claims = sr.extract_claims(sent, evidence, generic=True)
        self.assertGreaterEqual(len(claims), 2, claims)
        for c in claims:
            pkgs = [p.lower() for p in (c.get("packages") or [])]
            anchors = c.get("anchors") or []
            if any("review" in p for p in pkgs):
                self.assertNotIn(B, anchors, c)
            if any("plan" in p for p in pkgs) and not any("review" in p for p in pkgs):
                self.assertNotIn(A, anchors, c)


# ── Frente 4 (item 3a): ausência delimitada ───────────────────────────────

def plan1(entity_label, entity_id, url):
    return {"plan_id": "p", "version": 1,
            "entities": [{"id": entity_id, "label": entity_label,
                          "source_url": url, "required": True}],
            "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                          "description": "Eixo."}]}


class T4DelimitedAbsence(unittest.TestCase):
    """'LACUNA nos trechos apresentados' com premissa verificada é lacuna
    delimitada sustentada — nunca 'sem sobreposição'."""

    def test_windowed_absence_without_lacuna_word_is_declared(self):
        """'sem recurso ... no trecho apresentado' é gap delimitado à
        janela, mesmo sem a palavra LACUNA."""
        url = "https://github.com/team/river-deploy"
        plan = plan1("River Deploy", "c", url)
        corpus = {url: ("# River Deploy\nDeploys from local directories.")}
        sent = ("- River Deploy: planejamento insufficient, sem recurso "
                "nesse eixo no trecho apresentado [1].")
        self.assertTrue(vr.is_lacuna_declaration(sent), sent)
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_positive_prose_in_window_is_not_declaration(self):
        """Guarda: prosa positiva situada na janela não vira lacuna."""
        self.assertFalse(vr.is_lacuna_declaration(
            "River Deploy instala pacotes no trecho apresentado [1]."))

    def test_lacuna_nos_trechos_apresentados_is_declared(self):
        url = "https://github.com/acme/river-review"
        plan = plan1("River Review (acme)", "a", url)
        corpus = {url: ("# River Review\nPerforms automated code review "
                        "on pull requests.")}
        sent = ("- River Review (acme): LACUNA nos trechos apresentados, "
                "sem recurso de planejamento visível; isso não prova "
                "ausência no documento integral [1].")
        self.assertTrue(vr.is_lacuna_declaration(sent), sent)
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)
        decl = [d for d in (res.get("declared") or [])
                if d.get("sentence") == sent]
        self.assertEqual(len(decl), 1, res)
        self.assertIn("janela", str(decl[0].get("scope")), res)


# ── Frente 5 (item 3b): fatos positivos com overlap literal ────────────────

class T5PositiveFactsWithLiteralOverlap(unittest.TestCase):
    """Fatos positivos com overlap literal (cognatos PT→EN + bigramas)
    são sustentados, não 'sem sobreposição'."""

    def test_premise_scoped_version_in_lacuna_clause_is_exempt(self):
        """Versão-premissa controlada que delimita o escopo da LACUNA
        (não afirma fato do doc) não exige ocorrência no citado."""
        url = "https://github.com/team/river-plan"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "b", "label": "River Plan",
                              "source_url": url, "required": True}],
                "criteria": [{"id": "c0", "label": "compatibilidade",
                              "required": True, "description": "Eixo."}],
                "targets": ["River Plan"]}
        corpus = {url: ("# River Plan\nOrganizes tickets by category.")}
        sent = ("- River Plan: LACUNA de integração com 2.1.4 como "
                "premissa controlada do experimento [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan,
                               selection=None)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_review_pr_positive_is_supported(self):
        url = "https://github.com/acme/river-review"
        plan = plan1("River Review (acme)", "a", url)
        corpus = {url: ("# River Review\nPerforms automated code review on "
                        "pull requests using parallel subagents with "
                        "confidence scoring and threshold.")}
        sent = ("- River Review (acme): Documentado com revisão automatizada "
                "de pull requests por subagentes paralelos com pontuação e "
                "limiar [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_sidebar_cli_positive_is_supported(self):
        url = "https://github.com/team/river-plan"
        plan = plan1("River Plan", "b", url)
        corpus = {url: ("# River Plan\nPins tickets to the bottom of the "
                        "right sidebar. Tickets are grouped by category. "
                        "Runs in the local CLI.")}
        sent = ("- River Plan: Documentado parcialmente com sidebar agrupada "
                "por categoria e execução local em CLI [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_light_literal_via_is_supported(self):
        """Caso leve como via: literal distintivo ('bun test') + entidade
        mencionada = força da relação, não integração inventada."""
        url = "https://github.com/team/river-deploy"
        plan = plan1("River Deploy", "c", url)
        corpus = {url: ("# River Deploy\nRun bun test for the project "
                        "development before deploying.")}
        sent = ("- River Deploy: o excerto menciona bun test para "
                "desenvolvimento do próprio projeto [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)


# ── Frente 6 (item 3c): inferência de premissas separadas ─────────────────

class T6InferenceFromSeparatePremises(unittest.TestCase):
    """Inferência com 2 premissas em fontes distintas + limites explícitos
    é partial declarada — nunca exige citação de interop que nega haver."""

    def _plan(self):
        return {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": A, "required": True},
                             {"id": "b", "label": "River Plan",
                              "source_url": B, "required": True}],
                "criteria": [{"id": "c0", "label": "combinações",
                              "required": True, "description": "Eixo."}]}

    def test_denied_interop_inference_is_partial_not_unsupported(self):
        corpus = {A: ("# River Review\nRiver Review revisa código com "
                      "subagentes e diff."),
                  B: ("# River Plan\nRiver Plan organiza tickets e refina "
                      "planos.")}
        sent = ("- INFERÊNCIA de complementaridade entre River Review, que "
                "revisa código com diff, e River Plan, que organiza tickets, "
                "sem afirmar integração testada; ausência de prova continua "
                "LACUNA ([1]) ([2]).")
        res = vr.check_support(sent, {1: A, 2: B}, corpus, self._plan())
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)
        partial = [d for d in (res.get("partial_declared") or [])
                   if d.get("sentence") == sent]
        self.assertEqual(len(partial), 1, res)

    def test_fabricated_premise_stays_unsupported(self):
        """Controle: premissa inventada segue rejeitada."""
        corpus = {A: ("# River Review\nRiver Review revisa código com "
                      "subagentes e diff."),
                  B: ("# River Plan\nRiver Plan organiza tickets e refina "
                      "planos.")}
        sent = ("- INFERÊNCIA de complementaridade entre River Review e "
                "River Plan porque um dobra o espaço-tempo e o outro "
                "teletransporta pacotes; limites: sem prova de integração "
                "([1]) ([2]).")
        res = vr.check_support(sent, {1: A, 2: B}, corpus, self._plan())
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertTrue(bad, res)

    def test_source_possession_claim_is_supported(self):
        """'X tem fonte primária identificada [N]' com [N] sendo a fonte
        própria de X é fato verificado pela própria citação."""
        url = "https://github.com/acme/river-review"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review (acme)",
                              "source_url": url, "required": True}],
                "criteria": [{"id": "c0", "label": "fontes",
                              "required": True, "description": "Eixo."}]}
        corpus = {url: ("# River Review\nPerforms automated code review.")}
        sent = ("- River Review (acme) tem fonte primária identificada [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_source_possession_via_listed_source_is_supported(self):
        """Fonte declarada sem repo detectável (listagem): a citação da
        URL exata registrada, com a entidade nomeada no corpo, prova a
        posse."""
        url = "https://example.com/index/river-review"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": url, "required": True}],
                "criteria": [{"id": "c0", "label": "fontes",
                              "required": True, "description": "Eixo."}]}
        corpus = {url: ("River Review entry with install docs.")}
        sent = ("- River Review com fonte primária identificada [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)

    def test_provenance_note_is_not_a_claim(self):
        """Nota de procedência (inventário, não afirmação) não entra na
        auditoria de frases."""
        url = "https://github.com/acme/river-review"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review (acme)",
                              "source_url": url, "required": True}],
                "criteria": [{"id": "c0", "label": "fontes",
                              "required": True, "description": "Eixo."}]}
        corpus = {url: ("# River Review\nPerforms automated code review.")}
        sent = ("Nota de procedência: [1]: fonte obtida; incluída no "
                "material da síntese.")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        self.assertEqual(res.get("claims"), 0, res)
        self.assertEqual(res.get("unsupported"), [], res)

    def test_split_lacuna_clauses_still_declared(self):
        """'sem recurso ... nos trechos; LACUNA [N]' (escopo e marcador em
        orações distintas) é gap delimitado à janela."""
        url = "https://github.com/team/river-deploy"
        plan = plan1("River Deploy", "c", url)
        corpus = {url: ("# River Deploy\nDeploys from local directories.")}
        sent = ("- River Deploy não tem lista de dependências nos trechos; "
                "LACUNA [1].")
        self.assertTrue(vr.is_lacuna_declaration(sent), sent)
        res = vr.check_support(sent, {1: url}, corpus, plan)
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertEqual(bad, [], res)


# ── Frente 7: negativos conservados ───────────────────────────────────────

class T7NegativesConserved(unittest.TestCase):
    """Homônimo, doc alheio e função inventada continuam rejeitados."""

    def test_homonym_pair_stays_unsupported(self):
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "ea", "label": "River Review",
                              "source_url": "https://github.com/acme/river-review",
                              "required": True},
                             {"id": "eb", "label": "BigCorp River Review",
                              "source_url": "https://github.com/bigcorp/river-review",
                              "required": False}],
                "criteria": [{"id": "c0", "label": "revisão", "required": True,
                              "description": "Eixo."}]}
        doc = "BigCorp River Review models extended review flows."
        sent = "River Review declara recurso próprio de revisão [1]."
        res = vr.check_support(
            sent, {1: "https://github.com/bigcorp/river-review"},
            {"https://github.com/bigcorp/river-review": doc,
             "https://github.com/acme/river-review": "River Review declara recurso."},
            plan)
        self.assertTrue(res.get("unsupported"), res)

    def test_url_slugs_do_not_count_as_mention(self):
        """Slug de URL ('.../river-review') não é menção da entidade."""
        body = ("See https://github.com/bigcorp/river-review for the "
                "unrelated BigCorp tool. This document describes BigCorp "
                "workflows only.")
        self.assertFalse(vr._entity_mentioned("River Review", "a", body))

    def test_foreign_doc_attribution_stays_rejected(self):
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e8", "label": "River Plan",
                              "source_url": "https://github.com/team/river-plan",
                              "required": True},
                             {"id": "e9", "label": "River Notes",
                              "required": True}],
                "criteria": [{"id": "c0", "label": "planejamento", "required": True,
                              "description": "Eixo."}]}
        foreign = "https://github.com/team/river-plan"
        corpus = {foreign: ("River workflows and release notes describe "
                            "planning.")}
        sent = ("LACUNA nos excertos avaliados: River Notes sem trecho que "
                "demonstre planejamento próprio [1].")
        res = vr.check_support(sent, {1: foreign}, corpus, plan)
        self.assertTrue(res.get("unsupported"), res)

    def test_invented_function_stays_rejected(self):
        url = "https://github.com/acme/river-review"
        plan = plan1("River Review (acme)", "a", url)
        corpus = {url: "# River Review\nPerforms automated code review."}
        sent = ("- River Review (acme): Documentado com teletransporte "
                "quântico de pacotes [1].")
        res = vr.check_support(sent, {1: url}, corpus, plan)
        self.assertTrue(res.get("unsupported"), res)


# ── Frente 8 (2d): notas por entidade ─────────────────────────────────────

class T8ReconciliationNotesPerEntity(unittest.TestCase):
    """Notas de reconciliação usam refs da célula da entidade, não a
    referência representativa do critério."""

    def _state(self):
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = {"plan_id": "rivers", "version": 1,
                      "entities": [{"id": "a", "label": "River Review (acme)",
                                    "source_url": A, "required": True},
                                   {"id": "b", "label": "River Plan",
                                    "source_url": B, "required": True}],
                      "criteria": [{"id": "c0", "label": "Funcionalidades",
                                    "required": True, "description": "Eixo.",
                                    "applies_to": ["a", "b"]}]}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus({A: "River Review docs.", B: "River Plan docs."},
                       {A: {"status": "usable", "excluded": False,
                            "usable_text": "River Review docs."},
                        B: {"status": "usable", "excluded": False,
                            "usable_text": "River Plan docs."}})
        led.evaluate("c0", "covered", "rep", "corpus", [{"url": A}], None)
        led.evaluate("c0", "covered", "cell-a", "corpus", [{"url": A}], "a")
        led.evaluate("c0", "covered", "cell-b", "corpus", [{"url": B}], "b")
        st["question_coverage"] = led.compute()
        st["report"] = {"numbers": {"13": A, "17": B},
                        "selection": {"included_urls": [A, B]}}
        st["evidence"] = {A: "River Review docs.", B: "River Plan docs."}
        st["qualification"] = {A: {"status": "usable", "excluded": False},
                               B: {"status": "usable", "excluded": False}}
        return st

    def test_note_about_b_cites_b_doc(self):
        st = self._state()
        synth = ("River Plan: LACUNA nos trechos apresentados, sem função "
                 "demonstrada.")
        nums = {rr._norm(A): 13, rr._norm(B): 17}
        notes = rr._reconciliation_notes(st, synth, nums)
        self.assertTrue(notes, notes)
        for n in notes:
            if "River Plan" in n:
                self.assertIn("[17]", n, n)
                self.assertNotIn("[13]", n, n)

    def test_pair_note_ignores_homonym_slug_match(self):
        """Par homônimo: 'River Review' só dentro de 'BigCorp River Review'
        não nomeia o curto sozinho."""
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = {"plan_id": "p", "version": 1,
                      "entities": [{"id": "a", "label": "River Review",
                                    "source_url": A, "required": True},
                                   {"id": "b", "label": "River Plan",
                                    "source_url": B, "required": True},
                                   {"id": "z", "label": "BigCorp River Review",
                                    "source_url": X, "required": False}],
                      "criteria": [{"id": "c0", "label": "combinações",
                                    "required": True, "description": "Eixo."}]}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus({A: "x", X: "y", B: "w"}, {})
        st["question_coverage"] = led.compute()
        synth = ("INFERÊNCIA de complementaridade entre BigCorp River Review "
                 "e River Plan, com limite declarado.")
        notes = rr._pair_reconciliation_notes(st, synth)
        for n in notes:
            rest = str(n).replace("BigCorp River Review", "")
            self.assertNotIn("River Review", rest, n)

    def test_token_overlap_without_full_form_names_nothing(self):
        """'Alibaba Open Code Review' não nomeia 'OpenCode Code Review':
        overlap frouxo (open/code/review) sem forma cheia não casa."""
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = {"plan_id": "p", "version": 1,
                      "entities": [{"id": "a", "label": "OpenCode Code Review",
                                    "source_url": A, "required": True},
                                   {"id": "b", "label": "River Plan",
                                    "source_url": B, "required": True},
                                   {"id": "z", "label": "Alibaba Open Code Review",
                                    "source_url": X, "required": False}],
                      "criteria": [{"id": "c0", "label": "combinações",
                                    "required": True, "description": "Eixo."}]}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus({A: "x", X: "y", B: "w"}, {})
        st["question_coverage"] = led.compute()
        synth = ("INFERÊNCIA de complementaridade entre Alibaba Open Code "
                 "Review e River Plan, com limite declarado.")
        notes = rr._pair_reconciliation_notes(st, synth)
        for n in notes:
            rest = str(n).replace("Alibaba Open Code Review", "")
            self.assertNotIn("OpenCode Code Review", rest, n)

    def test_post_write_notes_stay_out_of_user_body(self):
        """Notas internas de pós-write/relação entregue são diagnóstico
        (vão ao anexo), nunca ao corpo visível §5."""
        self.assertTrue(rr._is_debug_note(
            "post-write window: c_costxe13 -> partial (x)"))
        self.assertTrue(rr._is_debug_note(
            "delivered relation c_combo -> partial (y)"))
        self.assertFalse(rr._is_debug_note(
            "Nota: os achados não registram cobertura conjunta de A e B."))


# ── Frente 9 (2b): critérios de síntese e relações pós-write ──────────────

class T9SynthesisCriteriaRefresh(unittest.TestCase):
    """Partial de síntese re-deriva refs/justificativa na síntese nova (sem
    promover a covered); critérios globais de relação são avaliados contra
    a síntese entregue."""

    def _state(self):
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = {"plan_id": "p", "version": 1,
                      "entities": [{"id": "a", "label": "River Review",
                                    "source_url": A, "required": True},
                                   {"id": "b", "label": "River Plan",
                                    "source_url": B, "required": True}],
                      "criteria": [
                          {"id": "c_doc", "label": "Diferenciar documentado",
                           "required": True, "synthesis": True,
                           "description": "Eixo."},
                          {"id": "c_combo", "label": "Combinações",
                           "required": True,
                           "description": "Conta como evidência justificativa de quais combinam, com citação de complementaridade."}]}
        st["evidence"] = {A: "River Review revisa código.",
                           B: "River Plan organiza tickets."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                   "usable_text": t}
                               for u, t in st["evidence"].items()}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        st["evaluations"] = []
        st["question_coverage"] = led.compute()
        return st

    def test_partial_synthesis_refreshed_not_promoted(self):
        st = self._state()
        s1 = ("Documentado: River Review revisa código (https://github.com/acme/river-review). "
              "INFERÊNCIA de complementaridade. LACUNA em aberto.")
        out1 = ac._assess_synthesis_criteria(st, st["question_coverage"], s1)
        self.assertIsNotNone(out1, st.get("notes"))
        st["question_coverage"] = out1
        partials = [e for e in st["evaluations"]
                    if e.get("criterion_id") == "c_doc"]
        self.assertTrue(partials and partials[-1]["state"] == "partial", st["evaluations"])
        s2 = ("Documentado: River Plan organiza tickets (https://github.com/team/river-plan). "
              "INFERÊNCIA de sobreposição. LACUNA em aberto.")
        out2 = ac._assess_synthesis_criteria(st, st["question_coverage"], s2)
        st["question_coverage"] = out2 or st["question_coverage"]
        partials = [e for e in st["evaluations"]
                    if e.get("criterion_id") == "c_doc"]
        self.assertTrue(partials, st["evaluations"])
        self.assertEqual(partials[-1]["state"], "partial", st["evaluations"])
        self.assertIn(B, str(partials[-1].get("references")), st["evaluations"])
        self.assertNotIn(A, str(partials[-1].get("references")), st["evaluations"])

    def test_global_relation_evaluated_from_delivered_synthesis(self):
        st = self._state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [A, B]},
                        "numbers": {"13": A, "19": B}}
        synth = ("- INFERÊNCIA de complementaridade entre River Review e "
                 "River Plan para revisão e planejamento, sem afirmar "
                 "integração testada; limites: janela auditada [13] [19].")
        out = ac._assess_delivered_relations(st, synth, {13: A, 19: B})
        self.assertIsNotNone(out, st.get("notes"))
        st["question_coverage"] = out
        combo = next((c for c in out.get("criteria") or []
                      if c.get("id") == "c_combo"), {})
        self.assertEqual(combo.get("state"), "partial", out)
        self.assertNotEqual(combo.get("state"), "covered", out)

    def test_premise_map_ignores_table_rows_and_contexts(self):
        """Linhas de tabela do renderer nunca viram premissa; entidade
        de contexto (host) nunca ancora relação (só exigidos contam)."""
        st = self._state()
        plan = st["plan"]
        plan["entities"].append({"id": "host", "label": "RiverHost",
                                 "required": True, "role": "context"})
        led = cl.Ledger(plan, run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [A, B]},
                        "numbers": {"13": A, "19": B}}
        synth = ("| River Review | parcial | detalhe [13] |\n"
                 "| River Plan | parcial | detalhe [19] |\n"
                 "Premissa de River Review: revisa código [13].\n"
                 "Premissa de RiverHost: hospeda tudo [19].\n"
                 "INFERÊNCIA de complementaridade entre River Review e "
                 "RiverHost.\n"
                 "Limites: sem prova de integração testada.")
        out = ac._assess_delivered_relations(st, synth, {13: A, 19: B})
        self.assertIsNone(out, st.get("notes"))

    def test_premise_map_grounds_bare_inference(self):
        """Premissas em frases próprias + inferência nua com limites:
        a avaliação usa as refs das premissas (sem exigir citação na
        frase de inferência)."""
        st = self._state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [A, B]},
                        "numbers": {"13": A, "19": B}}
        synth = ("Premissa de River Review: revisa código com diff [13].\n"
                 "Premissa de River Plan: organiza tickets [19].\n"
                 "INFERÊNCIA de complementaridade entre River Review e "
                 "River Plan para revisão e planejamento.\n"
                 "Limites: sem prova de integração testada.")
        out = ac._assess_delivered_relations(st, synth, {13: A, 19: B})
        self.assertIsNotNone(out, st.get("notes"))
        combo = next((c for c in out.get("criteria") or []
                      if c.get("id") == "c_combo"), {})
        self.assertEqual(combo.get("state"), "partial", out)
        refs = str(combo.get("references"))
        self.assertIn(A, refs, out)
        self.assertIn(B, refs, out)


# ── Frente 10 (2c): reexame pós-write do insufficient ─────────────────────

class T10PostWriteReexamination(unittest.TestCase):
    """Célula insufficient cuja janela do writer contém entidade+dimensão
    ganha evaluation+refs; sem isso, marca 'não re-examinada pós-write'
    em vez de negar."""

    def _state(self):
        st = adaptive_state.new_state("Compare River tools.")
        st["plan"] = {"plan_id": "p", "version": 1,
                      "entities": [{"id": "a", "label": "River Review",
                                    "source_url": A, "required": True},
                                   {"id": "b", "label": "River Plan",
                                    "source_url": B, "required": True}],
                      "criteria": [{"id": "c_cost", "label": "Custos",
                                    "required": True, "per_candidate": True,
                                    "applies_to": ["a", "b"],
                                    "description": "Custo e licença."}]}
        st["evidence"] = {A: "# River Review\nLicensed under MIT. Free.",
                           B: "# River Plan\nOrganizes tickets."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                   "usable_text": st["evidence"][u]}
                               for u in st["evidence"]}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("c_cost", "insufficient", "sem custo demonstrado",
                     "corpus", [{"url": A}], "a")
        st["evaluations"] = [dict(e) for e in led._evals.values()]
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [A],
                                      "excerpts": {A: "River Review licensed under MIT license, free of charge."}}}
        return st

    def test_window_hit_updates_evaluation_with_refs(self):
        st = self._state()
        st["report"] = {"selection": {"included_urls": [A],
                                      "excerpts": {A: "River Review licensed under MIT license, costs nothing, free of charge."}}}
        out = ac._reexamine_insufficient_post_write(st, "texto entregue")
        self.assertIsNotNone(out, st.get("notes"))
        cell = next((c for c in out.get("criteria") or []
                     if c.get("id") == "c_cost"), {})
        self.assertEqual((cell.get("entity_states") or {}).get("a"),
                         "partial", out)
        evs = (cell.get("entity_evaluations") or {}).get("a") or {}
        self.assertIn(A, str(evs.get("references")), out)

    def test_window_miss_marks_not_reexamined(self):
        st = self._state()
        st["report"] = {"selection": {"included_urls": [A],
                                      "excerpts": {A: "River Review revisa código."}}}
        out = ac._reexamine_insufficient_post_write(st, "texto entregue")
        self.assertIsNotNone(out, st.get("notes"))
        cell = next((c for c in out.get("criteria") or []
                     if c.get("id") == "c_cost"), {})
        self.assertEqual((cell.get("entity_states") or {}).get("a"),
                         "insufficient", out)
        evs = (cell.get("entity_evaluations") or {}).get("a") or {}
        self.assertIn("não re-examinada pós-write",
                      str(evs.get("justification")), out)

    def test_window_resolves_canonical_source(self):
        """Fonte declarada = docs, excerto sob o canonical: a janela é
        encontrada pelo repositório canônico."""
        st = self._state()
        for e in st["plan"]["entities"]:
            if e["id"] == "a":
                e["source_url"] = "https://example.com/docs/river"
                e["canonical_source_url"] = A
        st["report"] = {"selection": {"included_urls": [A],
                                      "excerpts": {A: "River Review licensed under MIT license, costs nothing."}}}
        out = ac._reexamine_insufficient_post_write(st, "texto entregue")
        self.assertIsNotNone(out, st.get("notes"))
        cell = next((c for c in out.get("criteria") or []
                     if c.get("id") == "c_cost"), {})
        self.assertEqual((cell.get("entity_states") or {}).get("a"),
                         "partial", out)


# ── Frente 11 (item 4): 2ª fonte + corte ancorado ─────────────────────────

class T11SecondSourceAndAnchoredCut(unittest.TestCase):
    """2ª fonte da entidade entra quando a 1ª não cobre dimensão com gap;
    corte retém janelas de revisão (diff/review/syntax)."""

    def test_second_source_admitted_for_open_gap(self):
        """Gap aberto admite 2ª fonte sobre a entidade com a dimensão,
        mesmo quando o piso menciona a dimensão (a insuficiência da
        célula é o sinal de cobertura, não o léxico do piso)."""
        primary = "https://github.com/acme/river-review"
        second = "https://blog.acme.com/river-review-notes"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": primary, "required": True,
                              "discovered": True}],
                "criteria": [{"id": "c_rev", "label": "Revisão de código",
                              "required": True, "per_candidate": True,
                              "applies_to": ["a"], "description": "Eixo."}]}
        bodies = {primary: ("River Review plugin. Install and configure "
                            "review tools."),
                  second: ("River Review side-by-side diffs, syntax highlight "
                           "e código de exemplo.")}
        gaps = [{"criterion_id": "c_rev", "entity_id": "a"}]
        out = ac._second_sources_for_gaps(plan, bodies, [primary], gaps)
        self.assertEqual(out, [(primary, second)], out)

    def test_no_gap_no_second_source(self):
        """Sem gap aberto, a seleção segue idêntica (sem 2ª fonte)."""
        primary = "https://github.com/acme/river-review"
        second = "https://blog.acme.com/river-review-notes"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": primary, "required": True,
                              "discovered": True}],
                "criteria": [{"id": "c_rev", "label": "Revisão de código",
                              "required": True, "per_candidate": True,
                              "applies_to": ["a"], "description": "Eixo."}]}
        bodies = {primary: ("River Review plugin. Install and configure "
                            "review tools."),
                  second: ("River Review side-by-side diffs, syntax highlight "
                           "e código de exemplo.")}
        out = ac._second_sources_for_gaps(plan, bodies, [primary], [])
        self.assertEqual(out, [], out)

    def test_listicle_without_affinity_not_admitted(self):
        """Listão genérico que menciona o projeto não é voz própria da
        entidade (sem afinidade de dono/site)."""
        primary = "https://github.com/acme/river-review"
        other = "https://example.com/index-of-plugins"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": primary, "required": True,
                              "discovered": True}],
                "criteria": [{"id": "c_rev", "label": "Revisão de código",
                              "required": True, "per_candidate": True,
                              "applies_to": ["a"], "description": "Eixo."}]}
        bodies = {primary: "River Review plugin.",
                  other: ("River Review is one of many plugins with code "
                          "review in this index.")}
        gaps = [{"criterion_id": "c_rev", "entity_id": "a"}]
        out = ac._second_sources_for_gaps(plan, bodies, [primary], gaps)
        self.assertEqual(out, [], out)

    def test_same_slug_foreign_repo_not_admitted(self):
        """Mesmo slug sob outro dono não é voz própria (regra identidade)."""
        primary = "https://github.com/acme/river-review"
        fork = "https://github.com/other/river-review"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "a", "label": "River Review",
                              "source_url": primary, "required": True,
                              "discovered": True}],
                "criteria": [{"id": "c_rev", "label": "Revisão de código",
                              "required": True, "per_candidate": True,
                              "applies_to": ["a"], "description": "Eixo."}]}
        bodies = {primary: "River Review plugin.",
                  fork: "River Review fork with code review changes."}
        gaps = [{"criterion_id": "c_rev", "entity_id": "a"}]
        out = ac._second_sources_for_gaps(plan, bodies, [primary], gaps)
        self.assertEqual(out, [], out)

    def test_cut_keeps_review_dimension_window(self):
        head = "River Review config and install fragments. " * 60
        tail = ("Review the final plan with side-by-side diffs and "
                "syntax-highlighted ask_code feedback. ")
        text = head + tail * 10
        chunk, _stripped, _win = ac._relevant_excerpt(
            text, 2000, ["revisão", "código"],
            groups=dict(ac._criterion_groups(
                {"criteria": [{"id": "c_rev", "label": "Revisão de código"}]})))
        self.assertIn("diffs", chunk, chunk[-200:])
        self.assertLessEqual(len(chunk), 2000)


class T12ReviewBatchesRespectTransportCeiling(unittest.TestCase):
    """Lotes de auditoria respeitam o teto do transporte: nenhum lote
    excede o orçamento de caracteres (evita prompt_too_large e
    review_incomplete em massa)."""

    def test_oversized_claims_split_into_more_batches(self):
        big = "x" * 30000
        items = [{"id": i, "claim": f"c{i}", "packages": ["p"],
                  "licences": [], "free_assertion": False,
                  "evidence": big} for i in range(6)]
        chunks = sr._batch_by_budget(items, max_items=12, max_chars=85000)
        self.assertGreater(len(chunks), 1, chunks)
        for ch in chunks:
            size = len(json.dumps(
                [{k: it[k] for k in
                  ("id", "claim", "packages", "licences",
                   "free_assertion", "evidence")} for it in ch],
                ensure_ascii=False))
            self.assertLessEqual(size, 85000, len(ch))
        self.assertEqual(sum(len(ch) for ch in chunks), 6, chunks)

    def test_small_claims_keep_single_batch(self):
        items = [{"id": i, "claim": f"c{i}", "packages": ["p"],
                  "licences": [], "free_assertion": False,
                  "evidence": "short"} for i in range(6)]
        chunks = sr._batch_by_budget(items, max_items=12, max_chars=85000)
        self.assertEqual(len(chunks), 1, chunks)


if __name__ == "__main__":
    unittest.main()
