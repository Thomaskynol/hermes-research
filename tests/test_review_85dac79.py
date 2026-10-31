"""Second independent offline review of sources reported as 85dac79.

Run after copying into the project's tests/ directory:
  python -m unittest discover -s tests -p test_review_85dac79.py -v
Failures state unresolved contract violations, not changes to production.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Second review: external network is forbidden")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl
import run_budget as rb
import semantic_review as sr

URL = "https://example.org/source/one"
URL2 = "https://example.org/source/two"
FACT = "O pacote opencode-alpha é gratuito e usa licença MIT."


def plan(n=1):
    return {
        "plan_id": "second-review", "version": 1,
        "entities": [{"id": f"e{i}", "required": True} for i in range(n)],
        "criteria": [{"id": f"c{i}", "label": f"criterion {i}",
                      "required": True, "applies_to": [f"e{i}"]}
                     for i in range(n)],
        "initial_paths": ["query"],
    }


def qualification(text):
    return {"status": "usable", "excluded": False, "usable_text": text}


def ev(cid="c0", url=URL):
    return {"criterion_id": cid, "state": "covered",
            "justification": "Assessment based on identified obtained text",
            "origin": "controlled model response", "references": [{"url": url}]}


def writer(view):
    return "Relatório de teste", {"included_urls": [], "cuts": "test boundary"}


def auditor(report, evidence):
    return {"enabled": False, "accepted": False}


class SecondReview(unittest.TestCase):
    def test_s01_default_auditor_cannot_bypass_zero_model_budget(self):
        p = plan()
        state = state_api.new_state("A software question")
        state["plan"] = p
        state["evidence"] = {URL: FACT}
        state["qualification"] = {URL: qualification(FACT)}
        state["stop"] = {"reason": "budget", "partial": True, "detail": "limit zero"}
        ledger = cl.Ledger(p)
        ledger.set_corpus(state["evidence"], state["qualification"])
        ledger.evaluate("c0", "covered", "\n\n" + FACT + "\n\n",
                        "controlled assessment", [{"url": URL}])
        calls = []
        async def vote(items, model, batch_size=12):
            calls.append([item["id"] for item in items])
            return [{"id": item["id"], "verdict": "sustained",
                     "support": "simulated provider response", "correction": ""}
                    for item in items]
        resolved = ac.resolve_adaptive("light", {"max_model_calls": 0})
        with patch.object(sr, "_review_pass", vote):
            result = ac._finalize(
                state, resolved, rb.Budget(resolved["budget"]), ledger.compute(),
                ac._default_writer, None, 0.0, lambda: 0.0, None)
        self.assertEqual(len(calls), 0,
                         f"Default audit made {len(calls)} simulated provider passes; "
                         f"recorded model calls={result['consumption']['model_calls']}")

    def test_s02_default_auditor_honors_explicit_semantic_disable(self):
        def review(report, evidence, enabled=True, **kwargs):
            return {"enabled": enabled, "accepted": False}
        with patch.dict(os.environ, {"SEMANTIC_REVIEW": "0"}), \
                patch.object(sr, "review_report", review):
            result = ac._default_auditor(FACT, {URL: FACT})
        self.assertFalse(result["enabled"])

    def test_s03_real_assessor_preserves_open_discovery_proposals(self):
        p = plan()
        p["open_discovery"] = {"needed": True}
        proposed = ev()
        proposed["propose_entity"] = {
            "entity": {"id": "new-candidate", "label": "New candidate"},
            "criteria": [{"id": "new-criterion", "required": True,
                          "applies_to": ["new-candidate"]}],
        }
        assessor = ac.make_model_assessor(lambda prompt: json.dumps([proposed]))
        state = state_api.new_state("Discover alternatives")
        state["plan"] = p
        state["discovery"]["open"] = True
        state["evidence"] = {URL: "A source describing the new candidate"}
        state["qualification"] = {URL: qualification(state["evidence"][URL])}
        ledger = cl.Ledger(p)
        ac._assess_round(state, assessor, ledger, ac.resolve_adaptive("light"))
        self.assertIn("new-candidate", [e["id"] for e in state["plan"]["entities"]])

    def test_s04_raw_error_string_is_not_qualified_as_usable(self):
        text = "ERROR: HTTP 403 Forbidden. Access denied."
        _, qual = ac._coerce_payload(text, URL)
        self.assertTrue(qual["excluded"], str(qual))

    def test_s05_writer_records_per_document_truncation(self):
        prompts = []
        def model(prompt):
            prompts.append(prompt)
            return "Resposta baseada no trecho disponível."
        write = ac.make_model_writer(model)
        _, selection = write({"question": "Explain the document",
                              "question_coverage": {},
                              "evidence": {URL: "X" * 5000}})
        self.assertLess(prompts[0].count("X"), 5000)
        self.assertNotEqual(selection["cuts"], "sem cortes", str(selection))

    def test_s06_resume_keeps_evaluations_accumulated_across_rounds(self):
        searches, assessments = [0], [0]
        def search(*_):
            searches[0] += 1
            if searches[0] == 1:
                return [{"url": URL}]
            if searches[0] == 2:
                return [{"url": URL2}]
            return []
        def assess(*_):
            assessments[0] += 1
            if assessments[0] == 1:
                return [ev("c0", URL)]
            if assessments[0] == 2:
                return [ev("c1", URL2)]
            return []
        with tempfile.TemporaryDirectory() as tmp:
            result = ac.run_adaptive(
                "A question", plan=plan(2), search_fn=search,
                fetch_fn=lambda url: "Evidence obtained at " + url,
                assess_fn=assess, writer_fn=writer, auditor_fn=auditor,
                run_dir=tmp, run_id="resume-evaluations", clock=lambda: 0.0,
                overrides={"max_rounds": 3, "max_model_calls": 20})
            self.assertTrue(result["question_coverage"]["complete"])
            resumed = ac.run_adaptive(
                "A question", resume=True, search_fn=search,
                fetch_fn=lambda url: "Evidence obtained at " + url,
                assess_fn=assess, writer_fn=writer, auditor_fn=auditor,
                run_dir=tmp, run_id="resume-evaluations", clock=lambda: 0.0,
                overrides={"max_rounds": 3, "max_model_calls": 20})
            self.assertTrue(resumed["question_coverage"]["complete"],
                            f"Coverage regressed without new invalidating evidence: "
                            f"{resumed['question_coverage']['proportion']}")

    def test_s07_assessor_cannot_cover_using_material_not_sent(self):
        hidden = "https://example.org/source/hidden-after-twenty-four"
        evidence = {f"https://example.org/source/{i:02}": f"Unrelated criterion excerpt {i}"
                    for i in range(24)}
        evidence[hidden] = "The only facts that address the mandatory criterion"
        prompts = []
        def model(prompt):
            prompts.append(prompt)
            return json.dumps([ev("c0", hidden)])
        assessor = ac.make_model_assessor(model)
        state = state_api.new_state("A question")
        state["plan"] = plan()
        state["evidence"] = evidence
        state["qualification"] = {u: qualification(t) for u, t in evidence.items()}
        _, coverage = ac._assess_round(
            state, assessor, cl.Ledger(state["plan"]), ac.resolve_adaptive("light"))
        self.assertNotIn(hidden, prompts[0])
        self.assertFalse(coverage["complete"],
                         "Reference resolves in storage but its material was not analyzed")

    def test_s08_internal_typeerror_is_not_retried_as_signature_detection(self):
        calls = []
        def assessor(*args):
            calls.append(len(args))
            if len(calls) == 1:
                raise TypeError("Internal failure after entering the assessor")
            return []
        state = state_api.new_state("A question")
        state["plan"] = plan()
        try:
            ac._assess_round(state, assessor, cl.Ledger(state["plan"]),
                             ac.resolve_adaptive("light", {"max_model_calls": 1}))
        except ac.TransportError:
            pass
        self.assertEqual(len(calls), 1,
                         f"Assessor executed twice but accounted once: {calls}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
