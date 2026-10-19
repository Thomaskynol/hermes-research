#!/usr/bin/env python3
"""Single-execution end-to-end + channel via the REAL adapter (S05 item 5).

- UMA execução: coleta parcial -> avaliação real (parser/assessor de
  aplicação, modelo simulado SÓ no transporte) -> op direcionada -> nova
  evidência -> nova avaliação -> cobertura atualizada. O coordenador e o
  assessor/writer reais nunca são substituídos por avaliações prontas.
- Canal testado no adaptador real (build_adaptive_transports), não no fake:
  busca web restrita a site identificada como tal, sem alegar API/conector
  não chamado.
Offline: rede bloqueada; transportes externos substituídos/bloqueados.
"""
import asyncio
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import gpt_researcher_integration as entry


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)

U1 = "https://example.org/single/u1"
U2 = "https://example.org/single/u2"


def base_plan():
    return {
        "plan_id": "single-run", "version": 1,
        "entities": [{"id": "e0", "required": True},
                     {"id": "e1", "required": True}],
        "criteria": [{"id": "c0", "label": "c0", "required": True,
                      "applies_to": ["e0"]},
                     {"id": "c1", "label": "c1", "required": True,
                      "applies_to": ["e1"]}],
        "initial_paths": ["single query"],
    }


class FakeModelTransport:
    """Só o transporte do modelo é simulado; assessor/writer são reais."""

    def __init__(self):
        self.calls = []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "Você avalia evidências" in prompt:
            evals = []
            # o assessor real embute excertos; marcadores no corpus viram
            # avaliações (parser/validação reais no assessor).
            if "COVER:c0" in prompt:
                url = U1 if U1 in prompt else U2
                evals.append({"criterion_id": "c0", "state": "covered",
                              "justification": "marker c0 no corpus",
                              "origin": "transport simulation",
                              "references": [{"url": url}]})
            if "COVER:c1" in prompt:
                url = U2 if U2 in prompt else U1
                evals.append({"criterion_id": "c1", "state": "covered",
                              "justification": "marker c1 no corpus",
                              "origin": "transport simulation",
                              "references": [{"url": url}]})
            return json.dumps(evals)
        if "Responda em português" in prompt:
            cited = [u for u in (U1, U2) if u in prompt]
            lines = ["# Resposta em português", "",
                     "Síntese do corpus selecionado."]
            for u in cited:
                lines.append(f"- evidência em {u}")
            return "\n".join(lines)
        return json.dumps(base_plan())


class SingleRun(unittest.TestCase):
    def test_partial_then_directed_op_updates_coverage_in_one_run(self):
        plan = base_plan()
        model = FakeModelTransport()
        calls = {"n": 0}

        def search(target, channel="web"):
            calls["n"] += 1
            if calls["n"] == 1:
                return [{"url": U1}]
            if calls["n"] == 2:
                return [{"url": U2}]
            return []

        def fetch(url):
            if url == U1:
                return "partial note COVER:c0"
            if url == U2:
                return "directed note COVER:c1"
            return "empty"

        res = entry.adaptive_entry(
            question="Single run demo", profile="light", plan=plan,
            model_transport=model, search_transport=search,
            fetch_transport=fetch, clock=lambda: 0.0,
            overrides={"max_rounds": 3, "max_model_calls": 20})
        # UMA execução, várias rodadas: cobertura final completa após a op
        # direcionada trazer a nova evidência e o assessor real reavaliar.
        self.assertGreaterEqual(len(res["rounds"]), 2, str(res["rounds"]))
        self.assertTrue(res["question_coverage"]["complete"],
                        json.dumps(res["question_coverage"])[:800])
        self.assertEqual(res["question_coverage"]["proportion"], 1.0)
        self.assertFalse(res["partial"])
        # writer real em PT a partir do corpus selecionado
        self.assertIn("Resposta em português", res["report"]["text"])
        self.assertFalse(res["report"]["selection"].get("fallback", False))

    def test_runtime_config_coherence_validated(self):
        import tempfile, json as _json
        from pathlib import Path as _P
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _P(tmp) / "config.json"
            cfg.write_text(_json.dumps({"SMART_LLM": "openrouter:x"}),
                           encoding="utf-8")
            with unittest.mock.patch.dict("os.environ",
                                          {"SMART_LLM": "openrouter:y"}):
                notes = entry._validate_runtime_config(str(cfg), {})
                self.assertTrue(any("diverge" in n for n in notes),
                                str(notes))

    def test_youtube_textual_preserved_without_asr(self):
        # Adaptador de leitura preserva YouTube textual (descrição/transcrito
        # parcial); sem ASR nem conectores duplicados.
        _, q1 = ac._coerce_payload("[description] trailer do vídeo",
                                   "https://www.youtube.com/watch?v=abc123")
        self.assertFalse(q1["excluded"], str(q1))
        _, q2 = ac._coerce_payload("[spoken 1/2] fala transcrita",
                                   "https://www.youtube.com/watch?v=abc123")
        self.assertFalse(q2["excluded"], str(q2))
        self.assertEqual(q2["status"], "partial", str(q2))
        import youtube_transcript as _yt
        self.assertTrue(hasattr(_yt, "fetch_transcript"))
        self.assertFalse(any("whisper" in n.lower() or "asr" in n.lower()
                             for n in dir(_yt)), str(dir(_yt)))

    def test_channel_uses_real_adapter_with_site_restriction(self):
        seen = []

        class StubResearcher:
            context = "Source: https://example.org/sweep/x\nsweep text"

            async def conduct_research(self):
                return None

            async def quick_search(self, query):
                seen.append(query)
                return [{"url": U1, "title": "t", "content": "c"}]

            cfg = object()

        search_fn, _, _ = entry.build_adaptive_transports(StubResearcher())
        # primeira chamada = varredura (sweep), sem quick_search
        first = search_fn("q", "web")
        self.assertTrue(any("example.org" in h["url"] for h in first))
        self.assertEqual(seen, [])
        # segunda chamada github = busca web restrita a site via quick_search
        hits = search_fn("some gap query", "github")
        self.assertEqual(len(seen), 1)
        self.assertIn("site:github.com", seen[0],
                      f"canal github deve usar busca restrita a site: {seen}")
        self.assertTrue(any(h["url"] == U1 for h in hits))
        # canais indisponíveis: erro explícito, nunca rótulo silencioso
        with self.assertRaises(ac.TransportError):
            search_fn("q", "inexistente")


if __name__ == "__main__":
    unittest.main(verbosity=2)
