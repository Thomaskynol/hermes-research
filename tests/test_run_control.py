#!/usr/bin/env python3
"""Contratos do controle de execução (status/control), offline.

Run: python3 -m unittest tests.test_run_control -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_control as rc  # noqa: E402


class StatusFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = Path(self._tmp.name) / "adaptive_run1"
        self.control = rc.RunControl(self.run_dir)

    def test_write_status_is_atomic_and_complete(self):
        payload = self.control.write_status(
            phase="round", round_no=2, counters={"queries": 3},
            elapsed_s=1.5, detail="assessing")
        self.assertTrue(self.control.status_path.is_file())
        self.assertEqual(list(self.run_dir.glob("*.tmp-*")), [])
        self.assertEqual(payload["run_id"], "adaptive_run1")
        self.assertEqual(payload["phase"], "round")
        self.assertEqual(payload["round"], 2)
        self.assertEqual(payload["counters"], {"queries": 3})
        self.assertEqual(payload["elapsed_s"], 1.5)
        self.assertEqual(payload["detail"], "assessing")
        self.assertEqual(payload["pid"], __import__("os").getpid())
        parsed = datetime.fromisoformat(payload["updated_at"].replace("Z", "+00:00"))
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)
        self.assertEqual(self.control.read_status(), payload)

    def test_status_overwrite_keeps_only_last(self):
        self.control.write_status(phase="round", round_no=1)
        self.control.write_status(phase="final", stop="done")
        status = self.control.read_status()
        self.assertEqual(status["phase"], "final")
        self.assertEqual(status["stop"], "done")
        self.assertNotIn("round", status)

    def test_read_status_missing_or_invalid_is_none(self):
        self.assertIsNone(self.control.read_status())
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.control.status_path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(self.control.read_status())


class ControlFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = Path(self._tmp.name) / "run"
        self.control = rc.RunControl(self.run_dir)

    def test_request_then_poll_consumes_once(self):
        self.control.request("pause")
        self.assertTrue(self.control.control_path.is_file())
        self.assertEqual(self.control.poll(), "pause")
        self.assertFalse(self.control.control_path.exists())
        self.assertTrue(self.control.taken_path.is_file())
        self.assertIsNone(self.control.poll())

    def test_poll_without_control_is_none(self):
        self.assertIsNone(self.control.poll())

    def test_invalid_json_is_quarantined_not_deleted(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.control.control_path.write_text("{broken", encoding="utf-8")
        self.assertIsNone(self.control.poll())
        self.assertFalse(self.control.control_path.exists())
        quarantined = list(self.run_dir.glob("control.invalid-*.json"))
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_text(encoding="utf-8"), "{broken")

    def test_unknown_command_is_quarantined(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.control.control_path.write_text(
            json.dumps({"command": "explode"}), encoding="utf-8")
        self.assertIsNone(self.control.poll())
        self.assertEqual(len(list(self.run_dir.glob("control.invalid-*.json"))), 1)

    def test_request_rejects_invalid_command(self):
        with self.assertRaises(ValueError):
            self.control.request("explode")
        self.assertFalse(self.control.control_path.exists())

    def test_all_valid_commands(self):
        for command in ("pause", "resume", "cancel"):
            self.control.request(command)
            self.assertEqual(self.control.poll(), command)

    def test_clear_removes_files_but_not_run_dir(self):
        self.control.write_status(phase="round")
        self.control.request("pause")
        self.control.poll()
        self.control.clear()
        self.assertTrue(self.run_dir.is_dir())
        self.assertFalse(self.control.status_path.exists())
        self.assertFalse(self.control.control_path.exists())
        self.assertFalse(self.control.taken_path.exists())


class Cli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = Path(self._tmp.name) / "run"

    def test_pause_returns_zero_and_writes_control(self):
        self.assertEqual(rc.main(["--run-dir", str(self.run_dir), "pause"]), 0)
        self.assertEqual(rc.RunControl(self.run_dir).poll(), "pause")

    def test_status_returns_zero_when_status_exists(self):
        control = rc.RunControl(self.run_dir)
        control.write_status(phase="round", round_no=1)
        self.assertEqual(rc.main(["--run-dir", str(self.run_dir), "status"]), 0)

    def test_status_missing_returns_two(self):
        self.assertEqual(rc.main(["--run-dir", str(self.run_dir), "status"]), 2)

    def test_invalid_usage_returns_two(self):
        with self.assertRaises(SystemExit) as ctx:
            rc.main(["--run-dir", str(self.run_dir), "explode"])
        self.assertEqual(ctx.exception.code, 2)

    def test_subprocess_entry_point(self):
        missing = subprocess.run(
            [sys.executable, str(ROOT / "run_control.py"),
             "--run-dir", str(self.run_dir), "status"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("no status.json", missing.stderr)
        paused = subprocess.run(
            [sys.executable, str(ROOT / "run_control.py"),
             "--run-dir", str(self.run_dir), "pause"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(paused.returncode, 0)
        self.assertEqual(rc.RunControl(self.run_dir).poll(), "pause")


if __name__ == "__main__":
    unittest.main(verbosity=2)
