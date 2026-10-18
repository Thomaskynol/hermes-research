"""Run the 11 suites in separate offline processes and retain literal output."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-report", type=Path, default=root / "fixtures" / "RELATORIO_CORRIGIDO_184601.md")
    parser.add_argument("--frozen-evidence", type=Path, default=root / "fixtures" / "replay_corrigido_evidence.json")
    parser.add_argument("--output-dir", type=Path, default=root / "validation")
    args = parser.parse_args()
    for fixture in (args.frozen_report, args.frozen_evidence):
        if not fixture.is_file():
            parser.error(f"Required existing frozen fixture not found: {fixture}")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    suites = ["evidence_selection", "failure_guard", "coverage", "coverage_review",
              "coverage_structure", "scope_boundary", "corpus_qualification_review",
              "qualification_final_cases", "e2e_integration_review", "e2e_replay_regressions",
              "replay_closure"]
    child = '''
import builtins, json, os, runpy, sys
def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network forbidden during offline validation")
sys.addaudithook(offline)
mapping = json.loads(os.environ["OFFLINE_FIXTURE_MAP"])
real_open = builtins.open
def mapped_open(file, *args, **kwargs):
    return real_open(mapping.get(str(file), file), *args, **kwargs)
builtins.open = mapped_open
sys.path.insert(0, os.environ["OFFLINE_REPO"])
path = sys.argv[1]
sys.argv = [path]
runpy.run_path(path, run_name="__main__")
'''
    env = dict(os.environ)
    env.update({"OFFLINE_REPO": str(root),
                "SEMANTIC_REVIEW_PATH": str(root / "semantic_review.py"),
                "INTEGRATION_PATH": str(root / "gpt_researcher_integration.py"),
                "COVERAGE_REVIEW_REPORT": str(args.frozen_report.resolve()),
                "EVIDENCE_FIXTURE_PATH": str(args.frozen_evidence.resolve()),
                "QUALIFICATION_OBSERVATIONS_PATH": str(out / "qualification_payloads.json"),
                "OFFLINE_FIXTURE_MAP": json.dumps({
                    "/opt/data/deep_research_outputs/gpt_researcher/output/RELATORIO_CORRIGIDO_184601.md": str(args.frozen_report.resolve()),
                    "/opt/data/deep_research_outputs/gpt_researcher/runs/replay_corrigido_evidence.json": str(args.frozen_evidence.resolve())})})
    results = []
    for suffix in suites:
        path = root / "scripts" / f"test_semantic_{suffix}.py"
        command = [sys.executable, "-c", child, str(path)]
        started = time.monotonic()
        proc = subprocess.run(command, env=env, cwd=root, capture_output=True,
                              text=True, timeout=120)
        output = proc.stdout + proc.stderr
        (out / f"{path.stem}_output.txt").write_text(output)
        results.append({"suite": path.name, "command": command, "exit_code": proc.returncode,
                        "duration_s": round(time.monotonic() - started, 3),
                        "combined_stdout_stderr": output})
        print(f"{path.name}: exit={proc.returncode}", flush=True)
    (out / "execution_outputs_reviewed.json").write_text(json.dumps({
        "mode": "offline; transport prohibited; simulations only where tests explicitly patch it",
        "results": results}, ensure_ascii=False, indent=2))
    return int(any(r["exit_code"] != 0 for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
