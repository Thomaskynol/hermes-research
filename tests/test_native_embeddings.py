#!/usr/bin/env python3
"""Boost funcional no path native (8082): _assess_round ranqueia a seleção.

Contrato (accept27; substitui a sonda record-only do accept26):
* base default = EMBEDDING_SERVER_URL ou http://172.17.0.1:8082/v1
  (alcançável do host e do container; nunca só 127.0.0.1);
* modelo default harrier-oss-v1-0.6b;
* cada _assess_round com candidatos vetoriza em 1 batch
  (embed_texts_native) e registra em state["embeddings"] endpoint/modelo/
  tokens/vetores/cache + efeito; avaliações e budgets intactos;
* 8082 down => status unavailable + efeito registrado, sem raise,
  sem fallback silencioso, seleção antiga preservada;
* HERMES_NATIVE_EMBEDDINGS=0 desliga (registrado como skipped);
* manifest carrega o resumo (endpoint/modelo/tokens da última chamada).

Offline: urllib/embed_query_native mockados — nenhum socket real.
Run: python3 -m unittest tests.test_native_embeddings -v
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL = "https://example.org/e1"


def qual(urls):
    return {u: {"status": "usable", "usable_text": "texto util " * 20,
                "excluded": False} for u in urls}


def plan1():
    return {
        "plan_id": "emb-plan", "version": 1,
        "question": "Comparar dois candidatos",
        "entities": [{"id": "e1", "required": True,
                      "discovered": True, "source_url": URL}],
        "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                      "per_candidate": True, "applies_to": ["e1"]}],
        "initial_paths": ["consulta"],
    }


def fake_assess(plan, evidence, qualification, attempts=None):
    return [{"criterion_id": "c1", "entity_id": "e1",
             "state": "partial",
             "justification": "cobre em parte com texto real",
             "origin": "assessor", "references": [{"url": URL}]}]


class TestNativeEmbeddingsProbe(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ["HERMES_NATIVE_EMBEDDINGS"] = "1"
        os.environ.pop("EMBEDDING_SERVER_URL", None)
        self._orig = ac.embed_query_native
        self._orig_texts = ac.embed_texts_native
        ac._EMBED_VEC_CACHE.clear()

    def tearDown(self):
        ac.embed_query_native = self._orig
        ac.embed_texts_native = self._orig_texts
        ac._EMBED_VEC_CACHE.clear()
        os.environ.clear()
        os.environ.update(self._env)

    def _state(self):
        st = state_api.new_state("Comparar dois candidatos")
        st["plan"] = plan1()
        st["evidence"] = {URL: "cand um é comparado aqui. corpo real " * 60}
        st["qualification"] = qual([URL])
        st["rounds"] = [{"round": 0}]
        return st

    def test_default_base_is_bridge_reachable(self):
        self.assertEqual(ac.EMBEDDING_DEFAULT_BASE,
                         "http://172.17.0.1:8082/v1")
        self.assertEqual(ac._embedding_base(), "http://172.17.0.1:8082/v1")

    def test_env_override_wins(self):
        os.environ["EMBEDDING_SERVER_URL"] = "http://10.0.0.9:8082/v1/"
        self.assertEqual(ac._embedding_base(), "http://10.0.0.9:8082/v1")

    def test_assess_round_records_boost_with_tokens(self):
        def fake_embed(texts, **kw):
            return {"endpoint": ac._embedding_base(),
                    "model": "harrier-oss-v1-0.6b",
                    "prompt_tokens": 7, "vectors": [[1.0]] * len(texts),
                    "status": "ok"}

        ac.embed_texts_native = fake_embed
        st = self._state()
        applied, _block = ac._assess_round(
            st, fake_assess, cl.Ledger(st["plan"], run_id=st["run_id"]), None)
        # avaliações intactas (boost só reordena, nunca decide)
        self.assertEqual(applied[0]["state"], "partial")
        calls = st["embeddings"]["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["endpoint"], "http://172.17.0.1:8082/v1")
        self.assertEqual(calls[0]["model"], "harrier-oss-v1-0.6b")
        self.assertEqual(calls[0]["prompt_tokens"], 7)
        self.assertEqual(calls[0]["status"], "ok")
        self.assertIn("effect", calls[0])
        self.assertTrue(any("semantic boost" in n for n in st["notes"]))

    def test_assess_round_down_records_unavailable_without_raise(self):
        def boom(texts, **kw):
            raise ac.TransportError("embeddings indisponível (x): refused")

        ac.embed_texts_native = boom
        st = self._state()
        applied, _block = ac._assess_round(
            st, fake_assess, cl.Ledger(st["plan"], run_id=st["run_id"]), None)
        self.assertEqual(applied[0]["state"], "partial")
        calls = st["embeddings"]["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["status"], "unavailable")
        self.assertIn("effect", calls[0])
        self.assertTrue(any("indispon" in n for n in st["notes"]))

    def test_assess_round_disabled_records_skipped(self):
        os.environ["HERMES_NATIVE_EMBEDDINGS"] = "0"
        called = []
        ac.embed_texts_native = lambda texts, **kw: called.append(texts) or {}
        st = self._state()
        ac._assess_round(st, fake_assess,
                         cl.Ledger(st["plan"], run_id=st["run_id"]), None)
        self.assertEqual(called, [])
        self.assertEqual(st["embeddings"]["status"], "disabled")

    def test_manifest_carries_embeddings_summary(self):
        import run_manifest as mf
        import tempfile, json
        st = state_api.new_state("q")
        st["embeddings"] = {"status": "ok", "calls": [
            {"endpoint": "http://172.17.0.1:8082/v1",
             "model": "harrier-oss-v1-0.6b", "prompt_tokens": 7,
             "status": "ok"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = mf.write_manifest(
                tmp, st, resolved={}, model_info="m",
                environment={"simulated": True}, artifacts=[])
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(payload["embeddings"]["status"], "ok")
        self.assertEqual(payload["embeddings"]["calls"], 1)
        last = payload["embeddings"]["last"]
        self.assertEqual(last["endpoint"], "http://172.17.0.1:8082/v1")
        self.assertEqual(last["model"], "harrier-oss-v1-0.6b")
        self.assertEqual(last["prompt_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
