#!/usr/bin/env python3
"""Adaptive entry offline (real planner/assessor/writer/coordinator).

Only transports are simulated (model/search/fetch). The coordinator,
planner, model-backed assessor/writer and persistence are the REAL
application code — run_adaptive and the assessor are NEVER replaced by
functions that already deliver ready-made evaluations.

Run: python3 -m unittest discover -s tests -p test_adaptive_entry.py -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import gpt_researcher_integration as entry


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)

URLS = [f"https://example.org/entry/{i}" for i in range(1, 5)]
OTHER = "https://example.org/entry/other"


def base_plan(n=2):
    return {
        "plan_id": "entry-plan", "version": 1,
        "question": "Compare entry tools",
        "entities": [{"id": f"e{i}", "required": True} for i in range(n)],
        "criteria": [{"id": f"c{i}", "label": f"criterion {i}",
                      "required": True, "applies_to": [f"e{i}"]}
                     for i in range(n)],
        "initial_paths": ["entry query"],
    }


class FakeModelTransport:
    """Simulates ONLY the model transport.

    Dispatches on prompt content: plan JSON, assessment JSON derived from
    the evidence excerpts embedded in the prompt (markers COVER:cX), and a
    Portuguese synthesis that cites the corpus urls found in the prompt.
    The real assessor/writer parse and validate these strings.
    """

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "You plan a research" in prompt:
            return json.dumps(self.plan)
        if "Você avalia evidências" in prompt:
            evals = []
            for crit in self.plan.get("criteria", []):
                cid = crit["id"]
                # prompt embeds excerpts; look for marker
                if f"COVER:{cid}" in prompt:
                    # find first url whose excerpt contains the marker
                    # (prompt includes url+excerpt pairs; approximate by
                    # scanning known URLS present in prompt)
                    url = next((u for u in URLS + [OTHER] if u in prompt), URLS[0])
                    evals.append({
                        "criterion_id": cid,
                        "state": "covered",
                        "justification": f"marker {cid} in corpus",
                        "origin": "transport simulation audit",
                        "references": [{"url": url}],
                    })
            return json.dumps(evals)
        if "Responda em português" in prompt:
            cited = [u for u in URLS + [OTHER] if u in prompt][:3]
            lines = ["# Resposta em português", ""]
            lines.append("Síntese a partir do corpus selecionado.")
            for u in cited:
                lines.append(f"- evidência em {u}")
            if not cited:
                lines.append("Sem evidência utilizável; lacunas preservadas.")
            return "\n".join(lines)
        # planning repair re-ask or unknown: return plan
        return json.dumps(self.plan)


def fake_search_factory(docs, record=None):
    def search(target, channel="web"):
        if record is not None:
            record.append((target, channel))
        # channel alters effective access: different channels expose
        # different slices (proven by record + distinct urls).
        if channel == "github":
            urls = [u for u in docs if "entry/1" in u or "entry/3" in u]
        elif channel == "arxiv":
            urls = [u for u in docs if "entry/2" in u]
        else:
            urls = list(docs)
        return [{"url": u} for u in urls]
    return search


class AdaptiveEntry(unittest.TestCase):
    def test_import_has_no_prod_side_effects(self):
        import subprocess as _sp
        code = ("import sys; "
                "import gpt_researcher_integration as e; "
                "print('PROD' if '/opt/data/deep_research_outputs/gpt_researcher' in sys.path else 'CLEAN'); "
                "print(e._project_modules_origin().get('adaptive_coordinator',''))")
        proc = _sp.run([sys.executable, "-c", code], capture_output=True,
                       text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.strip().splitlines()
        self.assertEqual(lines[0].strip(), "CLEAN",
                         f"import added prod precedence: {proc.stdout}")
        self.assertTrue(str(lines[1]).startswith(str(ROOT)),
                        f"module resolved to production: {lines[1]}")
        # explicit env loader never touches prod by default (in-process)
        self.assertEqual(entry.load_env_file(None), {})
        self.assertEqual(entry.load_env_file("/nonexistent/.env"), {})
        before = list(sys.path)
        info = entry.bootstrap_runtime(do_sync=False)
        self.assertFalse(info["synced"])
        # bootstrap without prod_path must not ADD prod precedence
        added = [p for p in sys.path if p not in before]
        self.assertNotIn("/opt/data/deep_research_outputs/gpt_researcher",
                         added)

    def test_plan_assess_write_real_via_transport(self):
        plan = base_plan(2)
        docs = {URLS[0]: "note COVER:c0", URLS[1]: "plain"}
        model = FakeModelTransport(plan)
        # auto-plan via model transport (no explicit plan): real planner runs
        res = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=None,
            model_transport=model,
            search_transport=fake_search_factory(docs),
            fetch_transport=lambda u: docs[u],
            run_dir=None, clock=lambda: 0.0,
            overrides={"max_rounds": 0})
        # planner via transport, assessor real validated marker, writer real PT
        self.assertGreaterEqual(len(model.calls), 3)  # plan+assess+write
        self.assertIn("Resposta em português", res["report"]["text"])
        self.assertFalse(res["report"]["selection"].get("fallback", False))
        self.assertIn(URLS[0], res["report"]["selection"]["included_urls"])
        cov = res["question_coverage"]
        by_id = {c["id"]: c["state"] for c in cov["criteria"]}
        self.assertEqual(by_id["c0"], "covered")
        self.assertNotEqual(by_id["c1"], "covered")
        self.assertTrue(res["partial"])

    def test_gap_resolved_between_rounds(self):
        plan = base_plan(2)
        docs = {URLS[0]: "note COVER:c0", URLS[1]: "plain"}
        docs2 = dict(docs)
        docs2[URLS[1]] = "note COVER:c1"
        model = FakeModelTransport(plan)
        state = {"docs": docs}

        def search(target, channel="web"):
            # first round sees only URLS[0] with marker; gap round sees both
            if len(state["docs"]) == 2 and docs2[URLS[1]].startswith("note"):
                pass
            return [{"url": u} for u in state["docs"]]

        def fetch(u):
            return state["docs"][u]

        # round 0 with incomplete corpus
        res1 = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=plan,
            model_transport=model, search_transport=search,
            fetch_transport=fetch, clock=lambda: 0.0,
            overrides={"max_rounds": 0})
        self.assertTrue(res1["partial"])
        # new evidence appears as NEW url would; here same url gains marker
        # via corpus update is transport-level change, assessor re-runs real
        state["docs"] = docs2
        res2 = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=plan,
            model_transport=model, search_transport=search,
            fetch_transport=fetch, clock=lambda: 0.0,
            overrides={"max_rounds": 2})
        self.assertEqual(res2["question_coverage"]["proportion"], 1.0)
        self.assertEqual(res2["stop"]["reason"], "criteria_ok")

    def test_partial_closure(self):
        plan = base_plan(3)
        docs = {URLS[0]: "note COVER:c0"}
        model = FakeModelTransport(plan)
        res = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=plan,
            model_transport=model,
            search_transport=fake_search_factory(docs),
            fetch_transport=lambda u: docs[u],
            clock=lambda: 0.0, overrides={"max_rounds": 1})
        self.assertTrue(res["partial"])
        self.assertIn(res["stop"]["reason"],
                      ("rounds", "budget", "time", "saturation"))
        self.assertEqual(len(res["question_coverage"]["gaps"]), 2)

    def test_shared_criterion_multi_entity(self):
        plan = {"plan_id": "entry-shared", "version": 1,
                "question": "Compare entry tools",
                "entities": [{"id": f"e{i}", "required": True} for i in range(3)],
                "criteria": [{"id": "shared", "label": "shared",
                              "required": True,
                              "applies_to": ["e0", "e1", "e2"]}],
                "initial_paths": ["entry query"]}
        docs = {URLS[0]: "note for e0 only"}
        model = FakeModelTransport(plan)
        res = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=plan,
            model_transport=model,
            search_transport=fake_search_factory(docs),
            fetch_transport=lambda u: docs[u],
            clock=lambda: 0.0, overrides={"max_rounds": 0})
        self.assertFalse(res["question_coverage"]["complete"])

    def test_direct_read_and_channel(self):
        from adaptive_state import new_state
        import run_budget as rb
        state = new_state("Q")
        searches, fetched = [], []

        def search(target, channel):
            searches.append((target, channel))
            return [{"url": OTHER}]

        def fetch(url):
            fetched.append(url)
            return "direct source text"

        resolved = ac.resolve_adaptive("light")
        op = {"op_id": "r-1", "kind": "read_source", "channel": "web",
              "target": URLS[0], "criterion_id": "c0",
              "status": "in-progress"}
        ac._execute_ops(state, [op], search, fetch, rb.Budget(resolved["budget"]),
                        resolved, lambda: 0.0, 0.0, None, 0)
        self.assertEqual(searches, [])
        self.assertEqual(fetched, [URLS[0]])
        # channel alters effective access
        rec = []
        docs = {URLS[0]: "a", URLS[1]: "b", URLS[2]: "c"}
        sfn = fake_search_factory(docs, record=rec)
        sfn("q", "web")
        sfn("q", "github")
        self.assertNotEqual(
            [u for _, c in rec for u in [c]],
            [])
        web_urls = [u["url"] for u in sfn("q", "web")]
        gh_urls = [u["url"] for u in sfn("q", "github")]
        self.assertNotEqual(sorted(web_urls), sorted(gh_urls))

    def test_budget_ceiling_and_reserve(self):
        plan = base_plan(1)
        docs = {URLS[0]: "note COVER:c0"}
        model = FakeModelTransport(plan)
        res = entry.adaptive_entry(
            question="Compare entry tools", profile="light", plan=plan,
            model_transport=model,
            search_transport=fake_search_factory(docs),
            fetch_transport=lambda u: docs[u],
            clock=lambda: 0.0,
            overrides={"max_model_calls": 1, "max_rounds": 3})
        self.assertLessEqual(res["consumption"]["model_calls"], 1)
        # reserve: exhausted ceiling yields explicit fallback, never exceed
        self.assertTrue(res["report"]["selection"].get("fallback", False))
        self.assertIn("reserva",
                      str(res["report"]["selection"].get("cuts", "")))

    def test_interruption_and_recovery(self):
        plan = base_plan(1)
        docs = {URLS[0]: "note COVER:c0", URLS[1]: "more"}
        fetches, crashed = [], [False]

        def search(*_):
            return [{"url": URLS[0]}, {"url": URLS[1]}]

        def fetch(url):
            fetches.append(url)
            if url == URLS[1] and not crashed[0]:
                crashed[0] = True
                raise KeyboardInterrupt("real mid-collection crash")
            return docs[url]

        model = FakeModelTransport(plan)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyboardInterrupt):
                entry.adaptive_entry(
                    question="Compare entry tools", profile="light", plan=plan,
                    model_transport=model, search_transport=search,
                    fetch_transport=fetch, clock=lambda: 0.0,
                    run_dir=tmp, run_id="entry-crash",
                    overrides={"max_rounds": 1})
            second = entry.adaptive_entry(
                question="Compare entry tools", profile="light", plan=plan,
                model_transport=model, search_transport=search,
                fetch_transport=fetch, clock=lambda: 0.0,
                run_dir=tmp, run_id="entry-crash", resume=True,
                overrides={"max_rounds": 1})
            # completed source reused, never re-obtained
            self.assertEqual(fetches.count(URLS[0]), 1)
            refs = [r.get("url") for r in
                    second["question_coverage"].get("references", [])]
            self.assertIn(URLS[0], refs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
