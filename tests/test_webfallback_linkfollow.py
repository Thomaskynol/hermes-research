#!/usr/bin/env python3
"""Fallback web (ddgs) + link-following github->candidates, offline.

Run: python3 -m unittest tests.test_webfallback_linkfollow -v
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

import adaptive_coordinator as ac  # noqa: E402
import adaptive_state as state_api  # noqa: E402
import native_transport as nt  # noqa: E402
import youtube_transcript as ytmod  # noqa: E402


class FakeResult:
    def __init__(self, *, status="obtained", qualification="usable", text="",
                 metadata=None, reason=None, ok=True, target="target"):
        self.status = status
        self.qualification = qualification
        self.text = text
        self.metadata = metadata or {}
        self.reason = reason
        self.ok = ok
        self.target = target


def _gateway_down(query, **kw):
    return FakeResult(status="unavailable", qualification="none",
                      reason="retriever_unavailable", ok=False)


class WebFallbackTest(unittest.TestCase):
    def test_fallback_serves_when_gateway_fails(self):
        fallback_hits = [{"url": "https://e.org/x", "title": "t",
                          "snippet": "s", "via": "ddgs-fallback"}]
        called = {}

        def fallback(query, **kw):
            called["query"] = query
            return fallback_hits

        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=_gateway_down, web_fallback_fn=fallback)
        self.assertEqual(search_fn("rag"), fallback_hits)
        self.assertEqual(called["query"], "rag")

    def test_primary_wins_fallback_not_called(self):
        def fallback(query, **kw):  # pragma: no cover - must not run
            raise AssertionError("fallback must not run when gateway works")

        def web(query, **kw):
            return FakeResult(metadata={"results": [
                {"url": "https://e.org", "title": "t", "snippet": "s"}]})

        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=web, web_fallback_fn=fallback)
        self.assertEqual(search_fn("q"), [{"url": "https://e.org",
                                           "title": "t", "snippet": "s"}])

    def test_double_failure_names_both_causes(self):
        def fallback(query, **kw):
            raise RuntimeError("no ddgs here")

        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=_gateway_down, web_fallback_fn=fallback)
        with self.assertRaises(Exception) as ctx:
            search_fn("q", "web")
        message = str(ctx.exception)
        self.assertIn("retriever_unavailable", message)
        self.assertIn("fallback failed", message)


class SameRepoLinksTest(unittest.TestCase):
    REPO = "https://github.com/assafelovic/gpt-researcher"

    def test_extracts_same_repo_blob_urls_bounded(self):
        text = ("guia "
                "https://github.com/assafelovic/gpt-researcher/blob/master/README.md e "
                "https://github.com/assafelovic/gpt-researcher/blob/master/docs/PLAN.md e "
                "outro https://github.com/other/repo/blob/main/x.md e "
                "a própria https://github.com/assafelovic/gpt-researcher")
        links = ac._extract_same_repo_links(text, self.REPO)
        self.assertEqual(len(links), 2)
        self.assertTrue(all("assafelovic/gpt-researcher/blob" in link
                            for link in links))

    def test_respects_limit(self):
        text = " ".join(
            f"https://github.com/assafelovic/gpt-researcher/blob/main/f{i}.md"
            for i in range(10))
        self.assertEqual(len(ac._extract_same_repo_links(text, self.REPO)), 4)

    def test_non_github_source_gives_nothing(self):
        self.assertEqual(
            ac._extract_same_repo_links("ver https://example.org/x",
                                        "https://example.org/x"), [])

    def test_incorporate_registers_candidates_when_open(self):
        state = state_api.new_state("linkfollow")
        state["discovery"]["open"] = True
        text = ("guia em "
                "https://github.com/assafelovic/gpt-researcher/blob/master/docs/DEEP.md")
        ac.incorporate(state, self.REPO, text, "op-1", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": text})
        self.assertIn(
            "https://github.com/assafelovic/gpt-researcher/blob/master/docs/DEEP.md",
            state["discovery"]["candidates"])

    def test_incorporate_ignores_links_when_closed(self):
        state = state_api.new_state("linkfollow fechado")
        state["discovery"]["open"] = False
        text = ("guia em "
                "https://github.com/assafelovic/gpt-researcher/blob/master/docs/DEEP.md")
        ac.incorporate(state, self.REPO, text, "op-1", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": text})
        self.assertEqual(state["discovery"]["candidates"], [])

    def test_incorporate_never_duplicates_evidence_or_candidates(self):
        state = state_api.new_state("linkfollow dedupe")
        state["discovery"]["open"] = True
        link = ("https://github.com/assafelovic/gpt-researcher/"
                "blob/master/docs/DEEP.md")
        text = f"guia em {link}"
        qual = {"status": "usable", "excluded": False, "usable_text": text}
        ac.incorporate(state, self.REPO, text, "op-1", 0, qualification=qual)
        ac.incorporate(state, link, "conteúdo do doc", "op-2", 1,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": "conteúdo do doc"})
        self.assertNotIn(link, state["discovery"]["candidates"])
        self.assertEqual(state["discovery"]["candidates"], [])


class YtBestEffortArgvTest(unittest.TestCase):
    """--cookies condicional: sem arquivo tenta sem cookie, nunca declara
    indisponivel sem tentar a rede."""

    def test_argv_without_cookie_file_omits_cookies_flag(self):
        argv = ytmod._ytdlp_argv(
            "https://www.youtube.com/watch?v=x", "en", Path("/tmp"),
            cookies="/caminho/que/nao/existe/cookies.txt")
        self.assertNotIn("--cookies", argv)
        self.assertIn("https://www.youtube.com/watch?v=x", argv)

    def test_argv_with_cookie_file_keeps_cookies_flag(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            argv = ytmod._ytdlp_argv(
                "https://www.youtube.com/watch?v=x", "en", Path("/tmp"),
                cookies=f.name)
        self.assertIn("--cookies", argv)
        self.assertEqual(argv[argv.index("--cookies") + 1], f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
