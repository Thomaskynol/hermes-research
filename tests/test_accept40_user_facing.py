#!/usr/bin/env python3
"""Accept40 user-facing hygiene (offline, generic, no product literals).

The accept40 delivery proves the 4 contracts but leaks internal artifacts
into the user-visible body (§§1-5): entity codes (e2/e3...), the
'desconhecido-legítimo' jargon, the English 'Skipped:' prefix and a
citation-numbers legend line without prose. Each test asserts the FIXED
behavior with generic fixtures; they must FAIL before the fix (RED) and
PASS after (GREEN). No network (incl. 8082).
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept40 user-facing test is offline (incl 8082)")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import report_renderer as rr


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


URL_A = "https://example.org/alpha-doc"
URL_B = "https://example.org/beta-doc"


def hygiene_state():
    st = state_api.new_state("q hygiene")
    st["plan"] = {
        "plan_id": "h40", "version": 1, "question": "q",
        "entities": [
            {"id": "e1", "label": "AlphaWidget", "required": True,
             "source_url": URL_A},
            {"id": "e2", "label": "BetaGadget", "required": True,
             "source_url": URL_B},
        ],
        "criteria": [
            {"id": "c1", "label": "eixo um", "required": True,
             "description": "Eixo um: o que conta como evidencia."},
        ],
    }
    body_a = "AlphaWidget detalhes do eixo um " * 40
    body_b = "BetaGadget detalhes do eixo um " * 40
    st["evidence"] = {URL_A: body_a, URL_B: body_b}
    st["qualification"] = {URL_A: qual(body_a), URL_B: qual(body_b)}
    try:
        st["counters"]["documents"]["obtained"] = [
            rr._norm(URL_A), rr._norm(URL_B)]
        st["counters"]["documents"]["usable"] = [
            rr._norm(URL_A), rr._norm(URL_B)]
        st["counters"]["counts"]["obtained"] = 2
        st["counters"]["counts"]["usable"] = 2
    except Exception:
        pass
    return st


def body_of(md):
    # User-visible body: everything before the technical annex (§8).
    # Split on the renderer header (newline + '## 8. '), never on '### 8.'
    # inside the synthesis (the latter contains '## 8.' as a substring).
    return md.split("\n## 8.")[0]


class EntityCodeMappingTest(unittest.TestCase):
    def test_findings_justification_uses_labels_not_ids(self):
        st = hygiene_state()
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.1,
            "criteria": [{
                "id": "c1", "label": "eixo um", "state": "partial",
                "justification": ("Material prova finalidade de e1 e e2 "
                                  "no corpus."),
                "references": [{"url": URL_A}],
                "examined_scope": "alcance examinado: teste",
            }],
            "gaps": [],
        }
        md = rr.render_report(st, synthesis_text="síntese mínima.")
        body = body_of(md)
        self.assertIn("AlphaWidget", body)
        self.assertIn("BetaGadget", body)
        self.assertNotRegex(body, r"\be1\b",
                            f"entity code leaked: {body[:800]}")
        self.assertNotRegex(body, r"\be2\b",
                            f"entity code leaked: {body[:800]}")

    def test_limits_gap_justification_uses_labels_not_ids(self):
        st = hygiene_state()
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.1, "criteria": [],
            "gaps": [{
                "criterion_id": "c1", "label": "eixo um",
                "state": "partial",
                "justification": "Faltam e1 e e2 no material.",
                "next": "investigar",
            }],
        }
        md = rr.render_report(st, synthesis_text="síntese mínima.")
        body = body_of(md)
        self.assertIn("AlphaWidget", body)
        self.assertNotRegex(body, r"\be1\b")

    def test_unknown_entity_id_falls_back_to_original(self):
        st = hygiene_state()
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.1,
            "criteria": [{
                "id": "c1", "label": "eixo um", "state": "partial",
                "justification": "Falta e9 no material.",
                "references": [], "examined_scope": "alcance",
            }],
            "gaps": [],
        }
        md = rr.render_report(st, synthesis_text="síntese mínima.")
        # e9 has no label in the plan: original token is preserved.
        self.assertIn("e9", body_of(md))


class AlcanceWordingTest(unittest.TestCase):
    def test_no_doc_entity_uses_user_facing_paraphrase(self):
        st = state_api.new_state("q alcance")
        st["plan"] = {
            "plan_id": "p", "version": 1,
            "entities": [
                {"id": "e1", "label": "AlphaWidget", "required": True},
                {"id": "e2", "label": "BetaGadget", "required": True},
            ],
            "criteria": [{"id": "c0", "label": "eixo um", "required": True,
                           "applies_to": ["e1", "e2"],
                           "description": "Eixo um: evidencia."}],
        }
        st["evidence"] = {URL_A: "AlphaWidget eixo um " * 10}
        st["qualification"] = {URL_A: qual(st["evidence"][URL_A])}
        scope = ac._criterion_scope(st, st["plan"]["criteria"][0])
        self.assertIn("sem fonte no corpus", scope,
                      f"user-facing paraphrase missing: {scope[:400]}")
        self.assertNotIn("desconhecido-legítimo", scope,
                         f"internal jargon leaked: {scope[:400]}")

    def test_render_paraphrases_stored_legacy_scope(self):
        st = hygiene_state()
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.1,
            "criteria": [{
                "id": "c1", "label": "eixo um", "state": "partial",
                "justification": "ok.", "references": [],
                "examined_scope": ("alcance examinado: teste; "
                                   "BetaGadget: desconhecido-legítimo "
                                   "(nada no corpus sobre a entidade)"),
            }],
            "gaps": [],
        }
        md = rr.render_report(st, synthesis_text="síntese mínima.")
        body = body_of(md)
        self.assertNotIn("desconhecido-legítimo", body)
        self.assertIn("sem fonte no corpus", body)


class SkippedPrefixTest(unittest.TestCase):
    def test_render_normalizes_skipped_to_portuguese(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        syn = ("Algum achado.\n\nSkipped: verificação runtime real fora "
               "dos excertos.")
        md = rr.render_report(st, synthesis_text=syn)
        body = body_of(md)
        self.assertNotIn("Skipped:", body, f"EN prefix leaked: {body[:600]}")
        self.assertIn("Não verificado:", body,
                      f"PT prefix missing: {body[:600]}")

    def test_writer_prompt_requires_portuguese_unverified_label(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        import coverage_ledger as cl
        st = hygiene_state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {}, "rounds": [],
                "evaluations": [], "unexplored_alternatives": [],
                "substitutions": [], "semantic_rank": []}
        ac.make_model_writer(fake_client, max_chars=2400)(view)
        prompt = seen.get("prompt", "")
        self.assertIn("Não verificado", prompt,
                      f"writer must require PT label: {prompt[:800]}")
        self.assertIn("Skipped", prompt,
                      "writer must name the banned EN token literally")


class SourceLegendTest(unittest.TestCase):
    def test_render_drops_standalone_source_legend(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        syn = ("> Legenda de fontes do corpus — toda afirmação traz "
               "citação: [1](https://example.org/alpha-doc) "
               "[2](https://example.org/beta-doc)\n\n"
               "AlphaWidget faz algo [1](https://example.org/alpha-doc).")
        md = rr.render_report(st, synthesis_text=syn)
        body = body_of(md)
        self.assertNotIn("Legenda de fontes", body,
                         f"legend line leaked: {body[:600]}")
        self.assertRegex(body, r"\[1\]",
                         f"inline citation must survive: {body[:600]}")

    def test_writer_prompt_bans_standalone_source_legend(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        import coverage_ledger as cl
        st = hygiene_state()
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {}, "rounds": [],
                "evaluations": [], "unexplored_alternatives": [],
                "substitutions": [], "semantic_rank": []}
        ac.make_model_writer(fake_client, max_chars=2400)(view)
        prompt = seen.get("prompt", "").lower()
        self.assertIn("legenda", prompt,
                      "writer must ban the standalone legend line")


class AssessorLabelGuidanceTest(unittest.TestCase):
    def test_assessor_prompt_prefers_labels_over_internal_ids(self):
        import json

        def fake_client(prompt):
            raise AssertionError("must not call model in this test")

        assess = ac.make_model_assessor(fake_client)
        # Inspect the prompt builder via a stubbed model that captures it.
        captured = {}

        def capture(prompt):
            captured["prompt"] = prompt
            return json.dumps([])

        assess2 = ac.make_model_assessor(capture)
        st = hygiene_state()
        try:
            assess2(st["plan"], dict(st["evidence"]),
                    dict(st["qualification"]), {})
        except Exception:
            pass
        prompt = captured.get("prompt", "")
        self.assertIn("rótulo", prompt.lower(),
                      f"assessor must prefer labels: {prompt[:800]}")


if __name__ == "__main__":
    unittest.main()
