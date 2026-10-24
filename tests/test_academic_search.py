#!/usr/bin/env python3
"""Busca acadêmica (OpenAlex + arXiv), offline por padrão.

Fixtures inline; transporte injetado; rede real bloqueada por audithook. Testes
opt-in usam HERMES_REAL_NETWORK=1.

Run: python3 -m unittest tests.test_academic_search -v
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import academic_search as ac  # noqa: E402


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


if os.environ.get("HERMES_REAL_NETWORK") != "1":
    sys.addaudithook(deny_network)

OPENALEX_WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1234/example.1",
    "title": "Retrieval Augmented Generation for Tests",
    "publication_year": 2023,
    "authorships": [
        {"author": {"display_name": "Ada Lovelace"}},
        {"author": {"display_name": "Alan Turing"}},
    ],
    "primary_location": {"source": {"display_name": "Journal of Fixtures"}},
    "cited_by_count": 42,
    "open_access": {"is_oa": True, "oa_url": "https://repo.example/paper"},
    "type": "article",
    "abstract_inverted_index": {
        "We": [0], "study": [1], "retrieval": [2], "augmented": [3],
        "generation": [4], "offline.": [5],
    },
}

OPENALEX_WORK_NO_ABSTRACT = {
    "id": "https://openalex.org/W2",
    "doi": "https://doi.org/10.1234/example.2",
    "title": "Metadata Only Work",
    "publication_year": 2020,
    "authorships": [],
    "cited_by_count": 1,
    "open_access": {"is_oa": False},
}

ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <published>2023-01-30T00:00:00Z</published>
    <title>An arXiv Fixture Paper</title>
    <summary>This is the abstract of the arXiv fixture paper.</summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <arxiv:doi>10.1234/arxiv.fixture</arxiv:doi>
    <arxiv:journal_ref>Fixture Journal</arxiv:journal_ref>
  </entry>
</feed>
"""

ARXIV_ERROR_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/9999.99999</id>
    <title>Error</title>
    <summary>No paper found for the given identifier.</summary>
  </entry>
