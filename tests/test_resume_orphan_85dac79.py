#!/usr/bin/env python3
"""Orphan checkpoint branch + run identity/consumption preservation (S06).

_stateless, offline: _reconcile_resume with a checkpoint-only URL becomes
an explicit retry candidate; run_id and accumulated consumption travel in
state (never reset on resume).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac
import adaptive_state as st


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline")


sys.addaudithook(deny_network)


class FakeCheckpoint:
    def __init__(self, urls):
        self._urls = list(urls)

    def load(self):
        return {"sources": {u: {"url": u} for u in self._urls},
                "queries_done": [], "learnings": []}


class ResumeOrphan(unittest.TestCase):
    def test_orphan_becomes_explicit_retry(self):
        state = st.new_state("Q", run_id="run-orph-1")
        state["consumption"]["model_calls"] = 3
        state["evidence"] = {"https://example.org/kept": "kept text"}
        ckpt = FakeCheckpoint(["https://example.org/kept",
                               "https://example.org/orphan-only"])
        ac._reconcile_resume(state, ckpt, run_dir=None)
        self.assertIn("https://example.org/orphan-only",
                      state["discovery"]["candidates"])
        self.assertNotIn("https://example.org/kept",
                         state["discovery"]["candidates"])
        self.assertTrue(any("orphan" in n or "retry" in n
                            for n in state["notes"]),
                        str(state["notes"]))
        # run_id e consumo preservados (não resetados na retomada)
        self.assertEqual(state["run_id"], "run-orph-1")
        self.assertEqual(state["consumption"]["model_calls"], 3)

    def test_no_orphan_no_candidates(self):
        state = st.new_state("Q", run_id="run-orph-2")
        ckpt = FakeCheckpoint([])
        ac._reconcile_resume(state, ckpt, run_dir=None)
        self.assertEqual(state["discovery"]["candidates"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
