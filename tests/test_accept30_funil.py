#!/usr/bin/env python3
"""accept30 funil — 4 mecanismos genéricos (Widget Alpha/Beta, sem hardcode).

M1 quarentena _sent: doc em _sent que sustenta célula aberta sem refs é
   recitado antes de não-enviados irrelevantes; _sent sem relação segue por
   último. Teto JSON intacto (só reordena).
M2 janela de excerto: passagem rara (termo da dimensão perto da menção da
   entidade) aparece no excerto de 1200 mesmo com termos dominantes.
M3 rounds proporcional: plano real 55 células → 7 adotado pré-loop com
   folga; sem redução; sem mudança pós-início.
M4 rodízio gap_query: alvos alternam entre entidades com gaps; 1 entidade
   preserva o comportamento atual.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept30 funil test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac

URL_S = "https://example.org/widget-alpha-manual"
URL_B = "https://example.org/filler-note"
SUPPORT = ("Widget Alpha overview. Widget Alpha is a planning helper. "
           "It does planning with gates and plans. " * 10)
FILLER = "Unrelated filler note about weather and lunch menus. " * 6


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def global_plan():
    return {"plan_id": "q", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": False, "discovered": True,
                          "source_url": URL_S}],
            "criteria": [{"id": "c0", "label": "overview",
                          "required": True, "description": "Eixo overview: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "initial_paths": ["q"]}


def cell_plan():
    return {"plan_id": "q", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True,
                          "source_url": URL_S}],
            "criteria": [{"id": "c1", "label": "planning",
                          "required": True, "per_candidate": True,
                          "applies_to": ["w1"], "description": "Eixo planning: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            "initial_paths": ["q"]}


class QuarantineResendTest(unittest.TestCase):
    def test_sent_doc_supporting_open_cell_is_resent_first(self):
        assess = ac.make_model_assessor(lambda prompt: "[]")
        assess(global_plan(), {URL_S: SUPPORT, URL_B: FILLER},
               {URL_S: qual(SUPPORT), URL_B: qual(FILLER)})
        grown = {URL_S: SUPPORT, URL_B: FILLER}
        grown.update({f"https://example.org/n{i}": ("lorem ipsum dolor "
                                                    "sit amet. " * 100)
                      for i in range(10)})
        grown_q = {u: qual(t) for u, t in grown.items()}
        assess(cell_plan(), grown, grown_q)
        sel = list((assess.last_selection or {}).get("urls") or [])
        self.assertIn(URL_S, sel,
                      f"doc em _sent que sustenta célula aberta deve voltar: {sel[:4]}")

    def test_unrelated_sent_doc_stays_last(self):
        assess = ac.make_model_assessor(lambda prompt: "[]")
        assess(global_plan(), {URL_S: SUPPORT, URL_B: FILLER},
               {URL_S: qual(SUPPORT), URL_B: qual(FILLER)})
        grown = {URL_S: SUPPORT, URL_B: FILLER}
        grown.update({f"https://example.org/n{i}": ("lorem ipsum dolor "
                                                    "sit amet. " * 100)
                      for i in range(10)})
        grown_q = {u: qual(t) for u, t in grown.items()}
        assess(cell_plan(), grown, grown_q)
        sel = list((assess.last_selection or {}).get("urls") or [])
        self.assertIn(URL_S, sel)
        self.assertNotIn(URL_B, sel,
                         f"_sent sem relação com gaps segue fora do teto: {sel[:4]}")


class AnchoredDimensionWindowTest(unittest.TestCase):
    def test_rare_dimension_term_near_mention_survives_excerpt(self):
        filler = "planning orchestration workflow pipeline stage gate " * 12
        mention = "notes on Widget Alpha"
        rare = "implementation detail: Widget Alpha ships a code generator"
        doc = (filler * 14 + " " + mention + " " + filler * 2 + " " + rare
               + " " + filler * 30)
        self.assertGreater(len(doc), 6000)
        groups = ({f"criterio:c{i}": ["planning"] for i in range(1, 9)})
        groups["criterio:c9"] = ["implementation"]
        exc, _, _ = ac._relevant_excerpt(
            doc, 1200, ["planning", "implementation"],
            groups=groups, entity_terms=["widget", "alpha"])
        self.assertLessEqual(len(exc), 1250)
        self.assertIn("implementation", exc,
                      "passagem rara dimensão-perto-menção deve ter ≥1 janela")

    def test_pin_replaces_group_turn_not_third_party(self):
        """Pin ancorado conta como o 1º turno do próprio grupo (Fase B M2):
        o grupo pinado pula sua passada no round-robin em vez de somar
        uma janela extra que expulsaria a última dimensão do teto."""
        filler = "planning orchestration workflow pipeline stage gate "
        mention = "notes on Widget Alpha"
        doc = (filler * 20 + " " + mention + " " + filler * 6 + " "
               "implementation notes for Widget Alpha setup " + filler * 200
               + " implementation implementation cluster " + filler * 40
               + " warranty terms apply " + filler * 10)
        self.assertGreater(len(doc), 6000)
        groups = {"criterio:c1": ["implementation"]}
        groups.update({f"criterio:c{i}": ["planning"] for i in range(2, 6)})
        groups["criterio:c6"] = ["warranty"]
        exc, _, _ = ac._relevant_excerpt(
            doc, 1200, ["planning", "implementation", "warranty"],
            groups=groups, entity_terms=["widget", "alpha"])
        self.assertLessEqual(len(exc), 1250)
        self.assertIn("implementation", exc)
        self.assertIn("warranty", exc,
                      "pin substitui a vez do próprio grupo, nunca de terceiros")


class ResendCapPerCellTest(unittest.TestCase):
    def test_one_resend_per_cell_with_trail(self):
        """Fase B M1: no máximo 1 reenvio por célula, com trilha auditável
        (url→célula) — presença fraca não vira pressão por parcial."""
        plan = {"plan_id": "p", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True}],
                "criteria": [{"id": "c1", "label": "planning",
                              "required": True, "per_candidate": True,
                              "applies_to": ["w1"], "description": "Eixo planning: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": ["q"]}
        docs = {f"https://example.org/s{i}":
                ("Widget Alpha planning helper guide. " * 12)
                for i in range(3)}
        q = {u: qual(t) for u, t in docs.items()}
        got = ac._resend_for_open_cells(
            plan, docs, q, set(docs), {}, {}, {})
        self.assertEqual(len(got), 1, got)
        url, cid, eid = got[0]
        self.assertIn(url, docs)
        self.assertEqual((cid, eid), ("c1", "w1"))


class EmptyDimensionRegressionTest(unittest.TestCase):
    def test_token_present_without_demo_stays_insufficient(self):
        """Fase B M1 (regressão): dimensão vazia real — token presente sem
        demonstração — permanece insufficient mesmo com o reenvio ativo
        (reenvio recita, nunca fabrica cobertura)."""
        import adaptive_state as state_api
        import coverage_ledger as cl
        URL_D = "https://example.org/widget-manual"
        doc = ("Widget Alpha manual. Widget Alpha is a planning helper. "
               "It does planning with gates and testing checklist notes. "
               * 8)
        plan = {"plan_id": "p", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True, "discovered": True,
                              "source_url": URL_D}],
                "criteria": [{"id": "c9", "label": "automated testing",
                              "required": True, "per_candidate": True,
                              "applies_to": ["w1"], "description": "Eixo automated testing: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": ["q"]}
        assess = ac.make_model_assessor(lambda prompt: "[]")
        assess({"plan_id": "p", "version": 1, "question": "q",
                "entities": [],
                "criteria": [{"id": "c0", "label": "overview",
                              "required": True, "description": "Eixo overview: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": ["q"]},
               {URL_D: doc}, {URL_D: qual(doc)})
        prior = [{"criterion_id": "c9", "entity_id": "w1",
                  "state": "insufficient",
                  "justification": "sem demonstração de execução de testes",
                  "origin": "material selecionado", "references": []}]
        grown = {URL_D: doc}
        grown.update({f"https://example.org/n{i}": ("lorem ipsum dolor "
                                                    "sit amet. " * 100)
                      for i in range(10)})
        st = state_api.new_state("q?")
        st["plan"] = plan
        st["evidence"] = dict(grown)
        st["qualification"] = {u: qual(t) for u, t in grown.items()}
        st["evaluations"] = list(prior)
        ledger = cl.Ledger(plan)
        resolved = ac.resolve_adaptive("light")
        _, block = ac._assess_round(st, assess, ledger, resolved)
        sel = list((assess.last_selection or {}).get("urls") or [])
        self.assertIn(URL_D, sel, "reenvio ativo para a célula aberta")
        self.assertTrue(any("reenvio de quarentena" in str(n)
                            for n in st.get("notes", [])),
                        [str(n)[:80] for n in st.get("notes", [])])
        crit = next(c for c in block["criteria"] if c["id"] == "c9")
        self.assertEqual(crit["state"], "insufficient", crit)


class ResendServesNewlyOpenedCellTest(unittest.TestCase):
    def test_doc_serving_old_cell_is_resent_for_new_cell(self):
        """Fase B marca (buraco inter-critérios): doc que serviu c1×e1 e faz
        falta em c2×e1 aberta sem refs é recitado — o reenvio qualifica por
        (url sustenta célula aberta sem refs), não pela marca de envio."""
        URL_D = "https://example.org/widget-guide"
        doc = ("Widget Alpha guide. Widget Alpha does planning and "
               "testing with gates. " * 10)
        base = {"plan_id": "p", "version": 1, "question": "q",
                "entities": [{"id": "w1", "label": "Widget Alpha",
                              "required": True}],
                "initial_paths": ["q"]}
        plan1 = dict(base, criteria=[
            {"id": "c1", "label": "planning", "required": True,
             "per_candidate": True, "applies_to": ["w1"], "description": "Eixo planning: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}])
        plan2 = dict(base, criteria=[
            {"id": "c1", "label": "planning", "required": True,
             "per_candidate": True, "applies_to": ["w1"], "description": "Eixo planning: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c2", "label": "testing", "required": True,
             "per_candidate": True, "applies_to": ["w1"], "description": "Eixo testing: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}])
        assess = ac.make_model_assessor(lambda prompt: "[]")
        assess(plan1, {URL_D: doc}, {URL_D: qual(doc)})
        assess.set_previous_evaluations([
            {"criterion_id": "c1", "entity_id": "w1", "state": "covered",
             "justification": "j", "origin": "o",
             "references": [{"url": URL_D}]}])
        grown = {URL_D: doc}
        grown.update({f"https://example.org/n{i}": ("lorem ipsum dolor "
                                                    "sit amet. " * 100)
                      for i in range(10)})
        assess(plan2, grown, {u: qual(t) for u, t in grown.items()})
        sel = list((assess.last_selection or {}).get("urls") or [])
        self.assertIn(URL_D, sel,
                      f"doc que sustenta c2×e1 aberta deve voltar: {sel[:4]}")


class ProportionalRoundsTest(unittest.TestCase):
    def _plan(self, n_ent, n_crit):
        return {"plan_id": "p55", "version": 1, "question": "q",
                "entities": [{"id": f"w{i}", "label": f"Widget {i}",
                              "required": True, "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."} for i in range(n_ent)],
                "criteria": [{"id": f"c{j}", "label": f"axis {j}",
                              "required": True, "per_candidate": True,
                              "applies_to": [f"w{i}" for i in range(n_ent)], "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}
                             for j in range(n_crit)],
                "initial_paths": ["q"]}

    def _transports(self):
        def search(target, channel="web"):
            return [{"url": "https://example.org/d",
                     "title": "d", "snippet": "s"}]

        def fetch(url):
            return "Widget 0 axis content here"

        def writer(view):
            return ("texto", {"included_urls": [], "cuts": "nenhum"})

        def auditor(report, evidence):
            return {"enabled": False, "accepted": False}
        return search, fetch, writer, auditor

    def test_real_plan_55_cells_adopts_7_pre_loop(self):
        import tempfile
        search, fetch, writer, auditor = self._transports()
        with tempfile.TemporaryDirectory() as tmp:
            res = ac.run_adaptive(
                "q", profile="medium", plan=self._plan(11, 5),
                search_fn=search, fetch_fn=fetch,
                assess_fn=lambda *a: [], writer_fn=writer,
                auditor_fn=auditor, run_dir=tmp, run_id="prop55",
                overrides={"max_rounds": 6})
            import json
            with open(Path(tmp) / "state.json") as fh:
                st = json.load(fh)
            self.assertEqual(
                st["config_applied"]["max_rounds"], 7, res.get("stop"))
            self.assertTrue(any("proporcional" in str(n).lower()
                                for n in st.get("notes", [])),
                            [n for n in st.get("notes", [])][-3:])

    def test_small_plan_never_reduces(self):
        import tempfile
        search, fetch, writer, auditor = self._transports()
        with tempfile.TemporaryDirectory() as tmp:
            ac.run_adaptive(
                "q", profile="medium", plan=self._plan(2, 2),
                search_fn=search, fetch_fn=fetch,
                assess_fn=lambda *a: [], writer_fn=writer,
                auditor_fn=auditor, run_dir=tmp, run_id="prop8",
                overrides={"max_rounds": 6})
            import json
            with open(Path(tmp) / "state.json") as fh:
                st = json.load(fh)
            self.assertEqual(st["config_applied"]["max_rounds"], 6)

    def test_no_change_after_loop_started(self):
        resolved = {"max_rounds": 6, "max_model_calls": 16,
                    "budget": {"queries": 30, "extractions": 120,
                               "time_s": 1800}}
        state = {"rounds": [{"round": 0}], "notes": [],
                 "config_applied": dict(resolved)}
        self.assertFalse(ac._maybe_adopt_proportional_rounds(
            state, resolved, self._plan(11, 5)))
        self.assertEqual(resolved["max_rounds"], 6)


class GapQueryRotationTest(unittest.TestCase):
    def _state(self):
        return {
            "question": "Compare widgets?",
            "plan": {
                "entities": [{"id": "w1", "label": "Widget Alpha"},
                             {"id": "w2", "label": "Widget Beta"}],
                "criteria": [{"id": "c1", "label": "Eixo",
                              "required": True, "per_candidate": True,
                              "applies_to": ["w1", "w2"], "description": "Eixo Eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
            },
            "attempts": {}, "rounds": [],
            "evaluations": [],
            "discovery": {"open": False, "candidates": []},
            "notes": [],
        }

    def _gaps(self):
        return [
            {"criterion_id": "c1", "label": "Eixo", "entity_id": "w1",
             "entity_label": "Widget Alpha", "state": "insufficient",
             "justification": "x", "next": "y"},
            {"criterion_id": "c1", "label": "Eixo", "entity_id": "w2",
             "entity_label": "Widget Beta", "state": "insufficient",
             "justification": "x", "next": "y"},
        ]

    def test_targets_alternate_across_entities(self):
        st = self._state()
        t1 = ac.select_ops(st, self._gaps(), 1)[0]["target"]
        t2 = ac.select_ops(st, self._gaps(), 1)[0]["target"]
        t3 = ac.select_ops(st, self._gaps(), 1)[0]["target"]
        self.assertIn("Alpha", t1, t1)
        self.assertIn("Beta", t2, t2)
        self.assertIn("Alpha", t3, t3)
        self.assertTrue(any("rodízio" in str(n) or "rodizio" in str(n)
                            for n in st.get("notes", [])),
                        st.get("notes"))

    def test_single_entity_keeps_current_behavior(self):
        st = self._state()
        solo = [self._gaps()[0]]
        t1 = ac.select_ops(st, solo, 1)[0]["target"]
        t2 = ac.select_ops(st, solo, 1)[0]["target"]
        self.assertIn("Alpha", t1)
        self.assertIn("Alpha", t2)
        self.assertFalse(any("rodízio" in str(n) or "rodizio" in str(n)
                             for n in st.get("notes", [])),
                         st.get("notes"))


if __name__ == "__main__":
    unittest.main()
