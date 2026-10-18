"""Remaining qualification cases; offline, only _review_pass is simulated."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden in offline qualification tests")


sys.addaudithook(offline_guard)
MODULE_PATH = Path(os.environ.get(
    "SEMANTIC_REVIEW_PATH", str(Path(__file__).resolve().parents[1] / "semantic_review.py")))
spec = importlib.util.spec_from_file_location("semantic_review", MODULE_PATH)
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)


class FinalQualificationCases(unittest.TestCase):
    def audit_text(self, raw, sentence="O pacote `opencode-alpha` usa licença MIT."):
        corpus = {"https://example.com/opencode-alpha": raw}
        original = copy.deepcopy(corpus)
        captured = []

        async def simulated(items, model, batch_size=12):
            captured.extend(copy.deepcopy(items))
            return [{"id": item["id"], "verdict": "gap", "support": "",
                     "correction": "simulated; no semantic approval"} for item in items]

        with patch.object(sr, "_review_pass", simulated):
            sr.review_report("# Relatório\n\n" + sentence + "\n", corpus,
                             votes=3, max_claims=10000)
        self.assertTrue(captured, "No claim reached the simulated auditor")
        self.assertEqual(corpus, original)
        return "\n".join(item["evidence"] for item in captured)

    def test_html_without_doctype_uses_the_clean_body(self):
        raw = ('<html><head><script>var hidden="SCRIPT_ONLY_813";</script>'
               '<style>/* STYLE_ONLY_813 */</style></head>'
               '<body><p>opencode-alpha usa licença MIT. '
               + "Documentação factual do pacote. " * 5 + '</p></body></html>')
        sent = self.audit_text(raw)
        self.assertIn("opencode-alpha usa licença MIT", sent)
        self.assertNotIn("SCRIPT_ONLY_813", sent)
        self.assertNotIn("STYLE_ONLY_813", sent)
        self.assertNotRegex(sent, r"(?i)<(?:html|head|script|style)\b")

    def test_head_text_cannot_supply_a_missing_body_fact(self):
        raw = ('<!DOCTYPE html><html><head><title>FREE '
               + "Marketing title without a captured body fact. " * 6
               + '</title></head><body><p>opencode-alpha</p></body></html>')
        q = sr._qualify_evidence_entry("https://example.com/pricing", raw)
        self.assertTrue(q["excluded"], "Head/title text was treated as a body fact")
        sent = self.audit_text(raw, "O pacote `opencode-alpha` é gratuito.")
        self.assertNotIn("Marketing title", sent)

    def test_generic_feature_body_is_not_limited_to_price_license_or_free(self):
        raw = ('<!DOCTYPE html><html><body><p>opencode-alpha exports project '
               'reports in CSV format and synchronizes project folders '
               'automatically after every change.</p></body></html>')
        sent = self.audit_text(raw, "O pacote `opencode-alpha` exporta relatórios CSV.")
        self.assertIn("exports project reports in CSV format", sent)

    def test_custom_api_format_retains_subject_and_each_tag_commit_pair(self):
        tag1, tag2, head = "a" * 40, "c" * 40, "b" * 40
        tags = [{"name": "v1.2.3", "zipball_url": "https://example.com/" + "long/" * 50,
                 "commit": {"sha": tag1}},
                {"name": "v1.2.2", "commit": {"sha": tag2}}]
        raw = ("GitHub metadata for example/opencode-alpha\n"
               + json.dumps({"default_branch": "main", "license": "MIT"})
               + "\n\ntags: " + json.dumps(tags, indent=2)
               + "\n\ncommits: " + head + ", " + tag2 + ", " + tag1)
        q = sr._qualify_evidence_entry(
            "https://api.github.com/repos/example/opencode-alpha", raw)
        self.assertFalse(q["excluded"])
        text = q["usable_text"]
        self.assertIn("example/opencode-alpha", text)
        self.assertIn("tag: v1.2.3 (commit " + tag1 + ")", text)
        self.assertIn("tag: v1.2.2 (commit " + tag2 + ")", text)
        self.assertNotIn("tag: v1.2.3 (commit " + head + ")", text)

    def test_code_documentation_lines_survive_removal_of_a_standalone_error(self):
        raw = ("# opencode-alpha\nLicense: MIT.\n"
               "404 means that the requested resource was not found.\n"
               "429 indicates that clients should retry after throttling.\n\n"
               "404: Not Found\n")
        sent = self.audit_text(raw)
        self.assertIn("404 means that", sent)
        self.assertIn("429 indicates that", sent)
        self.assertNotRegex(sent, r"(?m)^\s*404: Not Found\s*$")

    def test_frozen_api_tag_commit_relationships_are_preserved(self):
        path = Path(os.environ.get("EVIDENCE_FIXTURE_PATH",
                    str(MODULE_PATH.parent / "runs/replay_corrigido_evidence.json")))
        corpus = json.loads(path.read_text())["evidence"]
        checked = 0
        for url, raw in corpus.items():
            if not url.startswith("https://api.github.com/"):
                continue
            match = re.search(r"(?m)^tags:\s*", raw)
            self.assertIsNotNone(match)
            tags, _ = json.JSONDecoder().raw_decode(raw[match.end():].lstrip())
            text = sr._qualify_evidence_entry(url, raw)["usable_text"]
            for tag in tags:
                with self.subTest(url=url, tag=tag["name"]):
                    expected = "tag: " + tag["name"] + " (commit " + tag["commit"]["sha"] + ")"
                    self.assertIn(expected, text)
                    checked += 1
        self.assertEqual(checked, 4, "Expected four actual frozen tag/commit pairs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
