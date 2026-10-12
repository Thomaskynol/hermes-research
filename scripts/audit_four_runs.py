#!/usr/bin/env python3
"""Consolidated audit of the four depth runs, from the artifacts on disk.

Read-only. Produces runs/audit_four_runs.json with, per profile: effective
config, stop reason, budget consumption + source, word count, video usage,
manifest size, cost by step (or "unknown"), and an explicit coverage verdict.
Run:
    /opt/data/home/.agent-reach-venv/bin/python scripts/audit_four_runs.py
"""
import json
import re
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
OUT = WORKDIR / "runs" / "audit_four_runs.json"
STEM = "melhores_plugins_pro_opencode,_como_instalar_cada__report"


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def audit(profile: str) -> dict:
    base = WORKDIR / "output" / f"{profile}_{STEM}"
    md_path = base.with_suffix(".md")
    depth = load(base.parent / (base.name + "_depth.json"), {}) or {}
    audit_j = load(base.parent / (base.name + "_audit.json"), {}) or {}
    md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    videos = sorted(set(re.findall(r"watch\?v=([\w-]{11})", md)))
    # Identify the run that OWNS the report on disk. depth.json names the LAST
    # run, which may be a truncated one whose report is a failure notice; the
    # report actually delivered can come from an earlier run. Match by content
    # so every number below belongs to the same run as the report.
    owner_rid = depth.get("run_id")
    if md:
        for cand in sorted((WORKDIR / "runs").iterdir(), reverse=True):
            rm = cand / "report.md"
            if rm.exists() and rm.read_text(encoding="utf-8").strip() == md.strip():
                owner_rid = cand.name
                break
    rid0 = owner_rid
    run_man = None
    if rid0:
        cand = WORKDIR / "runs" / rid0 / "citation_manifest.json"
        run_man = load(cand)
        if run_man is None:
            # Rebuild from that run's own context.json (Source markers).
            ctx = WORKDIR / "runs" / rid0 / "context.json"
            if ctx.exists():
                urls = sorted({u.strip("`") for u in
                               re.findall(r"Source:\s*(\S+)", ctx.read_text(
                                   encoding="utf-8"))})
                run_man = {"manifest_urls": urls}
    manifest_n = (len(run_man["manifest_urls"]) if run_man
                  else len(audit_j.get("manifest_urls", [])))
    rec = {
        "profile": profile,
        "report_present": bool(md),
        "words": len(md.split()),
        "stop_reason": depth.get("stop_reason"),
        "partial": depth.get("partial"),
        "run_id": depth.get("run_id"),
        "effective_config": depth.get("resolved"),
        "budget_used": (depth.get("budget") or {}).get("used"),
        "budget_source": (depth.get("budget") or {}).get("consumption_source"),
        "manifest_urls": manifest_n,
        "report_findings": len(audit_j.get("report_findings", [])),
        "spoken_labels": len(re.findall(r"\[spoken \d+/\d+\]", md)),
        "videos_cited": videos,
        "videos_cited_n": len(videos),
    }
    # Cost: prefer the per-run stats.json of the run that OWNS the report.
    rid = rid0
    cost = "unknown (no stats.json for this run)"
    if rid:
        st = load(WORKDIR / "runs" / rid / "stats.json", {}) or {}
        tu = st.get("token_usage") or {}
        if tu:
            cost = {"total_usd": round(tu.get("total", 0), 4),
                    "by_step": {k: round(v, 4)
                                for k, v in (tu.get("steps") or {}).items()},
                    "note": ("report_writing only = planning/research not "
                             "attributed by the library on this path"
                             if set(tu.get("steps") or {}) == {"report_writing"}
                             else "all three steps attributed")}
    rec["cost"] = cost
    rec["report_owner_run"] = rid0
    # Artifact provenance: depth.json is written by the LAST run; when that run
    # truncated, the report on disk belongs to an earlier one. Say so instead of
    # silently mixing two runs' numbers.
    rec["artifacts_consistent"] = True
    if depth.get("run_id") and rid0 and depth.get("run_id") != rid0:
        rec["artifacts_consistent"] = False
        rec["artifact_note"] = (
            f"depth.json names run {depth['run_id']} (a truncated run) but the "
            f"report on disk matches run {rid0}; numbers here come from {rid0}, "
            f"the run that produced the delivered report")
    # Honest coverage verdict (mechanical + video aspect).
    if not md:
        rec["coverage_verdict"] = "FAILED: no report produced"
    elif rec["words"] < 100:
        rec["coverage_verdict"] = "PARTIAL: report is a failure notice, not an answer"
    elif rec["videos_cited_n"] == 0:
        rec["coverage_verdict"] = ("PARTIAL: answered, but the video aspect of "
                                   "the request is not represented in the report")
    else:
        rec["coverage_verdict"] = "OK: answer produced, video aspect represented"
    return rec


def deep_run_history() -> list[dict]:
    """Every deep run that produced a report, newest first.

    A profile can be run several times; the delivered report is one of them and
    the rest are still evidence. Listing them keeps the audit from implying a
    single deep run exists when there were several.
    """
    hist = []
    for cand in sorted((WORKDIR / "runs").iterdir(), reverse=True):
        run = cand / "run.json"
        rep = cand / "report.md"
        if not (run.exists() and rep.exists()):
            continue
        meta = load(run, {}) or {}
        if meta.get("depth") != "deep":
            continue
        md = rep.read_text(encoding="utf-8")
        st = load(cand / "stats.json", {}) or {}
        tu = st.get("token_usage") or {}
        hist.append({
            "run_id": cand.name,
            "words": len(md.split()),
            "videos_cited": len(set(re.findall(r"watch\?v=([\w-]{11})", md))),
            "spoken_labels": len(re.findall(r"\[spoken \d+/\d+\]", md)),
            "total_urls": st.get("total_urls"),
            "cost_usd": round(tu.get("total", 0), 4) if tu else "unknown",
            "model": (meta.get("config_sanitized") or {}).get("SMART_LLM"),
        })
    return hist


def main() -> int:
    out = {"runs": [audit(p) for p in ("light", "medium", "hard", "deep")],
           "deep_run_history": deep_run_history(),
           "legend": {
               "stop_reason": "condition actually reached (exit 0 != coverage)",
               "cost": "per-run when the library attributes it; 'unknown' otherwise",
               "budget_source": "vast:/budget = real consumption read from the "
                                "service that spends",
           }}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    for r in out["runs"]:
        print(f"{r['profile']:>6}: words={r['words']:>5} stop={r['stop_reason']} "
              f"videos={r['videos_cited_n']} manifest={r['manifest_urls']} "
              f"cost={r['cost'] if isinstance(r['cost'], str) else r['cost']['total_usd']}")
        print(f"        verdict: {r['coverage_verdict']}")
    print(f"\ndeep runs that produced a report: {len(out['deep_run_history'])}")
    for h in out["deep_run_history"]:
        print(f"  {h['run_id'][:24]}: {h['words']}w videos={h['videos_cited']} "
              f"spoken={h['spoken_labels']} ${h['cost_usd']}")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
