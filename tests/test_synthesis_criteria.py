"""Answer-form criteria are assessed against the synthesis, not excerpts (S1).

A criterion flagged "synthesis": true (e.g. 'separate documented features
from inferences') can never be satisfied by an excerpt: the excerpt-based
assessor always - and correctly - reports insufficient. When the delivered
synthesis visibly separates documented/inferred/gap material AND cites real
corpus sources, the cell becomes partial (never covered).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("synthesis criteria test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL = "https://example.org/plugin-doc"


def qual(text):
    return {"status": "usable", "excluded": False, "usable_text": text}


def synth_state():
    st = state_api.new_state("synthesis form")
    st["plan"] = {
        "plan_id": "s1", "version": 1,
        "entities": [{"id": "e0", "label": "Alvo", "required": True}],
        "criteria": [
            {"id": "c0", "label": "funciona", "required": True,
             "applies_to": ["e0"], "description": "Eixo funciona: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c1", "label": "separar documentado de inferido",
             "required": True, "synthesis": True, "description": "Eixo separar documentado de inferido: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
        "initial_paths": ["q"]}
    st["evidence"] = {URL: "the plugin supports planning with MIT license"}
    st["qualification"] = {URL: qual("the plugin supports planning")}
    return st


GOOD_TEXT = (
    "DOCUMENTADO: o plugin planeja (fonte %s). "
    "INFERÊNCIA: deve escalar. LACUNA: custos não informados." % URL)


class SynthesisCriteriaTest(unittest.TestCase):
    def test_marcadores_e_citacao_viram_parcial(self):
        st = synth_state()
        led = cl.Ledger(st["plan"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        out = ac._assess_synthesis_criteria(st, block, GOOD_TEXT)
        self.assertIsNotNone(out)
        row = {c["id"]: c for c in out["criteria"]}["c1"]
        self.assertEqual(row["state"], "partial")
        self.assertNotEqual(row["state"], "covered")
        self.assertTrue(any(e.get("criterion_id") == "c1"
                            and e.get("origin") == "synthesis"
                            for e in st["evaluations"]))
        # Global criterion untouched.
        self.assertEqual({c["id"]: c for c in out["criteria"]}["c0"]["state"],
                         block["criteria"][0]["state"])

    def test_sem_marcadores_nada_muda(self):
        st = synth_state()
        led = cl.Ledger(st["plan"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        out = ac._assess_synthesis_criteria(
            st, block, "O plugin e bom, veja %s." % URL)
        self.assertIsNone(out)

    def test_sem_citacao_do_corpus_nada_muda(self):
        st = synth_state()
        led = cl.Ledger(st["plan"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        out = ac._assess_synthesis_criteria(
            st, block, "DOCUMENTADO: x. INFERÊNCIA: y. LACUNA: z. "
                       "Fonte https://fora.example/nada.")
        self.assertIsNone(out)

    def test_planner_marca_criterio_de_forma(self):
        import adaptive_planner as planner
        prompt = planner.build_plan_prompt(
            "Diferencie funcionalidades documentadas de inferencias")
        self.assertIn("synthesis", prompt)

    def test_url_em_code_span_conta_como_citacao(self):
        # accept14: o writer cita fontes entre backticks
        # (`https://...`); o extrator deve reconhecê-las.
        st = synth_state()
        led = cl.Ledger(st["plan"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        out = ac._assess_synthesis_criteria(
            st, block,
            "DOCUMENTADO: o plugin planeja (fonte `%s`). "
            "INFERÊNCIA: deve escalar. LACUNA: custos." % URL)
        self.assertIsNotNone(out)
        row = {c["id"]: c for c in out["criteria"]}["c1"]
        self.assertEqual(row["state"], "partial")


if __name__ == "__main__":
    unittest.main()
