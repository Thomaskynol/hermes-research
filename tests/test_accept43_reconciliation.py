"""Contracts derived from the question and frozen primary sources, offline.

The fixtures are deliberately about other subjects too: no plugin/domain
blacklist, no candidate names chosen by the implementation.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adaptive_coordinator as ac
import adaptive_state
import coverage_ledger as cl
import report_renderer as rr
import semantic_review as sr
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("reconciliation tests forbid network, including 8082")


sys.addaudithook(offline)
A = "https://github.com/acme/river-review"
B = "https://github.com/team/river-plan"


def plan():
    return {"plan_id": "rivers", "version": 1,
            "open_discovery": {"needed": True}, "candidate_target": 2,
            "entities": [{"id": "host", "label": "RiverHost", "required": True},
                         {"id": "a", "label": "River Review (acme)",
                          "source_url": A, "discovered": True, "required": True},
                         {"id": "b", "label": "River Plan", "source_url": B,
                          "discovered": True, "required": True},
                         {"id": "old", "label": "Old Tool", "required": False}],
            "criteria": [{"id": "version", "label": "Versão local", "required": True,
                          "description": "Versão fornecida versus observada.", "applies_to": ["host"]},
                         {"id": "review", "label": "Revisão", "required": True,
                          "description": "Revisão documentada por candidato.",
                          "per_candidate": True, "applies_to": ["old", "a", "b"]},
                         {"id": "combo", "label": "Combinações", "required": True,
                          "description": "Inferir complementaridade das funções documentadas."}],
            "initial_paths": []}


def state():
    st = adaptive_state.new_state("Compare extensões para revisão e planejamento no RiverHost.")
    st["plan"] = plan()
    st["evidence"] = {A: "# River Review\nPerforms automated code review with confidence scoring.",
                      B: "# River Plan\nDocumented plan review and interactive questions."}
    st["qualification"] = {u: {"status": "usable", "excluded": False, "usable_text": t}
                           for u, t in st["evidence"].items()}
    return st


class ScopeAndSelection(unittest.TestCase):
    def test_equal_state_catalog_update_cannot_replace_primary_justification(self):
        st = state(); led = cl.Ledger(st["plan"]);led.set_corpus(st["evidence"],st["qualification"])
        led.evaluate("review", "partial", "River Review audits changes.", "assessor", [{"url": A}], "a")
        st["evaluations"] = list(led._evals.values())
        catalog = "https://catalog.example/list"
        st["evidence"][catalog] = "River Review — review tool."
        st["qualification"][catalog] = {"status": "usable", "usable_text": st["evidence"][catalog], "excluded": False}
        ac._assess_round(st, lambda *args: [{"criterion_id": "review", "entity_id": "a", "state": "partial",
             "justification": "River Review also supports JQL.", "origin": "assessor", "references": [{"url": catalog}]}], led)
        ev = next(e for e in st["evaluations"] if e.get("entity_id") == "a")
        self.assertEqual(ev["justification"], "River Review audits changes.")

    def test_writer_receives_late_cell_evidence_without_json_slice(self):
        st = state();st["question_coverage"] = {"criteria": [{"id": "review", "examined_scope": "scope " * 900},
             {"id": "cost", "entity_evaluations": {"a": {"justification": "Licença MIT documentada; custo de modelos não quantificado.", "references": [{"url": A}]}}}]}
        prompts = [];ac.make_model_writer(lambda p: prompts.append(p) or "Comparação parcial.")(st)
        self.assertIn("Licença MIT documentada; custo de modelos não quantificado.", prompts[0])
    def test_selection_change_invalidates_global_conclusion_and_archives_old_cells(self):
        st = state();led = cl.Ledger(st["plan"]);led.set_corpus(st["evidence"], st["qualification"])
        led.evaluate("combo", "partial", "River Review combina com River Plan.", "assessor", [{"url": A}])
        led.evaluate("review", "covered", "River Review audits changes.", "assessor", [{"url": A}], "a")
        led.evaluate("review", "partial", "River Plan reviews plans.", "assessor", [{"url": B}], "b")
        st["evaluations"] = list(led._evals.values())
        self.assertTrue(ac._do_substitute(st, led, "a", "old", "new evidence"))
        self.assertEqual(led.state_of("combo"), "uninvestigated")
        self.assertEqual(led.state_of("review", "b"), "partial")
        self.assertFalse(any(ev.get("entity_id") == "a" for ev in st["evaluations"]))
        self.assertTrue(st.get("historical_evaluations"))

    def test_large_plan_is_not_sliced_into_invalid_json_for_assessor(self):
        st = state(); p = st["plan"]
        p["criteria"][0]["description"] = "Definição operacional preservada. " * 220
        prompts = []
        assessor = ac.make_model_assessor(lambda prompt: prompts.append(prompt) or "[]")
        assessor(p, st["evidence"], st["qualification"])
        line = next(ln for ln in prompts[0].splitlines() if ln.startswith("Plano: "))[7:]
        self.assertTrue(line.endswith("}"), "Plano truncado antes de chegar ao assessor")
        self.assertEqual(json.loads(line)["criteria"][0]["description"], p["criteria"][0]["description"])

    def test_substitution_prefers_one_primary_to_many_shallow_mentions(self):
        st = state()
        st["plan"]["entities"][1]["required"] = False
        st["plan"]["entities"][3].update(discovered=True, required=True,
                                               source_url="https://catalog.example/old")
        st["rounds"] = [{"round": 0}, {"round": 1}]
        for i in range(4):
            st["evidence"][f"https://catalog.example/{i}"] = "Old Tool — review tool."
        led = cl.Ledger(st["plan"]); led.set_corpus(st["evidence"], st["qualification"])
        led.evaluate("review", "insufficient", "Sem função demonstrada.", "assessor", [], "old")
        st["evaluations"] = list(led._evals.values())
        self.assertTrue(ac._maybe_substitute(st, led))
        self.assertTrue(next(e for e in st["plan"]["entities"] if e["id"] == "a")["required"])

    def test_shallow_mentions_do_not_replace_substantial_primary(self):
        st = state(); st["plan"]["entities"][3].update(discovered=True, source_url="https://catalog.example/0")
        st["rounds"] = [{"round": 0}, {"round": 1}]
        for i in range(4):
            st["evidence"][f"https://catalog.example/{i}"] = "Old Tool — review tool."
        led = cl.Ledger(st["plan"]); led.set_corpus(st["evidence"], st["qualification"])
        led.evaluate("review", "insufficient", "Falta análise específica.", "assessor", [], "a")
        st["evaluations"] = list(led._evals.values())
        self.assertFalse(ac._maybe_substitute(st, led))

    def test_partial_catalog_candidate_can_yield_to_documented_primary(self):
        st = state(); st["plan"]["entities"][1]["required"] = False
        st["plan"]["entities"][3].update(discovered=True, required=True, source_url="https://catalog.example/old")
        st["evidence"]["https://catalog.example/old"] = "Old Tool offers review."
        st["qualification"]["https://catalog.example/old"] = {"status": "usable", "excluded": False, "usable_text": "Old Tool offers review."}
        st["rounds"] = [{"round": 0}, {"round": 1}]
        # Two partial catalog cells used to freeze the candidate, even
        # against a primary document with demonstrated relevant behavior.
        second = copy.deepcopy(st["plan"]["criteria"][1]);second["id"] = "features"
        st["plan"]["criteria"].append(second)
        led = cl.Ledger(st["plan"]);led.set_corpus(st["evidence"], st["qualification"])
        for cid in ["review", "features"]:
            led.evaluate(cid, "partial", "Catalog mention only.", "assessor", [{"url": "https://catalog.example/old"}], "old")
        led.evaluate("review", "covered", "Four review agents documented.", "assessor", [{"url": A}], "a")
        st["evaluations"] = list(led._evals.values())
        self.assertTrue(ac._maybe_substitute(st, led))
        self.assertEqual(st["substitutions"][-1]["new"], "a")

    def test_platform_and_global_criteria_do_not_become_candidate_cells(self):
        st = state()
        led = cl.Ledger(st["plan"])
        st["question_coverage"] = led.compute()
        self.assertEqual(led.cell_counts(), (0, 4))  # 2 candidate + version + global
        out = rr.render_report(st, synthesis_text="Comparação parcial.")
        matrix = out.split("### Matriz entidade×critério", 1)[1].split("###", 1)[0]
        self.assertNotIn("RiverHost", matrix)
        self.assertNotIn("Combinações", matrix)
        self.assertIn("River Review", matrix)

    def test_removed_candidate_cannot_supply_final_justification(self):
        st = state(); led = cl.Ledger(st["plan"])
        led.set_corpus(st["evidence"], st["qualification"])
        led.evaluate("review", "insufficient", "Old Tool não faz revisão.", "assessor", [], "old")
        led.evaluate("review", "covered", "River Review audits changes.", "assessor", [{"url": A}], "a")
        led.evaluate("review", "partial", "River Plan reviews plans only.", "assessor", [{"url": B}], "b")
        st["question_coverage"] = led.compute()
        section = rr.render_report(st, synthesis_text="Comparação parcial.").split("## 3.", 1)[1].split("## 4.", 1)[0]
        self.assertNotIn("Old Tool não faz", section)
        self.assertIn("River Plan reviews plans only", section)
        self.assertIn("River Review audits changes", section)

    def test_writer_prefers_substantial_primary_over_catalog(self):
        st = state()
        st["plan"]["entities"][1]["source_url"] = "https://catalog.example/list"
        st["evidence"]["https://catalog.example/list"] = "River Review — code review. River Plan — plans."
        writer = ac.make_model_writer(lambda prompt: "Comparação parcial.", max_chars=12000)
        _, sel = writer(st)
        self.assertIn(A, sel["included_urls"])
        self.assertIn(B, sel["included_urls"])
        self.assertEqual(sel["included_urls"][0], A)


class Identity(unittest.TestCase):
    def test_catalog_link_binds_owner_before_selecting_identical_fork_readme(self):
        st = state(); ent = st["plan"]["entities"][2]
        catalog = "https://catalog.example/list"
        ent["source_url"] = catalog
        st["evidence"][catalog] = f"River Plan — {B}"
        fork = "https://github.com/fork/river-plan"
        st["evidence"][fork] = st["evidence"][B]
        # Equal text and a competing owner: the catalog's explicit link
        # resolves provenance; a title match alone is not enough.
        _, selection = ac.make_model_writer(lambda p: "Comparação parcial.")(st)
        self.assertIn(B, selection["included_urls"])
        self.assertNotIn(fork, ac._entity_corpus_docs(ent, st["evidence"], st["qualification"]))

    def test_citation_audit_resolves_decorated_primary_and_rejects_fork(self):
        st = state()
        text = "River Review (acme) performs automated code review with confidence scoring [1]."
        r = vr.check_support(text, {A: 1}, {A: st["evidence"][A]}, st["plan"])
        self.assertEqual(r["supported"], 1, r)
        fork = "https://github.com/fork/river-review"
        r = vr.check_support(text, {fork: 1}, {fork: st["evidence"][A]}, st["plan"])
        self.assertTrue(r["unsupported"], r)
        r = vr.check_support(text, {A: 1, fork: 2}, {A: st["evidence"][A], fork: st["evidence"][A]}, st["plan"])
        self.assertEqual(r["supported"], 1, r)

    def test_decorated_owner_is_resolved_from_primary_repo_and_title(self):
        st = state(); ent = st["plan"]["entities"][1]
        self.assertIn(A, ac._entity_corpus_docs(ent, st["evidence"], st["qualification"]))

    def test_same_name_in_different_owner_repo_is_not_same_project(self):
        st = state(); ent = st["plan"]["entities"][1]
        u = "https://github.com/fork/river-review"
        self.assertEqual(ac._entity_corpus_docs(ent, {u: st["evidence"][A]}, {}), [])

    def test_plain_name_is_not_substring_of_another_entity(self):
        self.assertFalse(ac._identity_matches({"label": "Octto"}, "Octtober colors"))


class Audit(unittest.TestCase):
    def test_review_payload_deduplicates_identical_evidence_without_losing_it(self):
        evidence = "Documento substancial. " * 1100 + "TAIL_PROOF"
        items = [{"id": i, "claim": f"Afirmação {i}", "evidence": evidence} for i in range(12)]
        prompts = []
        fn = ac.make_review_fn(lambda p: prompts.append(p) or json.dumps([
            {"id": i, "verdict": "gap", "support": "", "correction": ""} for i in range(12)]))
        result = fn(items, "controlled")
        self.assertLess(len(prompts[0]), 100000)
        self.assertIn("TAIL_PROOF", prompts[0])
        self.assertEqual({r["id"] for r in result}, set(range(12)))
        packet = json.loads(prompts[0].splitlines()[-1])
        for item in packet["claims"]:
            self.assertEqual("\n\n".join(packet["evidence_store"][k] for k in item["evidence_refs"]), evidence)
    def test_price_claim_without_source_still_reaches_auditor_as_missing_evidence(self):
        text = ('## `river-alpha` e `river-beta`\n'
                '* O serviço (https://vendor.example/pricing) anuncia\n'
                '  **"200 req free every month"**, com uso medido.\n')
        claims = sr.extract_claims(text, {}, max_claims=25)
        self.assertTrue(any("200 req free every month" in c["claim"] for c in claims))
        self.assertTrue(any(c["free_assertion"] and c["evidence"] == "(sem evidência)" for c in claims))

    def test_version_mention_does_not_turn_complementarity_into_user_premise(self):
        p = {"entities": [{"id": "a", "label": "Alfa"}, {"id": "b", "label": "Beta"}]}
        text = ("INFERÊNCIA: Alfa complementa Beta: Alfa gera planos e Beta revisa código; "
                "sem prova de integração testada nem compatibilidade com a versão instalada informada pelo usuário [1][2].")
        result = vr.check_support(text, {A: 1, B: 2},
                                  {A: "Alfa gera planos.", B: "Beta revisa código."}, p)
        self.assertEqual(result["user_premises"], [])
        self.assertTrue(result["declared_inference"])

    def test_user_marker_does_not_exempt_false_feature(self):
        text = "Alfa executa testes quânticos, segundo a versão instalada informada pelo usuário [1]."
        r = vr.check_support(text, {A: 1}, {A: "Alfa gerencia planos."},
                             {"entities": [{"id": "a", "label": "Alfa"}]})
        self.assertEqual(r["user_premises"], [])
        self.assertTrue(r["unsupported"])

    def test_bullets_without_period_are_extracted_individually(self):
        text = ("# Comparação\n## Funções\n"
                "- Documentado: Alfa revisa código com quatro agentes (https://alpha.example/doc)\n"
                "- Documentado: Beta faz perguntas interativas para planejamento (https://beta.example/doc)\n")
        claims = sr.extract_claims(text, {"https://alpha.example/doc": "Alfa revisa código.",
                                          "https://beta.example/doc": "Beta faz perguntas."}, generic=True)
        self.assertTrue(any("Alfa revisa" in c["claim"] for c in claims))
        self.assertTrue(any("Beta faz" in c["claim"] for c in claims))
        self.assertFalse(any("Alfa revisa" in c["claim"] and "Beta faz" in c["claim"] for c in claims))


class Topic(unittest.TestCase):
    def test_harness_version_keeps_origin_separate_from_observed_version(self):
        st = state();st["user_context"] = {"origin": "harness", "facts": {"installed_version": "2.1.4"}}
        st["environment_observations"] = [{"command": "tool --version", "value": "2.2.5", "at": "controlled"}]
        out = rr.render_report(st, synthesis_text="Premissa do usuário: versão instalada 2.1.4.")
        self.assertNotIn("Premissa do usuário", out)
        self.assertNotIn("versão instalada 2.1.4", out)
        self.assertIn("premissa controlada do experimento", out)
        self.assertIn("tool --version → 2.2.5", out)

    def test_obtained_url_cannot_be_reported_as_outside_corpus(self):
        st = state();st["report"] = {"selection": {"included_urls": [A]}}
        ac._counters.record_obtained(st, A, st["evidence"][A], st["qualification"][A])
        out = rr.render_report(st, synthesis_text=f"Nota metodológica: o endereço {A} ficou fora do corpus e não foi usado como fonte lida.")
        self.assertNotIn("ficou fora do corpus", out)
        self.assertIn("obtida", out)
    def test_obtained_body_without_snippet_is_qualified_against_topic(self):
        st = state()
        st["pending_ops"] = [{"op_id": "g", "kind": "gap_query", "criterion_id": "combo"}]
        result = ac.incorporate(st, "https://colors.example/palette", "Combinações de cores e paletas harmoniosas.", "g", 1,
                                {"status": "usable", "excluded": False, "usable_text": "Combinações de cores e paletas harmoniosas."})
        self.assertEqual(result, "nogain")
        self.assertTrue(st["qualification"]["https://colors.example/palette"]["excluded"])
        self.assertIn("https://colors.example/palette", st["evidence"])  # obtained preserved

    def test_global_query_keeps_the_object_not_only_platform(self):
        st = state()
        q = ac._short_gap_query(st, {"criterion_id": "combo", "label": "Combinações entre candidatos"})
        self.assertIn("extens", q.lower())
        self.assertIn("riverhost", q.lower())

    def test_global_hit_requires_topic_not_criterion_word_alone(self):
        st = state(); op = {"kind": "gap_query", "criterion_id": "combo", "target": "Combinações"}
        hit = {"url": "https://colors.example/palette", "title": "Combinações de cores", "snippet": "Cores que combinam"}
        self.assertTrue(ac._hit_gated_by_snippet(st, op, hit))
        st["question"] = "Compare combinações de cores e paletas para pintura."
        self.assertFalse(ac._hit_gated_by_snippet(st, op, hit))

    def test_agent_residue_is_removed_from_delivery(self):
        st = state(); st["question_coverage"] = cl.Ledger(st["plan"]).compute()
        out = rr.render_report(st, synthesis_text="Comparação parcial.\nponytail: skipped detalhar candidatos.")
        self.assertNotIn("ponytail", out)


class IntegratedEntry(unittest.TestCase):
    def test_public_entry_preserves_scope_identity_and_cell_evidence_to_files(self):
        import gpt_researcher_integration as entry
        st = state(); p = st["plan"];p["initial_paths"] = ["RiverHost extensions"]
        p["entities"] = p["entities"][:3]
        p["criteria"][1]["applies_to"] = ["a", "b"]
        def model(prompt):
            if prompt.startswith("Você avalia evidências"):
                return json.dumps([
                    {"criterion_id": "review", "entity_id": "a", "state": "covered",
                     "justification": "River Review performs automated code review with confidence scoring.",
                     "origin": "model", "references": [{"url": A}]},
                    {"criterion_id": "review", "entity_id": "b", "state": "partial",
                     "justification": "River Plan documents plan review and interactive questions.",
                     "origin": "model", "references": [{"url": B}]}])
            if prompt.startswith("Responda em português"):
                return f"Recomendo River Review (acme) para revisão automatizada ({A}). River Plan auxilia revisão de planos ({B}).\nponytail: internal notes"
            raise AssertionError("Unexpected model call")
        with tempfile.TemporaryDirectory() as tmp:
            result = entry.adaptive_entry(question=st["question"], plan=p, profile="light", run_dir=tmp,
                model_transport=model, search_transport=lambda *a, **kw: [{"url": A}, {"url": B}],
                fetch_transport=lambda u: {"text": st["evidence"][u], "qualification": st["qualification"][u]},
                auditor_fn=lambda *a: {"enabled": False, "accepted": False, "verdict_state": "não revisado semanticamente"},
                overrides={"max_rounds": 0, "max_model_calls": 6}, clock=lambda: 0)
            out = Path(result["report_path"]).read_text()
            matrix = out.split("### Matriz entidade×critério")[1].split("###")[0]
            self.assertNotIn("RiverHost", matrix)
            self.assertNotIn("Combinações", matrix)
            self.assertIn("confidence scoring", matrix)
            self.assertNotIn("ponytail", out)
            self.assertTrue((Path(tmp) / "verification.json").is_file())
            saved = json.loads((Path(tmp) / "state.json").read_text())
            self.assertEqual(saved["question_coverage"]["denominator"], 4)


if __name__ == "__main__":
    unittest.main()
