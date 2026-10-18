"""Offline contracts for defects exposed by the 20261017 integrated run.

Copy to scripts/ in the project and run with its Python. Only _review_pass is
simulated in the failure-accounting test. No extraction or evidence store is
mocked, and no real provider credentials are used.
"""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden during offline integration checks")


sys.addaudithook(offline_guard)
module_path = Path(os.environ.get("SEMANTIC_REVIEW_PATH",
                   str(Path(__file__).resolve().parents[1] / "semantic_review.py")))
spec = importlib.util.spec_from_file_location("semantic_review", module_path)
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)


class E2EIntegrationContract(unittest.TestCase):
    def test_repeated_url_keeps_the_distinct_chunks_used_by_writer(self):
        url = "https://github.com/example/opencode-alpha"
        first = "Source: " + url + "\nTitle: README\nContent: License: Apache-2.0.\n\n"
        second = "Source: " + url + "\nTitle: README\nContent: opencode-alpha supports persistent sessions.\n"
        corpus = sr.build_evidence(first + second)
        self.assertIn(url, corpus)
        self.assertIn("License: Apache-2.0", corpus[url],
                      "An earlier chunk for the same URL was overwritten")
        self.assertIn("persistent sessions", corpus[url])
        items = sr.extract_claims(
            "# Relatório\n\nO pacote `opencode-alpha` usa licença Apache-2.0.\n",
            corpus, max_claims=10000)
        self.assertTrue(items)
        self.assertTrue(any("License: Apache-2.0" in item["evidence"] for item in items))

    def test_attribute_value_table_keeps_package_values_and_relationships(self):
        report = ("# Daytona OpenCode Plugin\n\n## Licensing & Distribution\n\n"
                  "| Attribute | Value |\n|---|---|\n"
                  "| npm Package | `@daytona/opencode` |\n"
                  "| Fork on OpenDock | `@veris-ai/daytona-opencode` (fork of `@daytona/opencode`) |\n")
        items = sr.extract_claims(report, {}, max_claims=10000)
        npm = [item["claim"] for item in items if "npm Package" in item["claim"]]
        fork = [item["claim"] for item in items if "Fork on OpenDock" in item["claim"]]
        self.assertTrue(npm, "The npm-package row was lost")
        self.assertTrue(fork, "The fork row was lost")
        self.assertTrue(any("@daytona/opencode" in text for text in npm),
                        "A value was mistaken for the subject and removed from the proposition")
        self.assertTrue(any("@veris-ai/daytona-opencode" in text and
                            "fork of" in text and "@daytona/opencode" in text for text in fork),
                        "The upstream/fork relationship was lost")

    def test_source_attribution_alone_is_not_a_package_fact(self):
        report = ("# Relatório\n\n"
                  "*Sources: Daytona docs, daytona/integrations README, "
                  "Goober-Codes/daytona-pi README*\n")
        items = sr.extract_claims(report, {}, max_claims=10000)
        self.assertEqual(items, [], "Source labels consumed factual-review slots")
        ledger = sr.get_coverage_report()
        self.assertTrue(ledger["blocks"], "The source material must remain traceable")

    def test_failure_votes_remain_visible_after_quorum_aggregation(self):
        calls = 0

        async def simulated(items, model, batch_size=12):
            nonlocal calls
            verdict = "transport_error" if calls < 2 else "sustained"
            calls += 1
            return [{"id": item["id"], "verdict": verdict, "support": "",
                     "correction": "offline fixture; no real API call"} for item in items]

        with patch.object(sr, "_review_pass", simulated):
            result = sr.review_report(
                "# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n",
                {"https://example.com/opencode-alpha": "opencode-alpha uses the MIT license."},
                votes=3, max_claims=10000)
        self.assertEqual(calls, 3)
        self.assertEqual(result["claims"], 1)
        self.assertEqual(result["summary"]["incomplete"], 1)
        self.assertEqual(result["summary"]["disputed_ties"], 0)
        self.assertFalse(result["accepted"])
        # Proposed explicit counter, measured per vote, avoiding ambiguity with
        # the existing aggregate 'technical_failures' counter measured per claim.
        self.assertEqual(result["summary"].get("technical_failure_votes"), 2,
                         "Technical failures disappeared from the summary after aggregation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
