"""Actual replay omissions and normal-path persistence; no network or model."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = Path(os.environ.get("SEMANTIC_REVIEW_PATH", ROOT / "semantic_review.py"))
spec = importlib.util.spec_from_file_location("semantic_review", MODULE)
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden during offline closure tests")


sys.addaudithook(offline_guard)


async def favorable(items, model, batch_size=12):
    return [{"id": item["id"], "verdict": "sustained", "support": "simulation",
             "correction": ""} for item in items]


class ReplayClosure(unittest.TestCase):
    def test_original_nested_capabilities_table_keeps_all_five_rows(self):
        report = (ROOT / "fixtures/relatorio_daytona_original.md").read_text()
        claims = sr.extract_claims(report, {}, max_claims=10000)
        expected = ("Secure Isolation", "Persistence", "Live Previews",
                    "Git Synchronization", "Zero-Config Runtime")
        blocks = {b["id"]: b for b in sr.get_coverage_report()["blocks"]}
        ledger = {c["id"]: c for c in sr.get_coverage_report()["claims"]}
        for label in expected:
            matches = [c for c in claims if c.get("table_row") and label in c["claim"]]
            self.assertEqual(len(matches), 1, label)
            block = blocks[ledger[matches[0]["id"]]["block_id"]]
            self.assertIn("1.2 Core Value Proposition", block["section"])
            self.assertIn(label, block["original_text"])
            self.assertEqual([p.lower() for p in matches[0]["packages"]], ["daytona"])

    def test_subject_does_not_leak_from_a_previous_sibling_section(self):
        report = ("# Comparison\n## Package opencode-alpha\n### Capabilities\n"
                  "| Feature | Value |\n|---|---|\n| Isolation | Sandbox A |\n"
                  "## Unidentified product\n### Capabilities\n"
                  "| Feature | Value |\n|---|---|\n| Retention | Unknown duration |\n")
        claims = sr.extract_claims(report, {}, max_claims=10000)
        self.assertTrue(any("Sandbox A" in c["claim"] for c in claims))
        self.assertFalse(any("Unknown duration" in c["claim"] for c in claims))
        self.assertFalse(sr.get_coverage_report()["coverage_complete"])

    def test_ambiguous_heading_does_not_assign_one_package_to_the_row(self):
        report = ("# Comparison\n## opencode-alpha and opencode-beta\n"
                  "| Feature | Value |\n|---|---|\n| Isolation | Remote sessions |\n")
        claims = sr.extract_claims(report, {}, max_claims=10000)
        self.assertFalse(any(c.get("table_row") for c in claims))
        self.assertFalse(sr.get_coverage_report()["coverage_complete"])

    def test_unresolved_table_row_blocks_acceptance_even_with_favorable_votes(self):
        report = ("# Research\n\n## Verified product\n\n"
                  "O pacote `opencode-alpha` é gratuito e usa licença MIT.\n\n"
                  "## Unidentified product\n\n"
                  "| Feature | Value |\n|---|---|\n"
                  "| Retention | Unknown duration |\n")
        with patch.object(sr, "_review_pass", favorable):
            result = sr.review_report(report, {}, votes=3, max_claims=10000)
        coverage = result["coverage"]
        self.assertGreater(result["claims_reviewed"], 0)
        self.assertTrue(all(v["verdict"] == "sustained" for v in result["verdicts"]))
        incomplete = [d for d in coverage["dropped"] if d["state"] == "incomplete"]
        self.assertTrue(incomplete)
        self.assertEqual(coverage["counts"].get("dropped_incomplete"), len(incomplete))
        self.assertFalse(coverage["coverage_complete"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict_state"], "revisão incompleta")

    def test_usage_dictionary_survives_repeated_normalization(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14,
                 "cost": 0, "completion_tokens_details": {"reasoning_tokens": 2}}
        normalized = sr._serialize_usage(usage)
        self.assertEqual(normalized, usage)
        self.assertEqual(sr._serialize_usage(normalized), usage)
        self.assertEqual(json.loads(json.dumps(normalized)), usage)

    def test_model_metadata_belongs_only_to_the_current_review(self):
        report = "O pacote opencode-alpha oferece sessões persistentes."
        counter = 0

        async def recording(items, model, batch_size=12):
            nonlocal counter
            counter += 1
            sr._MODEL_CALL_METADATA.append({"id": f"request-{counter}"})
            return await favorable(items, model, batch_size)

        with patch.object(sr, "_MODEL_CALL_METADATA", [{"id": "older-run"}]), \
             patch.object(sr, "_review_pass", recording):
            first = sr.review_report(report, {}, votes=3)
            second = sr.review_report(report, {}, votes=3)
            empty = sr.review_report("# Context", {}, votes=3)
            disabled = sr.review_report(report, {}, enabled=False)
        self.assertEqual([m["id"] for m in first["model_call_metadata"]],
                         ["request-1", "request-2", "request-3"])
        self.assertEqual([m["id"] for m in second["model_call_metadata"]],
                         ["request-4", "request-5", "request-6"])
        self.assertEqual(empty.get("model_call_metadata"), [])
        self.assertEqual(disabled.get("model_call_metadata"), [])

    def test_normal_entrypoint_keeps_votes_metadata_and_review_duration(self):
        """Evaluate the real record expressions without importing network hooks."""
        entry = Path(os.environ.get("INTEGRATION_PATH", ROOT / "gpt_researcher_integration.py"))
        tree = ast.parse(entry.read_text())
        record = next(node.value for node in ast.walk(tree)
                      if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "_depth_record"
                              for t in node.targets))
        fields = {key.value: value for key, value in zip(record.keys, record.values)}
        semantic = {"enabled": True, "duration_s": 25, "claims": 1,
                    "coverage": {"coverage_complete": False},
                    "verdicts": [{"id": 0, "vote_tally": {"unsupported": 3}}],
                    "model_call_metadata": [{"id": "real-request"}],
                    "accepted": False, "verdict_state": "reprovado", "summary": {}}
        namespace = {"_semantic": semantic, "_t_start": 100,
                     "_t_research_done": 110, "_t_write_done": 115,
                     "_t_audit_done": 120, "_t_semantic_done": 145}

        def evaluate(node):
            return eval(compile(ast.Expression(node), str(entry), "eval"), namespace)

        saved = evaluate(fields["semantic"])
        self.assertEqual(saved, semantic)
        json.dumps(saved)
        phases = evaluate(fields["phases"])
        self.assertEqual(phases["total_s"], 45)
        self.assertEqual(phases.get("semantic_s"), 25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
