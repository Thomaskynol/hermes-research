#!/usr/bin/env python3
"""Product core: six-stage counters, real concurrency, quantitative records,
Portuguese report, four independent verifications, run manifest and state
retrocompatibility.

Offline: network is blocked by an audithook; the coordinator, ledger,
assessor/writer and persistence are the REAL code. Only search/fetch/model
transports are simulated.

Run: python3 -m unittest discover -s tests -p test_product_core.py -v
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl
import quantitative as quant
import report_renderer as renderer
import research_counters as counters
import run_budget as rb
import run_manifest as manifest
import verification_report as verify


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("product core tests: external network is forbidden")


sys.addaudithook(offline_guard)

A = "https://example.org/core/a"
B = "https://example.org/core/b"
C = "https://example.org/core/c"
D = "https://example.org/core/d"
E = "https://example.org/core/e"
YT = "https://youtube.com/watch?v=core123"
META = "https://arxiv.org/abs/2401.00001"
OUTSIDE = "https://invented.example/not-in-corpus"


def plan(n=2):
    return {
        "plan_id": "core-plan", "version": 1,
        "question": "Comparar ferramentas do núcleo",
        "entities": [{"id": f"e{i}", "label": f"entidade {i}", "required": True, "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}
                     for i in range(n)],
        "criteria": [{"id": f"c{i}", "label": f"critério {i}",
                      "required": True, "applies_to": [f"e{i}"], "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}
                     for i in range(n)],
        "initial_paths": ["consulta inicial"],
    }


def corpus_search(docs):
    def search(target, channel="web"):
        return [{"url": url} for url in docs]
    return search


def corpus_fetch(docs, overrides=None):
    overrides = dict(overrides or {})

    def fetch(url):
        if url in overrides:
            return overrides[url]
        return docs.get(url, "conteúdo de " + url)
    return fetch


def model_transport(evals):
    def model(prompt):
        if "Você avalia evidências" in prompt:
            return json.dumps(evals)
        return json.dumps([])
    return model


def writer_with(cited_urls, included):
    def write(view):
        text = ("Resumo executivo com evidência em " + ", ".join(cited_urls)
                + f". Referência inventada: {OUTSIDE}.")
        return text, {"included_urls": list(included), "cuts": "teste",
                      "fallback": False}
    return write


def run_core(*, profile="light", writer=None, assessor=None, overrides=None,
             run_dir=None, quantitative=None):
    docs = {A: "Página A: fato verificável COVER:c0",
            B: "Página B: detalhe comparativo COVER:c1",
            C: "Página C: texto sem relação suficiente",
            D: "Página D: contexto adicional COVER:c1",
            E: "Página E: contexto extra"}
    overrides = {"max_rounds": 0, **(overrides or {})}
    evals = [
        {"criterion_id": "c0", "state": "covered",
         "justification": "fato verificável na página A",
         "origin": "avaliação simulada", "references": [{"url": A}]},
        {"criterion_id": "c1", "state": "insufficient",
         "justification": "evidência insuficiente para o critério 1",
         "origin": "avaliação simulada", "references": []},
    ]
    return ac.run_adaptive(
        "Comparar ferramentas do núcleo", profile=profile, plan=plan(2),
        search_fn=corpus_search([A, B, A, C, YT, META, D, E]),
        fetch_fn=corpus_fetch(
            docs, {C: {"text": docs[C], "status": "insufficient",
                       "excluded": True, "usable_text": ""},
                   YT: "[description]\nVídeo sobre as ferramentas",
                   META: {"text": "Title: X\nAuthors: Y\nAbstract: Z",
                          "status": "metadata_only", "excluded": True,
                          "usable_text": ""}}),
        assess_fn=assessor or ac.make_model_assessor(
            model_transport(evals), max_docs=3),
        writer_fn=writer or writer_with([A], [A, B]),
        auditor_fn=lambda report, evidence: {"enabled": False,
                                             "accepted": False},
        clock=time.monotonic, run_dir=run_dir,
        run_id="core-run" if run_dir else "",
        overrides=overrides, quantitative=quantitative)


class CountersTest(unittest.TestCase):
    def test_six_stages_with_duplicate_video_and_academic_metadata(self):
        result = run_core(profile="medium")
        counts = result["counters"]["counts"]
        docs = result["counters"]["documents"]
        self.assertEqual(counts["discovered"], 7)   # A B C YT META D E
        self.assertEqual(counts["obtained"], 5)     # A B C D E (text)
        self.assertEqual(counts["usable"], 4)       # A B D E (C insufficient)
        self.assertEqual(counts["analyzed"], 3)     # real assessor selection
        self.assertEqual(counts["used_in_synthesis"], 2)
        self.assertEqual(counts["cited"], 1)        # only A is in the body
        self.assertEqual(len(set(counts.values())), 6,
                         f"stages must be distinguishable: {counts}")
        # Duplicate URL in search results counts once.
        self.assertEqual(docs["discovered"].count(A), 1)
        # Video without transcript and academic metadata never count as read.
        self.assertNotIn(YT, docs["obtained"])
        self.assertNotIn(META, docs["obtained"])
        self.assertIn(YT, docs["discovered"])
        self.assertIn(META, docs["discovered"])
        # analyzed = documents really sent to the assessor (A, B, C).
        self.assertEqual(sorted(docs["analyzed"]), sorted([A, B, C]))
        self.assertEqual(sorted(docs["used_in_synthesis"]), sorted([A, B]))
        self.assertEqual(docs["cited"], [A])

    def test_versions_and_republication_relations(self):
        state = state_api.new_state("relações")
        ac.incorporate(state, A, "texto original da versão 1", "op-1", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": "texto"})
        ac.incorporate(state, A, "texto revisado da versão 2", "op-2", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": "texto"})
        ac.incorporate(state, B, "texto revisado da versão 2", "op-3", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": "texto"})
        snapshot = counters.counters_snapshot(state)
        kinds = {rel["kind"] for rel in snapshot["relations"]}
        self.assertIn("version", kinds)
        self.assertIn("duplicate", kinds)
        # Two distinct versions of one URL are one document, one obtained.
        self.assertEqual(snapshot["counts"]["obtained"], 1)


class ConcurrencyTest(unittest.TestCase):
    def _ops(self, n=4):
        return [{"op_id": f"op-{i}", "kind": "gap_query", "channel": "web",
                 "target": f"t{i}", "criterion_id": "", "status": "in-progress"}
                for i in range(n)]

    def _search(self):
        def search(target, channel="web"):
            time.sleep(0.2)
            return [{"url": f"https://example.org/conc/{target}"}]
        return search

    def _run(self, concurrency, budget=None):
        state = state_api.new_state("concorrência")
        ops = self._ops(4)
        for op in ops:
            state["pending_ops"].append(dict(op))
        resolved = ac.resolve_adaptive("light", {"concurrency": concurrency,
                                                 "time_s": 60})
        budget = budget or rb.Budget({"queries": 20, "extractions": 20,
                                      "time_s": 60}, profile="light")
        t_start = time.monotonic()
        wall = time.perf_counter()
        ac._execute_ops(state, ops, self._search(),
                        lambda url: "conteúdo real de " + url,
                        budget, resolved, time.monotonic, t_start, None, 0)
        elapsed = time.perf_counter() - wall
        return state, ops, budget, elapsed

    def test_parallel_is_really_faster_and_ordered(self):
        parallel, ops4, _, fast = self._run(4)
        sequential, ops1, _, slow = self._run(1)
        self.assertLess(fast, 0.5, f"concurrency=4 took {fast:.3f}s")
        self.assertGreater(slow, 0.7, f"concurrency=1 took {slow:.3f}s")
        expected = [f"https://example.org/conc/t{i}" for i in range(4)]
        self.assertEqual(list(parallel["evidence"]), expected)
        self.assertEqual(list(sequential["evidence"]), expected)
        self.assertEqual([o["outcome"] for o in ops4],
                         ["new_useful"] * 4)

    def test_shared_budget_never_exceeds_ceiling(self):
        budget = rb.Budget({"queries": 2, "extractions": 20, "time_s": 60},
                           profile="light")
        state, ops, budget, _ = self._run(4, budget=budget)
        self.assertEqual(budget.snapshot()["used"]["queries"], 2)
        self.assertEqual(state["consumption"]["queries"], 2)
        outcomes = [o["outcome"] for o in ops]
        self.assertEqual(outcomes.count("budget"), 2, outcomes)
        self.assertEqual(len(state["evidence"]), 2)

    def test_time_exhausted_marks_unfinished_ops_as_time(self):
        state = state_api.new_state("tempo")
        ops = self._ops(2)
        for op in ops:
            state["pending_ops"].append(dict(op))
        resolved = ac.resolve_adaptive("light", {"concurrency": 4, "time_s": 0})
        calls = []

        def search(target, channel="web"):
            calls.append(target)
            return []

        budget = rb.Budget({"queries": 20, "extractions": 20, "time_s": 60},
                           profile="light")
        ac._execute_ops(state, ops, search, lambda url: "conteúdo",
                        budget, resolved, time.monotonic, time.monotonic(),
                        None, 0)
        self.assertEqual([o["outcome"] for o in ops], ["time", "time"])
        self.assertEqual(calls, [], "no transport after the deadline")


class QuantitativeTest(unittest.TestCase):
    def test_percent_change_reproducible_bit_for_bit(self):
        spec = {"formula_id": "preco-2026", "op": "percent_change",
                "old": 120.0, "new": 150.0, "units": {"currency": "BRL"},
                "assumptions": ["preços da mesma data"],
                "source_urls": [A, B]}
        first = quant.compute(spec, computed_at="2026-10-24T00:00:00Z")
        second = quant.compute(spec, computed_at="2026-10-24T00:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(first["result"], 25.0)
        for key in ("formula_id", "inputs", "units", "assumptions", "result",
                    "computed_at", "source_urls"):
            self.assertIn(key, first)
        json.dumps(first)  # serialisable
        block = quant.to_markdown_block(first)
        self.assertIn("preco-2026", block)
        self.assertIn("120.0", block)

    def test_declared_operations_and_unit_conversion(self):
        self.assertEqual(quant.compute(
            {"formula_id": "m", "op": "mean", "values": [1, 2, 3]})["result"],
            2.0)
        self.assertEqual(quant.compute(
            {"formula_id": "med", "op": "median",
             "values": [1, 2, 3, 4]})["result"], 2.5)
        self.assertAlmostEqual(quant.compute(
            {"formula_id": "wm", "op": "weighted_mean",
             "values": [10, 20], "weights": [1, 3]})["result"], 17.5)
        self.assertAlmostEqual(quant.compute(
            {"formula_id": "cg", "op": "compound_growth",
             "initial": 100, "final": 121, "periods": 2})["result"], 10.0)
        converted = quant.compute(
            {"formula_id": "km-mi", "op": "unit_convert", "quantity": "length",
             "from": "km", "to": "mi", "value": 10})
        self.assertAlmostEqual(converted["result"], 6.2137119223733395)
        self.assertEqual(converted["units"]["to"], "mi")

    def test_run_report_includes_reproducible_calculation(self):
        spec = {"formula_id": "preco-2026", "op": "percent_change",
                "old": 120.0, "new": 150.0, "units": {"currency": "BRL"},
                "assumptions": ["preços da mesma data"],
                "source_urls": [A, B]}
        with tempfile.TemporaryDirectory() as tmp:
            result = run_core(run_dir=tmp, quantitative=[spec])
            state = state_api.load(tmp, "core-run")
        self.assertIn("4. Comparações e cálculos", result["report_markdown"])
        self.assertIn("preco-2026", result["report_markdown"])
        self.assertEqual(result["quantitative"][0]["result"], 25.0)
        self.assertEqual(state["quantitative"][0]["result"], 25.0)
        # Invalid specs are recorded as a note, never silently computed.
        with tempfile.TemporaryDirectory() as tmp:
            invalid = run_core(run_dir=tmp, quantitative=[
                {"formula_id": "bad", "op": "ratio", "numerator": 1,
                 "denominator": 0}])
            invalid_state = state_api.load(tmp, "core-run")
        self.assertEqual(invalid["quantitative"], [])
        self.assertTrue(any("quantitative spec rejected" in note
                            for note in invalid_state["notes"]))

    def test_invalid_inputs_raise_explicit_value_error(self):
        with self.assertRaises(ValueError):
            quant.compute({"formula_id": "x", "op": "percent_change",
                           "old": 0, "new": 5})
        with self.assertRaises(ValueError):
            quant.compute({"formula_id": "x", "op": "ratio",
                           "numerator": 1, "denominator": 0})
        with self.assertRaises(ValueError):
            quant.compute({"formula_id": "x", "op": "mean",
                           "values": [1, float("nan")]})
        with self.assertRaises(ValueError):
            quant.compute({"formula_id": "x", "op": "unit_convert",
                           "quantity": "currency", "from": "BRL", "to": "USD",
                           "value": 1})
        with self.assertRaises(ValueError):
            quant.compute({"formula_id": "x", "op": "__import__"})


class ReportTest(unittest.TestCase):
    def test_report_structure_and_corpus_only_sources(self):
        # Rebuild the same state by re-running with a directory, then render.
        with tempfile.TemporaryDirectory() as tmp:
            result = run_core(run_dir=tmp)
            state = state_api.load(tmp, "core-run")
            markdown = result["report_markdown"]
            for section in ("1. Resposta direta", "2. Escopo", "3. Achados",
                            "5. Limitações", "6. Conclusão", "7. Fontes"):
                self.assertIn(section, markdown)
            annex = (Path(tmp) / "technical_annex.md").read_text()
            self.assertIn("8. Anexo", annex)
            self.assertIn("9. Encerramento", annex)
            self.assertNotIn("8. Anexo", markdown)
            self.assertIn("technical_annex.md", markdown)
            self.assertIn("Motivo de parada", markdown)
            self.assertIn("rounds", markdown.lower())
            self.assertIn("[1]", markdown)
            self.assertIn("discovered", annex)  # counters table
            self.assertIn("execution", annex)   # verifications table
            sources_block = markdown.split("## 7. Fontes", 1)[1].split(
                "## 8.", 1)[0]
            self.assertNotIn(OUTSIDE, sources_block,
                             "out-of-corpus citation became a source")
            self.assertNotIn(YT, sources_block,
                             "video without transcript became a source")
            self.assertNotIn(META, sources_block,
                             "academic metadata became a source")
            self.assertIn(A, sources_block)
            self.assertTrue(any("fora do corpus" in note
                                for note in state["notes"]))
            # gap / uncertainty text is present, never hidden.
            self.assertIn("critério 1", markdown)
            self.assertIn("parcial", markdown.lower())
            # persisted artifacts
            self.assertTrue((Path(tmp) / "report.md").is_file())
            self.assertTrue((Path(tmp) / "verification.json").is_file())
            self.assertEqual(Path(result["report_path"]),
                             Path(tmp) / "report.md")
            self.assertTrue(Path(result["report_path"]).is_file())

    def test_light_is_shorter_than_deep(self):
        with tempfile.TemporaryDirectory() as tmp:
            light = run_core(profile="light", run_dir=tmp)
        with tempfile.TemporaryDirectory() as tmp:
            deep = run_core(profile="deep", run_dir=tmp)
        self.assertLess(len(light["report_markdown"]),
                        len(deep["report_markdown"]))
        self.assertIn("Limitações", light["report_markdown"])
        self.assertIn("parcial", light["report_markdown"].lower())


class VerificationTest(unittest.TestCase):
    def _state(self):
        state = state_api.new_state("verificação", run_id="verify-run")
        plan_ = plan(2)
        state["plan"] = plan_
        state["evidence"] = {A: "Evidência real A", B: "Evidência real B"}
        state["qualification"] = {
            A: {"status": "usable", "excluded": False, "usable_text": "A"},
            B: {"status": "usable", "excluded": False, "usable_text": "B"}}
        ledger = cl.Ledger(plan_, run_id="verify-run")
        ledger.set_corpus(state["evidence"], state["qualification"])
        ledger.evaluate("c0", "covered", "fato A", "auditoria",
                        [{"url": A}])
        state["question_coverage"] = ledger.compute()
        state["pending_ops"] = [
            {"op_id": "1", "status": "done", "outcome": "new_useful",
             "channel": "web"},
            {"op_id": "2", "status": "failed", "outcome": "failed",
             "channel": "arxiv"}]
        state["stop"] = {"reason": "rounds", "partial": True, "detail": "x"}
        state["semantic"] = {
            "enabled": True, "accepted": True, "claims": 2,
            "claims_reviewed": 2, "verdict_state": "aceito",
            "verdicts": [{"id": "a", "verdict": "sustained", "valid_count": 3},
                         {"id": "b", "verdict": "sustained", "valid_count": 3}],
            "summary": {"votes": 3, "technical_failures": 0},
            "coverage": {"counts": {"blocks_total": 1, "blocks_processed": 1}}}
        return state, ledger

    def test_four_dimensions_are_independent(self):
        state, ledger = self._state()
        execution = verify.verify_execution(state)
        question = verify.verify_question(state, ledger)
        review = verify.verify_review(state, state["semantic"])
        # consultado vs mencionado: so evidence pondera unknown; bare e
        # utilidade, markdown e evidencia (fora do corpus falha)
        support = verify.verify_support(
            state, f"Conclusão sustentada em [{A}]({A}) e em [fora]({OUTSIDE}).",
            state["semantic"])
        self.assertEqual(execution["status"], "ok")
        self.assertEqual(question["status"], "partial")
        self.assertEqual(review["status"], "ok")
        self.assertEqual(support["status"], "failed")
        self.assertIn(OUTSIDE, support["evidence"]["citations_unknown"])
        # Semantic approval never promotes question coverage.
        self.assertNotEqual(question["status"], "ok")
        self.assertTrue(question["evidence"]["required_pending"])
        aggregate = verify.verify_all(state, ledger=ledger,
                                      audit=state["semantic"],
                                      report_text=f"Ver {A}.")
        self.assertEqual(aggregate["overall"], "partial")
        self.assertEqual(set(aggregate["dimensions"]),
                         {"execution", "question", "review", "support"})

    def test_support_ok_only_with_resolved_citations(self):
        state, ledger = self._state()
        support = verify.verify_support(
            state, f"Conclusão sustentada em {A} e {B}.", state["semantic"])
        self.assertEqual(support["status"], "ok")
        empty = verify.verify_support(state, "Sem citações.",
                                      {"enabled": False})
        self.assertEqual(empty["status"], "not_run")


class ManifestTest(unittest.TestCase):
    def test_manifest_marks_simulation_redacts_and_keeps_unknown(self):
        state = state_api.new_state("manifesto", run_id="manifest-run")
        state["consumption"] = {"queries": 3, "tokens": "unknown",
                                "cost_usd": "unknown"}
        resolved = ac.resolve_adaptive("light")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "report.md").write_text("relatório", encoding="utf-8")
            path = manifest.write_manifest(
                tmp, state, resolved=resolved,
                model_info={"planner": "declared/model-x",
                            "api_key": "sk-super-secret"},
                environment={"simulated": True, "network": "blocked"},
                artifacts=["report.md"])
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIs(payload["simulated"] if "simulated" in payload else
                      payload["environment"]["simulated"], True)
        self.assertNotIn("sk-super-secret", json.dumps(payload))
        self.assertEqual(payload["models"]["api_key"], "[redacted]")
        self.assertEqual(payload["consumption"]["tokens"], "unknown")
        self.assertEqual(payload["consumption"]["cost_usd"], "unknown")
        self.assertTrue(payload["module_hashes"])
        self.assertEqual(payload["artifacts"][0]["exists"], True)
        self.assertTrue(payload["artifacts"][0]["sha256"])

    def test_manifest_requires_explicit_simulation_flag(self):
        state = state_api.new_state("manifesto")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                manifest.write_manifest(tmp, state, resolved={},
                                        environment={"network": "blocked"})


class StateRetrocompatTest(unittest.TestCase):
    def test_old_state_loads_with_new_defaults(self):
        old = {"schema": 1, "run_id": "old-run", "question": "antiga",
               "mode": "adaptive", "profile": "light",
               "evidence": {}, "segments": [], "qualification": {},
               "rounds": [], "consumption": {}, "pending_ops": [],
               "attempts": {}, "discovery": {"candidates": [], "open": False},
               "notes": [], "report": {}, "stop": {"reason": None}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "state.json").write_text(json.dumps(old),
                                                  encoding="utf-8")
            loaded = state_api.load(tmp, "old-run")
            self.assertIn("counters", loaded)
            self.assertEqual(loaded["counters"]["counts"]["discovered"], 0)
            self.assertEqual(loaded["gaps"], [])
            self.assertIn("verification", loaded)
            self.assertIn("manifest", loaded)
            state_api.save(tmp, loaded)
            self.assertFalse(list(Path(tmp).glob("*.tmp-*")))
            reloaded = state_api.load(tmp, "old-run")
            self.assertEqual(reloaded["counters"]["counts"]["obtained"], 0)

    def test_new_state_has_defaults(self):
        state = state_api.new_state("nova")
        for key in ("counters", "verification", "manifest", "gaps"):
            self.assertIn(key, state)
        self.assertEqual(set(state["counters"]["counts"]), set(counters.STAGES))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class SubstantiveExcerptTest(unittest.TestCase):
    def test_skips_badges_and_keeps_substance(self):
        text = ("\n".join([
            '<div align="center" id="top">',
            '<img src="https://x/logo.png" alt="Logo" width="80">',
            "####",
            "[![Website](https://img.shields.io/badge/x)](https://x)",
            "",
            "## Features",
            "",
            "Adaptive routing picks the retrieval strategy per query.",
        ]))
        excerpt, stripped = ac._substantive_excerpt(text, 1200)
        self.assertGreater(stripped, 0)
        self.assertIn("Adaptive routing", excerpt)
        self.assertNotIn("img.shields.io", excerpt)
        self.assertNotIn("<div", excerpt)

    def test_plain_text_untouched(self):
        text = "line one\nline two\nline three"
        excerpt, stripped = ac._substantive_excerpt(text, 1200)
        self.assertEqual(excerpt, text)
        self.assertEqual(stripped, 0)

    def test_limit_still_applies_after_strip(self):
        text = "[![a](https://img.shields.io/b)]\n" + "x" * 2000
        excerpt, stripped = ac._substantive_excerpt(text, 100)
        self.assertEqual(len(excerpt), 100)
        self.assertGreater(stripped, 1000)

    def test_raw_html_single_line_yields_visible_text(self):
        html = ('<!DOCTYPE html><html lang="pt"><head><meta charset="utf-8"/>'
                '<title>ignore me</title><script>var x=1;</script>'
                '<style>.a{color:red}</style></head><body><nav>Menu</nav>'
                '<h1>Como o uv gerencia cache</h1><p>O cache fica em ~/.cache/uv.</p>'
                '</body></html>')
        excerpt, stripped = ac._substantive_excerpt(html, 1200)
        self.assertIn("Como o uv gerencia cache", excerpt)
        self.assertIn("~/.cache/uv", excerpt)
        self.assertNotIn("<meta", excerpt)
        self.assertNotIn("var x=1", excerpt)
        self.assertNotIn("color:red", excerpt)
        self.assertGreater(stripped, 0)

    def test_visible_text_only_for_html(self):
        text = "plain <b>bold</b> text"
        visible, removed = ac._visible_text(text)
        self.assertEqual(visible, text)
        self.assertEqual(removed, 0)
