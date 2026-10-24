#!/usr/bin/env python3
"""Contratos dos transportes de modelo (offline, subprocess mockado).

Run: python3 -m unittest tests.test_model_transport -v
"""
import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import model_transport as mt  # noqa: E402


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)


class _Cfg:
    def __init__(self, model):
        self.smart_llm = model


class _Researcher:
    def __init__(self, model):
        self.cfg = _Cfg(model)


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["opencode"], returncode,
                                       stdout=stdout, stderr=stderr)


class LitellmModelResolution(unittest.TestCase):
    def test_openrouter_prefix_is_normalised(self):
        client = mt.litellm_client(model="openrouter:vendor/model:free")
        self.assertEqual(client.model_id, "openrouter/vendor/model:free")

    def test_all_supported_prefixes(self):
        for raw in ("openai:gpt-x", "anthropic:claude-x",
                    "google_genai:gemini-x"):
            provider = raw.split(":", 1)[0]
            self.assertEqual(mt.litellm_client(model=raw).model_id,
                             f"{provider}/{raw.split(':', 1)[1]}")

    def test_existing_slash_is_kept(self):
        self.assertEqual(mt.litellm_client(model="openrouter/vendor/x").model_id,
                         "openrouter/vendor/x")

    def test_explicit_model_beats_researcher_and_env(self):
        with mock.patch.dict(os.environ, {"SMART_LLM": "openrouter:env/model"}):
            client = mt.litellm_client(model="openai:explicit/model",
                                       researcher=_Researcher("openrouter:cfg/model"))
        self.assertEqual(client.model_id, "openai/explicit/model")

    def test_researcher_cfg_beats_env(self):
        with mock.patch.dict(os.environ, {"SMART_LLM": "openrouter:env/model"}):
            client = mt.litellm_client(researcher=_Researcher("openrouter:cfg/model"))
        self.assertEqual(client.model_id, "openrouter/cfg/model")

    def test_env_is_last_resort(self):
        with mock.patch.dict(os.environ, {"SMART_LLM": "openrouter:env/model"}):
            client = mt.litellm_client(researcher=_Researcher(""))
        self.assertEqual(client.model_id, "openrouter/env/model")

    def test_missing_model_is_explicit(self):
        with mock.patch.dict(os.environ, {"SMART_LLM": ""}):
            with self.assertRaises(mt.ModelTransportError) as ctx:
                mt.litellm_client()
        self.assertIn("model_not_configured", str(ctx.exception))

    def test_unknown_provider_is_explicit(self):
        with self.assertRaises(mt.ModelTransportError) as ctx:
            mt.litellm_client(model="cohere:command-x")
        self.assertIn("unknown_provider:cohere", str(ctx.exception))


class LitellmCalls(unittest.TestCase):
    def test_missing_library_is_explicit_at_call_time(self):
        client = mt.litellm_client(model="openrouter:x")
        with mock.patch.dict(sys.modules, {"litellm": None}):
            with self.assertRaises(mt.ModelTransportError) as ctx:
                client("hi")
        self.assertIn("litellm_unavailable", str(ctx.exception))
        self.assertEqual(client.describe()["kind"], "litellm")

    def test_successful_completion_and_describe(self):
        seen = {}

        class _Message:
            content = "resposta"

        class _Choice:
            message = _Message()

        class _Response:
            choices = [_Choice()]

        def _completion(**kwargs):
            seen.update(kwargs)
            return _Response()

        fake = types.SimpleNamespace(completion=_completion)
        with mock.patch.dict(sys.modules, {"litellm": fake}):
            client = mt.litellm_client(model="openrouter:x", timeout=7.0)
            self.assertEqual(client("pergunta"), "resposta")
        self.assertEqual(seen["model"], "openrouter/x")
        self.assertEqual(seen["timeout"], 7.0)
        self.assertEqual(seen["messages"], [{"role": "user", "content": "pergunta"}])
        desc = client.describe()
        self.assertEqual(desc, {"kind": "litellm", "model_id": "openrouter/x",
                                "calls": 1, "timeout": 7.0})
        self.assertEqual(client.calls, 1)

    def test_provider_error_is_short_and_redacted(self):
        def _boom(**kwargs):
            raise RuntimeError("401 User not found key=sk-secret123456")

        with mock.patch.dict(sys.modules, {"litellm": types.SimpleNamespace(completion=_boom)}):
            client = mt.litellm_client(model="openrouter:x")
            with self.assertRaises(mt.ModelTransportError) as ctx:
                client("hi")
        message = str(ctx.exception)
        self.assertIn("litellm_call_failed", message)
        self.assertNotIn("sk-secret", message)
        self.assertLessEqual(len(message), 300)


