#!/usr/bin/env python3
"""Fase F — 4 contratos do caminho integrado (TDD RED→GREEN, offline, genérico).

Sem literais de produto (AlphaWidget/BetaGadget...). Offline: audithook bloqueia
rede inclusive 8082; construtores reais (Ledger, planner, coordinator, renderer).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("fase F test is offline (inclusive 8082)")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_planner as planner
import adaptive_state
import coverage_ledger as cl


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def desc_for(label):
    return (f"Eixo {label}: o que conta como evidencia operacional para este "
            f"eixo, com exemplos de trechos e condicoes de aceite.")


def plan_label_only():
    return {
        "plan_id": "ff-c1", "version": 1, "question": "q",
        "entities": [{"id": "eA", "label": "AlphaWidget", "required": True}],
        "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                      "applies_to": ["eA"]}],
    }


class C1ValidateFailClosedTest(unittest.TestCase):
    def test_required_label_only_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            cl.validate_plan(plan_label_only())
        msg = str(ctx.exception).lower()
        self.assertIn("c1", msg)
        self.assertTrue("description" in msg or "definition" in msg)

    def test_required_with_description_accepted(self):
        p = plan_label_only()
        p["criteria"][0]["description"] = desc_for("eixo um")
        cl.validate_plan(p)

    def test_optional_label_only_accepted(self):
        p = plan_label_only()
        p["criteria"][0]["required"] = False
        cl.validate_plan(p)

    def test_planner_prompt_requires_description(self):
        prompt = planner.build_plan_prompt("compare dois candidatos")
        self.assertIn('"description"', prompt)

    def test_generate_plan_rejects_label_only(self):
        import json

        def model(_prompt):
            return json.dumps(plan_label_only())

        with self.assertRaises(planner.PlanError):
            planner.generate_plan("compare dois candidatos", model)

    def test_generate_plan_rejects_weak_description(self):
        import json
        p = plan_label_only()
        p["criteria"][0]["description"] = "curto"
        def model(_prompt):
            return json.dumps(p)
        with self.assertRaises(planner.PlanError):
            planner.generate_plan("compare dois candidatos", model)

    def test_generate_plan_accepts_operational_description(self):
        import json
        p = plan_label_only()
        p["criteria"][0]["description"] = desc_for("eixo um")
        def model(_prompt):
            return json.dumps(p)
        plan, _meta = planner.generate_plan("compare dois candidatos", model)
        self.assertEqual(plan["criteria"][0]["description"],
                         desc_for("eixo um"))


class C2CorpusSelecitonTest(unittest.TestCase):
    def _view(self, evidence, plan, cover_refs, eval_refs):
        block = {"criteria": [{"id": "c1", "label": "eixo um",
                                "references": [{"url": u} for u in cover_refs], "description": "Eixo eixo um: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}
        return {"question": "q", "plan": plan,
                "evidence": dict(evidence), "user_context": {},
                "question_coverage": block, "stop": {}, "rounds": [],
                "evaluations": [
                    {"criterion_id": "c1", "entity_id": "eA",
                     "state": "partial", "justification": "j",
                     "origin": "assessor",
                     "references": [{"url": u} for u in eval_refs]}],
                "unexplored_alternatives": [], "substitutions": [],
                "semantic_rank": []}

    def test_floor_prefers_source_over_listing(self):
        src = "https://example.org/alpha-source"
        listing = "https://example.org/catalog-listing"
        src_body = ("AlphaWidget guia completo. AlphaWidget documenta o eixo "
                    "um com exemplos. " * 20)
        list_body = ("Catalogo geral. AlphaWidget mencionado em uma linha. "
                     "AlphaWidget na lista. " * 20)
        plan = {
            "plan_id": "ff-c2", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um",
                          "required": True, "applies_to": ["eA"],
                          "description": desc_for("eixo um")}],
        }
        evidence = {src: src_body, listing: list_body}
        # listing mais referenciado (4x) que a fonte (1x); teto pequeno
        # para o piso decidir quem entra (1 doc cabe).
        view = self._view(evidence, plan, [listing] * 4, [listing] * 4)
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "relatorio"
        write = ac.make_model_writer(fake_client, max_chars=2100)
        _text, selection = write(view)
        included = selection.get("included_urls") or []
        self.assertEqual(included[:1], [src],
                         f"piso deve priorizar fonte propria: {selection}")

    def test_candidate_status_uses_qualified_body(self):
        src = "https://example.org/alpha-source"
        ent = {"id": "eA", "label": "AlphaWidget", "source_url": src}
        # raw menciona, qualificado nao menciona -> nao e fonte propria
        evidence = {src: "AlphaWidget detalhes " * 20}
        qualification = {src: qual("texto generico sem o nome " * 20)}
        try:
            st, urls = ac._candidate_corpus_status(
                evidence, ent, frozenset(), qualification)
        except TypeError:
            self.fail("_candidate_corpus_status deve aceitar corpo qualificado")
        self.assertNotEqual(st, "fonte própria", (st, urls))

    def test_four_stage_status_observable(self):
        src = "https://example.org/alpha-source"
        st = adaptive_state.new_state("q quatro estagios")
        st["plan"] = {
            "plan_id": "ff-c2s", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "applies_to": ["eA"],
                          "description": desc_for("eixo um")}],
        }
        body = "AlphaWidget detalhes do eixo um " * 60
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["assessments"] = [{"selection": [src], "cuts": "c"}]
        status = ac._candidate_selection_status(
            st, st["plan"]["entities"][0], [src])
        for key in ("obtida_usable", "examinada_assessor",
                    "incluida_writer", "analisada_celula"):
            self.assertIn(key, status, status)
        self.assertTrue(status["obtida_usable"])
        self.assertTrue(status["examinada_assessor"])
        self.assertTrue(status["incluida_writer"])

    def test_renderer_vetoes_outside_corpus_when_docs_exist(self):
        import report_renderer as renderer
        src = "https://example.org/alpha-source"
        body = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q veto")
        st["plan"] = {
            "plan_id": "ff-c2v", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "applies_to": ["eA"],
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["question_coverage"] = {"status": "partial", "proportion": 0.0,
                                   "criteria": [], "gaps": []}
        synth = ("AlphaWidget com fonte propria está fora do corpus: nenhum "
                 "documento trata da entidade.")
        md = renderer.render_report(st, synthesis_text=synth)
        low = md.lower()
        self.assertNotIn("fora do corpus: nenhum documento", low,
                         f"veto deve reescrever: {md[:1200]}")
        self.assertTrue("fora da seleção" in low or "lacuna" in low, md[:1200])

    def test_verification_fails_contradictory_absence(self):
        import verification_report as vr
        src = "https://example.org/alpha-source"
        body = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q contradi")
        st["plan"] = {
            "plan_id": "ff-c2c", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "applies_to": ["eA"],
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["report"] = {"numbers": {"1": src}}
        report = ("AlphaWidget está fora do corpus. Nenhum documento trata "
                  "da entidade [1].")
        res = vr.verify_support(st, report, None)
        self.assertEqual(res.get("status"), "failed",
                         f"contradição §0-ausência × §7-usable deve falhar: {res}")


class C3ComparativeSubstitutionTest(unittest.TestCase):
    def _state(self):
        A = "https://example.org/alpha-a"
        B = "https://example.org/beta-b"
        plan = {
            "plan_id": "ff-c3", "version": 1, "question": "q",
            "candidate_target": 1,
            "entities": [
                {"id": "eOld", "label": "AlphaWidget", "required": True,
                 "discovered": True, "source_url": A},
                {"id": "eNew", "label": "BetaGadget", "required": False,
                 "discovered": True, "source_url": B},
            ],
            "criteria": [
                {"id": "c1", "label": "eixo um", "required": True,
                 "per_candidate": True, "applies_to": ["eOld", "eNew"],
                 "description": desc_for("eixo um")},
                {"id": "c2", "label": "eixo dois", "required": True,
                 "per_candidate": True, "applies_to": ["eOld", "eNew"],
                 "description": desc_for("eixo dois")},
            ],
        }
        st = adaptive_state.new_state("q troca")
        st["plan"] = plan
        st["evidence"] = {
            A: "AlphaWidget eixo um parcial " * 40,
            B: ("BetaGadget eixo um coberto com detalhes. "
                "BetaGadget eixo dois coberto com detalhes. " * 40),
        }
        st["qualification"] = {u: qual(t) for u, t in st["evidence"].items()}
        st["rounds"] = [{"round": 0}, {"round": 1}]
        st["evaluations"] = []
        return st

    def test_weak_partial_is_compared_not_immutable(self):
        st = self._state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        A = "https://example.org/alpha-a"
        B = "https://example.org/beta-b"
        led.evaluate("c1", "partial", "AlphaWidget parcial fraco",
                     "assessor", [{"url": A}], "eOld")
        led.evaluate("c1", "covered", "BetaGadget cobre eixo um",
                     "assessor", [{"url": B}], "eNew")
        led.evaluate("c2", "covered", "BetaGadget cobre eixo dois",
                     "assessor", [{"url": B}], "eNew")
        st["evaluations"] = [dict(v) for v in led._evals.values()]
        self.assertTrue(ac._maybe_substitute(st, led),
                        f"troca comparativa esperada: {st.get('notes')}")
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertFalse(emap["eOld"].get("required", True))
        self.assertTrue(emap["eNew"].get("required", True))
        rec = st["plan_versions"][-1]
        self.assertIn("old-vs-novo", str(rec.get("reason") or "").lower()
                      .replace(" ", "-").replace("_", "-")
                      or rec.get("reason"),
                      f"reason com tabela old-vs-novo: {rec}")

    def test_tie_keeps_and_records_unexplored(self):
        st = self._state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        A = "https://example.org/alpha-a"
        B = "https://example.org/beta-b"
        led.evaluate("c1", "partial", "AlphaWidget parcial",
                     "assessor", [{"url": A}], "eOld")
        led.evaluate("c1", "partial", "BetaGadget parcial",
                     "assessor", [{"url": B}], "eNew")
        st["evaluations"] = [dict(v) for v in led._evals.values()]
        self.assertFalse(ac._maybe_substitute(st, led))
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(emap["eOld"].get("required", True))
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs, "empate mantém + unexplored")

    def test_writer_distinguishes_targets_from_selection(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "texto"

        write = ac.make_model_writer(fake_client, max_chars=3000)
        plan = {
            "plan_id": "ff-c3w", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "discovered": True}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        view = {"question": "q", "plan": plan,
                "evidence": {"https://example.org/x": "AlphaWidget x " * 50},
                "user_context": {"targets": ["AlphaWidget"]},
                "question_coverage": {"criteria": []}, "stop": {},
                "rounds": [], "evaluations": [],
                "unexplored_alternatives": [], "substitutions": [],
                "semantic_rank": []}
        write(view)
        prompt = seen.get("prompt", "")
        self.assertNotIn("sem substituição", prompt,
                         f"carimbo indevido: {prompt[:800]}")
        self.assertIn("user_context", prompt.lower()
                      or "alvo do usuário" in prompt.lower()
                      or "targets" in prompt.lower(),
                      f"deve distinguir alvos do usuário: {prompt[:800]}")


class C4SynthesisReportTest(unittest.TestCase):
    def test_assessor_guides_combination_criteria(self):
        seen = {}

        def client(prompt):
            seen["prompt"] = prompt
            return "[]"

        assess = ac.make_model_assessor(client)
        st = adaptive_state.new_state("q combinacao")
        st["plan"] = {
            "plan_id": "ff-c4a", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [{"id": "c12", "label": "combinacao",
                          "required": True, "description": desc_for("c12")}],
        }
        st["evidence"] = {"https://example.org/a": "AlphaWidget a " * 100}
        st["qualification"] = {u: qual(t) for u, t in st["evidence"].items()}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        ac._assess_round(st, assess, led,
                         ac.resolve_adaptive("light",
                                              {"max_model_calls": 8}))
        prompt = seen.get("prompt", "")
        self.assertIn("INFER", prompt.upper(),
                      f"guidance de combinação ausente: {prompt[:1000]}")

    def test_finalize_promotes_partial_declared(self):
        import verification_report as vr
        st = adaptive_state.new_state("q promo")
        st["plan"] = {
            "plan_id": "ff-c4p", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [{"id": "c12", "label": "combinacao",
                          "required": True, "description": desc_for("c12")}],
        }
        doc_a = "AlphaWidget premissa um com detalhes " * 40
        doc_b = "BetaGadget premissa dois com detalhes " * 40
        ua, ub = "https://example.org/a", "https://example.org/b"
        st["evidence"] = {ua: doc_a, ub: doc_b}
        st["qualification"] = {ua: qual(doc_a), ub: qual(doc_b)}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        decl = {"sentence": ("INFERÊNCIA: complementaridade plausível entre "
                             "premissas [1][2] com limites explícitos."),
                "citations": [1, 2], "anchor_ok": True,
                "relation_ok": False,
                "scope": "limites explícitos",
                "premise_docs": [ua, ub]}
        n2u = {1: ua, 2: ub}
        ok = ac._promote_partial_declared(st, led, [decl], n2u)
        self.assertTrue(ok, f"promoção esperada: {st.get('notes')}")
        self.assertEqual(led.state_of("c12"), "partial")
        self.assertNotEqual(led.state_of("c12"), "covered")

    def test_renderer_cuts_at_sentence_boundary(self):
        import report_renderer as renderer
        st = adaptive_state.new_state("q corte")
        st["plan"] = {
            "plan_id": "ff-c4c", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {}
        st["qualification"] = {}
        long_just = ("Primeira frase completa. " +
                     "Segunda frase longa " + "x" * 700 + " fim. " +
                     "Terceira frase que nao deve aparecer cortada no meio.")
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.0,
            "criteria": [{"id": "c1", "label": "eixo um",
                          "state": "insufficient",
                          "justification": long_just,
                          "origin": "assessor", "references": [],
                          "applies_to": ["eA"], "description": "Eixo eixo um: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "gaps": []}
        md = renderer.render_report(st, synthesis_text="sintese curta.")
        # Corte em fronteira de frase (achados): o trecho truncado termina
        # em frase completa + […] e nunca em fragmento mid-word. Extrai a
        # linha do achado (seção 3) e confere o corte.
        import re as _re
        m = _re.search(r"### eixo um[^\n]*\n([^\n]+)", md)
        self.assertIsNotNone(m, f"achado ausente: {md[:1500]}")
        line = m.group(1)
        self.assertIn("[…]", line, f"corte esperado: {line[:500]}")
        self.assertTrue(line.rstrip().endswith("[…]"),
                        f"corte deve terminar em […]: {line[:500]}")
        # Gate de frase: sem fragmento longo de x sem fronteira.
        cut = renderer._cut_at_sentence(long_just, 600)
        self.assertIn("[…]", cut)
        self.assertNotRegex(cut, r"x{20}x",
                            f"corte mid-word: {cut[:500]}")

    def test_debug_prefixes_extended(self):
        import report_renderer as renderer
        for prefix in ("downgrade", "not_applicable", "identity-mismatch"):
            self.assertTrue(
                any(prefix in p for p in renderer._DEBUG_NOTE_PREFIXES),
                f"prefixo ausente: {prefix} em {renderer._DEBUG_NOTE_PREFIXES}")


if __name__ == "__main__":
    unittest.main()
