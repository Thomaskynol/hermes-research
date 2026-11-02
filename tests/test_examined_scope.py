"""Alcance examinado dos vereditos + reconciliação das métricas.

accept17 residuals: vereditos missing_dimension generalizavam excertos
(~0,4% dos chars) para o corpus; "10 analisados" (counters: docs únicos
na last_selection do assessor) vs "42 em excertos" (métrica de leitura
acumulada, com repetições entre chamadas) sem reconciliação.

Contratos: cada avaliação carrega o alcance examinado da chamada que a
produziu; o relatório distingue "não examinado por orçamento" de
"sem fonte no corpus (nada no corpus)"; a linha de Leitura separa
batches (com repetição) de docs únicos.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("scope test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl


def scope_state():
    st = state_api.new_state("scope question")
    st["plan"] = {
        "plan_id": "p", "version": 1,
        "entities": [
            {"id": "e0", "label": "AlphaWidget", "required": True},
            {"id": "e1", "label": "BetaGadget", "required": True},
            {"id": "e2", "label": "GammaTool", "required": True},
        ],
        "criteria": [{"id": "c0", "label": "custo de licenca",
                       "required": True,
                       "applies_to": ["e0", "e1", "e2"], "description": "Eixo custo de licenca: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
    }
    st["evidence"] = {
        "https://example.org/alpha/0": "AlphaWidget custo de licenca MIT",
        "https://example.org/alpha/1": "mais sobre alphawidget e licenca",
        "https://example.org/beta/0": "BetaGadget custo de licenca anual",
        "https://example.org/beta/1": "mais sobre betagadget e licenca",
    }
    st["qualification"] = {u: {"status": "usable", "excluded": False,
                               "usable_text": t}
                           for u, t in st["evidence"].items()}
    st["assessments"] = [{"round": 0,
                           "selection": ["https://example.org/alpha/0"],
                           "cells_requested": 3, "cells_returned": 1,
                           "missing_cells": ["c0×e1", "c0×e2"]}]
    st["reading"] = {"collected_chars": 10000, "excerpted_chars": 40,
                     "docs_collected": 2, "docs_excerpted": 1}
    return st


class ExaminedSnapshotTest(unittest.TestCase):
    def test_eval_carries_examined_scope(self):
        import json
        url = "https://example.org/alpha/0"
        st = scope_state()
        ledger = cl.Ledger(st["plan"])

        def model(prompt):
            return json.dumps([{
                "criterion_id": "c0", "entity_id": "e0", "state": "partial",
                "justification": "licenca MIT no excerto",
                "origin": "stub", "references": [{"url": url}]}])

        assess = ac.make_model_assessor(model)
        ac._assess_round(st, assess, ledger, ac.resolve_adaptive("light"))
        ev = [e for e in st["evaluations"]
              if e.get("criterion_id") == "c0"][0]
        examined = ev.get("examined") or {}
        self.assertGreaterEqual(examined.get("selection_docs", 0), 1)
        self.assertIn("excerpt_chars", examined)
        self.assertIn("collected_chars", examined)


class ScopeWordingTest(unittest.TestCase):
    def test_budget_vs_legitimate_unknown(self):
        scope = ac._criterion_scope(scope_state(),
                                    scope_state()["plan"]["criteria"][0])
        self.assertIn("orçamento", scope)
        self.assertIn("sem fonte no corpus", scope)
        self.assertNotIn("desconhecido-legítimo", scope)

    def test_scope_survives_s1_rebuild(self):
        import copy
        st = scope_state()
        block = {"criteria": [{"id": "c0", "label": "custo de licenca",
                               "state": "insufficient",
                               "justification": "j", "origin": "stub",
                               "references": [], "description": "Eixo custo de licenca: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]}
        ac._annotate_examined_scope(st, block)
        self.assertIn("alcance examinado", block["criteria"][0][
            "examined_scope"])
        # S1 rebuilds entries from evaluations (scope lost) -> re-annotate.
        rebuilt = {"criteria": [dict(c) for c in block["criteria"]]}
        for c in rebuilt["criteria"]:
            del c["examined_scope"]
        ac._annotate_examined_scope(st, rebuilt)
        self.assertIn("orçamento",
                      rebuilt["criteria"][0]["examined_scope"])

    def test_examined_cell_reports_doc_scope(self):
        scope = ac._criterion_scope(scope_state(),
                                    scope_state()["plan"]["criteria"][0])
        self.assertIn("1/2", scope)


class ReadingReconciliationTest(unittest.TestCase):
    def test_unique_docs_tracked_separately_from_batches(self):
        st = state_api.new_state("q")
        ac._accumulate_reading(
            st, 100, 2, urls=["https://a.example/1",
                              "https://a.example/2"])
        ac._accumulate_reading(
            st, 100, 2, urls=["https://a.example/2",
                              "https://a.example/3"])
        reading = st["reading"]
        self.assertEqual(reading["docs_excerpted"], 4)
        self.assertEqual(reading["docs_excerpted_unique"], 3)

    def test_report_line_reconciles_batches_vs_unique(self):
        import report_renderer as rr
        st = state_api.new_state("q")
        st["counters"] = {"counts": {"discovered": 5, "obtained": 4,
                                     "usable": 4, "analyzed": 2,
                                     "used_in_synthesis": 2, "cited": 1},
                          "documents": {}, "meta": {}, "relations": [],
                          "outside_corpus_citations": []}
        st["reading"] = {"collected_chars": 10000, "excerpted_chars": 40,
                         "docs_collected": 4, "docs_excerpted": 5,
                         "docs_excerpted_unique": 3}
        lines = rr._annex_section(st, rr._labels("pt-BR"), None, False, set())
        text = "\n".join(lines)
        self.assertIn("únicos", text)
        self.assertIn("repeti", text)


if __name__ == "__main__":
    unittest.main()
