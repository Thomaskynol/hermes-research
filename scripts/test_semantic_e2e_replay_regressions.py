"""Regression cases from the revised E2E package; strictly offline.

The coverage test replaces only _review_pass. The protocol test keeps
_review_pass real and supplies an in-memory SDK response at the transport
boundary. No real key, environment credential or network is used.
"""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden in offline replay regression tests")


sys.addaudithook(offline_guard)
module_path = Path(os.environ.get("SEMANTIC_REVIEW_PATH",
                   str(Path(__file__).resolve().parents[1] / "semantic_review.py")))
spec = importlib.util.spec_from_file_location("semantic_review", module_path)
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)

TABLE = ("# Pacote `opencode-alpha`\n\n"
         "| Attribute | Value |\n|---|---|\n"
         "| License | MIT |\n"
         "| External service | Mandatory paid account |\n")


class RevisedReplayRegressions(unittest.TestCase):
    def test_attribute_rows_inherit_context_without_repeating_the_package(self):
        claims = sr.extract_claims(TABLE, {}, max_claims=10000)
        texts = [item["claim"] for item in claims]
        self.assertTrue(any("License" in text and "MIT" in text for text in texts),
                        "The license row vanished because it did not repeat a package name")
        self.assertTrue(any("External service" in text and "Mandatory paid account" in text
                            for text in texts), "The paid-service fact vanished")

    def test_missing_table_facts_cannot_produce_a_complete_accepted_review(self):
        report = TABLE + "\nO pacote `opencode-alpha` oferece sessões persistentes.\n"

        async def simulated(items, model, batch_size=12):
            return [{"id": item["id"], "verdict": "sustained", "support": "fixture",
                     "correction": ""} for item in items]

        with patch.object(sr, "_review_pass", simulated):
            result = sr.review_report(report, {}, votes=3, max_claims=10000)
        reviewed_text = "\n".join(item["claim"] for item in result["verdicts"])
        all_facts_present = "MIT" in reviewed_text and "Mandatory paid account" in reviewed_text
        if not all_facts_present:
            self.assertFalse(result["coverage"]["coverage_complete"],
                             "Missing factual rows were silently counted as complete")
            self.assertFalse(result["accepted"], "Review accepted after table facts vanished")

    def test_empty_response_records_a_protocol_failure_on_the_request(self):
        async def create(**kwargs):
            return SimpleNamespace(model="offline-model", id="offline-request",
                                   usage=None, choices=[SimpleNamespace(
                                       finish_reason="stop",
                                       message=SimpleNamespace(content=""))])

        fake_client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)))
        fake_sdk = SimpleNamespace(AsyncOpenAI=lambda **kwargs: fake_client)
        items = [{"id": 0, "claim": "opencode-alpha uses MIT.",
                  "packages": ["opencode-alpha"], "licences": ["MIT"],
                  "free_assertion": False, "evidence": "License: MIT."}]
        with patch.dict(sys.modules, {"openai": fake_sdk}), \
             patch.object(sr, "_load_key", return_value="offline-placeholder"), \
             patch.object(sr, "_MODEL_CALL_METADATA", []):
            result = asyncio.run(sr._review_pass(items, "offline-model"))
            records = list(sr._MODEL_CALL_METADATA)
        self.assertEqual(result[0]["verdict"], "invalid_json")
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].get("protocol_error"),
                        "The request log calls an empty invalid response error-free")


if __name__ == "__main__":
    unittest.main(verbosity=2)