</feed>
"""


def json_response(payload, status=200):
    return {"status": status, "text": json.dumps(payload), "error": None, "url": ""}


def text_response(text, status=200):
    return {"status": status, "text": text, "error": None, "url": ""}


def route(routes):
    """Transporte fake que escolhe a resposta pelo marcador presente na URL."""
    def _transport(url, timeout):
        for marker, response in routes.items():
            if marker in url:
                return response
        return {"status": 404, "text": "", "error": "HTTP 404", "url": url}
    return _transport


class AcademicFetchTests(unittest.TestCase):
    def test_pdf_is_fetched_as_binary_and_html_as_text(self):
        calls = []

        def fake_get(url, timeout, *, binary=False, headers=None):
            calls.append((url, binary))
            return {"status": 200, "text": "", "body": b"%PDF-1.4", "error": None}

        with mock.patch.object(ac, "_http_get", fake_get):
            ac._academic_fetch("https://example.org/paper.pdf", 5)
            ac._academic_fetch("https://arxiv.org/pdf/2301.12345", 5)
            ac._academic_fetch("https://example.org/paper", 5)
        self.assertEqual([binary for _, binary in calls], [True, True, False])

    def test_pdf_syntax_is_not_plausible_text(self):
        self.assertFalse(ac._plausible_text("%PDF-1.3\n1 0 obj\nendobj\nxref"))
        self.assertFalse(ac._plausible_text("endobj " * 200))
        self.assertTrue(ac._plausible_text("A real paper sentence with words. " * 40))


class ParsingTests(unittest.TestCase):
    def test_openalex_fields_and_inverted_abstract(self):
        works = ac.parse_openalex(json.dumps({"results": [OPENALEX_WORK]}))
        self.assertEqual(len(works), 1)
        work = works[0]
        self.assertEqual(work["doi"], "10.1234/example.1")
        self.assertEqual(work["title"], "Retrieval Augmented Generation for Tests")
        self.assertEqual(work["year"], 2023)
        self.assertEqual(work["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertEqual(work["venue"], "Journal of Fixtures")
        self.assertEqual(work["cited_by_count"], 42)
        self.assertTrue(work["is_oa"])
        self.assertEqual(work["abstract"],
                         "We study retrieval augmented generation offline.")
        self.assertEqual(work["oa_url"], "https://repo.example/paper")

    def test_arxiv_fields(self):
        works = ac.parse_arxiv(ARXIV_FEED)
        self.assertEqual(len(works), 1)
        work = works[0]
        self.assertEqual(work["arxiv_id"], "2301.12345v1")
        self.assertEqual(work["title"], "An arXiv Fixture Paper")
        self.assertEqual(work["year"], 2023)
        self.assertEqual(work["authors"], ["Ada Lovelace", "Grace Hopper"])
        self.assertEqual(work["doi"], "10.1234/arxiv.fixture")
        self.assertEqual(work["venue"], "Fixture Journal")
        self.assertTrue(work["is_oa"])
        self.assertIn("abstract of the arXiv fixture", work["abstract"])

    def test_arxiv_error_entry_is_not_a_work(self):
        with self.assertRaises(ValueError):
            ac.parse_arxiv(ARXIV_ERROR_FEED)

    def test_identifier_forms(self):
        cases = {
            "10.1038/nature12373": ("doi", "10.1038/nature12373"),
            "https://doi.org/10.1038/nature12373": ("doi", "10.1038/nature12373"),
            "doi:10.1038/nature12373": ("doi", "10.1038/nature12373"),
            "W2741809807": ("openalex", "W2741809807"),
            "https://openalex.org/W2741809807": ("openalex", "W2741809807"),
            "2301.12345": ("arxiv", "2301.12345"),
            "arXiv:2301.12345v2": ("arxiv", "2301.12345v2"),
            "https://arxiv.org/abs/2301.12345": ("arxiv", "2301.12345"),
            "https://arxiv.org/pdf/2301.12345.pdf": ("arxiv", "2301.12345"),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(ac.classify_identifier(value), expected)
        self.assertIsNone(ac.classify_identifier("not-an-id"))


class SearchWorksTests(unittest.TestCase):
    def test_openalex_search(self):
        result = ac.search_works("retrieval augmented generation", limit=5,
                                 transport=lambda u, t: json_response(
                                     {"results": [OPENALEX_WORK]}))
        self.assertTrue(result.ok)
        self.assertEqual(result.operation, "academic_search")
        self.assertEqual(result.channel, "openalex")
        self.assertEqual(result.status, ac.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ac.QUAL_METADATA)
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.metadata["count"], 1)
        self.assertEqual(result.metadata["works"][0]["doi"], "10.1234/example.1")
        self.assertEqual(result.text, "")
        self.assertIn("metadata_and_abstract_only_no_full_text", result.limits)

    def test_arxiv_search(self):
        result = ac.search_works("retrieval", source="arxiv", limit=3,
                                 transport=lambda u, t: text_response(ARXIV_FEED))
        self.assertTrue(result.ok)
        self.assertEqual(result.channel, "arxiv")
        self.assertEqual(result.metadata["works"][0]["arxiv_id"], "2301.12345v1")
        self.assertIn("export.arxiv.org", result.evidence["url"])

    def test_both_sources_merge_and_dedupe(self):
        arxiv_same_doi = ARXIV_FEED.replace(
            "10.1234/arxiv.fixture", "10.1234/example.1")
        transport = route({
            "api.openalex.org": json_response({"results": [OPENALEX_WORK]}),
            "export.arxiv.org": text_response(arxiv_same_doi),
        })
        result = ac.search_works("q", source="both", transport=transport)
        self.assertTrue(result.ok)
        self.assertEqual(result.channel, "academic")
        self.assertEqual(result.metadata["count"], 1, "mesmo DOI não duplica")
        self.assertEqual(result.metadata["sources_ok"], ["openalex", "arxiv"])

    def test_one_source_failure_is_partial(self):
        transport = route({
            "api.openalex.org": json_response({"results": [OPENALEX_WORK]}),
            "export.arxiv.org": text_response("upstream error", status=500),
        })
        result = ac.search_works("q", source="both", transport=transport)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ac.STATUS_PARTIAL)
        self.assertEqual(result.metadata["sources_ok"], ["openalex"])
        self.assertTrue(result.metadata["sources_failed"])
        self.assertIn("partial_source_failure", result.reason)

    def test_all_sources_fail(self):
        transport = route({
            "api.openalex.org": {"status": None, "text": "", "error": "URLError: refused"},
            "export.arxiv.org": {"status": None, "text": "", "error": "URLError: refused"},
        })
        result = ac.search_works("q", source="both", transport=transport)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ac.STATUS_FAILED)
        self.assertEqual(result.reason, "academic_unavailable")

    def test_empty_results_is_unavailable(self):
        result = ac.search_works("q", transport=lambda u, t: json_response({"results": []}))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ac.STATUS_UNAVAILABLE)
        self.assertEqual(result.reason, "no_results")

    def test_invalid_source_and_empty_query(self):
        self.assertEqual(ac.search_works("q", source="semantic_scholar").reason,
                         "unsupported_source")
        self.assertEqual(ac.search_works("  ").reason, "empty_query")


class ReadWorkTests(unittest.TestCase):
    def test_doi_returns_abstract_level(self):
        seen = {}

        def transport(url, timeout):
            seen["url"] = url
            return json_response(OPENALEX_WORK)

        result = ac.read_work("10.1234/example.1", transport=transport)
        self.assertTrue(result.ok)
        self.assertEqual(result.channel, "openalex")
        self.assertEqual(result.status, ac.STATUS_PARTIAL)
        self.assertEqual(result.metadata["read_level"], "abstract")
        self.assertEqual(result.qualification, ac.QUAL_PARTIAL)
        self.assertIn("api.openalex.org/works/https://doi.org/10.1234/example.1",
                      seen["url"])
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.text, "", "abstract não vira texto completo")
        self.assertIn("retrieval augmented generation", result.metadata["abstract"])
        self.assertEqual(result.title, "Retrieval Augmented Generation for Tests")

    def test_openalex_id_lookup(self):
        seen = {}

        def transport(url, timeout):
            seen["url"] = url
            return json_response(OPENALEX_WORK)

        result = ac.read_work("https://openalex.org/W2741809807", transport=transport)
        self.assertTrue(result.ok)
        self.assertTrue(seen["url"].endswith("/W2741809807"))

    def test_arxiv_id_returns_abstract_level(self):
        result = ac.read_work("2301.12345", transport=lambda u, t: text_response(ARXIV_FEED))
        self.assertTrue(result.ok)
        self.assertEqual(result.channel, "arxiv")
        self.assertEqual(result.metadata["read_level"], "abstract")
        self.assertEqual(result.metadata["arxiv_id"], "2301.12345v1")
        self.assertEqual(result.metadata["doi"], "10.1234/arxiv.fixture")

    def test_metadata_only_when_no_abstract(self):
        result = ac.read_work("10.1234/example.2",
                              transport=lambda u, t: json_response(OPENALEX_WORK_NO_ABSTRACT))
        self.assertTrue(result.ok)
        self.assertEqual(result.metadata["read_level"], "metadata")
        self.assertEqual(result.qualification, ac.QUAL_METADATA)
        self.assertIsNone(result.metadata["abstract"])

    def test_not_found(self):
        result = ac.read_work("10.1234/missing",
                              transport=lambda u, t: {"status": 404, "text": "",
                                                      "error": "HTTP 404"})
        self.assertFalse(result.ok)
        self.assertEqual(result.status, ac.STATUS_UNAVAILABLE)
        self.assertEqual(result.reason, "work_not_found")
        self.assertEqual(result.http_status, 404)

    def test_unsupported_identifier(self):
        result = ac.read_work("https://example.org/paper")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "unsupported_identifier")

    def test_full_text_via_open_access_html(self):
        transport = route({
            "api.openalex.org": json_response(OPENALEX_WORK),
            "repo.example/paper": text_response(
                "<html><body><article>" + "full text body " * 80 + "</article></body></html>"),
        })
        result = ac.read_work("10.1234/example.1", full_text=True, transport=transport)
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ac.STATUS_OBTAINED)
        self.assertEqual(result.qualification, ac.QUAL_USABLE)
        self.assertEqual(result.metadata["read_level"], "full_text")
        self.assertIn("full text body", result.text)
        self.assertGreater(result.chars, ac.FULLTEXT_MIN_CHARS)
        self.assertEqual(result.evidence["read_scope"], "full_text")

    def test_full_text_without_free_location_is_honest(self):
        work = dict(OPENALEX_WORK)
        work.pop("open_access", None)
        result = ac.read_work("10.1234/example.1", full_text=True,
                              transport=lambda u, t: json_response(work))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, ac.STATUS_PARTIAL)
        self.assertEqual(result.metadata["read_level"], "abstract")
        self.assertEqual(result.qualification, ac.QUAL_PARTIAL)
        self.assertTrue(result.reason.startswith("full_text_unavailable"))
        self.assertIn("no_free_full_text_location", result.limits)

    def test_full_text_pdf_without_extractor_is_a_declared_limit(self):
        work = dict(OPENALEX_WORK)
        work.pop("open_access", None)
        work["best_oa_location"] = {"pdf_url": "https://repo.example/paper.pdf"}
        transport = route({
            "api.openalex.org": json_response(work),
            "paper.pdf": {"status": 200, "body": b"%PDF-1.4 fake", "text": "",
                          "error": None},
        })
        result = ac.read_work("10.1234/example.1", full_text=True, transport=transport)
        self.assertEqual(result.status, ac.STATUS_PARTIAL)
        self.assertEqual(result.metadata["read_level"], "abstract")
        self.assertTrue(result.reason.startswith("full_text_unavailable"))
        self.assertTrue(any("pdf" in limit for limit in result.limits))

    def test_arxiv_html_error_page_is_not_full_text(self):
        transport = route({
            "export.arxiv.org/api": text_response(ARXIV_FEED),
            "arxiv.org/html/2301.12345v1": text_response(
                "<html><body><p>No HTML for '2301.12345v1'</p>"
                "<p>HTML is not available for this paper. Use the PDF.</p></body></html>"),
            "arxiv.org/pdf/2301.12345v1": {"status": 200, "body": b"%PDF-1.4 fake",
                                            "text": "", "error": None},
        })
        result = ac.read_work("2301.12345v1", full_text=True, transport=transport)
        self.assertEqual(result.status, ac.STATUS_PARTIAL)
        self.assertEqual(result.metadata["read_level"], "abstract")
        self.assertTrue(result.reason.startswith("full_text_unavailable"))

    def test_arxiv_full_text_via_html(self):
        transport = route({
            "export.arxiv.org/api": text_response(ARXIV_FEED),
            "arxiv.org/html/2301.12345v1": text_response(
                "<html><body>" + "arxiv full text " * 80 + "</body></html>"),
        })
        result = ac.read_work("arXiv:2301.12345v1", full_text=True, transport=transport)
        self.assertTrue(result.ok)
        self.assertEqual(result.metadata["read_level"], "full_text")
        self.assertIn("arxiv full text", result.text)


@unittest.skipUnless(os.environ.get("HERMES_REAL_NETWORK") == "1",
                     "rede real: defina HERMES_REAL_NETWORK=1")
class RealAcademicTests(unittest.TestCase):
    def test_openalex_real_search(self):
        result = ac.search_works("retrieval augmented generation", limit=3,
                                 source="openalex", timeout=60)
        self.assertTrue(result.ok, result.reason)
        self.assertGreaterEqual(result.metadata["count"], 1)
        self.assertEqual(result.http_status, 200)

    def test_arxiv_real_search(self):
        result = ac.search_works("retrieval augmented generation", limit=3,
                                 source="arxiv", timeout=60)
        self.assertTrue(result.ok, result.reason)
        self.assertGreaterEqual(result.metadata["count"], 1)

    def test_real_doi_read(self):
        result = ac.read_work("10.1038/nature12373", timeout=60)
        self.assertTrue(result.ok, result.reason)
        self.assertIn(result.metadata["read_level"], {"abstract", "full_text"})
        self.assertEqual(result.http_status, 200)


if __name__ == "__main__":
    unittest.main()
