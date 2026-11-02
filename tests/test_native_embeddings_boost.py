#!/usr/bin/env python3
"""Boost semântico no path native: embeddings 8082 ranqueiam a seleção.

Contrato (accept27):
* base default http://172.17.0.1:8082/v1, modelo harrier-oss-v1-0.6b;
* _assess_round ranqueia candidatos por similaridade à pergunta+lacunas
  via embed_texts_native (batch, 1 chamada) e entrega ao assessor pelo
  hook opcional set_semantic_rank (custom sem hook: inalterado);
* boost SÓ reordena (reservas/gates intactos): doc de entidade errada
  continua impedido de sustentar (_evaluation_refs_have_identity);
* cache por hash de conteúdo: 2ª rodada sem mudança = 0 chamadas;
* down = unavailable + efeito, sem raise, sem fallback, seleção antiga;
* HERMES_NATIVE_EMBEDDINGS=0 desliga (sem chamada, seleção antiga);
* embeddings nunca gastam budget de modelo (consumption intacto);
* writer usa a ordem no restante (refs/piso intactos);
* manifest separa consumo de embeddings das chamadas ao gerador.

Fixtures genéricas (Widget Alfa/Bravo); sem nomes de produtos.
Offline: embed_texts_native sempre mockado + guarda anti-socket.

Run: python3 -m unittest tests.test_native_embeddings_boost -v
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL_D1 = "https://example.org/alfa-overview"
URL_D2 = "https://example.org/bravo-install"
URL_D3 = "https://example.org/alfa-quickstart"

# D1: nomeia Alfa muitas vezes, sem resposta do critério.
T_D1 = ("Widget Alfa Widget Alfa overview. Widget Alfa is a widget. "
        "Widget Alfa does things. ") * 20
# D2: doc parecido (instalação) mas de OUTRA entidade (Bravo).
T_D2 = ("Widget Bravo installation: run npm install bravo-widget "
        "to install Widget Bravo. ") * 20
# D3: nomeia Alfa + responde o critério (instalação); por último na ordem.
T_D3 = ("Widget Alfa quickstart: to install Widget Alfa run "
        "npm install alfa-widget in your project. ") * 20


def plan1():
    return {
        "plan_id": "boost-plan", "version": 1,
        "question": "How to install Widget Alfa?",
        "entities": [{"id": "e1", "label": "Widget Alfa", "required": True}],
        "criteria": [{"id": "c1", "label": "installation", "required": True,
                      "per_candidate": True, "applies_to": ["e1"], "description": "Eixo installation: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        "initial_paths": ["consulta"],
    }


def qual_all():
    return {u: {"status": "usable", "usable_text": t, "excluded": False}
            for u, t in ((URL_D1, T_D1), (URL_D2, T_D2), (URL_D3, T_D3))}


def client_for_eval(evaluation):
    def _client(prompt):
        return json.dumps([evaluation])
    return _client


EVAL_COVERS_D3 = {
    "criterion_id": "c1", "entity_id": "e1", "state": "covered",
    "justification": "quickstart documents the install command",
    "origin": "test-client", "references": [{"url": URL_D3}],
}
EVAL_COVERS_D2_WRONG = {
    "criterion_id": "c1", "entity_id": "e1", "state": "covered",
    "justification": "install documented here",
    "origin": "test-client", "references": [{"url": URL_D2}],
}


class BoostBase(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ["HERMES_NATIVE_EMBEDDINGS"] = "1"
        os.environ.pop("EMBEDDING_SERVER_URL", None)
        self._orig_texts = ac.embed_texts_native
        self._orig_query = ac.embed_query_native
        ac._EMBED_VEC_CACHE.clear()
        self.server_calls = []

    def tearDown(self):
        ac.embed_texts_native = self._orig_texts
        ac.embed_query_native = self._orig_query
        ac._EMBED_VEC_CACHE.clear()
        os.environ.clear()
        os.environ.update(self._env)

    def _state(self):
        st = state_api.new_state("How to install Widget Alfa?")
        st["plan"] = plan1()
        st["evidence"] = {URL_D1: T_D1, URL_D2: T_D2, URL_D3: T_D3}
        st["qualification"] = qual_all()
        st["rounds"] = [{"round": 0}]
        return st

    def _assess(self, st, evaluation, max_docs=2):
        assess = ac.make_model_assessor(client_for_eval(evaluation),
                                        max_docs=max_docs)
        return ac._assess_round(
            st, assess, cl.Ledger(st["plan"], run_id=st["run_id"]), None)


class TestSemanticRerank(BoostBase):
    def test_recovers_doc_old_selection_missed(self):
        # Ordem semântica [D3, D2, D1]: D3 entra na seleção e sustenta.
        ac.embed_texts_native = self._ranked_fake([URL_D3, URL_D2, URL_D1])
        st = self._state()
        applied, _block = self._assess(st, EVAL_COVERS_D3)
        sel = ac._last_sel_urls(st)
        self.assertEqual(sel, [URL_D1, URL_D3])  # reserva + recuperado
        self.assertEqual(applied[0]["state"], "covered")
        self.assertEqual(applied[0]["references"], [{"url": URL_D3}])
        self.assertEqual(len(self.server_calls), 1)  # 1 batch p/ rodada

    def test_disabled_keeps_old_selection(self):
        os.environ["HERMES_NATIVE_EMBEDDINGS"] = "0"
        ac.embed_texts_native = self._boom("must not be called")
        st = self._state()
        applied, _block = self._assess(st, EVAL_COVERS_D3)
        # seleção antiga [D1, D2]: D3 fora -> covered cai (insuficiência
        # preservada, nunca fabricada).
        self.assertEqual(ac._last_sel_urls(st), [URL_D1, URL_D2])
        self.assertEqual(applied, [])
        self.assertEqual(st["embeddings"]["status"], "disabled")

    def test_down_falls_back_without_raise(self):
        ac.embed_texts_native = self._boom("embeddings down")
        st = self._state()
        applied, _block = self._assess(st, EVAL_COVERS_D3)
        self.assertEqual(ac._last_sel_urls(st), [URL_D1, URL_D2])
        self.assertEqual(applied, [])
        rec = st["embeddings"]
        self.assertEqual(rec["status"], "unavailable")
        self.assertIn("effect", rec["calls"][-1])
        self.assertTrue(any("indispon" in n for n in st["notes"]))

    def test_wrong_entity_doc_never_sustains(self):
        # D2 em 1º no rank semântico: entra na seleção mas NÃO sustenta e1.
        ac.embed_texts_native = self._ranked_fake([URL_D2, URL_D1, URL_D3])
        st = self._state()
        applied, _block = self._assess(st, EVAL_COVERS_D2_WRONG)
        self.assertIn(URL_D2, ac._last_sel_urls(st))  # boost não filtra
        self.assertEqual(applied, [])  # gate de identidade rejeita
        self.assertTrue(any("identity mismatch" in n for n in st["notes"]))

    def test_cache_avoids_recompute(self):
        # 2ª rodada, mesmo plano + mesmo corpus => 0 chamadas novas
        # (tudo do cache), mesmo rerank e avaliações preservadas.
        ac.embed_texts_native = self._ranked_fake([URL_D3, URL_D2, URL_D1])
        st = self._state()
        self._assess(st, EVAL_COVERS_D3)
        n_calls = len(self.server_calls)
        self.assertGreater(n_calls, 0)
        applied, _block = self._assess(st, EVAL_COVERS_D3)
        self.assertEqual(len(self.server_calls), n_calls)  # 0 novas
        # célula fechada libera a reserva: seleção segue a ordem semântica
        # nos não-enviados; D3 segue sustentando (gates intactos).
        self.assertEqual(ac._last_sel_urls(st), [URL_D3, URL_D2])
        totals = st["embeddings"]["totals"]
        self.assertGreater(totals["cache_hits"], 0)
        self.assertEqual(applied[0]["state"], "covered")

    def test_no_model_budget_spent(self):
        ac.embed_texts_native = self._ranked_fake([URL_D3, URL_D2, URL_D1])
        st = self._state()
        before = int(st["consumption"]["model_calls"])
        ac._assess_round(st, ac._default_assess,
                         cl.Ledger(st["plan"], run_id=st["run_id"]), None)
        self.assertEqual(int(st["consumption"]["model_calls"]), before)
        self.assertGreater(len(st["embeddings"]["calls"]), 0)

    def test_offline_never_touches_socket(self):
        import socket as _sio
        ac.embed_texts_native = self._ranked_fake([URL_D3, URL_D2, URL_D1])
        st = self._state()
        _orig = _sio.socket
        def _boom(*a, **k):
            raise AssertionError("socket real usado em teste offline")
        _sio.socket = _boom
        try:
            applied, _block = self._assess(st, EVAL_COVERS_D3)
        finally:
            _sio.socket = _orig
        self.assertEqual(applied[0]["state"], "covered")

    # -- helpers de rank controlado ------------------------------------
    def _ranked_fake(self, rank):
        """Vetores reais na forma: query=[1,0]; doc score por posição."""
        pos = {u: i for i, u in enumerate(rank)}
        frags = {URL_D1: "does things", URL_D2: "bravo-widget",
                 URL_D3: "alfa-widget"}

        def _fake(texts, **kw):
            self.server_calls.append(list(texts))
            vecs = []
            for t in texts:
                best_i = None
                for u in rank:
                    if frags[u] in (t or ""):
                        best_i = pos[u]
                        break
                if best_i is None:
                    vecs.append([1.0, 0.0])  # query (sem frag de doc)
                else:
                    # cosseno decrescente com a posição no rank
                    vecs.append([1.0 - 0.3 * best_i, 0.3 * best_i])
            return {"endpoint": ac._embedding_base(),
                    "model": "harrier-oss-v1-0.6b",
                    "prompt_tokens": 3 * len(texts),
                    "vectors": vecs, "status": "ok"}
        return _fake

    def _boom(self, msg):
        def _fake(texts, **kw):
            raise ac.TransportError(f"embeddings indisponível (x): {msg}")
        return _fake


class TestCosineAndBatch(unittest.TestCase):
    def test_cosine_basics(self):
        self.assertAlmostEqual(ac._cosine([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(ac._cosine([1, 0], [0, 1]), 0.0)
        self.assertEqual(ac._cosine([1, 0], [0, 0]), 0.0)

    def test_batch_parses_vectors_by_index(self):
        import urllib.request as _url
        import io

        body = json.dumps({
            "model": "harrier-oss-v1-0.6b",
            "usage": {"prompt_tokens": 7},
            "data": [{"index": 1, "embedding": [0.0, 1.0]},
                     {"index": 0, "embedding": [1.0, 0.0]}]}).encode()

        class _Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return body

        _orig = _url.urlopen
        _url.urlopen = lambda req, timeout=None: _Resp()
        try:
            got = ac.embed_texts_native(["aa", "bb"])
        finally:
            _url.urlopen = _orig
        self.assertEqual(got["vectors"], [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(got["prompt_tokens"], 7)
        self.assertEqual(got["model"], "harrier-oss-v1-0.6b")

    def test_batch_down_raises_transport(self):
        import urllib.request as _url
        import urllib.error as _err
        _orig = _url.urlopen
        _url.urlopen = lambda req, timeout=None: (_ for _ in ()).throw(
            _err.URLError("refused"))
        try:
            with self.assertRaises(ac.TransportError):
                ac.embed_texts_native(["aa"])
        finally:
            _url.urlopen = _orig


class TestWriterUsesRank(unittest.TestCase):
    def test_rest_follows_semantic_rank_refs_intact(self):
        import adaptive_coordinator as _ac
        _ac._EMBED_VEC_CACHE.clear()
        plan = plan1()
        ev = {URL_D1: T_D1, URL_D2: T_D2, URL_D3: T_D3,
              "https://example.org/extra": "unrelated filler " * 50}
        cov = {"criteria": [{"id": "c1",
                             "references": [{"url": URL_D3}]}]}
        view = {"question": plan["question"], "plan": plan,
                "evidence": dict(ev), "question_coverage": cov,
                "evaluations": [dict(EVAL_COVERS_D3)],
                "semantic_rank": [URL_D3, URL_D2, URL_D1,
                                  "https://example.org/extra"]}
        write = _ac.make_model_writer(lambda prompt: ("", {}),
                                      max_chars=200000)
        _text, sel = write(view)
        urls = sel["included_urls"]
        self.assertIn(URL_D3, urls)  # ref preservada
        # piso de identidade (Alfa) antes do restante; restante sem refs
        # empatadas segue o rank: extra por último não; D2 antes de D1.
        self.assertLess(urls.index(URL_D2), urls.index(URL_D1))


class TestManifestTotals(unittest.TestCase):
    def test_manifest_separates_embedding_consumption(self):
        import run_manifest as mf
        import tempfile
        st = state_api.new_state("q")
        st["embeddings"] = {
            "status": "ok",
            "calls": [{"endpoint": "http://172.17.0.1:8082/v1",
                       "model": "harrier-oss-v1-0.6b", "prompt_tokens": 12,
                       "status": "ok", "vectors": 4, "cache_hits": 1}],
            "totals": {"server_calls": 1, "vectors": 4,
                       "prompt_tokens": 12, "cache_hits": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            path = mf.write_manifest(
                tmp, st, resolved={}, model_info="m",
                environment={"simulated": True}, artifacts=[])
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        emb = payload["embeddings"]
        self.assertEqual(emb["status"], "ok")
        self.assertEqual(emb["server_calls"], 1)
        self.assertEqual(emb["vectors"], 4)
        self.assertEqual(emb["prompt_tokens_total"], 12)
        self.assertNotIn("model_calls", emb)  # gerador separado


if __name__ == "__main__":
    unittest.main()
