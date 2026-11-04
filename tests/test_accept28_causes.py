#!/usr/bin/env python3
"""accept28 causas-raiz — testes de contrato genéricos (sem nomes de produto).

Widget Alpha/Beta seguem a convenção dos testes do repo; nenhum nome de
plugin/fonte real. Cada teste falha antes do fix (TDD RED) e passa depois,
sem reescrever auditores.

A1 descoberta aberta com estados concordantes (DESC b: teto conta todas as
   required; unexplored reconciliado; writer nunca chama required de
   alternativa).
A2 conjunto cobre propósito sem exigir tudo de cada um (DESC c: N/A
   delimitado respeitado; N/A->insufficient exige evidência nova; trilha de
   avaliações por round para auditoria).
A3 identidade vínculo verificável (IDENT: refs covered/partial exigem
   identidade universal; doc genérico descartado).
A4 inferência prudente declarada nunca integração testada sem doc-interop
   com >=2 formas cheias (IDENT C9, nos dois espelhos).
A5 config proporcional com reserva (ORÇAMENTO: stop rounds com registro
   proporcional + fonte user/default; parcial quando há gaps).
A6 verificação correspondente (ORÇAMENTO: sem support ok com question
   partial + misses do oráculo diagnose).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept28 test is offline")


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
        "evaluations": [], "run_id": "accept28-tdd",
        "rounds": [{"round": 0}, {"round": 1}], "notes": [],
        "plan_versions": [], "attempts": {},
        "consumption": {"model_calls": 0, "rounds": 0},
        "unexplored_alternatives": [],
    }


class DescBCapTest(unittest.TestCase):
    def test_g5_cap_counts_all_required(self):
        """Teto de candidatos conta TODAS as required (não só discovered)."""
        plan = ledger_mod.validate_plan({
            "plan_id": "cap", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget Alpha",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["e0"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "candidate_target": 1,
            "open_discovery": {"needed": True,
                               "need": "discover candidates"},
        })
        st = base_state(plan, {URL_B: DOC_B})
        st["discovery"]["candidates"] = [URL_B]
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._apply_discovery(
            st, led,
            {"entity": {"id": "w2", "label": "Widget Beta", "url": URL_B},
             "criteria": []},
            {"criterion_id": "c1"})
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w2")
        self.assertFalse(new.get("required", True),
                         f"teto estourou: {st['plan']['entities']}")


class DescBReconcileTest(unittest.TestCase):
    def _weak_state(self):
        plan = ledger_mod.validate_plan({
            "plan_id": "sub", "version": 1, "question": "q",
            "entities": [{"id": "w2", "label": "Widget Beta", "required": True,
                          "discovered": True, "source_url": URL_B}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["w2"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        st = base_state(plan, {URL_B: DOC_B})
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        return st, led

    def test_unexplored_records_entity_id(self):
        st, led = self._weak_state()
        self.assertFalse(ac._maybe_substitute(st, led))
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs, "deveria registrar o que deixou de explorar")
        self.assertEqual(recs[0].get("entity_id"), "w2", recs)

    def test_covered_entity_is_not_unexplored(self):
        """Entidade com covered/partial nunca é 'alternativa não
        investigada' (writer não chama required investigado de alternativa)."""
        st, led = self._weak_state()
        led.evaluate("c1", "covered", "doc trata de Widget Beta",
                     "selected_material", [{"url": URL_B}], "w2")
        st["evaluations"] = [dict(led._evals[("c1", "w2")])]
        self.assertFalse(ac._maybe_substitute(st, led))
        recs = [r for r in (st.get("unexplored_alternatives") or [])
                if r.get("entity_id", r.get("entity")) in ("w2", "Widget Beta")]
        self.assertEqual(recs, [], f"stale unexplored: {recs}")

    def test_writer_prompt_excludes_investigated_required(self):
        """O writer não lista required investigado como alternativa não
        investigada: após reconciliação, o prompt não traz a seção."""
        st, led = self._weak_state()
        led.evaluate("c1", "covered", "doc trata de Widget Beta",
                     "selected_material", [{"url": URL_B}], "w2")
        st["evaluations"] = [dict(led._evals[("c1", "w2")])]
        st["unexplored_alternatives"] = [
            {"entity": "Widget Beta", "entity_id": "w2", "urls": []}]
        ac._reconcile_unexplored(st)
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        write = ac.make_model_writer(fake_client, max_chars=2400)
        block = led.compute()
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {},
                "rounds": st["rounds"],
                "evaluations": list(st["evaluations"]),
                "unexplored_alternatives": list(
                    st.get("unexplored_alternatives") or []),
                "substitutions": [], "semantic_rank": []}
        write(view)
        self.assertNotIn("Alternativas descobertas", seen.get("prompt", ""),
                         seen.get("prompt", "")[:1500])

    def test_substitute_ignores_url_slug(self):
        """Slug só na URL não sustenta troca: corpo auditado (usable_text)
        sem a forma cheia nunca admite o candidato."""
        URL_G = "https://example.com/widget-gamma"
        plan = ledger_mod.validate_plan({
            "plan_id": "slug", "version": 1, "question": "q",
            "entities": [
                {"id": "w_old", "label": "Widget Old", "required": True,
                 "discovered": True},
                {"id": "w_new", "label": "Widget Gamma", "required": False,
                 "discovered": True, "source_url": URL_G}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True,
                          "applies_to": ["w_old", "w_new"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        body = "a generic catalog of tools with no candidate names in it"
        st = base_state(plan, {URL_G: body})
        st["discovery"]["candidates"] = []
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        self.assertFalse(ac._maybe_substitute(st, led),
                         "slug na URL não é menção no corpo")
        kept = {e["id"]: e.get("required", True)
                for e in st["plan"]["entities"]}
        self.assertTrue(kept["w_old"], kept)

    def test_assess_round_reconciles_stale_unexplored(self):
        """Avaliação covered posterior reconcilia registro stale."""
        st, led = self._weak_state()
        st["unexplored_alternatives"] = [
            {"entity": "Widget Beta", "entity_id": "w2", "urls": []}]

        def assess(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w2",
                     "state": "covered",
                     "justification": "Widget Beta documentado no corpo",
                     "origin": "selected_material",
                     "references": [{"url": URL_B}]}]

        ac._assess_round(st, assess, led, None)
        recs = [r for r in (st.get("unexplored_alternatives") or [])
                if r.get("entity_id") == "w2"]
        self.assertEqual(recs, [], f"stale após covered: {recs}")


class DescCGuardTest(unittest.TestCase):
    def _na_state(self):
        plan = ledger_mod.validate_plan({
            "plan_id": "na", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha", "required": True,
                          "discovered": True},
                         {"id": "w2", "label": "Widget Beta", "required": True,
                          "discovered": True, "source_url": URL_B}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True,
                          "applies_to": ["w1", "w2"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        # The historical transition guard is about a *valid* N/A. A
        # description of distribution alone does not exclude indirect help.
        st = base_state(plan, {URL_A: DOC_A,
                               URL_B: DOC_B + " Widget Beta does not help with axis."})
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        na = led.evaluate(
            "c1", "not_applicable",
            "Widget Beta scope is distribution; testing axis out of scope",
            "selected_material", [{"url": URL_B}], "w2")
        st["evaluations"] = [dict(na)]
        st["_assessed_evidence_keys"] = sorted(st["evidence"])
        st["_assessed_evidence_hashes"] = ac._evidence_content_hashes(st)
        return st, led

    def test_na_to_insufficient_needs_new_evidence(self):
        """N/A->insufficient sem evidência nova é rejeitado (mantém N/A)."""
        st, led = self._na_state()

        def assess(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w2",
                     "state": "insufficient",
                     "justification": "no testing evidence in selection",
                     "origin": "selected_material",
                     "references": [{"url": URL_B}]}]

        ac._assess_round(st, assess, led, None)
        kept = {(e.get("criterion_id"), e.get("entity_id")): e.get("state")
                for e in st["evaluations"]}
        self.assertEqual(kept.get(("c1", "w2")), "not_applicable",
                         f"N/A rebaixado sem fato novo: {kept}")
        self.assertTrue(
            any("not_applicable" in str(n) and "w2" in str(n)
                for n in st["notes"]),
            f"rebaixamento barrado deve ser auditável: {st['notes']}")

    def test_insufficient_to_na_allowed_with_scope(self):
        """Direcional: insufficient->N/A com justificativa de escopo é
        permitido sem evidência nova (só N/A->insufficient exige fato
        novo); a transição fica auditável em notes."""
        st, led = self._na_state()
        st["evaluations"] = []
        st["_assessed_evidence_keys"] = sorted(st["evidence"])

        def assess_insuf(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w2",
                     "state": "insufficient",
                     "justification": "nothing yet in selection",
                     "origin": "selected_material",
                     "references": [{"url": URL_B}]}]

        ac._assess_round(st, assess_insuf, led, None)

        def assess_na(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w2",
                     "state": "not_applicable",
                     "justification": "Widget Beta scope is distribution; "
                                      "testing axis out of scope",
                     "origin": "selected_material",
                     "references": [{"url": URL_B}]}]

        ac._assess_round(st, assess_na, led, None)
        kept = {(e.get("criterion_id"), e.get("entity_id")): e.get("state")
                for e in st["evaluations"]}
        self.assertEqual(kept.get(("c1", "w2")), "not_applicable", kept)
        self.assertTrue(
            any("c1" in str(n) and "w2" in str(n) for n in st["notes"]),
            st["notes"])

    def test_same_url_new_content_counts_as_new_evidence(self):
        """Mesma URL com conteúdo novo conta como evidência nova: o
        rebaixamento citando o excerto atualizado é aplicado."""
        plan = ledger_mod.validate_plan({
            "plan_id": "chg", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "applies_to": ["w1"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        st = base_state(plan, {URL_A: DOC_A})
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))

        def assess_covered(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w1",
                     "state": "covered",
                     "justification": "Widget Alpha documentado",
                     "origin": "selected_material",
                     "references": [{"url": URL_A}]}]

        ac._assess_round(st, assess_covered, led, None)
        st["evidence"][URL_A] = ("Widget Alpha scope now excludes testing; "
                                 "page rewritten")
        st["qualification"][URL_A] = qual(URL_A, st["evidence"][URL_A])

        def assess_partial(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w1",
                     "state": "partial",
                     "justification": "reescrita restringe o escopo",
                     "origin": "selected_material",
                     "references": [{"url": URL_A}]}]

        ac._assess_round(st, assess_partial, led, None)
        kept = {(e.get("criterion_id"), e.get("entity_id")): e.get("state")
                for e in st["evaluations"]}
        self.assertEqual(kept.get(("c1", "w1")), "partial",
                         f"conteúdo novo ignorado: {kept}")

    def test_evaluation_trail_recorded_per_round(self):
        """Avaliações aplicadas por round persistem para auditoria."""
        st, led = self._na_state()

        def assess(plan, evidence, qualification):
            return []

        ac._assess_round(st, assess, led, None)
        trail = st.get("evaluation_trail") or []
        self.assertTrue(trail, "trilha de avaliações por round ausente")
        self.assertTrue(all("round" in t and "applied" in t for t in trail),
                        trail)


class DescAReserveTest(unittest.TestCase):
    def test_open_discovery_reserve_op_without_entity(self):
        """≥1 op/round para descoberta sem nome de entidade enquanto eixos
        zerados (de open_discovery.need)."""
        plan = ledger_mod.validate_plan({
            "plan_id": "res", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget", "required": True}],
            "criteria": [{"id": "c1", "label": "planning axis", "required": True,
                          "per_candidate": True, "applies_to": ["e0"], "description": "Eixo planning axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "open_discovery": {"needed": True,
                               "need": "discover planning candidates"},
        })
        st = base_state(plan, {})
        gaps = [{"criterion_id": "c1", "entity_id": "e0",
                 "entity_label": "Widget", "label": "planning axis",
                 "state": "insufficient"}]
        ops = ac.select_ops(st, gaps, 3)
        disc = [o for o in ops
                if not o.get("entity_id") and o.get("kind") == "gap_query"]
        self.assertTrue(disc, f"sem reserva de descoberta: {ops}")
        self.assertIn("discover", disc[0].get("target", ""), disc)

    def test_g6_reads_audited_body_not_raw(self):
        """G6 lê o mesmo corpo auditado da seleção (usable_text), não o
        raw: menção só no raw fora da janela não admite."""
        plan = ledger_mod.validate_plan({
            "plan_id": "g6b", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget", "required": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["e0"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "candidate_target": 5,
            "open_discovery": {"needed": True, "need": "discover"},
        })
        raw = "Widget Beta is documented here in full raw text"
        st = base_state(plan, {URL_B: raw})
        st["qualification"][URL_B] = qual(
            URL_B, "unrelated catalog listing without the name")
        st["discovery"]["candidates"] = [URL_B]
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._apply_discovery(
            st, led,
            {"entity": {"id": "w2", "label": "Widget Beta", "url": URL_B},
             "criteria": []},
            {"criterion_id": "c1"})
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w2")
        self.assertFalse(new.get("required", True),
                         "G6 deve auditar usable_text, não o raw")

    def test_discovery_reserve_preserves_cell_reads_cap1(self):
        """Com cap=1 e célula G1 pendente, a reserva não expulsa o
        read_source (prioridade absoluta de célula)."""
        URL_CELL = "https://example.com/cell-source"
        plan = ledger_mod.validate_plan({
            "plan_id": "cell", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget", "required": True,
                          "discovered": True, "source_url": URL_CELL}],
            "criteria": [{"id": "c1", "label": "planning axis", "required": True,
                          "per_candidate": True, "applies_to": ["e0"], "description": "Eixo planning axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "open_discovery": {"needed": True,
                               "need": "discover planning candidates"},
        })
        st = base_state(plan, {})
        st["discovery"]["candidates"] = []
        gaps = [{"criterion_id": "c1", "entity_id": "e0",
                 "entity_label": "Widget", "label": "planning axis",
                 "state": "insufficient", "source_url": URL_CELL}]
        ops = ac.select_ops(st, gaps, 1)
        self.assertEqual(len(ops), 1, ops)
        self.assertEqual(ops[0].get("kind"), "read_source", ops)
        self.assertEqual(ops[0].get("target"), URL_CELL, ops)
        self.assertTrue(any("reserve" in str(n).lower()
                            for n in st["notes"]), st["notes"])

    def test_g6_requires_full_form_mention_in_body(self):
        """G6 endurecido: menção exige forma cheia no corpo (não só tokens
        soltos)."""
        plan = ledger_mod.validate_plan({
            "plan_id": "g6", "version": 1, "question": "q",
            "entities": [{"id": "e0", "label": "Widget", "required": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True, "applies_to": ["e0"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "candidate_target": 5,
            "open_discovery": {"needed": True, "need": "discover"},
        })
        apart = ("widget guides and beta testing notes for managers")
        st = base_state(plan, {URL_B: apart})
        st["discovery"]["candidates"] = [URL_B]
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._apply_discovery(
            st, led,
            {"entity": {"id": "w2", "label": "Widget Beta", "url": URL_B},
             "criteria": []},
            {"criterion_id": "c1"})
        new = next(e for e in st["plan"]["entities"] if e["id"] == "w2")
        self.assertFalse(new.get("required", True),
                         "tokens soltos não são menção à forma cheia")


class IdentUniversalTest(unittest.TestCase):
    """Universais por ref: toda ref covered/partial exige identidade
    própria; a frouxa é descartada com nota (não pega carona). Entidade
    sem parte distintiva mantém o legado (nada a exigir)."""

    def _w1_state(self, evidence):
        plan = ledger_mod.validate_plan({
            "plan_id": "ident", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True},
                         {"id": "w2", "label": "Widget Beta",
                          "required": True, "discovered": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True,
                          "applies_to": ["w1", "w2"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        st = base_state(plan, evidence)
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        return st, led

    def test_loose_ref_stripped_keeps_good_one(self):
        """Ref genérica ([17]-genérico) descartada com nota; a boa sustenta."""
        st, led = self._w1_state({URL_A: DOC_A, URL_B: DOC_B})

        def assess(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w1",
                     "state": "covered",
                     "justification": "Widget Alpha documentado; Beta citado",
                     "origin": "selected_material",
                     "references": [{"url": URL_A}, {"url": URL_B}]}]

        ac._assess_round(st, assess, led, None)
        got = {(e.get("criterion_id"), e.get("entity_id")): e
               for e in st["evaluations"]}
        self.assertEqual(got[("c1", "w1")]["state"], "covered", got)
        urls = [r.get("url")
                for r in got[("c1", "w1")].get("references", [])]
        self.assertEqual(urls, [URL_A], f"frouxa não descartada: {urls}")
        self.assertTrue(any("identity mismatch" in str(n) and "descarta" in str(n)
                            for n in st["notes"]), st["notes"])

    def test_all_loose_refs_rejected(self):
        """Só refs frouxas: avaliação rejeitada (kept as insufficiency)."""
        st, led = self._w1_state({URL_B: DOC_B})

        def assess(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w1",
                     "state": "covered",
                     "justification": "doc genérico sem Widget Alpha",
                     "origin": "selected_material",
                     "references": [{"url": URL_B}]}]

        ac._assess_round(st, assess, led, None)
        got = {(e.get("criterion_id"), e.get("entity_id")): e.get("state")
               for e in st["evaluations"]}
        self.assertNotEqual(got.get(("c1", "w1")), "covered", got)
        self.assertTrue(any("identity mismatch" in str(n)
                            for n in st["notes"]), st["notes"])

    def test_generic_label_full_form_mention_accepted(self):
        ent = {"id": "e9", "label": "OpenCode Marketplace Plugin"}
        body = ("OpenCode Marketplace Plugin lists tools for review "
                "and testing.")
        st = {"evidence": {URL_A: body}, "qualification": {}}
        self.assertTrue(
            ac._evaluation_refs_have_identity(st, ent, [{"url": URL_A}]))

    def test_distinctive_entity_body_without_mention_rejected(self):
        """Corpo negativo discrimina o gate: entidade com parte
        distintiva sem menção no corpo → False (não vacuous True)."""
        ent = {"id": "w1", "label": "Widget Alpha"}
        st = {"evidence": {URL_B: DOC_B}, "qualification": {}}
        self.assertFalse(
            ac._evaluation_refs_have_identity(st, ent, [{"url": URL_B}]))


class PlanSharedTokensTest(unittest.TestCase):
    """Identidade sem hardcodar nomes: kind-words fixas + tokens
    presentes em todas as labels do plano e/ou na pergunta."""

    def test_no_product_literals_in_kind_set(self):
        self.assertNotIn("opencode", ac._GENERIC_KIND_TOKENS)
        self.assertNotIn("open", ac._GENERIC_KIND_TOKENS)
        self.assertNotIn("code", ac._GENERIC_KIND_TOKENS)

    def test_shared_label_tokens_are_generic(self):
        plan = {"entities": [{"id": "w1", "label": "Widget Alpha"},
                             {"id": "w2", "label": "Widget Beta"}]}
        shared = ac._plan_shared_tokens(plan, "")
        self.assertIn("widget", shared, shared)
        self.assertNotIn("alpha", shared, shared)
        toks = ac._entity_distinctive_tokens(
            {"id": "w1", "label": "Widget Alpha"}, shared)
        self.assertNotIn("widget", toks, toks)
        self.assertIn("alpha", toks, toks)

    def test_question_tokens_are_generic(self):
        shared = ac._plan_shared_tokens(
            {"entities": []}, "Compare widgets for planning")
        self.assertIn("widgets", shared, shared)
        toks = ac._entity_distinctive_tokens(
            {"id": "w1", "label": "Widget Alpha"}, shared)
        self.assertIn("alpha", toks, toks)

    def test_entity_without_distinctive_part_keeps_legacy(self):
        # Sem parte kind-distintiva (só kind-words): legado fail-open.
        plan = {"entities": [{"id": "e9", "label": "Plugin Manager Tool"},
                             {"id": "e8", "label": "Plugin Manager Helper"}]}
        shared = ac._plan_shared_tokens(plan, "")
        toks = ac._entity_distinctive_tokens(
            {"id": "e9", "label": "Plugin Manager Tool"}, shared)
        self.assertEqual(toks, [], toks)

    def test_kind_distinctive_never_stripped_to_zero(self):
        # "OpenCode" sai da lista fixa; o plano o deriva como
        # compartilhado — mas refinar nunca aniquila: sem ele o nome
        # ficaria vazio, então a parte kind-distintiva é mantida.
        plan = {"entities": [
            {"id": "e9", "label": "OpenCode Marketplace Plugin"},
            {"id": "e8", "label": "OpenCode Marketplace Helper"}]}
        shared = ac._plan_shared_tokens(plan, "")
        self.assertIn("opencode", shared, shared)
        toks = ac._entity_distinctive_tokens(
            {"id": "e9", "label": "OpenCode Marketplace Plugin"}, shared)
        self.assertEqual(toks, ["opencode"], toks)


class IdentNoAnchorTest(unittest.TestCase):
    PLAN_2 = {"plan_id": "p", "version": 1,
              "entities": [{"id": "e0", "label": "Widget Alpha",
                            "required": True},
                           {"id": "e1", "label": "Widget Beta",
                            "required": True}],
              "criteria": [{"id": "c0", "label": "compatibilidade",
                            "required": True,
                            "applies_to": ["e0", "e1"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}
    SENT = ("Os dois planejadores testados, por inferência, "
            "funcionam de forma combinada [1].")
    DOC = ("Os dois planejadores testados funcionam de forma "
           "combinada no fluxo documentado e estável.")
    URL_C = "https://example.com/combined-flow"

    def test_audit_inference_without_anchor_never_interop(self):
        """Sem âncora (named vazios): relation_ok=False, nunca supported /
        integração testada."""
        a_ok, r_ok, _ar, rr = verify._audit_inference(
            "Os dois planejadores testados",
            "por inferência funcionam de forma combinada",
            self.DOC, [], [])
        self.assertFalse(r_ok, "sem âncora não há relação sustentada")
        self.assertIn("ncora", (rr or "").lower(), rr)

    def test_check_support_paraphrase_combo_is_not_interop(self):
        res = verify.check_support(
            self.SENT, {1: self.URL_C}, {self.URL_C: self.DOC}, self.PLAN_2)
        self.assertEqual(res["supported"], 0, res)
        rels = [(d or {}).get("relation_ok")
                for d in (res.get("declared_inference") or [])]
        self.assertTrue(rels, res)
        self.assertFalse(any(rels), res)

    def test_diagnose_mirror_paraphrase_combo_is_not_interop(self):
        import diagnose_run as diag
        st = {"plan": self.PLAN_2, "evidence": {self.URL_C: self.DOC},
              "report": {"markdown": self.SENT + "\n",
                         "numbers": {"1": self.URL_C}}}
        out = diag.synthesis_audit(st)
        self.assertGreaterEqual(out["unsupported"], 1, out)
        self.assertEqual(out["supported"], 0, out)


class SlugUrlSelectionTest(unittest.TestCase):
    """URL nunca conta (resíduo): slug só na URL não seleciona floor de
    entidade nem gera termos de relevância."""

    def _plan(self):
        # Sem source_url: sem desempate que mascare o floor.
        return {"plan_id": "slug-sel", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Gamma",
                              "required": True, "discovered": True}],
                "criteria": [{"id": "c1", "label": "axis", "required": True,
                              "per_candidate": True,
                              "applies_to": ["w1"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

    def test_floor_ignores_url_slug(self):
        """Floor pins doc COM menção no corpo, nunca slug alfabético."""
        slug_url = "https://example.com/aaa-widget-gamma"
        body_url = "https://example.com/zzz-doc"
        view = {"question": "q", "plan": self._plan(),
                "evidence": {slug_url: "unrelated catalog text here",
                             body_url: "Widget Gamma is documented here"},
                "question_coverage": {}, "stop": {}, "rounds": [],
                "evaluations": [], "unexplored_alternatives": [],
                "substitutions": [], "semantic_rank": []}
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        write = ac.make_model_writer(fake_client)
        _, selection = write(view)
        included = selection.get("included_urls") or []
        self.assertTrue(included, selection)
        self.assertEqual(included[0], body_url,
                         f"slug não é menção: {included}")

    def test_relevance_terms_ignore_url_slug(self):
        """Termos de relevância do doc vêm do corpo auditado: slug na
        URL sem forma cheia no corpo gera lista vazia (espiona o
        argumento real passado a _relevant_excerpt, que segue executando)."""
        slug_url = "https://example.com/widget-gamma"
        plan = {"plan_id": "slug-terms", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Gamma",
                              "required": True}],
                "criteria": [{"id": "c1", "label": "axis", "required": True,
                              "applies_to": ["w1"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": ["q"]}
        seen_terms = []
        real_excerpt = ac._relevant_excerpt

        def spy(text, limit, terms=None, groups=None, entity_terms=None):
            seen_terms.append(list(entity_terms or []))
            return real_excerpt(text, limit, terms, groups, entity_terms)

        def fake_client(prompt):
            return "[]"

        assess = ac.make_model_assessor(fake_client)
        st = base_state(plan, {slug_url: "some unrelated filler text here"})
        led = ledger_mod.Ledger(plan, run_id="t")
        ac._relevant_excerpt = spy
        try:
            ac._assess_round(st, assess, led, None)
        finally:
            ac._relevant_excerpt = real_excerpt
        self.assertTrue(seen_terms, "excerto nunca chamado?")
        self.assertTrue(all(et == [] for et in seen_terms),
                        f"slug gerou termos: {seen_terms}")


class BudgetRoundsTest(unittest.TestCase):
    def test_max_rounds_source_recorded(self):
        # Contrato accept29 (3): override de harness marca source=harness;
        # user só com exigência explícita na pergunta/contexto.
        r_harness = ac.resolve_adaptive("medium", {"max_rounds": 3})
        self.assertEqual(r_harness.get("max_rounds_source"), "harness",
                         r_harness)
        r_user = ac.resolve_adaptive("medium", {"max_rounds": 3},
                                     user_demands_rounds=True)
        self.assertEqual(r_user.get("max_rounds_source"), "user", r_user)
        r_default = ac.resolve_adaptive("medium", None)
        self.assertEqual(r_default.get("max_rounds_source"), "default",
                         r_default)

    def test_rounds_stop_is_proportional_and_partial(self):
        """Stop rounds com gaps: motivo mantido, parcial, detalhe com
        consumo/limite + reserva + fonte."""
        docs = {"https://example.com/u1": "no markers here"}
        corp_docs = dict(docs)

        def search(target, channel="web"):
            return [{"url": u, "title": u, "snippet": "s"} for u in corp_docs]

        def fetch(url):
            return corp_docs[url]

        def assess(plan, evidence, qualification):
            return []

        def writer(view):
            return "# t\ntexto sem cobertura", {"included_urls": [],
                                                "cuts": "none"}

        def auditor(report, evidence):
            return {"enabled": False,
                    "verdict_state": "não revisado", "accepted": False}

        import time as _t
        res = ac.run_adaptive(
            "Compare widgets", profile="light",
            plan={"plan_id": "b", "version": 1,
                  "question": "Compare widgets",
                  "entities": [{"id": "e0", "label": "Widget",
                                "required": True}],
                  "criteria": [{"id": "c1", "label": "axis", "required": True,
                                "applies_to": ["e0"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                  "initial_paths": ["Compare widgets"]},
            search_fn=search, fetch_fn=fetch, assess_fn=assess,
            writer_fn=writer, auditor_fn=auditor, clock=_t.monotonic,
            overrides={"max_rounds": 1, "max_ops_per_round": 1})
        self.assertEqual(res["stop"]["reason"], "rounds", res["stop"])
        self.assertTrue(res["stop"].get("partial"), res["stop"])
        detail = str(res["stop"].get("detail", ""))
        for token in ("source=harness", "queries", "model_calls"):
            self.assertIn(token, detail, detail)


class InferencePremisesPairTest(unittest.TestCase):
    """Ponto 1 (positivo declarado) vs ponto 2 (negativo sem premissas).

    Positivo: 2 docs de entidades distintas sustentam cada premissa;
    o auditor declara INFERÊNCIA de complementaridade plausível COM
    limites e SEM rótulo integração testada (nunca supported por
    âncora). Negativo: sem doc-interop e sem âncora -> rejeição
    (LACUNA/rejeitado, nunca supported). Lado a lado provam que nem
    toda combinação vira o mesmo LACUNA genérico.
    """

    PLAN_2 = {"plan_id": "p", "version": 1,
              "entities": [{"id": "e0", "label": "Widget Alpha",
                            "required": True},
                           {"id": "e1", "label": "Widget Beta",
                            "required": True}],
              "criteria": [{"id": "c0", "label": "compatibilidade",
                            "required": True,
                            "applies_to": ["e0", "e1"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}

    def test_positive_two_docs_each_sustain_premise_declares_plausible(self):
        sent = ("Widget Alpha gerencia planos [1] \u2014 INFER\u00caNCIA: "
                "uso complementar com Widget Beta para fluxo combinado [2].")
        res = verify.check_support(
            sent, {1: URL_A, 2: URL_B},
            {URL_A: DOC_A, URL_B: DOC_B}, self.PLAN_2)
        # Nunca supported só por âncora: exige doc-interop para supported.
        self.assertEqual(res["supported"], 0, res)
        self.assertTrue(res["unsupported"], res)
        reason = str(res["unsupported"][0].get("reason", "").lower())
        self.assertIn("complementaridade plaus", reason, res)
        self.assertIn("ntegra", reason, res)  # "não integração testada"
        decl = res.get("declared_inference") or []
        self.assertTrue(decl, res)
        self.assertTrue(any(d.get("anchor_ok") for d in decl), decl)
        self.assertFalse(any(d.get("relation_ok") for d in decl), decl)
        scopes = " | ".join(str((d or {}).get("scope", "")) for d in decl)
        low = scopes.lower()
        # Declarada com limites, sem rótulo positivo de integração testada.
        self.assertIn("complementaridade plaus", low, scopes)
        self.assertTrue("limite" in low or "janela" in low, scopes)
        self.assertNotIn("integração testada (interoperabilidade citada)",
                         scopes, scopes)

    def test_negative_without_anchor_nor_interop_rejected_never_supported(self):
        sent = ("Os dois planejadores testados, por inferência, "
                "funcionam de forma combinada [1].")
        doc = ("Os dois planejadores testados funcionam de forma "
               "combinada no fluxo documentado e estável.")
        url = "https://example.com/combined-flow"
        res = verify.check_support(sent, {1: url}, {url: doc}, self.PLAN_2)
        self.assertEqual(res["supported"], 0, res)
        self.assertTrue(res["unsupported"], res)
        reason = str(res["unsupported"][0].get("reason", "").lower())
        self.assertIn("ncora", reason, reason)
        decl = res.get("declared_inference") or []
        self.assertTrue(decl, res)
        self.assertFalse(any((d or {}).get("anchor_ok") for d in decl),
                         decl)
        self.assertFalse(any((d or {}).get("relation_ok") for d in decl),
                         decl)
        scopes = " | ".join(str((d or {}).get("scope", "")) for d in decl)
        self.assertNotIn("integração testada (interoperabilidade citada)",
                         scopes, scopes)


class DeliveryPathTest(unittest.TestCase):
    """Ponto 3: atribuicao/contradicao no caminho da entrega.

    Caminho real assess->ledger->_reconcile_unexplored->writer/selecao.
    Ref frouxa tipo [17] (doc que nao menciona a entidade) e
    descartada com nota e nao chega a entrega como premissa; celula
    sem cobertura (C9 sintese vs c12/c13 ledger) vira LACUNA declarada
    no texto entregue - nao so no diagnose. Verifica saida do
    writer/selecao, nao so estado interno.
    """

    def test_loose_ref_discarded_before_delivery(self):
        plan = ledger_mod.validate_plan({
            "plan_id": "deliv", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True}],
            "criteria": [{"id": "c1", "label": "axis", "required": True,
                          "per_candidate": True,
                          "applies_to": ["w1"], "description": "Eixo axis: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        st = base_state(plan, {URL_A: DOC_A, URL_B: DOC_B})
        led = ledger_mod.Ledger(plan, run_id="t")
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))

        def assess(plan, evidence, qualification):
            return [{"criterion_id": "c1", "entity_id": "w1",
                     "state": "covered",
                     "justification": "Widget Alpha documentado; Beta citado",
                     "origin": "selected_material",
                     "references": [{"url": URL_A}, {"url": URL_B}]}]

        ac._assess_round(st, assess, led, None)
        got = {(e.get("criterion_id"), e.get("entity_id")): e
               for e in st["evaluations"]}
        self.assertEqual(got[("c1", "w1")]["state"], "covered", got)
        urls = [r.get("url")
                for r in got[("c1", "w1")].get("references", [])]
        self.assertEqual(urls, [URL_A], f"frouxa nao descartada: {urls}")
        self.assertTrue(any("identity mismatch" in str(n)
                            and "descarta" in str(n)
                            for n in st["notes"]), st["notes"])
        ac._reconcile_unexplored(st)
        block = led.compute()
        crit = next(c for c in block["criteria"] if c["id"] == "c1")
        self.assertEqual([r.get("url")
                          for r in crit.get("references", [])],
                         [URL_A], block)
        self.assertNotIn(URL_B, [r.get("url")
                                 for r in block.get("references", [])],
                         block)
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        write = ac.make_model_writer(fake_client, max_chars=2400)
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {},
                "rounds": st["rounds"],
                "evaluations": list(st["evaluations"]),
                "unexplored_alternatives": list(
                    st.get("unexplored_alternatives") or []),
                "substitutions": [], "semantic_rank": []}
        text, selection = write(view)
        self.assertTrue(seen.get("prompt"), "writer nunca chamado?")
        self.assertIn("cite APENAS", seen["prompt"], seen["prompt"][:2000])
        included = selection.get("included_urls") or []
        self.assertTrue(included, selection)
        self.assertEqual(included[0], URL_A,
                         f"piso nao pinou o doc da entidade: {included}")
        self.assertTrue(text.strip(), "texto entregue vazio?")

    def test_ledger_gap_becomes_declared_lacuna_in_delivered_text(self):
        # C9 (sintese: combinacao sem doc-interop) vs c12/c13 (ledger
        # sem cobertura): a entrega declara LACUNA, nunca afirma
        # integracao testada.
        plan = ledger_mod.validate_plan({
            "plan_id": "gap", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True},
                         {"id": "w2", "label": "Widget Beta",
                          "required": True, "discovered": True}],
            "criteria": [{"id": "c12", "label": "planejamento",
                          "required": True, "per_candidate": True,
                          "applies_to": ["w1", "w2"], "description": "Eixo planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                         {"id": "c13", "label": "distribuicao",
                          "required": True, "per_candidate": True,
                          "applies_to": ["w1", "w2"], "description": "Eixo distribuicao: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        })
        st = base_state(plan, {URL_A: DOC_A, URL_B: DOC_B})
        led = ledger_mod.Ledger(plan, run_id="t")

        def assess_empty(plan, evidence, qualification):
            return []

        ac._assess_round(st, assess_empty, led, None)
        ac._reconcile_unexplored(st)
        block = led.compute()
        gap_ids = {g.get("criterion_id") for g in block.get("gaps", [])}
        self.assertTrue({"c12", "c13"} <= gap_ids, block)
        c9 = ("Widget Alpha gerencia planos e integra com Widget Beta "
              "para uso combinado [1][2].")
        res = verify.check_support(
            c9, {1: URL_A, 2: URL_B},
            {URL_A: DOC_A, URL_B: DOC_B},
            {"plan_id": "p", "version": 1,
             "entities": plan["entities"],
             "criteria": [{"id": "c0", "label": "compatibilidade",
                           "required": True,
                           "applies_to": ["w1", "w2"], "description": "Eixo compatibilidade: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]})
        self.assertEqual(res["supported"], 0, res)
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            self.assertIn("c12", prompt, prompt[:4000])
            self.assertIn("c13", prompt, prompt[:4000])
            return ("# Relatorio\n\n"
                    "LACUNA: c12 sem evidencia suficiente nos excertos.\n"
                    "LACUNA: c13 sem evidencia suficiente nos excertos.\n")

        write = ac.make_model_writer(fake_client, max_chars=2400)
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {},
                "rounds": st["rounds"],
                "evaluations": list(st["evaluations"]),
                "unexplored_alternatives": list(
                    st.get("unexplored_alternatives") or []),
                "substitutions": [], "semantic_rank": []}
        text, selection = write(view)
        self.assertIn("LACUNA", text, text)
        self.assertIn("c12", text, text)
        self.assertIn("c13", text, text)
        self.assertNotIn("integração testada", text.lower(), text)
        self.assertTrue((selection.get("included_urls") or []), selection)


# diagnose_audit e so pos-hoc, fora do produto: verify_support le
# state["diagnose_audit"] apenas como oraculo externo (misses viram
# failed SOMENTE com pergunta parcial; sem pendencia viram nota).
# O que foi corrigido NO produto: gates universais de identidade
# (refs covered/partial exigem identidade propria), N/A direcional
# (N/A->insufficient exige evidencia nova), G5/G6 (teto conta todas
# as required; mencao exige forma cheia no corpo auditado), reserva
# de descoberta sem nome, rounds com detalhe+fonte, oraculo
# condicional. Nunca popular oraculo in-product.
class VerifyOracleTest(unittest.TestCase):
    def test_support_not_ok_with_question_partial_and_oracle_misses(self):
        """Sem support ok com question partial + misses do oráculo."""
        report = "Widget Alpha gerencia planos com revisao [1]."
        state = {
            "run_id": "t", "plan": IdentNoAnchorTest.PLAN_2,
            "evidence": {URL_A: DOC_A}, "qualification": {},
            "counters": {"documents": {"used_in_synthesis": [URL_A]}},
            "report": {"markdown": report, "numbers": {"1": URL_A}},
            "semantic": {"enabled": True, "claims": 1, "claims_reviewed": 1,
                         "verdicts": [{"id": 0, "verdict": "sustained"}],
                         "accepted": True},
            "question_coverage": {"complete": False,
                                   "proportion": 0.1,
                                   "gaps": [{"criterion_id": "c0"}]},
            "diagnose_audit": {
                "unsupported": 1,
                "unsupported_items": [{"sentence": "combo sem prova",
                                       "reason": "inferência sem citação de "
                                                 "interoperabilidade"}]},
        }
        dim = verify.verify_support(state, report, state["semantic"])
        self.assertNotEqual(dim["status"], "ok", dim)

    def test_support_oracle_without_question_partial_is_note_only(self):
        """Oráculo com misses mas pergunta sem pendência: nota
        informativa, sem forçar failed."""
        report = "Widget Alpha gerencia planos com revisao [1]."
        state = {
            "run_id": "t", "plan": IdentNoAnchorTest.PLAN_2,
            "evidence": {URL_A: DOC_A}, "qualification": {},
            "counters": {"documents": {"used_in_synthesis": [URL_A]}},
            "report": {"markdown": report, "numbers": {"1": URL_A}},
            "semantic": {"enabled": True, "claims": 1, "claims_reviewed": 1,
                         "verdicts": [{"id": 0, "verdict": "sustained"}],
                         "accepted": True},
            "question_coverage": {"complete": True,
                                   "proportion": 1.0,
                                   "gaps": []},
            "diagnose_audit": {
                "unsupported": 1,
                "unsupported_items": [{"sentence": "combo sem prova",
                                       "reason": "inferência sem citação de "
                                                 "interoperabilidade"}]},
        }
        dim = verify.verify_support(state, report, state["semantic"])
        self.assertEqual(dim["status"], "ok", dim)
        self.assertTrue(any("oráculo" in str(n).lower()
                            for n in dim.get("notes", [])), dim)


if __name__ == "__main__":
    unittest.main()
