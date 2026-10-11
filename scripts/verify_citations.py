#!/usr/bin/env python3
"""Quality gate: citations + provenance of research reports.

No arguments. Offline, frozen fixtures, no model calls. Tests the CURRENT
code in scripts/citation_audit.py (positive + negative), then audits the
REAL replay artifacts (runs/replay_entry_20261011.md + transcript fixture).

Exit 0 = all pass. Exit 1 = any failure.
"""
import json
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR / "scripts"))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

import citation_audit as ca

FAILURES: list[str] = []


def check(name: str, ok: bool, evidence: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def codes(findings):
    return [f["code"] for f in findings]


def main() -> int:
    # ---- unit: normalizer ----
    check("U1_normalize_basic",
          ca.normalize_url("HTTPS://Example.COM:443/a?b=1#frag")
          == "https://example.com/a?b=1", "case/port/fragment handled")
    check("U2_preserve_path_query",
          ca.normalize_url("https://x.com/a?b=1") != ca.normalize_url("https://x.com/a?b=2"),
          "query differences preserved")
    check("U3_malformed_none",
          ca.normalize_url("nota url") is None
          and ca.normalize_url("ftp://x.com/") is None
          and ca.normalize_url("https://exa mple.com/") is None,
          "3 malformed inputs -> None")

    # ---- unit: extractor + classifier ----
    sample = ("See [the docs](https://opencode.ai/install) and run "
              "`npm i -g opencode-ai` from https://opencode.ai.\n"
              "Source: `https://www.youtube.com/watch?v=abc123DEF45`, [spoken 2/9]\n"
              "[1] https://example.com/ref\n")
    refs = ca.extract_references(sample)
    kinds = {(r["format"], ca.classify_reference(r)) for r in refs}
    check("U4_formats_covered",
          {"markdown", "bare", "source_marker", "numbered"}
          <= {r["format"] for r in refs},
          f"formats={[r['format'] for r in refs]}")
    check("U5_install_url_not_source",
          ("bare", "utility") in kinds or ("bare", "in_command") in kinds,
          "bare install URL not counted as evidence")
    check("U6_command_url_in_command",
          any(ca.classify_reference(r) == "in_command" for r in refs
              if "npm i" in r["snippet"]),
          "URL inside install command classified in_command")

    # ---- negatives: each error code must fire ----
    man = {"https://www.youtube.com/watch?v=abc123DEF45": {
        "url": "https://www.youtube.com/watch?v=abc123DEF45",
        "evidence_types": ["transcript"], "segments_total": 9,
        "segments_consistent": True, "content_chars": 5000,
        "content_bearing": True, "provenance": "t"}}
    f = ca.validate("Source: `https://www.youtube.com/watch?v=zzz999ZZZ99`, [spoken 1/9]\n", man)
    check("N1_unknown_source", "SOURCE_NOT_IN_MANIFEST" in codes(f), "fired")
    f = ca.validate("Source: `https://www.youtube.com/watch?v=abc123DEF45`, [spoken 1/7]\n", man)
    check("N2_wrong_segment_total", "WRONG_URL_ATTRIBUTION" in codes(f), "fired")
    man_desc = {"https://site.com/p": {
        "url": "https://site.com/p", "evidence_types": ["description"],
        "segments_total": None, "segments_consistent": True,
        "content_chars": 300, "content_bearing": True, "provenance": "t"}}
    f = ca.validate("Source: `https://site.com/p`, [spoken 1/3]\n", man_desc)
    check("N3_description_as_speech", "TYPE_MISMATCH" in codes(f), "fired")
    f = ca.validate("see (https://broken url/) here\n", man)
    check("N4_malformed", "MALFORMED" in codes(f) or not ca.extract_references(
        "see (https://broken url/) here\n"), "malformed or unextracted")
    man_empty = {"https://x.com/e": {
        "url": "https://x.com/e", "evidence_types": ["unknown"],
        "segments_total": None, "segments_consistent": True,
        "content_chars": 0, "content_bearing": False, "provenance": "discovered"}}
    f = ca.validate("Source: `https://x.com/e`\n", man_empty)
    check("N5_discovered_only", "DISCOVERED_ONLY" in codes(f), "fired")
    f = ca.validate_messages(man, "unrelated text without the source")
    check("N6_absent_from_messages", "EVIDENCE_ABSENT_FROM_MESSAGES" in codes(f),
          "fired")

    # ---- positive: valid evidence passes clean ----
    f = ca.validate(
        "Source: `https://www.youtube.com/watch?v=abc123DEF45`, [spoken 2/9]\n", man)
    check("P1_valid_evidence_clean", f == [], f"findings={f}")
    f = ca.validate_messages(
        man, "Source: https://www.youtube.com/watch?v=abc123DEF45\n[spoken 2/9]\n")
    check("P2_messages_trace_clean", f == [], f"findings={f}")

    # ---- integration: real replay artifacts, read-only ----
    fx = json.loads((WORKDIR / "fixtures" / "transcript_replay.json")
                     .read_text(encoding="utf-8"))
    real_man = ca.build_manifest(fx["docs"])
    rep = (WORKDIR / "runs" / "replay_entry_20261011.md").read_text(encoding="utf-8")
    refs = ca.extract_references(rep)
    check("R1_real_report_refs", len(refs) >= 30,
          f"{len(refs)} references extracted")
    findings = ca.validate(rep, real_man)
    bad = [f for f in findings if f["code"] in (
        "MALFORMED", "SOURCE_NOT_IN_MANIFEST", "TYPE_MISMATCH",
        "WRONG_URL_ATTRIBUTION")]
    check("R2_real_report_no_hard_errors", not bad,
          f"hard_errors={[(b['code'], b['reference'].get('url')) for b in bad]}")
    soft = [f for f in findings if f["code"] not in (
        "MALFORMED", "SOURCE_NOT_IN_MANIFEST", "TYPE_MISMATCH",
        "WRONG_URL_ATTRIBUTION")]
    print(f"INFO real_report_soft_findings: {[(s['code']) for s in soft]}")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
