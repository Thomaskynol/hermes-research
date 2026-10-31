#!/usr/bin/env python3
"""Quebra do monopolio single-origin sem sinal de enriquecimento (offline).

Reproduz o modo de falha do accept21: gateway devolve pagina cheia de um
unico host sem transcricao (HTML boilerplate no fetch, sem [transcript]),
e o short-circuit impede SearXNG/ddgs de tentar na mesma op. Com vast DOWN,
o fallback ddgs salvava (accept20); com vast UP degradado, nunca tenta.

Run: python3 -m unittest tests.test_web_monopoly_break -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)

import native_transport as nt  # noqa: E402


class FakeResult:
    def __init__(self, *, status="obtained", qualification="usable", text="",
                 metadata=None, reason=None, ok=True, target="target"):
        self.status = status
        self.status = status
        self.qualification = qualification
        self.text = text
        self.metadata = metadata or {}
        self.reason = reason
        self.ok = ok
        self.target = target


def _monopoly_gateway(query, **kw):
    # 8 hits do mesmo host, sem marcador de transcricao (so descricao-isca).
    return FakeResult(metadata={"results": [
        {"url": f"https://www.youtube.com/watch?v=vid{i:04d}",
         "title": f"Video {i}",
         "snippet": f"Video {i} descricao isca sem conteudo falado"}
        for i in range(8)
    ]})


def _transcript_gateway(query, **kw):
    # Mesmo host, MAS com secao de transcricao no snippet (conteudo real).
    return FakeResult(metadata={"results": [
        {"url": f"https://www.youtube.com/watch?v=vid{i:04d}",
         "title": f"Video {i}",
         "snippet": ("Video {i} descricao\n\n[transcript origin=live lang=en "
                     "automatic=unknown chars=18000 segments=20]\n[spoken 1/20]\n"
                     "fala transcrita do video").format(i=i)}
        for i in range(8)
    ]})


def _single_hit_gateway(query, **kw):
    return FakeResult(metadata={"results": [
        {"url": "https://e.org", "title": "t", "snippet": "s"},
    ]})


def _searxng_down(query, **kw):
    raise RuntimeError("searxng fora (teste)")


def _ddgs_diverse(query, **kw):
    return [{"url": "https://docs.example.org/guide",
             "title": "Guide", "snippet": "guide text",
             "via": "ddgs-fallback"},
            {"url": "https://blog.example.net/post",
             "title": "Post", "snippet": "post text",
             "via": "ddgs-fallback"}]


def _must_not_run(query, **kw):  # pragma: no cover - guarda de short-circuit
    raise AssertionError("fallback must not run for good/single-hit primary")


class MonopolyBreakTest(unittest.TestCase):
    def test_monopoly_without_transcript_tries_fallbacks(self):
        seen = []

        def ddgs(query, **kw):
            seen.append(query)
            return _ddgs_diverse(query, **kw)

        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=_monopoly_gateway,
            searxng_search_fn=_searxng_down,
            web_fallback_fn=ddgs)
        hits = search_fn("opencode plugins review")
        self.assertTrue(seen, "ddgs nunca tentou: short-circuit manteve o monopolio")
        urls = [h["url"] for h in hits]
        self.assertIn("https://docs.example.org/guide", urls)
        self.assertLessEqual(len(hits), nt.SEARCH_LIMIT)
        # Nao pode ser puro single-host: diversidade entrou na mesma op.
        hosts = {u.split("/")[2] for u in urls}
        self.assertGreater(len(hosts), 1)

    def test_transcript_bearing_monopoly_keeps_short_circuit(self):
        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=_transcript_gateway,
            searxng_search_fn=_searxng_down,
            web_fallback_fn=_must_not_run)
        hits = search_fn("q")
        self.assertEqual(len(hits), 8)
        self.assertTrue(all("youtube.com" in h["url"] for h in hits))

    def test_single_hit_short_circuit_preserved(self):
        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=_single_hit_gateway,
            searxng_search_fn=_searxng_down,
            web_fallback_fn=_must_not_run)
        self.assertEqual(search_fn("q"), [{"url": "https://e.org",
                                           "title": "t", "snippet": "s"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
