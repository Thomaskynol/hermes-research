#!/usr/bin/env python3
"""Quality gate: depth profiles for the deep-research skill.

No arguments. Offline, frozen fixtures inline, no model/network calls.
Tests depth_profiles.py (table, resolve, counts, stop rules, provenance)
plus the gpt_researcher_integration.py wiring (static checks only — the
module runs sync_config.sync() at import, which needs live services).

Exit 0 = all pass. Exit 1 = any failure. Every line printed is
`PASS|FAIL name: objective evidence`.
"""
import json
import sys
import tempfile
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
sys.path.insert(0, str(WORKDIR / "scripts"))

# Hermetic execution: drop foreign venv paths (same cleanup as the other
# verify scripts).
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

import depth_profiles as dp

FAILURES: list[str] = []


def check(name: str, ok: bool, evidence: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def expect_raise(name: str, fn, evidence: str) -> None:
    try:
        fn()
    except ValueError:
        check(name, True, evidence)
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"wrong exception {type(exc).__name__}: {exc}")
    else:
        check(name, False, "no exception raised")


# ---- frozen fixtures (inline, no network) ----
FIX_DOCS = [
    {"url": "https://www.youtube.com/watch?v=abc123DEF45",
     "content": "[transcript origin=live lang=en automatic=unknown chars=500 "
                "segments=2]\n[spoken 1/2]\nhello world\n[spoken 2/2]\nbye",
     "provenance": "vast-cache"},
    {"url": "https://www.youtube.com/watch?v=abc123DEF45#frag",
     "content": "[transcript origin=live lang=en automatic=unknown chars=500 "
                "segments=2]\n[spoken 1/2]\nhello world chunk2",
     "provenance": "vast-cache"},
    {"url": "https://github.com/owner/repo",
     "content": "[description]\nA repo readme about plugins.",
     "provenance": "vast-page"},
    {"url": "https://example.com/guide?x=1",
     "content": "plain web content with details",
     "provenance": "searx"},
    {"url": "https://example.com/guide?x=2",
     "content": "different query string, different doc",
     "provenance": "searx"},
]

FIX_REPORT = (
    "See [the guide](https://example.com/guide?x=1) for setup.\n"
    "Source: `https://www.youtube.com/watch?v=abc123DEF45`, [spoken 1/2]\n"
)

FIX_MESSAGES = (
    "Source: https://www.youtube.com/watch?v=abc123DEF45\n"
    "[spoken 1/2]\nhello world\n"
    "Source: https://example.com/guide?x=1\nplain web content\n"
)

FIX_SECTIONS = [
    {"url": "https://www.youtube.com/watch?v=abc123DEF45",
     "content": "[transcript origin=cache lang=en automatic=unknown "
                "chars=500 segments=2]\n[spoken 1/2]\nhello",
     "provenance": "vast-cache"},
    {"url": "https://github.com/owner/repo",
     "content": "[description]\nA repo readme about plugins.",
     "provenance": "vast-page"},
    {"url": "https://example.com/plain",
     "content": "no markers here at all",
     "provenance": "searx"},
]

TABLE = {
    "light": ("quick_report", 1, 2, 1, 600, 6, 1),
    "medium": ("research_report", 2, 3, 2, 1200, 10, 2),
    "hard": ("detailed_report", 3, 5, 3, 2500, 12, 3),
    "deep": ("deep", 5, 8, 4, 4000, 12, 3),
}


