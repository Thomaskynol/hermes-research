"""Offline qualification checks through the real extraction/review path.

Run from the repository root:
    python scripts/test_semantic_corpus_qualification_review.py

Only _review_pass is replaced: extraction, selection and evidence windows stay
real. The replacement returns simulated gaps and records its input. It does
not evaluate semantic truth or change the approval policy.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch


NETWORK_ATTEMPTS = []
OBSERVATIONS = []


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        NETWORK_ATTEMPTS.append(event)
        raise RuntimeError("Network forbidden in this offline review")


sys.addaudithook(offline_guard)
MODULE_PATH = Path(os.environ.get(
    "SEMANTIC_REVIEW_PATH",
    str(Path(__file__).resolve().parents[1] / "semantic_review.py"),
)).resolve()
spec = importlib.util.spec_from_file_location("semantic_review", MODULE_PATH)
sr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sr
spec.loader.exec_module(sr)


class CorpusQualificationContract(unittest.TestCase):
    def review_input(self, report, corpus):
        """Capture the real items that would enter the auditor, without an LLM."""
        original_corpus = copy.deepcopy(corpus)
        captured = []

        async def fake_review_pass(items, model, batch_size=12):
            captured.extend(copy.deepcopy(items))
            return [{"id": item["id"], "verdict": "gap", "support": "",
                     "correction": "simulated review; no semantic approval"}
                    for item in items]

        with patch.object(sr, "_review_pass", fake_review_pass):
            result = sr.review_report(report, corpus, votes=3, max_claims=10000)
        self.assertEqual(corpus, original_corpus, "Raw corpus was modified")
        self.assertTrue(captured, "No real extracted claim reached _review_pass")
        unique = {item["id"]: item for item in captured}
        items = list(unique.values())
        OBSERVATIONS.append({
            "test": self.id(), "report": report, "corpus": original_corpus,
            "auditor_input": [{k: item.get(k) for k in
                               ("id", "claim", "anchors", "evidence")}
                              for item in items],
            "simulated_review": True,
            "actual_result_claim_count": result.get("claims"),
        })
        return items

    def qualification(self, url, text):
        result = sr._qualify_evidence_entry(url, text)
        OBSERVATIONS.append({"test": self.id(), "url": url,
                             "qualification": result})
        return result

    def test_excluded_error_does_not_reenter_auditor_via_fallbacks(self):
        scenarios = [
            ("explicit_url", "https://example.com/error", "404: Not Found",
             "A página https://example.com/error confirma que o pacote "
             "`opencode-alpha` usa licença MIT."),
            ("package_suffix", "https://example.com/error", "404: alpha",
             "O pacote `opencode-alpha` usa licença MIT."),
            ("content_tokens", "https://example.com/error",
             "404: licença MIT gratuito",
             "O pacote `opencode-alpha` é gratuito e usa licença MIT."),
            ("price_fallback", "https://example.com/error", "404: $99/month",
             "O pacote `opencode-alpha` custa $99/month."),
        ]
        for label, url, raw, sentence in scenarios:
            with self.subTest(path=label):
                q = self.qualification(url, raw)
                self.assertTrue(q["excluded"], "Fixture must qualify as excluded")
                items = self.review_input("# Relatório\n\n" + sentence + "\n",
                                          {url: raw})
                for item in items:
                    self.assertNotIn(raw, item["evidence"],
                                     "Excluded error payload entered the auditor")

    def test_script_only_html_is_not_factual_content(self):
        url = "https://example.com/opencode-alpha"
        raw = ('<!DOCTYPE html><html><head><script>'
               'var plan="FREE"; var noise="' + "x" * 180 + '";'
               '</script></head><body><p>opencode-alpha</p></body></html>')
        items = self.review_input(
            "# Relatório\n\nO pacote `opencode-alpha` é gratuito.\n", {url: raw})
        q = self.qualification(url, raw)
        self.assertTrue(q["excluded"], "Script strings were mistaken for page facts")
        for item in items:
            self.assertNotIn('var plan="FREE"', item["evidence"])

    def test_useful_html_body_reaches_auditor_without_script_or_style(self):
        url = "https://example.com/opencode-alpha"
        raw = ('<!DOCTYPE html><html><head>'
               '<script>const hidden="SCRIPT_ONLY_917";</script>'
               '<style>/* STYLE_ONLY_917 */ p { color: red; }</style>'
               '</head><body><p>opencode-alpha usa licença MIT. '
               + "Documentação do pacote. " * 8 + '</p></body></html>')
        items = self.review_input(
            "# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n", {url: raw})
        q = self.qualification(url, raw)
        self.assertFalse(q["excluded"], "Useful body text was lost")
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("opencode-alpha usa licença MIT", combined)
        self.assertNotIn("SCRIPT_ONLY_917", combined)
        self.assertNotIn("STYLE_ONLY_917", combined)
        self.assertNotRegex(combined, r"(?i)<(?:html|head|script|style)\b")

    def test_github_api_facts_are_retained_for_the_fields_they_contain(self):
        url = "https://api.github.com/repos/example/opencode-alpha"
        tag_sha, head_sha = "a" * 40, "b" * 40
        raw = "GitHub metadata for example/opencode-alpha\n" + json.dumps({
            "default_branch": "main", "license": "MIT",
            "tags": [{"name": "v1.2.3", "commit": {"sha": tag_sha}}],
            "commits": [{"sha": head_sha}],
        })
        items = self.review_input(
            "# Relatório\n\n## Pacote `opencode-alpha`\n"
            "- **Tag:** v1.2.3\n- **Branch:** main\n"
            "- **Commit (tag v1.2.3):** " + tag_sha + "\n"
            "- **Branch `main` HEAD:** " + head_sha + "\n", {url: raw})
        q = self.qualification(url, raw)
        self.assertFalse(q["excluded"],
                         "Factual API fields were discarded because they are metadata")
        for fact in ("main", "MIT", "v1.2.3", tag_sha, head_sha):
            self.assertIn(fact, q["usable_text"])
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn(tag_sha, combined)
        self.assertIn(head_sha, combined)

    def test_mixed_readme_isolates_standalone_error_but_keeps_facts(self):
        url = "https://github.com/example/opencode-alpha"
        raw = ("# opencode-alpha\n\nLicense: MIT.\n"
               "The API documentation describes handling HTTP 429 responses.\n\n"
               "404: Not Found\n\n"
               "GitHub metadata for example/opencode-alpha\n"
               '{"default_branch": "main", "license": "MIT"}\n')
        items = self.review_input(
            "# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n", {url: raw})
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("License: MIT", combined)
        self.assertIn("handling HTTP 429 responses", combined)
        self.assertNotRegex(combined, r"(?m)^\s*404: Not Found\s*$",
                            "Standalone collection error remained as probative text")

    def test_legitimate_http_code_documentation_remains_available(self):
        url = "https://example.com/docs/opencode-alpha"
        raw = ("opencode-alpha uses the MIT license.\n"
               "HTTP 404 means a resource was not found; HTTP 429 indicates throttling.\n"
               "These are documented response codes, not this collection's result.")
        items = self.review_input(
            "# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n", {url: raw})
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("MIT", combined)
        self.assertIn("HTTP 404 means", combined)
        self.assertIn("HTTP 429 indicates", combined)

    def test_youtube_description_and_partial_spoken_markers_stay_distinct(self):
        url = "https://www.youtube.com/watch?v=qualification_fixture"
        for marker, sentence in [
            ("[description]", "opencode-alpha usa licença MIT na descrição."),
            ("[spoken 5/11]", "opencode-alpha usa licença MIT neste trecho."),
        ]:
            with self.subTest(marker=marker):
                raw = marker + " " + sentence
                items = self.review_input(
                    "# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n",
                    {url: raw})
                q = self.qualification(url, raw)
                self.assertFalse(q["excluded"])
                if marker.startswith("[spoken"):
                    self.assertEqual(q["status"], "partial")
                combined = "\n".join(item["evidence"] for item in items)
                self.assertIn(marker, combined)
                self.assertIn(sentence, combined)
                other = "[description]" if marker.startswith("[spoken") else "[spoken"
                self.assertNotIn(other, combined)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        output_path = os.environ.get("QUALIFICATION_OBSERVATIONS_PATH")
        if output_path:
            Path(output_path).write_text(json.dumps({
                "module_sha256": hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest(),
                "simulated_review": True, "network_attempts": NETWORK_ATTEMPTS,
                "observations": OBSERVATIONS,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
