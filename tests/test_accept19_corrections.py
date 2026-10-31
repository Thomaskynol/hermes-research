"""Regression tests for the accept19 correction batch (identity as concept).

Q1: evaluation-referenced entity sources must reach the writer prompt
    (per-entity floor) instead of falling off by alphabetical order.
Q2: strict identity — one shared word (or a far-apart coincidence) is
    not aboutness; listing lines name the entity, prose does not.
Q3: substitution explores the discovery pool; when nobody qualifies,
    the kept candidate records what was left unexplored.
Q4: support/verification alignment — the §7 sources table is inventory,
    not claims; leading LACUNA marks are premise-audited.

All offline (pure functions, stub model client).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import verification_report as verify


class WriterFloorTest(unittest.TestCase):
    def _view(self):
        return {
            "question": "compare plugins",
            "plan": {"plan_id": "p", "entities": [
                {"id": "e1", "label": "planning-with-files",
                 "required": True, "discovered": True,
                 "source_url": "https://zzz.example/pwf"},
                {"id": "e2", "label": "lit-opencode",
                 "required": True, "discovered": True,
                 "source_url": "https://aaa.example/lit"},
            ], "criteria": [
                {"id": "c1", "label": "planning", "required": True,
                 "applies_to": ["e1", "e2"]},
            ]},
            "evidence": {
                "https://zzz.example/pwf": (
                    "<title>Planning With Files plugin</title> per-turn "
                    "plan injection, write reminders, compaction flush."),
                "https://aaa.example/lit": (
                    "lit-opencode adds a repeatable planning workflow."),
                "https://mmm.example/filler": "generic filler text here. " * 200,
            },
            "question_coverage": {"criteria": [
                {"id": "c1", "references": [
                    {"url": "https://aaa.example/lit"}]},
            ]},
            "evaluations": [
                {"criterion_id": "c1", "entity_id": "e1", "state": "partial",
                 "references": [{"url": "https://zzz.example/pwf"}]},
            ],
            "stop": {}, "rounds": [], "substitutions": [],
            "unexplored_alternatives": [],
        }

    def test_eval_referenced_doc_survives_tight_budget(self):
        seen = {}

        def stub_client(prompt):
            seen["prompt"] = prompt
            return "RELATÓRIO"

        write = ac.make_model_writer(stub_client, max_chars=4500)
        _text, selection = write(self._view())
        included = selection["included_urls"]
        self.assertIn("https://zzz.example/pwf", included,
                      "evaluation-referenced entity source must be floored "
                      "into the prompt even when alphabetically last")
        self.assertIn("https://aaa.example/lit", included)
        self.assertIn("Planning With Files", seen["prompt"])

    def test_writer_prompt_marks_user_context_as_non_evidence(self):
        seen = {}

        def stub_client(prompt):
            seen["prompt"] = prompt
            return "RELATÓRIO"

        write = ac.make_model_writer(stub_client, max_chars=4500)
        write(self._view())
        self.assertIn("contexto informado pelo usuário", seen["prompt"])
        self.assertIn("LACUNA", seen["prompt"])

    def test_entity_without_corpus_doc_gets_no_floor(self):
        view = self._view()
        view["plan"]["entities"].append(
            {"id": "e3", "label": "ghost-plugin",
             "required": True, "discovered": True})

        def stub_client(prompt):
            return "RELATÓRIO"

        write = ac.make_model_writer(stub_client, max_chars=6000)
        _text, selection = write(view)
        ghost = {"id": "e3", "label": "ghost-plugin"}
        for url in selection["included_urls"]:
            self.assertFalse(
                ac._identity_matches(ghost, url),
                "no floor doc exists for ghost-plugin; nothing may be "
                "promoted in its name")


class IdentityMatchesTest(unittest.TestCase):
    def test_dedicated_source_matches(self):
        ent = {"id": "e4", "label": "planning-with-files"}
        body = ("<title>Planning With Files — OpenCode plugin</title>"
                "per-turn plan injection, write reminders.")
        self.assertTrue(ac._identity_matches(ent, body))

    def test_shared_word_is_not_aboutness(self):
        ent = {"id": "e4", "label": "planning-with-files"}
        body = ("planning our sprint: tasks, files to review, "
                "with the team tomorrow")
        self.assertFalse(ac._identity_matches(ent, body))

    def test_far_apart_tokens_are_not_aboutness(self):
        ent = {"id": "e5", "label": "opencode-local-memory"}
        body = ("local " + "x " * 50 + "memory " + "y " * 50)
        self.assertFalse(ac._identity_matches(ent, body))

    def test_homonym_without_name_does_not_match(self):
        ent = {"id": "e2", "label": "lit-opencode"}
        lit_dev = ("Lit — Simple. Fast. Web Components. "
                   "documentation for reactive lit elements.")
        self.assertFalse(ac._identity_matches(ent, lit_dev))
        lit_page = "lit-opencode adds a repeatable planning workflow."
        self.assertTrue(ac._identity_matches(ent, lit_page))

    def test_corpus_docs_strict(self):
        ev = {
            "https://d.example/pwf": "Planning With Files plugin page",
            "https://d.example/gen": "planning tasks and files with team",
            "https://lit.dev/": "Lit web components docs",
        }
        ent = {"id": "e4", "label": "planning-with-files"}
        self.assertEqual(
            ac._entity_corpus_docs(ent, ev, {}), ["https://d.example/pwf"])


class LeadingMarkTest(unittest.TestCase):
    def test_lacuna_prefix_is_declaration(self):
        self.assertTrue(verify.is_lacuna_declaration(
            "- LACUNA: dependências não documentadas no excerto [1]."))

    def test_combined_inferencia_lacuna_prefix_is_declaration(self):
        self.assertTrue(verify.is_lacuna_declaration(
            "- INFERÊNCIA/LACUNA de compatibilidade: premissa "
            "verificável [8]; teste exato é LACUNA."))

    def test_bare_inferencia_prefix_keeps_anchor_path(self):
        # Pure inference without anchor must still fail the audit.
        self.assertFalse(verify.is_lacuna_declaration(
            "INFERÊNCIA: provavelmente é grátis e sem limites [1]."))

    def test_prose_lacuna_is_not_declaration(self):
        self.assertFalse(verify.is_lacuna_declaration(
            "a lacuna foi preenchida na versão nova [1]."))


class SupportBeyondTableTest(unittest.TestCase):
    def _state(self, report_text):
        return {
            "run_id": "t",
            "evidence": {
                "https://used.example/doc": "substantive text here",
                "https://table.example/other": "other text here",
            },
            "qualification": {},
            "counters": {"documents": {
                "used_in_synthesis": ["https://used.example/doc"]}},
            "report": {"markdown": report_text},
        }

    def test_sources_table_is_not_beyond(self):
        report = (
            "## 1. Síntese\n\nAfirmação com citação [1].\n\n"
            "## 7. Fontes\n\n"
            "| # | URL |\n|---|---|\n"
            "| [1] | https://used.example/doc |\n"
            "| [2] | https://table.example/other |\n")
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [], "accepted": True}
        dim = verify.verify_support(self._state(report), report, audit)
        self.assertEqual(dim["evidence"]["cited_beyond_synthesis"], [])
        self.assertFalse(any("fora da base" in n for n in dim["notes"]))

    def test_genuine_beyond_still_flagged(self):
        report = (
            "## 1. Síntese\n\nVer https://table.example/other "
            "para detalhes.\n\n"
            "## 7. Fontes\n\n"
            "| # | URL |\n|---|---|\n"
            "| [1] | https://used.example/doc |\n")
        audit = {"enabled": True, "claims": 1, "claims_reviewed": 1,
                 "verdicts": [], "accepted": True}
        dim = verify.verify_support(self._state(report), report, audit)
        self.assertIn("https://table.example/other",
                      dim["evidence"]["cited_beyond_synthesis"])


class DiscoveryPromotionTest(unittest.TestCase):
    def _state(self):
        return {
            "run_id": "t",
            "plan": {
                "plan_id": "p",
                "candidate_target": 1,
                "entities": [
                    {"id": "e1", "label": "ghost-plugin", "required": True,
                     "discovered": True,
                     "source_url": "https://old.example/ghost"},
                ],
                "criteria": [
                    {"id": "c1", "label": "planning", "required": True,
                     "per_candidate": True, "applies_to": ["e1"]},
                ],
            },
            "plan_versions": [{"version": 1}],
            "rounds": [{}, {}],
            "evidence": {
                "https://old.example/ghost": "unrelated text",
                "https://github.com/x/real-planner":
                    "real-planner plans with structured planning files",
            },
            "qualification": {},
            "evaluations": [
                {"criterion_id": "c1", "entity_id": "e1",
                 "state": "insufficient", "references": [],
                 "justification": "nothing", "origin": "evidence"},
            ],
            "discovery": {"open": True, "candidates": [
                "https://github.com/x/real-planner"]},
            "notes": [],
        }

    def test_pool_candidate_is_promoted(self):
        import coverage_ledger as ledger_mod
        st = self._state()
        ledger = ledger_mod.Ledger(st["plan"], run_id="t")
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        self.assertTrue(ac._maybe_substitute(st, ledger))
        subs = st.get("substitutions") or []
        self.assertEqual(len(subs), 1)
        new_id = subs[0]["new"]
        ent = next(e for e in st["plan"]["entities"]
                   if e["id"] == new_id)
        self.assertTrue(ent.get("required"))
        self.assertEqual(
            ent.get("source_url"), "https://github.com/x/real-planner")

    def test_no_pool_match_records_unexplored(self):
        import coverage_ledger as ledger_mod
        st = self._state()
        st["discovery"] = {"open": True, "candidates": []}
        ledger = ledger_mod.Ledger(st["plan"], run_id="t")
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        self.assertFalse(ac._maybe_substitute(st, ledger))
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs)
        self.assertTrue(any("não exploradas" in n for n in st["notes"]))

    def test_weak_entity_without_old_records_unexplored(self):
        # Entidade fraca (só insufficient com refs de menção) não é
        # trocável, mas o pool não explorado deve ser registrado.
        import coverage_ledger as ledger_mod
        st = self._state()
        st["discovery"] = {"open": True, "candidates": [
            "https://github.com/x/ghost-plugin-fork"]}
        ledger = ledger_mod.Ledger(st["plan"], run_id="t")
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        ledger.evaluate("c1", "insufficient", "só menção",
                        "evidence",
                        [{"url": "https://old.example/ghost"}], "e1")
        # e1 tem avaliação referenciada -> não é "old"; continua fraca
        # (nenhuma covered/partial) -> registra o pool não explorado.
        self.assertFalse(ac._maybe_substitute(st, ledger))
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs)
        self.assertEqual(recs[0]["entity"], "ghost-plugin")
        self.assertIn("https://github.com/x/ghost-plugin-fork",
                      recs[0]["urls"])


if __name__ == "__main__":
    unittest.main()
