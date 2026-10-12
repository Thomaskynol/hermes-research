#!/usr/bin/env python3
"""Gates for global run limits + crash-safe resume + deep guard behaviour.

Offline, frozen fixtures, no network/model calls. Run with:
    /opt/data/home/.agent-reach-venv/bin/python scripts/verify_run_limits.py
Exit 0 = all pass.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

import run_budget
import run_checkpoint
import depth_profiles

FAILURES: list[str] = []


def check(name, ok, evidence):
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def main() -> int:
    # ---- A. per-profile budget ceilings ----
    for prof, want in (("light", 600), ("medium", 1800),
                       ("hard", 3600), ("deep", 7200)):
        r = depth_profiles.resolve(prof)
        check(f"A1_{prof}_time_budget", r["budget"]["time_s"] == want,
              f"time_s={r['budget']['time_s']} queries={r['budget']['queries']}")

    r = depth_profiles.resolve("deep", {"budget_time_s": 120, "budget_queries": 5})
    check("A2_override_budget",
          r["budget"]["time_s"] == 120 and r["budget"]["queries"] == 5,
          f"override honoured: {r['budget']}")

    # ---- B. budget accounting + stop reason ----
    run_budget.reset()
    b = run_budget.install("light", {"queries": 3, "extractions": 2,
                                     "yt_live_fetches": 1, "time_s": 0})
    ok1 = b.spend("queries", 2)
    ok2 = b.spend("queries", 2)   # would exceed 3
    check("B1_refuses_over_limit", ok1 and not ok2,
          f"spend(2)={ok1} spend(2 again)={ok2} used={b.snapshot()['used']}")
    check("B2_stop_reason_named", b.exhausted() == "budget:queries",
          f"exhausted()={b.exhausted()!r} (not a bare 'coverage')")
    check("B3_remaining", b.remaining("queries") == 1,
          f"remaining(queries)={b.remaining('queries')}")
    check("B4_unenforced_declared",
          b.snapshot()["unenforced"] == ["tokens", "cost_usd"],
          "tokens/cost declared unenforced, not faked")
    run_budget.reset()

    # ---- C. concurrent branches do not double-spend ----
    run_budget.reset()
    b = run_budget.install("light", {"queries": 10, "extractions": 10,
                                     "yt_live_fetches": 10, "time_s": 0})
    results = []

    def worker():
        for _ in range(5):
            results.append(b.spend("queries", 1))

    import threading
    ts = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    granted = sum(1 for x in results if x)
    check("C1_concurrent_no_double_spend", granted == 10,
          f"{granted} granted across 4 threads x5 (limit 10) — lock holds")
    run_budget.reset()

    # ---- D. crash-safe checkpoint + resume ----
    with tempfile.TemporaryDirectory() as td:
        ck = run_checkpoint.Checkpoint(td)
        ck.note_query_done("q1", 2)
        ck.note_source("https://a.com/1", source="web",
                       content="hello world", evidence_type="description")
        ck.note_source("https://b.com/2", source="youtube",
                       content="[transcript]\n[spoken 1/2]\nfala", evidence_type="transcript")
        ck.note_learning("found plugin X")
        # simulate a hard kill: truncated final line
        with open(ck.path, "a", encoding="utf-8") as fh:
            fh.write('{"kind": "source", "url": "https://c.com/3"')  # no newline/close
        plan = run_checkpoint.resume_plan(ck, ["q1", "q2", "q3"])
        check("D1_survives_truncated_tail", len(plan["already_have_urls"]) == 2,
              f"2 complete sources kept, partial line skipped: {plan['already_have_urls']}")
        check("D2_does_not_repeat_done_query", plan["pending_queries"] == ["q2", "q3"],
              f"done q1 not repeated; pending={plan['pending_queries']}")
        check("D3_preserves_identity_and_type",
              plan["learnings"] == ["found plugin X"]
              and plan["already_have_urls"] == ["https://a.com/1", "https://b.com/2"],
              "learnings + URL identity preserved across the crash")

        # ---- E. resume does not re-collect (integration with vast selection) ----
        state = ck.load()
        yt = [u for u, r in state["sources"].items() if r["evidence_type"] == "transcript"]
        check("E1_resume_skips_recollection", yt == ["https://b.com/2"],
              f"transcript source identified for reuse without re-fetch: {yt}")

    # ---- F. deep guard: preserves state + flags insufficient evidence ----
    import deep_research_fix
    from gpt_researcher.skills.deep_research import DeepResearchSkill

    async def zero_queries(self, query, num_queries=3):
        return []

    deep_research_fix.install()
    inst = object.__new__(DeepResearchSkill)
    inst.generate_search_queries = zero_queries.__get__(inst, DeepResearchSkill)
    out = asyncio.run(DeepResearchSkill.deep_research(
        inst, "q", breadth=2, depth=1,
        learnings=["prior learning"], citations={"https://x": "title"},
        visited_urls={"https://x"}))
    check("F1_preserves_prior_learnings", out["learnings"] == ["prior learning"],
          f"learnings carried through the zero-query branch: {out['learnings']}")
    check("F2_preserves_citations_urls",
          out["citations"] == {"https://x": "title"} and out["visited_urls"] == {"https://x"},
          "citations + visited_urls preserved, not zeroed")
    check("F3_flags_insufficient_evidence", out.get("insufficient_evidence") is True,
          "explicit flag so callers cannot read this as coverage")
    check("F4_no_new_evidence_is_not_coverage",
          out["insufficient_evidence"] is True and out["context"] == [],
          "no context produced -> cannot be counted as coverage")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
