#!/usr/bin/env python3
"""Assessor context: dimension-windowed excerpts and entity-first selection.

Regression source: accept11 (2026-10-29). 19 mandatory cells had evidence in
the corpus but no cited document: the assessor saw 24 docs/call, the entity
docs sat at the end of the order and were seen once, and a 1200-char excerpt
prioritized criterion terms so generic facts (license/version/cost) never
appeared. Excerpt groups + entity source_url slots + call stats fix the
mechanism, never the case names.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("assessor context test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl


def fact_doc():
    """Long doc: criterion terms dominate the head, facts live in the body."""
    head = "Performance benchmark results are discussed here. " * 80
    facts = ("License: MIT. Version: 0.6.0. Install with npm. "
             "Cost: free. Stars: 1200. " * 3)
    tail = "Closing remarks and acknowledgements. " * 40
    return head + "\n\n" + facts + "\n\n" + tail


class DimensionExcerptTest(unittest.TestCase):
    def test_anchor_group_surfaces_fact_window(self):
        excerpt, _stripped, windows = ac._relevant_excerpt(
            fact_doc(), 1200, ["performance", "benchmark", "latency"],
            groups={"criterio:c": ["performance", "benchmark"],
                    "ancora": list(ac._ANCHOR_FACT_TERMS)})
        self.assertIn("license: mit", excerpt.lower())
        self.assertIn("relevancia", windows)

    def test_without_groups_old_output_is_preserved(self):
        # Fixed case: short body is returned whole, same tuple as before.
        self.assertEqual(ac._relevant_excerpt("short text here", 1200,
                                              ["text"]),
                         ("short text here", 0, "corpo integral"))
        # Fixed case: no terms -> head cut, same label as before.
        doc = fact_doc()
        excerpt, stripped, windows = ac._relevant_excerpt(doc, 200, None)
        self.assertEqual(excerpt, doc[:200])
        self.assertEqual(stripped, len(doc) - 200)
        self.assertEqual(windows, "cabeca (sem termos ou corpo curto)")
        # No groups: the fact window is not forced into the excerpt.
        excerpt, _stripped, _windows = ac._relevant_excerpt(
            doc, 1200, ["performance", "benchmark", "latency"])
        self.assertNotIn("license: mit", excerpt.lower())


class EntityFirstSelectionTest(unittest.TestCase):
    def test_entity_source_url_gets_reserved_slot(self):
        urls = [f"https://example.org/doc/{i}" for i in range(30)]
        entity_url = urls[-1]  # last in insertion order: the accept11 defect
        evidence = {u: f"content about {u}" for u in urls}
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e0", "label": "Alpha", "required": True,
                              "discovered": True, "source_url": entity_url}],
                "criteria": [{"id": "c0", "label": "feature",
                              "required": True, "applies_to": ["e0"], "description": "Eixo feature: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": []}
        assess = ac.make_model_assessor(lambda prompt: "[]", max_docs=5)
        assess(plan, evidence, {}, {})
        selection = assess.last_selection["urls"]
        self.assertEqual(len(selection), 5)
        self.assertEqual(selection[0], entity_url)


class AssessRoundStatsTest(unittest.TestCase):
    def test_round_records_selection_and_missing_cells(self):
        url = "https://example.org/source"
        plan = {"plan_id": "p", "version": 1,
                "entities": [{"id": "e0", "label": "Alpha", "required": True}],
                "criteria": [{"id": "c0", "label": "feature one",
                              "required": True, "applies_to": ["e0"], "description": "Eixo feature one: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
                             {"id": "c1", "label": "feature two",
                              "required": True, "applies_to": ["e0"], "description": "Eixo feature two: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                "initial_paths": []}

        def client(prompt):
            return json.dumps([{
                "criterion_id": "c0", "entity_id": "e0", "state": "covered",
                "justification": "explicit evidence", "origin": "stub",
                "references": [{"url": url}]}])

        state = state_api.new_state("stats question")
        state["plan"] = plan
        state["evidence"] = {url: "Alpha substantive text about the feature"}
        state["qualification"] = {url: {
            "status": "usable", "excluded": False,
            "usable_text": "Alpha substantive text about the feature"}}
        assess = ac.make_model_assessor(client)
        ledger = cl.Ledger(plan)
        resolved = ac.resolve_adaptive("light")
        ac._assess_round(state, assess, ledger, resolved)
        record = state["assessments"][-1]
        self.assertEqual(record["round"], 0)
        self.assertRegex(record["at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(record["selection"], [url])
        self.assertEqual(record["cells_requested"], 2)
        self.assertEqual(record["cells_returned"], 1)
        self.assertEqual(record["missing_cells"], ["c1×e0"])
        # The omitted cell never overwrites prior state: c0 was applied.
        kept = [e for e in state["evaluations"]
                if e.get("criterion_id") == "c0"]
        self.assertEqual(kept[0]["state"], "covered")


if __name__ == "__main__":
    unittest.main()
