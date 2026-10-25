#!/usr/bin/env python3
"""Contratos dos transportes nativos (sem gpt_researcher), offline.

Run: python3 -m unittest tests.test_native_transport -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import native_transport as nt  # noqa: E402


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)


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


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SearchChannels(unittest.TestCase):
    def test_academic_maps_works_to_hits(self):
        seen = {}

        def academic(query, **kw):
            seen["query"] = query
            seen.update(kw)
            return FakeResult(metadata={"works": [
                {"title": "T1", "url": "https://example.org/1",
                 "abstract": "A" * 600, "doi": "10.1/x"},
                {"title": "T2", "doi": "10.2/y", "abstract": "short"},
                {"title": "no-url-no-doi"},
            ]})

        search_fn, _, _ = nt.build_native_transports(academic_search_fn=academic)
        hits = search_fn("rag", "academic")
        self.assertEqual(seen, {"query": "rag", "limit": 8, "source": "both"})
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["snippet"], "A" * 500)
        self.assertEqual(hits[1]["url"], "https://doi.org/10.2/y")
        self.assertEqual(set(hits[0]), {"url", "title", "snippet"})

    def test_academic_without_works_is_visible_failure(self):
        search_fn, _, _ = nt.build_native_transports(
            academic_search_fn=lambda q, **kw: FakeResult(
                status="unavailable", qualification="none",
                reason="academic_unavailable", ok=False))
        with self.assertRaises(Exception) as ctx:
            search_fn("q", "academic")
        self.assertIn("academic", str(ctx.exception))

    def test_github_search_uses_api_and_maps_items(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return _Response({"items": [
                {"html_url": "https://github.com/o/r", "full_name": "o/r",
                 "description": "desc"},
                {"html_url": None},
            ]})

        with mock.patch.object(nt, "urlopen", side_effect=fake_urlopen):
            search_fn, _, _ = nt.build_native_transports(
                github_token="tok", timeout=9.0)
            hits = search_fn("deep research", "github")
        request, timeout = requests[0]
        self.assertIn("api.github.com/search/repositories", request.full_url)
        self.assertIn("deep%20research", request.full_url)
        self.assertIn("per_page=8", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer tok")
        self.assertEqual(timeout, 9.0)
        self.assertEqual(hits, [{"url": "https://github.com/o/r",
                                 "title": "o/r", "snippet": "desc"}])

    def test_github_rate_limit_is_honest_error(self):
        error = HTTPError("https://api.github.com", 403, "Forbidden", None, None)
        with mock.patch.object(nt, "urlopen", side_effect=error):
            search_fn, _, _ = nt.build_native_transports()
            with self.assertRaises(Exception) as ctx:
                search_fn("q", "github")
        message = str(ctx.exception)
        self.assertIn("github search failed", message)
        self.assertIn("403", message)

    def test_web_unavailable_raises_with_reason(self):
        # Contrato: quando gateway E fallback falham, o erro nomeia as duas
        # causas. Fallback injetado como falha determinística: o default real
        # (ddgs) depende de pacote/rede do ambiente e não pertence ao teste
        # offline.
        search_fn, _, _ = nt.build_native_transports(
            web_search_fn=lambda q, **kw: FakeResult(
                status="unavailable", qualification="none",
                reason="retriever_unavailable", ok=False),
            web_fallback_fn=lambda q, limit: (_ for _ in ()).throw(
                nt._error("ddgs indisponível (offline)")))
        with self.assertRaises(Exception) as ctx:
            search_fn("q", "web")
        self.assertIn("retriever_unavailable", str(ctx.exception))

    def test_web_maps_results(self):
        def web(query, **kw):
            self.assertEqual(kw, {"limit": 8, "channel": "web"})
            return FakeResult(metadata={"results": [
                {"url": "https://e.org", "title": "t", "snippet": "s"},
                {"title": "no url"},
            ]})

        search_fn, _, _ = nt.build_native_transports(web_search_fn=web)
        self.assertEqual(search_fn("q"), [{"url": "https://e.org",
                                           "title": "t", "snippet": "s"}])

    def test_unknown_channel_is_explicit(self):
        search_fn, _, _ = nt.build_native_transports()
        with self.assertRaises(Exception) as ctx:
            search_fn("q", "youtube")
        self.assertIn("unavailable", str(ctx.exception))

    def test_describe_reports_channels_and_limits(self):
        search_fn, fetch_fn, _ = nt.build_native_transports()
        desc = search_fn.describe()
        self.assertEqual(desc["kind"], "native")
        self.assertEqual(set(desc["channels"]), {"web", "academic", "github"})
        self.assertIn("web_depends_on_local_retriever", desc["limits"])
        self.assertIs(fetch_fn.describe, search_fn.describe)


class FetchDispatch(unittest.TestCase):
    def setUp(self):
        self.work = mock.Mock(return_value=FakeResult(
            text="paper text", qualification="usable", target="arxiv"))
        self.repo = mock.Mock(return_value=FakeResult(
            text="readme text", qualification="partial", target="repo"))
        self.page = mock.Mock(return_value=FakeResult(
            text="page text", qualification="usable", target="page"))
        patcher = mock.patch.multiple(
            nt, _read_work=self.work, _read_repo=self.repo, _read_page=self.page)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_arxiv_dispatches_to_read_work(self):
        _, fetch_fn, _ = nt.build_native_transports(timeout=4.0)
        payload = fetch_fn("https://arxiv.org/abs/2401.00001")
        self.work.assert_called_once_with("https://arxiv.org/abs/2401.00001",
                                          timeout=4.0)
        self.repo.assert_not_called()
        self.assertEqual(payload, {"text": "paper text", "status": "usable",
                                   "reason": "", "usable_text": "paper text",
                                   "excluded": False})

    def test_github_dispatches_to_read_repo_without_token_kwarg(self):
        # Contrato real: agent_reach.read_repo(url, timeout, transport) não
        # aceita token (usa GITHUB_TOKEN do env). Regressão RAG_003: o
        # transporte passava token= e toda leitura de repo falhava.
        _, fetch_fn, _ = nt.build_native_transports(github_token="tok")
        payload = fetch_fn("https://github.com/o/r")
        self.repo.assert_called_once_with("https://github.com/o/r",
                                          timeout=nt.DEFAULT_TIMEOUT_S)
        self.page.assert_not_called()
        self.assertEqual(payload["status"], "partial")
        self.assertFalse(payload["excluded"])

    def test_other_urls_dispatch_to_read_page_with_injected_transport(self):
        page_transport = object()
        _, fetch_fn, _ = nt.build_native_transports(page_transport=page_transport)
        payload = fetch_fn("https://example.org/a")
        self.page.assert_called_once_with("https://example.org/a",
                                          timeout=nt.DEFAULT_TIMEOUT_S,
                                          transport=page_transport)
        self.assertEqual(payload["usable_text"], "page text")

    def test_failed_fetch_is_visible(self):
        self.page.return_value = FakeResult(
            status="failed", qualification="none", text="HTTP 403 Forbidden",
            reason="access_failure", ok=False)
        _, fetch_fn, _ = nt.build_native_transports()
        with self.assertRaises(Exception) as ctx:
            fetch_fn("https://example.org/a")
        self.assertIn("access_failure", str(ctx.exception))

    def test_metadata_only_is_never_usable_text(self):
        self.work.return_value = FakeResult(
            status="partial", qualification="metadata_only", text="",
            reason="full_text_unavailable")
        _, fetch_fn, _ = nt.build_native_transports()
        payload = fetch_fn("https://arxiv.org/abs/2401.00001")
        self.assertEqual(payload["usable_text"], "")
        self.assertTrue(payload["excluded"])
        self.assertEqual(payload["status"], "empty")
        self.assertIn("full_text_unavailable", payload["reason"])

    def test_payload_is_coerce_compatible(self):
        _, fetch_fn, _ = nt.build_native_transports()
        payload = fetch_fn("https://example.org/a")
        self.assertEqual(set(payload), {"text", "status", "reason",
                                        "usable_text", "excluded"})


class Isolation(unittest.TestCase):
    def test_module_never_imports_gpt_researcher(self):
        code = ("import sys; sys.path.insert(0, %r); import native_transport; "
                "assert 'gpt_researcher' not in sys.modules, 'imported'; "
                "print('ok')" % str(ROOT))
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