class OpencodeCalls(unittest.TestCase):
    def _run_client(self, client, run_mock, prompt="q"):
        with mock.patch.object(mt.shutil, "which", return_value="/usr/bin/opencode"), \
                mock.patch.object(mt.subprocess, "run", run_mock):
            return client(prompt)

    def test_jsonl_text_parts_are_concatenated(self):
        stdout = "\n".join([
            json.dumps({"type": "step_start"}),
            json.dumps({"type": "text", "part": {"text": "Hel"}}),
            "not json at all",
            json.dumps({"type": "text", "part": {"text": "lo"}}),
            json.dumps({"type": "tool", "part": {"text": "ignored"}}),
        ])
        run = mock.Mock(return_value=_completed(stdout=stdout))
        client = mt.opencode_client(model="opencode/m", timeout=11.0)
        self.assertEqual(self._run_client(client, run), "Hello")
        argv = run.call_args.args[0]
        self.assertEqual(argv[:6], ["opencode", "run", "--standalone",
                                    "--format", "json", "-m"])
        self.assertEqual(argv[6], "opencode/m")
        self.assertEqual(argv[7], "q")
        self.assertEqual(run.call_args.kwargs,
                         {"capture_output": True, "text": True,
                          "timeout": 11.0, "shell": False})
        desc = client.describe()
        self.assertEqual(desc["kind"], "opencode")
        self.assertEqual(desc["model_id"], "opencode/m")
        self.assertEqual(desc["calls"], 1)

    def test_no_text_reports_stderr_tail_without_prompt(self):
        prompt = "PROMPT-SENTINEL " + "x" * 50
        run = mock.Mock(return_value=_completed(
            stdout=json.dumps({"type": "step_start"}),
            stderr="upstream exploded", returncode=1))
        client = mt.opencode_client(model="opencode/m")
        with self.assertRaises(mt.ModelTransportError) as ctx:
            self._run_client(client, run, prompt)
        message = str(ctx.exception)
        self.assertIn("opencode_no_text", message)
        self.assertIn("upstream exploded", message)
        self.assertNotIn("PROMPT-SENTINEL", message)

    def test_timeout_is_explicit(self):
        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=3)

        client = mt.opencode_client(model="opencode/m", timeout=3.0)
        with self.assertRaises(mt.ModelTransportError) as ctx:
            self._run_client(client, mock.Mock(side_effect=_timeout))
        self.assertIn("opencode_timeout", str(ctx.exception))

    def test_max_calls_blocks_before_execution(self):
        run = mock.Mock(return_value=_completed(
            stdout=json.dumps({"type": "text", "part": {"text": "ok"}})))
        client = mt.opencode_client(model="opencode/m", max_calls=1)
        self.assertEqual(self._run_client(client, run), "ok")
        with self.assertRaises(mt.ModelTransportError) as ctx:
            self._run_client(client, run)
        self.assertIn("max_calls_exceeded", str(ctx.exception))
        self.assertEqual(run.call_count, 1)

    def test_missing_binary_is_explicit(self):
        run = mock.Mock()
        client = mt.opencode_client(model="opencode/m")
        with mock.patch.object(mt.shutil, "which", return_value=None), \
                mock.patch.object(mt.subprocess, "run", run):
            with self.assertRaises(mt.ModelTransportError) as ctx:
                client("q")
        self.assertIn("opencode_cli_unavailable", str(ctx.exception))
        run.assert_not_called()

    def test_prompt_too_large_is_refused(self):
        run = mock.Mock()
        client = mt.opencode_client(model="opencode/m")
        with mock.patch.object(mt.subprocess, "run", run):
            with self.assertRaises(mt.ModelTransportError) as ctx:
                client("x" * (mt.MAX_PROMPT_CHARS + 1))
        self.assertIn("prompt_too_large", str(ctx.exception))
        run.assert_not_called()


class Factory(unittest.TestCase):
    def test_unknown_kind_is_explicit(self):
        with self.assertRaises(mt.ModelTransportError):
            mt.from_env(kind="magic")

    def test_opencode_defaults(self):
        client = mt.from_env(kind="opencode")
        self.assertEqual(client.model_id, mt.DEFAULT_OPENCODE_MODEL)
        self.assertEqual(client.describe()["kind"], "opencode")

    def test_explicit_kwargs_are_forwarded(self):
        client = mt.from_env(kind="litellm", model="openai:x", timeout=5.0)
        self.assertEqual(client.describe()["timeout"], 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
