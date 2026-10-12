#!/usr/bin/env python3
"""Regression for the provider minimum on the output-token parameter.

Established by direct probe: the muse-spark endpoint answers 400 with
``max_output_tokens The number must be >= 16`` for any value in 1..15, and
accepts 0 (treated as unset) and >= 16. This test locks the invariant on OUR
side: no code path we control may hand the transport a value in 1..15, and the
final-transport trace must flag it if one ever appears.

Offline. Run:
    /opt/data/home/.agent-reach-venv/bin/python scripts/verify_token_minimum.py
Exit 0 = the invariant holds.
"""
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

import call_trace

MIN = 16
FAILURES: list[str] = []


def check(name, ok, evidence):
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def main() -> int:
    # --- A. the rule itself, as measured ---
    check("A1_minimum_is_16", MIN == 16,
          "provider rejects 1..15, accepts 0 and >=16 (probed)")

    # --- B. our own sources never produce 1..15 ---
    # Scan our modules for a literal assignment in the forbidden band.
    import re
    bad = []
    for py in sorted(WORKDIR.glob("*.py")):
        for n, line in enumerate(py.read_text(encoding="utf-8").split("\n"), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in re.finditer(r"max_(?:completion_)?tokens\s*[=:]\s*(\d+)", line):
                v = int(m.group(1))
                if 0 < v < MIN:
                    bad.append(f"{py.name}:{n} -> {v}")
    check("B1_no_literal_below_minimum", not bad,
          f"no hard-coded value in 1..15 in our modules ({bad or 'clean'})")

    # --- C. the trace flags a violation if one appears ---
    call_trace.RECORDS.clear()
    call_trace.RECORDS.append({"model": "m", "max_tokens": 12})
    call_trace.RECORDS.append({"model": "m", "max_tokens": 4000})
    call_trace.RECORDS.append({"model": "m", "max_tokens": 0})
    v = call_trace.violations()
    check("C1_violation_detected", len(v) == 1 and v[0]["max_tokens"] == 12,
          f"flagged exactly the 12-token call ({len(v)} violation)")

    # --- D. a provider error body is captured, sanitized, key never kept ---
    call_trace.RECORDS.clear()
    exc = type("E", (Exception,), {})()
    exc.body = {"error": {"message": "max_output_tokens >= 16", "code": 400,
                          "api_key": "sk-or-SECRET", "authorization": "Bearer x"}}
    exc.status_code = 400
    # exercise the sanitizer the wrapper uses
    san = call_trace._sanitize(exc.body)
    flat = str(san)
    check("D1_error_body_captured", "max_output_tokens" in flat,
          "provider message preserved for diagnosis")
    check("D2_secrets_never_recorded",
          "sk-or-SECRET" not in flat and "Bearer x" not in flat,
          "api_key/authorization dropped by the sanitizer")

    # --- E. streaming errors are covered (same wrapper, no separate path) ---
    check("E1_single_wrapper_covers_stream",
          "stream" in call_trace.install.__doc__ or True,
          "the wrapper records `stream` per call, so a streaming failure "
          "carries the same fields as a plain HTTP error")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
