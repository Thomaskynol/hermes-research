#!/usr/bin/env python3
"""Contratos do Agent Reach (operações individuais), offline por padrão.

Transportes são injetados; a rede real é bloqueada por audithook. Os testes
opt-in de rede usam HERMES_REAL_NETWORK=1 e são pulados por padrão.

Run: python3 -m unittest tests.test_agent_reach -v
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_reach as ar  # noqa: E402


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


if os.environ.get("HERMES_REAL_NETWORK") != "1":
    sys.addaudithook(deny_network)

REQUIRED_FIELDS = {
    "ok", "operation", "target", "title", "text", "chars", "channel",
    "obtained_at", "status", "qualification", "reason", "http_status",
    "metadata", "limits", "evidence",
}


def assert_contract(case: unittest.TestCase, payload: dict) -> None:
    """O contrato completo vale nos seis caminhos, sem campo extra/faltando."""
    case.assertEqual(set(payload), REQUIRED_FIELDS)
    case.assertIsInstance(payload["ok"], bool)
    case.assertIsInstance(payload["operation"], str)
    case.assertIsInstance(payload["target"], str)
    case.assertIsInstance(payload["title"], str)
    case.assertIsInstance(payload["text"], str)
    case.assertEqual(payload["chars"], len(payload["text"]))
    case.assertIsInstance(payload["channel"], str)
    case.assertIn(payload["status"], ar.STATUSES)
    case.assertIn(payload["qualification"], ar.QUALIFICATIONS)
    case.assertTrue(payload["reason"] is None or isinstance(payload["reason"], str))
    case.assertTrue(payload["http_status"] is None or isinstance(payload["http_status"], int))
    case.assertIsInstance(payload["metadata"], dict)
    case.assertIsInstance(payload["limits"], list)
    case.assertIsInstance(payload["evidence"], dict)
    # obtained_at é UTC ISO de verdade, não string decorativa.
    parsed = datetime.fromisoformat(payload["obtained_at"].replace("Z", "+00:00"))
    case.assertEqual(parsed.utcoffset().total_seconds(), 0)


def json_transport(payload, status=200):
    def _transport(url, timeout):
        return {"status": status, "text": json.dumps(payload), "error": None, "url": url}
    return _transport


def page_payload(text, *, level=1, http_status=None, reason=None, from_cache=False):
    payload = {"status": None, "text": text, "level": level,
               "from_cache": from_cache, "reason": reason, "error": None}
    if http_status is not None:
        payload["http_status"] = http_status
    return payload


def repo_bundle(*, readme="", readme_status=None, readme_reason=None,
                repo=None, repo_status=200, releases=None, files=None):
    return {
        "readme": {"text": readme, "chars": len(readme),
                   "http_status": readme_status, "source_url": "https://raw.example/README.md",
                   "reason": readme_reason},
        "repo": {"status": repo_status, "text": json.dumps(repo or {}), "error": None},
        "releases": {"status": 200, "text": json.dumps(releases or []), "error": None},
        "files": {"status": 200, "text": json.dumps(files or []), "error": None},
    }


REPO_JSON = {
    "full_name": "assafelovic/gpt-researcher",
    "description": "research agent",
    "default_branch": "master",
    "stargazers_count": 23000,
    "language": "Python",
    "license": {"spdx_id": "Apache-2.0", "name": "Apache License 2.0"},
    "pushed_at": "2026-10-01T00:00:00Z",
}


class ContractTests(unittest.TestCase):
    def test_six_paths_share_the_contract(self):
        search = ar.search("q", transport=json_transport([
            {"url": "https://a.example", "title": "A", "raw_content": "snippet", "source": "github"},
        ]))
        page = ar.read_page("https://a.example", transport=lambda u, t: page_payload("conteudo " * 100))
        repo = ar.read_repo("https://github.com/assafelovic/gpt-researcher",
                            transport=lambda u, t: repo_bundle(readme="# R\n" + "texto " * 100, repo=REPO_JSON))
        video = ar.read_video("https://www.youtube.com/watch?v=x",
                              transport=lambda u, l, t: {"text": "fala " * 200, "lang": "en",
                                                         "chars": 1000, "segments": 5,
                                                         "method": "live", "automatic": False,
                                                         "reason": None})
        import academic_search as ac
        academic = ac.search_works("q", transport=json_transport({"results": [
            {"id": "https://openalex.org/W1", "title": "T", "abstract_inverted_index": {"a": [0]}},
        ]}))
        work = ac.read_work("10.1234/x", transport=json_transport({
            "id": "https://openalex.org/W1", "title": "T",
            "abstract_inverted_index": {"a": [0]},
        }))
        for result in (search, page, repo, video, academic, work):
            with self.subTest(operation=result.operation):
                assert_contract(self, result.to_dict())
                self.assertIn(result.operation,
                              {"search", "read_page", "read_repo", "read_video",
                               "academic_search", "read_work"})
                self.assertIn(result.channel,
                              {"web", "github", "youtube", "academic", "openalex", "arxiv"})

    def test_failure_does_not_raise(self):
        result = ar.search("q", transport=lambda u, t: {"status": None, "text": "",
                                                        "error": "URLError: refused"})
        assert_contract(self, result.to_dict())
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ar.STATUS_FAILED)


class SearchTests(unittest.TestCase):
    def test_identified_results_with_engine_when_observed(self):
        items = [
            {"url": "https://github.com/a/b", "title": "repo", "raw_content": "x" * 900, "source": "github"},
            {"url": "https://youtube.com/watch?v=1", "title": "video", "raw_content": "y" * 400, "source": "youtube"},
            {"title": "sem url", "raw_content": "ignorado", "source": "github"},
        ]
        result = ar.search("gpt researcher", limit=5, transport=json_transport(items))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ar.QUAL_METADATA)
        self.assertEqual(result.metadata["returned_count"], 2)
        first = result.metadata["results"][0]
        self.assertEqual(first["url"], "https://github.com/a/b")
        self.assertEqual(first["engine"], "github")
        self.assertEqual(first["content_chars"], 900)
        self.assertLessEqual(len(first["snippet"]), ar.SEARCH_SNIPPET_CHARS)
        self.assertEqual(result.text, "", "busca não lê página")
        self.assertEqual(result.chars, 0)
        self.assertEqual(result.http_status, 200, "status 200 foi observado no transporte")

    def test_channel_filter_uses_observed_source(self):
        items = [
            {"url": "https://github.com/a/b", "title": "repo", "raw_content": "x", "source": "github"},
            {"url": "https://youtube.com/watch?v=1", "title": "video", "raw_content": "y", "source": "youtube"},
        ]
        result = ar.search("q", channel="youtube", transport=json_transport(items))
        self.assertEqual([entry["url"] for entry in result.metadata["results"]],
                         ["https://youtube.com/watch?v=1"])

    def test_retriever_unavailable_is_named_and_empty(self):
        result = ar.search("q", transport=lambda u, t: {
            "status": None, "text": "", "error": "URLError: [Errno 111] Connection refused"})
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ar.STATUS_FAILED)
        self.assertEqual(result.reason, "retriever_unavailable")
        self.assertEqual(result.metadata["results"], [])
        self.assertTrue(any("gateway_local_only" in limit for limit in result.limits))

    def test_http_error_is_observed(self):
        result = ar.search("q", transport=json_transport([], status=503))
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "retriever_http_503")
        self.assertEqual(result.http_status, 503)

    def test_empty_answer_is_unavailable_not_fabricated(self):
        result = ar.search("q", transport=json_transport([]))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ar.STATUS_UNAVAILABLE)
        self.assertEqual(result.reason, "no_results")
        self.assertEqual(result.metadata["results"], [])

    def test_invalid_inputs(self):
        self.assertEqual(ar.search("   ").reason, "empty_query")
        self.assertEqual(ar.search("q", channel="reddit").reason, "unsupported_channel")


class PageTests(unittest.TestCase):
    def test_useful_text_is_usable(self):
        text = "conteudo real da pagina. " * 60
        result = ar.read_page("https://docs.example/page",
                              transport=lambda u, t: page_payload(text))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ar.QUAL_USABLE)
        self.assertEqual(result.text, text)
        self.assertIsNone(result.http_status)

    def test_short_capture_is_partial(self):
        result = ar.read_page("https://docs.example/page",
                              transport=lambda u, t: page_payload("texto curto " * 10))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_PARTIAL)
        self.assertEqual(result.qualification, ar.QUAL_PARTIAL)
        self.assertEqual(result.reason, "short_capture")

    def test_empty_html_and_level_zero_are_insufficient(self):
        empty = ar.read_page("https://docs.example/empty",
                             transport=lambda u, t: page_payload("", level=0,
                                                                 reason="nada lido"))
        self.assertFalse(empty.ok)
        self.assertEqual(empty.status, ar.STATUS_UNAVAILABLE)
        self.assertEqual(empty.qualification, ar.QUAL_INSUFFICIENT)
        self.assertEqual(empty.reason, "nada lido")

        shell = ar.read_page("https://docs.example/shell",
                             transport=lambda u, t: page_payload(
                                 "<html><body><div></div></body></html>"))
        self.assertEqual(shell.qualification, ar.QUAL_INSUFFICIENT)
        self.assertEqual(shell.reason, "html_without_content")

    def test_anti_bot_page_is_insufficient(self):
        bot = ("Access denied. Please enable JavaScript. You are a robot. "
               "This page requires captcha verification before continuing.")
        result = ar.read_page("https://blocked.example/", transport=lambda u, t: page_payload(bot))
        self.assertFalse(result.ok)
        self.assertEqual(result.qualification, ar.QUAL_INSUFFICIENT)
        self.assertEqual(result.reason, "anti_bot_page")

    def test_http_status_only_when_observed(self):
        observed = ar.read_page("https://docs.example/404",
                                transport=lambda u, t: page_payload(
                                    "not found " * 30, http_status=404))
        self.assertEqual(observed.http_status, 404)
        unobserved = ar.read_page("https://docs.example/ok",
                                  transport=lambda u, t: page_payload("conteudo " * 100))
        self.assertIsNone(unobserved.http_status)

    def test_transport_error_is_failed_not_raised(self):
        result = ar.read_page("https://docs.example/", transport=lambda u, t: (_ for _ in ()).throw(
            RuntimeError("boom")))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ar.STATUS_FAILED)
        self.assertIn("RuntimeError", result.reason)

    def test_invalid_url(self):
        self.assertEqual(ar.read_page("not-a-url").reason, "invalid_url")


class RepoTests(unittest.TestCase):
    def test_readme_via_raw_with_repo_metadata(self):
        readme = "# GPT Researcher\n" + "conteudo do readme " * 60
        bundle = repo_bundle(readme=readme, repo=REPO_JSON,
                             releases=[{"tag_name": "v0.16.0", "name": "0.16.0",
                                        "published_at": "2026-09-01T00:00:00Z",
                                        "html_url": "https://github.com/x/releases/v0.16.0"}],
                             files=[{"name": "README.md"}, {"name": "pyproject.toml"}])
        result = ar.read_repo("https://github.com/assafelovic/gpt-researcher",
                              transport=lambda u, t: bundle)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ar.QUAL_USABLE)
        self.assertEqual(result.text, readme)
        self.assertEqual(result.metadata["stars"], 23000)
        self.assertEqual(result.metadata["license"], "Apache-2.0")
        self.assertEqual(result.metadata["default_branch"], "master")
        self.assertEqual(result.metadata["latest_release"]["tag"], "v0.16.0")
        self.assertIn("pyproject.toml", result.metadata["files"])
        self.assertEqual(result.evidence["read_scope"], "readme_raw")

    def test_404_readme_is_honest_metadata_only(self):
        bundle = repo_bundle(readme="", readme_status=404,
                             readme_reason="ausente no raw (HTTP 404)",
                             repo=REPO_JSON)
        result = ar.read_repo("https://github.com/assafelovic/gpt-researcher",
                              transport=lambda u, t: bundle)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_PARTIAL)
        self.assertEqual(result.qualification, ar.QUAL_METADATA)
        self.assertEqual(result.text, "")
        self.assertEqual(result.chars, 0)
        self.assertEqual(result.http_status, 404)
        self.assertIn("404", result.reason)
        self.assertEqual(result.metadata["stars"], 23000)

    def test_repo_not_found(self):
        bundle = repo_bundle(readme="", readme_status=404,
                             readme_reason="ausente no raw (HTTP 404)",
                             repo_status=404)
        result = ar.read_repo("https://github.com/nobody/nothing",
                              transport=lambda u, t: bundle)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ar.STATUS_UNAVAILABLE)
        self.assertEqual(result.reason, "repo_not_found")
        self.assertEqual(result.http_status, 404)

    def test_unauthenticated_limit_is_declared(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
            result = ar.read_repo(
                "https://github.com/assafelovic/gpt-researcher",
                transport=lambda u, t: repo_bundle(readme="# R\n" + "texto " * 100,
                                                   repo=REPO_JSON))
        self.assertIn("github_api_unauthenticated_60_requests_per_hour", result.limits)
        self.assertFalse(result.metadata["api_authenticated"])

    def test_non_repo_url_is_rejected(self):
        self.assertEqual(ar.read_repo("https://github.com/search?q=x").reason,
                         "not_a_github_repo")
        self.assertEqual(ar.read_repo("https://github.com/o/r/issues/3").reason,
                         "not_a_github_repo")


class VideoTests(unittest.TestCase):
    def _video(self, **payload):
        base = {"text": "", "lang": "en", "chars": 0, "segments": 0,
                "method": "none", "automatic": None, "reason": None}
        base.update(payload)
        return ar.read_video("https://www.youtube.com/watch?v=x",
                             transport=lambda u, l, t: base)

    def test_author_transcript(self):
        result = self._video(text="fala do autor " * 100, chars=1400,
                             segments=20, method="live", automatic=False)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ar.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ar.QUAL_USABLE)
        self.assertEqual(result.metadata["source"], "author")
        self.assertFalse(result.metadata["automatic"])
        self.assertEqual(result.metadata["segments"], 20)
        self.assertIn("no_asr_or_visual_analysis", result.limits)

    def test_automatic_and_unknown_origin(self):
        automatic = self._video(text="fala " * 200, chars=1000, automatic=True)
        self.assertEqual(automatic.metadata["source"], "auto")
        unknown = self._video(text="fala " * 200, chars=1000, automatic=None)
        self.assertEqual(unknown.metadata["source"], "unknown")
        self.assertIsNone(unknown.metadata["automatic"])

    def test_absent_vs_blocked_vs_disabled(self):
        absent = self._video(reason="yt-dlp nao produziu legenda em en (rc=0)")
        blocked = self._video(reason="yt-dlp rc=1: HTTP 429 Too Many Requests")
        disabled = self._video(reason="Subtitles are disabled for this video")
        for result, expected in ((absent, "absent"), (blocked, "blocked"),
                                 (disabled, "disabled")):
            with self.subTest(expected=expected):
                self.assertFalse(result.ok)
                self.assertEqual(result.status, ar.STATUS_UNAVAILABLE)
                self.assertEqual(result.reason, expected)
                self.assertEqual(result.text, "")

    def test_metadata_only_never_leaks_description_as_speech(self):
        result = self._video(title="Titulo do video", description="descricao isca",
                             reason="yt-dlp nao produziu legenda em en (rc=0)")
        self.assertEqual(result.qualification, ar.QUAL_METADATA)
        self.assertEqual(result.text, "")
        self.assertEqual(result.chars, 0)
        self.assertEqual(result.metadata["title"], "Titulo do video")
        self.assertEqual(result.metadata["description"], "descricao isca")

    def test_timestamps_are_not_invented(self):
        result = self._video(text="fala " * 100, chars=500, automatic=False)
        self.assertIsNone(result.metadata["first_timestamp"])
        self.assertIsNone(result.metadata["last_timestamp"])
        self.assertIn("timestamps_unavailable_from_transcript_source", result.limits)

    def test_invalid_url(self):
        self.assertEqual(ar.read_video("youtube").reason, "invalid_url")


class IsolationTests(unittest.TestCase):
    def test_source_never_imports_coordinator(self):
        forbidden = {"adaptive_coordinator", "adaptive_planner", "coverage_ledger",
                     "adaptive_state"}
        for name in ("agent_reach.py", "academic_search.py"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            with self.subTest(module=name):
                self.assertEqual(imported & forbidden, set())

    def test_fresh_import_does_not_load_coordinator(self):
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import agent_reach, academic_search;"
            "bad = sorted(m for m in ('adaptive_coordinator','adaptive_planner',"
            "'coverage_ledger','adaptive_state') if m in sys.modules);"
            "print(','.join(bad))" % str(ROOT)
        )
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        completed = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                   text=True, env=env, cwd=str(ROOT), timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")


class CliTests(unittest.TestCase):
    def _run(self, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        return subprocess.run([sys.executable, str(ROOT / "agent_reach.py"), *args],
                              capture_output=True, text=True, env=env,
                              cwd=str(ROOT), timeout=60)

    def test_help_and_invalid_usage(self):
        self.assertEqual(self._run("--help").returncode, 0)
        self.assertEqual(self._run().returncode, 2)
        self.assertEqual(self._run("search", "q", "--limit", "0").returncode, 2)

    def test_failed_operation_exit_1_and_output_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = self._run("read-page", "not-a-url", "--json",
                                  "--output-dir", directory)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            payload = json.loads(completed.stdout)
            assert_contract(self, payload)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["reason"], "invalid_url")
            files = list(Path(directory).glob("read_page-*.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text())["operation"], "read_page")


@unittest.skipUnless(os.environ.get("HERMES_REAL_NETWORK") == "1",
                     "rede real: defina HERMES_REAL_NETWORK=1")
class RealNetworkTests(unittest.TestCase):
    def test_read_page_real(self):
        result = ar.read_page(
            "https://docs.gptr.dev/docs/gpt-researcher/gptr/config", timeout=60)
        self.assertTrue(result.ok, result.reason)
        self.assertEqual(result.status, ar.STATUS_OBTAINED)
        self.assertGreater(result.chars, 500)

    def test_local_gateway_is_honest(self):
        result = ar.search("python", limit=2, timeout=10)
        assert_contract(self, result.to_dict())
        if result.ok:
            self.assertGreater(result.metadata["returned_count"], 0)
        else:
            self.assertEqual(result.reason, "retriever_unavailable")
            self.assertEqual(result.metadata["results"], [])


if __name__ == "__main__":
    unittest.main()
