"""Untried-channel rescue: never declare blocked while a path was untried.

Regression from real run satrun5 (2026-10-25): round 0 tried arxiv
(transient Atom errors) + github (nogain); web was never attempted, yet
the run stopped `blocked` after round 0 with 0 evidence. A blocked stop
is only honest after every channel was tried.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("rescue test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def make_plan():
    return {
        "plan_id": "rescue", "version": 1,
        "entities": [{"id": "e0", "required": True}],
        "criteria": [{"id": "c0", "label": "criterion zero",
                      "required": True, "applies_to": ["e0"]}],
        "initial_paths": [
            {"query": "q-arxiv", "channel": "arxiv"},
            {"query": "q-github", "channel": "github"},
        ],
    }


def fresh_state():
    import adaptive_state as state_api
    state = state_api.new_state("rescue question")
    state["plan"] = make_plan()
    return state


class UntriedChannelTest(unittest.TestCase):
    def test_select_ops_prefers_untried_channel(self):
        state = fresh_state()
        state["attempts"] = {"c0": [
            {"channel": "arxiv", "outcome": "failed"},
            {"channel": "github", "outcome": "nogain"},
        ]}
        gaps = [{"criterion_id": "c0", "label": "criterion zero"}]
        ops = ac.select_ops(state, gaps, cap=1)
        self.assertEqual(len(ops), 1)
        # web was never tried: rescue must go there, not rotate arxiv->github.
        self.assertEqual(ops[0]["channel"], "web")

    def test_run_does_not_stop_blocked_with_web_untried(self):
        def search_fn(query, channel="web"):
            if channel in ("arxiv", "github"):
                raise ac.TransportError(f"{channel} down in stub")
            return [{"url": "https://example.org/rescued",
                     "title": "rescued", "snippet": "rescued substance"}]

        def fetch_fn(url):
            # Raw payload (never pre-wrapped): the coordinator wraps it
            # into ("ok", payload) itself; a pre-wrapped tuple would be
            # double-wrapped and rejected by _coerce_payload.
            return {"text": "substantive rescued text about c0",
                    "status": "usable"}

        def assess_fn(plan, evidence, qualification, attempts=None):
            if evidence:
                return [{"criterion_id": "c0", "entity_id": "e0",
                         "state": "partial",
                         "justification": "web evidence incorporated",
                         "origin": "stub",
                         "references": [{"url": u} for u in evidence]}]
            return [{"criterion_id": "c0", "entity_id": "e0",
                     "state": "blocked",
                     "justification": "nothing obtained yet",
                     "origin": "stub", "references": []}]

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            res = ac.run_adaptive(
                "rescue question", profile="light", plan=make_plan(),
                search_fn=search_fn, fetch_fn=fetch_fn, assess_fn=assess_fn,
                writer_fn=lambda view: ("stub synthesis", {}),
                auditor_fn=lambda report, evidence: {"status": "ok"},
                overrides={"max_rounds": 3, "max_ops_per_round": 2,
                           "max_model_calls": 6, "time_s": 120},
                clock=lambda: 0.0, run_dir=tmp)
            import adaptive_state as state_api
            import json
            from pathlib import Path as _P
            saved = json.loads(
                (_P(tmp) / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(saved["evidence"], "web rescue must obtain evidence")
        self.assertNotEqual(
            (res.get("stop") or {}).get("detail"),
            "all required criteria blocked",
            "must not stop blocked while web was untried")
        self.assertTrue(any("blocked stop deferred" in str(n)
                            for n in saved.get("notes", [])))


if __name__ == "__main__":
    unittest.main()