def main() -> int:
    # ---- T. profile table ----
    for profile, (rt, it, br, de, wo, vm, yl) in TABLE.items():
        r = dp.resolve(profile)
        ok = (r["report_type"] == rt and r["MAX_ITERATIONS"] == it
              and r["DEEP_RESEARCH_BREADTH"] == br
              and r["DEEP_RESEARCH_DEPTH"] == de
              and r["TOTAL_WORDS"] == wo
              and r["vast_max"] == vm and r["yt_live"] == yl
              and r["profile"] == profile
              and r["DEEP_RESEARCH_CONCURRENCY"] == 4)
        check(f"T_table_{profile}", ok,
              f"report_type={r['report_type']} it={r['MAX_ITERATIONS']} "
              f"br={r['DEEP_RESEARCH_BREADTH']} de={r['DEEP_RESEARCH_DEPTH']} "
              f"words={r['TOTAL_WORDS']} vast={r['vast_max']} yt={r['yt_live']}")

    # ---- A. aliases ----
    for alias, canonical in (("quick", "light"), ("standard", "medium"),
                             ("detailed", "hard"), ("deep", "deep")):
        r = dp.resolve(alias)
        check(f"A_alias_{alias}_is_{canonical}",
              r["profile"] == canonical
              and r == dp.resolve(canonical),
              f"resolved profile={r['profile']}")

    # ---- R. resolve validation ----
    expect_raise("R_unknown_profile_raises",
                 lambda: dp.resolve("ultra"),
                 "ValueError on unknown profile")
    expect_raise("R_unknown_override_raises",
                 lambda: dp.resolve("light", {"TOTAL_WORDS": 800,
                                              "BOGUS_KEY": 1}),
                 "ValueError on unknown override key")
    expect_raise("R_nonstring_profile_raises",
                 lambda: dp.resolve(None),
                 "ValueError on non-string profile")
    r = dp.resolve("light", {"TOTAL_WORDS": 800})
    check("R_override_applied", r["TOTAL_WORDS"] == 800
          and r["profile"] == "light", f"TOTAL_WORDS={r['TOTAL_WORDS']}")
    r = dp.resolve("medium", {"vast_max": 5})
    check("R_override_below_cap_kept", r["vast_max"] == 5,
          f"vast_max={r['vast_max']}")
    r = dp.resolve("light", {"vast_max": 99, "yt_live": 99})
    check("R_clamp_vast_max_12", r["vast_max"] == 12,
          f"vast_max={r['vast_max']} (contract: never >12)")
    check("R_clamp_yt_live_3", r["yt_live"] == 3,
          f"yt_live={r['yt_live']} (contract: never >3)")
    for profile in ("hard", "deep"):
        r = dp.resolve(profile)
        check(f"R_contract_{profile}",
              r["vast_max"] <= 12 and r["yt_live"] <= 3,
              f"vast_max={r['vast_max']} yt_live={r['yt_live']}")

    # ---- C. source counting ----
    import citation_audit as ca
    man = ca.build_manifest(FIX_DOCS)
    counts = dp.count_sources(
        discovered=[d["url"] for d in FIX_DOCS] + ["nota url",
                                                   "ftp://x.com/"],
        with_content=[{"url": d["url"]} for d in FIX_DOCS],
        used_in_analysis=[FIX_DOCS[0]],
        in_messages=FIX_MESSAGES,
        cited_report=FIX_REPORT,
        manifest=man)
    check("C_dedupe_chunks_once",
          counts["discovered"] == 4,
          f"discovered={counts['discovered']} (5 raw incl. #frag dupe "
          f"+ 2 malformed skipped -> 4 unique)")
    check("C_unique_union",
          counts["unique"] == 4,
          f"unique={counts['unique']}")
    check("C_with_content",
          counts["with_content"] == 4,
          f"with_content={counts['with_content']}")
    check("C_used_in_analysis",
          counts["used_in_analysis"] == 1,
          f"used_in_analysis={counts['used_in_analysis']}")
    check("C_in_messages",
          counts["in_messages"] == 2,
          f"in_messages={counts['in_messages']}")
    check("C_cited",
          counts["cited"] == 2,
          f"cited={counts['cited']}")
    check("C_by_channel",
          counts["by_channel"].get("youtube") == 1
          and counts["by_channel"].get("github") == 1
          and counts["by_channel"].get("web") == 2
          and sum(counts["by_channel"].values()) == counts["unique"],
          f"by_channel={counts['by_channel']}")
    # different query strings stay distinct
    check("C_query_variants_distinct",
          ca.normalize_url("https://example.com/guide?x=1")
          != ca.normalize_url("https://example.com/guide?x=2"),
          "query differences preserved by normalizer")

    # ---- S. stop reasons ----
    s = dp.decide_stop(aspects_covered=0.97, novelty_last_rounds=0.5,
                       gaps=[])
    check("S_coverage_stop",
          s == {"stop": True, "stop_reason": "coverage", "partial": False},
          f"{s}")
    s = dp.decide_stop(aspects_covered=0.7, novelty_last_rounds=0.05,
                       gaps=["q1"])
    check("S_novelty_stop",
          s["stop"] is True and s["stop_reason"] == "novelty"
          and s["partial"] is False,
          f"{s}")
    s = dp.decide_stop(aspects_covered=0.4, novelty_last_rounds=0.8,
                       budget={"time_used_s": 600, "time_budget_s": 600},
                       gaps=["q1", "q2"])
    check("S_budget_partial_with_gaps",
          s["stop"] is True and s["stop_reason"] == "budget"
          and s["partial"] is True,
          f"{s}")
    s = dp.decide_stop(aspects_covered=0.4, novelty_last_rounds=0.8,
                       budget={"tokens_used": 9000, "tokens_budget": 9000},
                       gaps=[])
    check("S_budget_clean_without_gaps",
          s["stop"] is True and s["stop_reason"] == "budget"
          and s["partial"] is False,
          f"{s}")
    s = dp.decide_stop(aspects_covered=0.3, novelty_last_rounds=0.9,
                       blocked=True, gaps=["q1"])
    check("S_blocked_partial_with_gaps",
          s["stop"] is True and s["stop_reason"] == "blocked"
          and s["partial"] is True,
          f"{s}")
    s = dp.decide_stop(aspects_covered=0.3, novelty_last_rounds=0.9,
                       gaps=["q1", "q2"])
    check("S_continue_when_gaps",
          s == {"stop": False, "stop_reason": "continue",
                "partial": False},
          f"{s}")
    # simple question ends early even in deep
    deep = dp.resolve("deep")
    s = dp.decide_stop(aspects_covered=0.98, novelty_last_rounds=0.02,
                       budget={"rounds_used": 1,
                               "rounds_budget": deep["MAX_ITERATIONS"]},
                       gaps=[])
    check("S_early_stop_simple_question_in_deep",
          s["stop"] is True and s["stop_reason"] == "coverage",
          f"deep still stops early: {s}")
    # larger profiles investigate more when gaps simulated
    light = dp.resolve("light")
    light_rounds = deep_rounds = 0
    for rnd in range(1, 7):
        kw = dict(aspects_covered=0.4, novelty_last_rounds=0.8,
                  gaps=["open-q"])
        sl = dp.decide_stop(budget={"rounds_used": rnd,
                                    "rounds_budget": light["MAX_ITERATIONS"]},
                            **kw)
        sd = dp.decide_stop(budget={"rounds_used": rnd,
                                    "rounds_budget": deep["MAX_ITERATIONS"]},
                            **kw)
        if not sl["stop"]:
            light_rounds = rnd
        if not sd["stop"]:
            deep_rounds = rnd
    check("S_deep_investigates_more_than_light",
          deep_rounds > light_rounds and light_rounds == 0
          and deep_rounds == 4,
          f"light kept going {light_rounds} rounds, "
          f"deep {deep_rounds} rounds (budgets 1 vs 5)")

    # ---- P. intermediate synthesis provenance ----
    carried = dp.carry_provenance([dict(s) for s in FIX_SECTIONS])
    check("P_count_preserved", len(carried) == 3,
          f"{len(carried)} sections carried")
    by_url = {s["url"]: s for s in carried}
    check("P_transcript_type",
          by_url["https://www.youtube.com/watch?v=abc123DEF45"]
          ["evidence_type"] == "transcript",
          "spoken labels -> transcript")
    check("P_description_type",
          by_url["https://github.com/owner/repo"]["evidence_type"]
          == "description",
          "description marker -> description")
    check("P_unknown_type",
          by_url["https://example.com/plain"]["evidence_type"]
          == "unknown",
          "no markers -> unknown")
    check("P_provenance_kept",
          all(s.get("provenance") for s in carried),
          "provenance fields preserved on every section")
    weird = dp.carry_provenance(
        [{"url": "nota url", "content": "[spoken 1/2]\ntext",
          "provenance": "x"}])
    check("P_never_drops_source_identity",
          len(weird) == 1 and weird[0]["url"] == "nota url"
          and weird[0]["evidence_type"] == "transcript",
          "malformed URL section still carried with best-effort type")

    # ---- W. apply_profile writes config + env (offline, temp copy) ----
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        cfg_path.write_text(json.dumps({
            "RETRIEVER": "custom,searx,duckduckgo,arxiv",
            "MAX_ITERATIONS": 3, "DEEP_RESEARCH_BREADTH": 3,
            "DEEP_RESEARCH_DEPTH": 2, "DEEP_RESEARCH_CONCURRENCY": 4,
            "TOTAL_WORDS": 1200, "SIMILARITY_THRESHOLD": 0.42,
        }), encoding="utf-8")
        res = dp.resolve("hard")
        dp.apply_profile(cfg_path, res)
        back = json.loads(cfg_path.read_text(encoding="utf-8"))
        import os as _os
        ok = (back["MAX_ITERATIONS"] == 3
              and back["DEEP_RESEARCH_BREADTH"] == 5
              and back["DEEP_RESEARCH_DEPTH"] == 3
              and back["TOTAL_WORDS"] == 2500
              and back["SIMILARITY_THRESHOLD"] == 0.42
              and back["RETRIEVER"] == "custom,searx,duckduckgo,arxiv"
              and _os.environ.get("VAST_DOCS_CAP") == "12"
              and _os.environ.get("VAST_YT_LIVE_CAP") == "3")
        check("W_apply_profile_config_env", ok,
              f"hard written: {back['MAX_ITERATIONS']}/"
              f"{back['DEEP_RESEARCH_BREADTH']}/"
              f"{back['DEEP_RESEARCH_DEPTH']}/{back['TOTAL_WORDS']} "
              f"+ untouched keys preserved")

    # ---- I. integration wiring (static: module runs sync at import) ----
    integ = (WORKDIR / "gpt_researcher_integration.py").read_text(
        encoding="utf-8")
    check("I_profile_after_sync",
          integ.index("sync_config.sync()")
          < integ.index("depth_profiles.apply_profile("),
          "apply_profile() runs after sync_config.sync()")
    check("I_resolve_call",
          "depth_profiles.resolve(" in integ,
          "profile resolved via depth_profiles.resolve()")
    check("I_aliases_accepted",
          all(a in integ for a in ("light", "medium", "hard"))
          and "PROFILE_ALIASES" not in ("",),
          "new depth names wired (aliases live in PROFILE_ALIASES)")
    check("I_depth_artifact",
          "_depth.json" in integ and "stop_reason" in integ,
          "<stem>_depth.json with stop_reason recorded per run")
    check("I_audit_hook",
          "run_provenance_audit(report" in integ,
          "run_provenance_audit() still called after write_report")
    check("I_evidence_prompt_intact",
          "EVIDENCE_PROMPT" in integ
          and "custom_prompt=EVIDENCE_PROMPT" in integ
          and "NOT verified video content" in integ
          and "never orders" in integ,
          "EVIDENCE_PROMPT defined and passed via custom_prompt=")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
