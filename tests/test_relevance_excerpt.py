"""Relevance-windowed excerpts, infra-URL redaction, html/ arXiv, read_level.

Regression source: acadrun (2026-10-24/25). The arXiv abs page held the
full 131K-char body, but the assessor saw a head-only cut ("summary up to
4.4") and judged insufficient; the model then cited the SearXNG base URL
as a source (leaked from attempt notes into the prompt).
"""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("relevance excerpt test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def long_doc():
    head = ("Abstract. This paper studies adaptive retrieval. " * 40 + "\n\n")
    body = ("Section 5.2.4 failure analysis: component-level failures "
            "account for 63.5 percent of errors and architectural failures "
            "for 36.5 percent. " * 20 + "\n\n")
    tail = ("Section 6.1 limitations declared here. " * 20 + "\n")
    return head + body + tail


class RelevantExcerptTest(unittest.TestCase):
    def test_window_around_terms_beats_head(self):
        doc = long_doc()
        excerpt, _stripped, windows = ac._relevant_excerpt(
            doc, 1200, ["failure", "limitations", "architectural"])
        self.assertIn("63.5", excerpt)
        self.assertIn("relevancia", windows)
        self.assertLessEqual(len(excerpt), 1200 + 50)

    def test_no_terms_falls_back_to_head(self):
        doc = long_doc()
        excerpt, _stripped, windows = ac._relevant_excerpt(doc, 200, None)
        self.assertTrue(excerpt.startswith("Abstract"))
        self.assertIn("cabeca", windows)

    def test_terms_without_hits_falls_back_to_head(self):
        doc = long_doc()
        excerpt, _stripped, windows = ac._relevant_excerpt(
            doc, 200, ["xyznonexistent"])
        self.assertTrue(excerpt.startswith("Abstract"))
        self.assertIn("sem ocorrencia", windows)

    def test_short_body_returned_whole(self):
        excerpt, _stripped, windows = ac._relevant_excerpt(
            "short text here", 1200, ["text"])
        self.assertEqual(excerpt, "short text here")

    def test_deterministic(self):
        doc = long_doc()
        terms = ["failure", "limitations"]
        first = ac._relevant_excerpt(doc, 1200, terms)
        second = ac._relevant_excerpt(doc, 1200, terms)
        self.assertEqual(first, second)


class RedactInternalUrlsTest(unittest.TestCase):
    def test_searxng_base_and_loopback_redacted(self):
        os.environ["SEARXNG_URL"] = "http://172.18.0.2:8888"
        text = ("web search unavailable: gateway failed; searxng failed "
                "(http://172.18.0.2:8888/search?q=x); tried "
                "http://localhost:8001/health and http://127.0.0.1:8888/")
        red = ac._redact_internal_urls(text)
        self.assertNotIn("172.18.0.2", red)
        self.assertNotIn("localhost:8001", red)
        self.assertNotIn("127.0.0.1", red)
        self.assertIn("[infra-local]", red)

    def test_bare_word_and_public_url_preserved(self):
        text = ("the tutorial serves on localhost port 8000; see "
                "https://arxiv.org/abs/2510.22344v1 for the paper")
        red = ac._redact_internal_urls(text)
        self.assertIn("localhost port 8000", red)
        self.assertIn("https://arxiv.org/abs/2510.22344v1", red)


class AssessorRelevanceTest(unittest.TestCase):
    def test_assessor_selection_contains_relevant_window(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "[]"

        assess = ac.make_model_assessor(fake_client)
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e", "required": True}],
                "criteria": [{"id": "c", "label": "failure modes",
                              "required": True, "applies_to": ["e"]}],
                "initial_paths": []}
        evidence = {"https://example.org/paper": long_doc()}
        try:
            assess(plan, evidence, {}, {})
        except Exception:
            pass  # empty list return may raise inside validation; prompt kept
        self.assertIn("63.5", seen.get("prompt", ""),
                      "assessor prompt must carry the relevant window, "
                      "not just the head")

    def test_attempts_with_infra_url_are_redacted_in_prompt(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "[]"

        os.environ["SEARXNG_URL"] = "http://172.18.0.2:8888"
        assess = ac.make_model_assessor(fake_client)
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e", "required": True}],
                "criteria": [{"id": "c", "label": "something",
                              "required": True, "applies_to": ["e"]}],
                "initial_paths": []}
        attempts = {"c": [{"channel": "web",
                            "outcome": "failed",
                            "note": "searxng http://172.18.0.2:8888 down"}]}
        try:
            assess(plan, {"https://example.org/x": "some text here"},
                   {}, attempts)
        except Exception:
            pass
        self.assertNotIn("172.18.0.2", seen.get("prompt", ""))
        self.assertIn("[infra-local]", seen.get("prompt", ""))


class ArxivHtmlAndReadLevelTest(unittest.TestCase):
    def test_classify_arxiv_html_url(self):
        import academic_search as acad
        self.assertEqual(
            acad.classify_identifier("https://arxiv.org/html/2510.22344v1"),
            ("arxiv", "2510.22344v1"))

    def test_payload_propagates_read_level(self):
        import native_transport as nt
        res = SimpleNamespace(status="obtained", qualification="usable",
                              text="full text here", reason="",
                              read_level="full_text",
                              metadata={"read_level": "full_text"})
        payload = nt._payload(res)
        self.assertEqual(payload.get("read_level"), "full_text")
        _text, qual = ac._coerce_payload(payload, "https://example.org/x")
        self.assertEqual((qual or {}).get("read_level"), "full_text")


if __name__ == "__main__":
    unittest.main()
