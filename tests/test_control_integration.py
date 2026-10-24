#!/usr/bin/env python3
"""Integração do controle de execução (pause/resume/cancel) com o coordenador
real e manifesto da execução. Offline: só transportes simulados.

Run: python3 -m unittest tests.test_control_integration -v
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("control integration tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac  # noqa: E402
import gpt_researcher_integration as entry  # noqa: E402


A = "https://example.org/ctrl/a"
B = "https://example.org/ctrl/b"


def plan():
    return {
        "plan_id": "ctrl-plan", "version": 1,
        "question": "Pergunta de controle",
        "entities": [{"id": "e0", "label": "entidade 0", "required": True}],
        "criteria": [{"id": "c0", "label": "critério 0",
                      "required": True, "applies_to": ["e0"]}],
        "initial_paths": ["consulta inicial"],
    }


def transports(fetches=None):
    docs = {A: "Página A com evidência COVER:c0",
            B: "Página B complementar"}
    def search(target, channel="web"):
        return [{"url": u} for u in docs]
    def fetch(url):
        if fetches is not None:
            fetches[url] = fetches.get(url, 0) + 1
        return docs.get(url, "conteúdo de " + url)
    evals = [{"criterion_id": "c0", "state": "covered",
              "justification": "evidência na página A",
              "origin": "avaliação simulada",
              "references": [{"url": A}]}]
    def model(prompt):
        if "Você avalia evidências" in prompt:
            return json.dumps(evals)
        return "relatório parcial honesto"
    return search, fetch, model


class ScriptControl:
    """Controle programável: poll consome o roteiro; status é registrado."""
    def __init__(self, script):
        self.script = list(script)
        self.statuses = []

    def poll(self):
        if self.script:
            return self.script.pop(0)
        return None

    def write_status(self, **kw):
        self.statuses.append(kw)
        return kw


def run(ctrl, run_dir, fetches, overrides=None, resume=False):
    search, fetch, model = transports(fetches)
    assess = ac.make_model_assessor(model, max_docs=3)
    return ac.run_adaptive(
        "Pergunta de controle", profile="light", plan=plan(),
        search_fn=search, fetch_fn=fetch, assess_fn=assess,
        writer_fn=lambda view: ("Síntese honesta.", {"included_urls": [A],
                                                     "cuts": "nenhum"}),
        auditor_fn=lambda report, evidence: {"enabled": False,
                                             "accepted": False},
        clock=time.monotonic, run_dir=run_dir, run_id="ctrl-run",
        overrides={"max_rounds": 0, **(overrides or {})},
        control=ctrl, resume=resume)


class ControlIntegration(unittest.TestCase):
    def test_pause_preserves_state_and_resume_continues_without_repetition(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = str(Path(tmp) / "run")
            fetches: dict = {}
            ctrl = ScriptControl([None, None, "pause"])
            first = run(run_dir=run_dir, ctrl=ctrl, fetches=fetches)
            self.assertTrue(first.get("partial"))
            self.assertEqual(first["stop"]["reason"], "paused")
            phases = [s["phase"] for s in ctrl.statuses]
            for expected in ("plan", "round", "finalize", "done"):
                self.assertIn(expected, phases)
            obtained = list(first["counters"]["documents"]["obtained"])
            self.assertIn(A, obtained)
            n_fetches_after_pause = dict(fetches)
            # Retomada: sem comando, continua e não re-obtém o já concluído.
            resumed = run(run_dir=run_dir, ctrl=ScriptControl([]),
                          fetches=fetches, overrides=None, resume=True)
            self.assertEqual(resumed["stop"]["reason"], "rounds")
            for url, n in n_fetches_after_pause.items():
                self.assertEqual(fetches.get(url, 0), n,
                                 f"{url} re-obtido na retomada")
            self.assertEqual(set(resumed["counters"]["documents"]["obtained"]),
                             set(obtained))

    def test_cancel_marks_cancelled_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = str(Path(tmp) / "run")
            ctrl = ScriptControl(["cancel"])
            result = run(run_dir=run_dir, ctrl=ctrl, fetches={})
            self.assertTrue(result.get("partial"))
            self.assertEqual(result["stop"]["reason"], "cancelled")

    def test_resume_without_command_finishes_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = str(Path(tmp) / "run")
            result = run(run_dir=run_dir, ctrl=ScriptControl([]), fetches={})
            self.assertEqual(result["stop"]["reason"], "rounds")


class ManifestTest(unittest.TestCase):
    def _result(self, run_id="ctrl-run"):
        return {"run_id": run_id, "profile": "light",
                "counters": {"counts": {"obtained": 1}},
                "resolved": {"profile": "light", "max_rounds": 0},
                "stop": {"reason": "rounds_exhausted", "partial": False}}

    def test_manifest_records_simulated_flag_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            for simulated in (True, False):
                path = entry.write_adaptive_manifest(
                    run_dir, result=self._result(), question="Q",
                    transport="native", model_transport="opencode",
                    model_info={"kind": "opencode", "model_id": "m",
                                "calls": 2},
                    simulated=simulated)
                manifest = json.loads(Path(path).read_text(encoding="utf-8"))
                self.assertEqual(manifest["simulated"], simulated)
                blob = json.dumps(manifest)
                self.assertNotIn("sk-or-v1", blob)
                self.assertNotIn("Bearer", blob)
                self.assertEqual(manifest["models"]["model_id"], "m")
