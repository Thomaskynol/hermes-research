"""Coerência documentado x inferido em comparações (accept43, defeitos 1-2).

Regra: uma comparação que nomeia N candidatos precisa de uma premissa
citada por candidato na mesma frase; a relação apurada de documentos
distintos sem trecho que documente o vínculo é INFERÊNCIA, nunca
"documentada". "Documentada" só quando um documento citado documentar
o vínculo. Fixtures genéricas (rios), sem nomes do produto.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adaptive_coordinator as ac
import adaptive_state
import report_renderer as rr
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("comparison tests forbid network, including 8082")


sys.addaudithook(offline)
A = "https://github.com/acme/river-review"
B = "https://github.com/team/river-plan"
C = "https://example.com/river-comparison"


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


def registered(st, *urls):
    for url in urls:
        ac._counters.record_obtained(st, url, st["evidence"][url], st["qualification"][url])


class ComparisonWording(unittest.TestCase):
    def test_two_entity_overlap_without_link_is_reworded_to_inference(self):
        st = state()
        registered(st, A, B)
        text = ("Sobreposição parcial documentada entre River Review (acme) e River Plan na revisão "
                f"({A}) ({B}).")
        out = rr.render_report(st, synthesis_text=text)
        self.assertIn("River Review (acme)", out)
        self.assertIn("River Plan", out)
        self.assertIn("[1]", out)
        self.assertIn("[2]", out)
        self.assertIn("relação comparativa é inferência", out)
        self.assertNotIn("Sobreposição parcial documentada", out)
        self.assertIn("INFERÊNCIA de sobreposição parcial", out)

    def test_three_entity_overlap_missing_source_is_reworded_and_flagged(self):
        st = state()
        c = "https://github.com/team/river-deploy"
        st["plan"]["entities"].append({"id": "c", "label": "River Deploy", "source_url": c,
                                      "required": True, "discovered": True})
        st["evidence"][c] = "# River Deploy\nRiver Deploy deploys packages."
        st["qualification"][c] = {"status": "usable", "excluded": False,
                                  "usable_text": st["evidence"][c]}
        registered(st, A, B, c)
        text = ("Sobreposição parcial documentada entre River Review (acme), River Plan e "
                f"River Deploy no eixo revisão ({A}) ({B}).")
        out = rr.render_report(st, synthesis_text=text)
        self.assertIn("Referência pendente", out)
        self.assertIn("River Deploy", out.split("Referência pendente", 1)[1])
        self.assertNotIn("Sobreposição parcial documentada", out)
        self.assertIn("INFERÊNCIA de sobreposição parcial", out)
        self.assertIn("River Deploy", out.split("INFERÊNCIA de sobreposição parcial", 1)[1].split("\n")[0])

    def test_documented_link_between_entities_keeps_documentada_wording(self):
        st = state()
        st["evidence"][C] = ("# River comparison\nRiver Review performs automated code review "
                             "with confidence scoring. River Plan offers plan review and "
                             "interactive questions. Both overlap in review workflows: "
                             "River Review audits code while River Plan reviews plans.")
        st["qualification"][C] = {"status": "usable", "excluded": False,
                                  "usable_text": st["evidence"][C]}
        text = ("Sobreposição documentada entre River Review (acme) e River Plan na revisão: "
                "ambos atuam em revisão, um em código e outro em planos [3].")
        r = vr.check_support(text, {A: 1, B: 2, C: 3}, st["evidence"], st["plan"])
        self.assertEqual(r.get("missing_entity_sources", []), [], r)
        self.assertEqual(r.get("inferred_comparisons", []), [], r)
        registered(st, A, B)
        out = rr.render_report(
            st, synthesis_text=text.replace("[3]", f"({C})").replace("[1]", f"({A})").replace("[2]", f"({B})"))
        self.assertIn("Sobreposição documentada", out)
        self.assertNotIn("Referência pendente", out)
        self.assertNotIn("relação comparativa é inferência", out)

    def test_inferred_overlap_stays_inference_in_verification(self):
        st = state()
        text = ("Sobreposição parcial documentada entre River Review (acme) e River Plan na revisão "
                "[1] [2].")
        r = vr.check_support(text, {A: 1, B: 2}, st["evidence"], st["plan"])
        self.assertTrue(r.get("inferred_comparisons"), r)
        scopes = [d.get("scope", "") for d in r.get("declared_inference", [])]
        self.assertTrue(any("nunca integração testada" in s for s in scopes), r)
        self.assertFalse(any("integração testada (interoperabilidade citada)" in s for s in scopes), r)

    def test_writer_guidance_forbids_documentada_for_unlinked_relations(self):
        guidance = ac._writer_complementarity_guidance()
        self.assertIn("INFERÊNCIA", guidance)
        self.assertIn("documentada", guidance)
        self.assertTrue(any(w in guidance for w in ("nunca 'documentada'", "nunca \"documentada\"")),
                        guidance)


class IntegratedEntry(unittest.TestCase):
    def test_defective_comparison_is_reworded_through_public_entry_to_files(self):
        import gpt_researcher_integration as entry
        st = state()
        c = "https://github.com/team/river-deploy"
        st["plan"]["entities"].append({"id": "c", "label": "River Deploy", "source_url": c,
                                      "required": True, "discovered": True})
        st["evidence"][c] = "# River Deploy\nRiver Deploy deploys packages."
        st["evidence"][A] = ("# River Review\nPerforms automated code review with "
                             "confidence scoring.")
        st["evidence"][B] = ("# River Plan\nDocumented plan review and interactive questions.")
        st["qualification"][c] = {"status": "usable", "excluded": False,
                                  "usable_text": st["evidence"][c]}
        p = st["plan"]
        p["initial_paths"] = ["RiverHost extensions"]
        seen_prompts = {}

        def model(prompt):
            if prompt.startswith("Você avalia evidências"):
                return json.dumps([])
            if prompt.startswith("Responda em português"):
                seen_prompts["writer"] = prompt
                return ("Sobreposição parcial documentada entre River Review (acme), "
                        "River Plan e River Deploy no eixo revisão "
                        f"({A}) ({B}).\n"
                        "Sobreposição parcial documentada entre River Review (acme) "
                        f"e River Plan na revisão ({A}) ({B}).")
            raise AssertionError("Unexpected model call")

        with tempfile.TemporaryDirectory() as tmp:
            result = entry.adaptive_entry(
                question=st["question"], plan=p, profile="light", run_dir=tmp,
                user_context={"installed_riverhost_version": "2.1.4"},
                context_origin="harness",
                model_transport=model,
                search_transport=lambda *a, **kw: [{"url": A}, {"url": B}, {"url": c}],
                fetch_transport=lambda u: {"text": st["evidence"][u],
                                           "qualification": st["qualification"][u]},
                auditor_fn=lambda *a: {"enabled": False, "accepted": False,
                                       "verdict_state": "não revisado semanticamente"},
                overrides={"max_rounds": 0, "max_model_calls": 6}, clock=lambda: 0)
            out = Path(result["report_path"]).read_text()
            self.assertIn("INFERÊNCIA de sobreposição parcial", out)
            self.assertNotIn("Sobreposição parcial documentada", out)
            self.assertIn("Referência pendente", out)
            self.assertIn("River Deploy", out.split("Referência pendente", 1)[1])
            self.assertIn("relação comparativa é inferência", out)
            self.assertIn("nunca 'documentada'", seen_prompts["writer"])
            verification = json.loads((Path(tmp) / "verification.json").read_text())
            sent = verification["dimensions"]["support"]["evidence"]["sentence_support"]
            self.assertTrue(any("River Deploy" in x.get("missing_entities", [])
                                for x in sent.get("missing_entity_sources", [])),
                            sent.get("missing_entity_sources"))
            self.assertEqual(sent.get("inferred_comparisons", []), [], sent)
            self.assertEqual(len(sent.get("declared_inference", [])), 2, sent)
            self.assertTrue(all("nunca integração testada" in d.get("scope", "")
                                for d in sent.get("declared_inference", [])), sent)
            self.assertEqual(verification["dimensions"]["support"]["evidence"]["rendered_sha"],
                             hashlib.sha256(out.encode("utf-8")).hexdigest()[:16])
            self.assertTrue((Path(tmp) / "technical_annex.md").is_file())


if __name__ == "__main__":
    unittest.main()
