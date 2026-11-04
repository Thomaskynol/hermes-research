#!/usr/bin/env python3
"""M7 (not_applicable) + M8 (substitution) + M9 (reading metric).

Offline: only coordinator/ledger/planner/renderer (REAL code). Transports
are fakes. Run: python3 -m unittest tests.test_na_swap_reading -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl
import report_renderer as renderer


A = "https://example.org/na/a"
B = "https://example.org/na/b"
C = "https://example.org/na/c"


def qual(urls):
    return {u: {"status": "usable", "usable_text": "texto util " * 20,
                "excluded": False} for u in urls}


def plan2():
    return {
        "plan_id": "na-plan", "version": 1,
        "question": "Comparar dois candidatos",
        "entities": [
            {"id": "e1", "label": "cand um", "required": True,
             "discovered": True, "source_url": A},
            {"id": "e2", "label": "cand dois", "required": True,
             "discovered": True, "source_url": B},
        ],
        "criteria": [
            {"id": "c1", "label": "eixo um", "required": True,
             "per_candidate": True, "applies_to": ["e1", "e2"], "description": "Eixo eixo um: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["consulta"],
    }


class TestNALedger(unittest.TestCase):
    def test_na_excluded_from_denominator(self):
        p = plan2()
        lg = cl.Ledger(p, run_id="r1")
        # Scope exclusion must actually be present in the cited source.
        source_b = "cand dois does not help with eixo um. " + "y" * 500
        q = qual([A, B]); q[B]["usable_text"] = source_b
        lg.set_corpus({A: "x" * 500, B: source_b}, q)
        lg.evaluate("c1", "covered", "cobre e1", "assessor",
                    [{"url": A}], "e1")
        lg.evaluate("c1", "not_applicable", "e2 declara escopo que "
                    "exclui o eixo (fonte do candidato)", "assessor",
                    [{"url": B}], "e2")
        block = lg.compute()
        self.assertEqual(block["numerator"], 1)
        self.assertEqual(block["denominator"], 1)
        self.assertEqual(block["proportion"], 1.0)
        self.assertEqual(block["na"], 1)
        self.assertEqual(len(block["na_cells"]), 1)
        nc = block["na_cells"][0]
        self.assertEqual(
            (nc["criterion_id"], nc["entity_id"]), ("c1", "e2"))
        self.assertIn("justification", nc)
        self.assertIn("references", nc)
        # N/A listed separately, never hidden, never a gap.
        self.assertEqual(block["gaps"], [])
        self.assertTrue(block["complete"])
        self.assertIn("not_applicable", block["definition"])

    def test_na_global_rejected(self):
        p = {"plan_id": "g", "version": 1, "question": "q",
             "entities": [{"id": "e1", "label": "um", "required": True}],
             "criteria": [{"id": "c1", "label": "global", "required": True, "description": "Eixo global: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
             "initial_paths": ["x"]}
        lg = cl.Ledger(p, run_id="r1")
        lg.set_corpus({A: "x" * 500}, qual([A]))
        with self.assertRaises(ValueError):
            lg.evaluate("c1", "not_applicable", "nao cabe", "assessor",
                        [{"url": A}], None)

    def test_na_single_entity_rejected(self):
        p = plan2()
        p["criteria"] = [{"id": "c1", "label": "eixo um", "required": True,
                          "applies_to": ["e1"], "description": "Eixo eixo um: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]
        lg = cl.Ledger(p, run_id="r1")
        lg.set_corpus({A: "x" * 500}, qual([A]))
        with self.assertRaises(ValueError):
            lg.evaluate("c1", "not_applicable", "nao cabe", "assessor",
                        [{"url": A}], "e1")

    def test_na_non_discovered_entity_rejected(self):
        p = plan2()
        p["entities"][1] = {"id": "e2", "label": "cand dois",
                            "required": True}  # not discovered
        lg = cl.Ledger(p, run_id="r1")
        lg.set_corpus({A: "x" * 500, B: "y" * 500}, qual([A, B]))
        with self.assertRaises(ValueError):
            lg.evaluate("c1", "not_applicable", "nao cabe", "assessor",
                        [{"url": B}], "e2")


class TestNACoordinator(unittest.TestCase):
    def _state(self):
        st = state_api.new_state("Comparar dois candidatos")
        st["plan"] = plan2()
        st["evidence"] = {A: "corpo a " * 200, B: "corpo b " * 200}
        st["qualification"] = qual([A, B])
        st["rounds"] = [{"round": 0}, {"round": 1}]
        return st

    def test_na_without_refs_downgraded(self):
        st = self._state()

        def fake_assess(plan, evidence, qualification, attempts=None):
            return [{"criterion_id": "c1", "entity_id": "e2",
                     "state": "not_applicable",
                     "justification": "escopo exclui o eixo",
                     "origin": "assessor", "references": []}]

        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        applied, block = ac._assess_round(st, fake_assess, lg, None)
        self.assertEqual(applied[0]["state"], "insufficient")
        self.assertIn("N/A sem evidência de escopo",
                      applied[0]["justification"])
        self.assertTrue(any("N/A sem evidência de escopo" in n
                            for n in st["notes"]))
        # Downgraded cell stays a gap (never silently covered).
        self.assertTrue(block["gaps"])

    def test_na_with_unresolvable_ref_downgraded(self):
        st = self._state()

        def fake_assess(plan, evidence, qualification, attempts=None):
            return [{"criterion_id": "c1", "entity_id": "e2",
                     "state": "not_applicable",
                     "justification": "escopo exclui o eixo",
                     "origin": "assessor",
                     "references": [{"url": "https://ghost.example/nada"}]}]

        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        applied, block = ac._assess_round(st, fake_assess, lg, None)
        self.assertEqual(applied[0]["state"], "insufficient")
        self.assertIn("N/A sem evidência de escopo",
                      applied[0]["justification"])
        self.assertTrue(block["gaps"])

    def test_assessor_prompt_documents_na(self):
        seen = {}

        def client(prompt):
            seen["prompt"] = prompt
            return "[]"

        assess = ac.make_model_assessor(client)
        st = self._state()
        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        ac._assess_round(st, assess, lg,
                         ac.resolve_adaptive("light",
                                              {"max_model_calls": 8}))
        self.assertIn("not_applicable", seen["prompt"])
        self.assertIn("escopo", seen["prompt"])


class TestSubstitution(unittest.TestCase):
    def _state(self):
        p = plan2()
        p["entities"].append(
            {"id": "e3", "label": "cand tres", "required": False,
             "discovered": True, "source_url": C})
        st = state_api.new_state("Comparar dois candidatos")
        st["plan"] = p
        st["evidence"] = {A: "nada util aqui " * 50,
                          C: "cand tres detalhes do eixo um " * 50}
        st["qualification"] = qual([A, C])
        # Corpo auditado (usable_text) menciona o candidato — a troca
        # exige menção no corpo auditado, nunca só no raw/slug.
        st["qualification"][C] = {
            "status": "usable",
            "usable_text": "cand tres detalhes do eixo um " * 50,
            "excluded": False}
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "e1",
             "state": "insufficient", "justification": "tentativa com fonte",
             "origin": "assessor", "references": [{"url": A}]},
            {"criterion_id": "c1", "entity_id": "e2",
             "state": "insufficient", "justification": "sem evidencia",
             "origin": "assessor", "references": []},
        ]
        st["rounds"] = [{"round": 0}, {"round": 1}]
        return st

    def test_supported_without_dominance_keeps_and_records(self):
        # Contrato 3 (fase F fix-lane): troca exige dominância estrita em
        # _comparative_pairs. e3 tem fonte própria coletada+mencionada mas
        # nenhuma avaliação covered/partial com ref própria — suportado sem
        # dominância — logo não há troca; registra unexplored em vez de
        # sumir silenciosamente. (Antes afirmava a troca; requisito mudou
        # pelo contrato 3 — ver NOTAS.txt da lane; sem commit.)
        st = self._state()
        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        lg.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        for ev in st["evaluations"]:
            lg.evaluate(ev["criterion_id"], ev["state"],
                        ev["justification"], ev["origin"],
                        ev["references"], ev["entity_id"])
        # e2 has no referenced evaluation at all; e3 explored with
        # collected+mentioned source but no own-ref covered/partial, so
        # no dominance pair exists (e2 is the weak candidate here).
        self.assertFalse(ac._maybe_substitute(st, lg))
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(emap["e2"]["required"])
        self.assertFalse(emap["e3"]["required"])
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs, "sem troca deve registrar unexplored")
        # Old stays tracked (explored, in selection).
        self.assertIn("e2", emap)

    def test_no_swap_without_better_evidence(self):
        st = self._state()
        # e3 source never collected: no swap allowed.
        del st["evidence"][C]
        del st["qualification"][C]
        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        lg.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        for ev in st["evaluations"]:
            lg.evaluate(ev["criterion_id"], ev["state"],
                        ev["justification"], ev["origin"],
                        ev["references"], ev["entity_id"])
        self.assertFalse(ac._maybe_substitute(st, lg))
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(emap["e2"]["required"])
        self.assertFalse(emap["e3"]["required"])

    def test_writer_keeps_old_out_of_selection(self):
        seen = {}

        def client(prompt):
            seen["prompt"] = prompt
            return "texto"

        write = ac.make_model_writer(client)
        view = {"question": "q", "plan": plan2(),
                "evidence": {A: "texto " * 100},
                "question_coverage": {"criteria": []}, "stop": {},
                "rounds": [],
                "substitutions": [{"old": "e2", "new": "e3",
                                   "reason": "mais evidência"}]}
        write(view)
        self.assertIn("fora da seleção", seen["prompt"])
        self.assertIn("e2", seen["prompt"])


class TestReading(unittest.TestCase):
    def test_reading_accumulates(self):
        st = state_api.new_state("Comparar dois candidatos")
        st["plan"] = plan2()
        st["evidence"] = {A: "corpo alfa " * 300, B: "corpo beta " * 300}
        st["qualification"] = qual([A, B])

        def client(prompt):
            return "[]"

        assess = ac.make_model_assessor(client)
        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        ac._assess_round(st, assess, lg,
                         ac.resolve_adaptive("light",
                                              {"max_model_calls": 8}))
        reading = st.get("reading") or {}
        self.assertGreater(reading.get("collected_chars", 0), 0)
        self.assertEqual(reading["collected_chars"],
                         len(st["evidence"][A]) + len(st["evidence"][B]))
        self.assertEqual(reading["docs_collected"], 2)
        self.assertGreater(reading.get("excerpted_chars", 0), 0)
        self.assertGreaterEqual(reading.get("docs_excerpted", 0), 1)

    def test_renderer_shows_na_and_reading(self):
        p = plan2()
        lg = cl.Ledger(p, run_id="r1")
        source_b = "cand dois does not help with eixo um. " + "y" * 500
        q = qual([A, B]); q[B]["usable_text"] = source_b
        lg.set_corpus({A: "x" * 500, B: source_b}, q)
        lg.evaluate("c1", "covered", "cobre e1", "assessor",
                    [{"url": A}], "e1")
        lg.evaluate("c1", "not_applicable", "e2 declara escopo que "
                    "exclui o eixo", "assessor", [{"url": B}], "e2")
        st = state_api.new_state("Comparar dois candidatos")
        st["plan"] = p
        st["evidence"] = {A: "x" * 500, B: source_b}
        st["qualification"] = q
        st["question_coverage"] = lg.compute()
        st["reading"] = {"collected_chars": 1000, "excerpted_chars": 400,
                         "docs_collected": 2, "docs_excerpted": 2}
        md = renderer.render_report(st, synthesis_text="síntese")
        self.assertIn("não aplicável", md)
        self.assertIn("Leitura:", md)
        self.assertIn("40.0%", md)
        self.assertIn("saturação de URLs novas ≠ análise esgotada", md)


if __name__ == "__main__":
    unittest.main()
