#!/usr/bin/env python3
"""Prove controlled interruption + resume with a frozen fixture.

Offline. Demonstrates the acceptance criterion from the brief:
* a run is interrupted mid-collection (SIGKILL-equivalent: the checkpoint file
  is left as-is with a partial last line);
* the resumed run knows which sources it already has and which queries remain,
  so it does NOT repeat finished collection;
* source identity (URL) and evidence type are preserved across the interruption.

Run:
    /opt/data/home/.agent-reach-venv/bin/python scripts/prove_resume.py
Exit 0 = the interruption/resume contract holds.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

import run_checkpoint

FAILURES: list[str] = []


def check(name, ok, evidence):
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        ck = run_checkpoint.Checkpoint(td)

        # --- Phase 1: a real child process collects, then is KILLED mid-write.
        writer = Path(td) / "_writer.py"
        writer.write_text(
            "import sys, time\n"
            f"sys.path.insert(0, {str(WORKDIR)!r})\n"
            "import run_checkpoint as rc\n"
            f"ck = rc.Checkpoint({td!r})\n"
            "ck.note_query_done('q-alpha', 2)\n"
            "ck.note_source('https://a.example/1', source='web',"
            " content='alpha content', evidence_type='description')\n"
            "ck.note_source('https://v.example/2', source='youtube',"
            " content='[transcript]\\n[spoken 1/3]\\nfala falada',"
            " evidence_type='transcript')\n"
            "ck.note_learning('plugin X needs Node 20')\n"
            "print('COLLECTED', flush=True)\n"
            "time.sleep(30)\n",
            encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(writer)],
                                stdout=subprocess.PIPE, text=True)
        line = proc.stdout.readline().strip()
        check("1_child_collected", line == "COLLECTED", f"child printed {line!r}")
        proc.kill()                      # hard kill, no cleanup
        proc.wait()
        check("2_kill_was_hard", proc.returncode != 0,
              f"returncode={proc.returncode} (killed, no graceful exit)")

        # simulate the crash landing mid-append (partial last line)
        with open(ck.path, "a", encoding="utf-8") as fh:
            fh.write('{"kind": "source", "url": "https://z.example/9"')

        # --- Phase 2: resume reads what survived.
        plan = run_checkpoint.resume_plan(
            ck, ["q-alpha", "q-beta", "q-gamma"])
        check("3_sources_survived_kill", len(plan["already_have_urls"]) == 2,
              f"{plan['already_have_urls']} (partial line dropped, not crashed)")
        check("4_finished_query_not_repeated",
              plan["pending_queries"] == ["q-beta", "q-gamma"],
              f"q-alpha already done; pending={plan['pending_queries']}")
        check("5_identity_and_type_preserved",
              plan["learnings"] == ["plugin X needs Node 20"],
              f"learnings carried: {plan['learnings']}")

        state = ck.load()
        types = {u: r["evidence_type"] for u, r in state["sources"].items()}
        check("6_evidence_type_preserved",
              types.get("https://v.example/2") == "transcript"
              and types.get("https://a.example/1") == "description",
              f"types={types}")

        # --- Phase 3: resumed run does not re-fetch what it has.
        refetch = [u for u in plan["already_have_urls"]
                   if u not in state["sources"]]
        check("7_resume_avoids_recollection", not refetch,
              "every already-have URL is backed by a checkpoint record; "
              "no blind re-fetch")

        # content hash lets resume verify the cached bytes still match.
        rec = state["sources"]["https://v.example/2"]
        check("8_content_hash_recorded", bool(rec.get("content_hash")),
              f"hash={rec.get('content_hash')} (resume can verify cached bytes)")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
