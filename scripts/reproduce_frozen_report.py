#!/usr/bin/env python3
"""Reassess and regenerate a frozen corpus without any new collection.

This is a new, bounded reproduction, not resume of the original research.
Only the generator may be live; source transports and embeddings are blocked.
The public entry is covered separately by test_accept43_reconciliation.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import adaptive_coordinator as ac
import adaptive_state as sa
import coverage_ledger as cl
import model_transport
import report_renderer as rr
import run_budget
import run_manifest
import verification_report as vr


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--model", help="OpenCode generator; omission renders historical synthesis only")
    p.add_argument("--assessment-calls", type=int, default=2, choices=range(0, 4))
    p.add_argument("--observed-version", default="", help="Output already obtained from a local command")
    p.add_argument("--assessment-replay-from", type=Path,
                   help="Reuse recorded assessor answers only when current prompts match byte for byte")
    args = p.parse_args()
    source, out = args.source_dir.resolve(), args.output_dir.resolve()
    if source == out or source in out.parents or out.exists():
        p.error("Use a new output directory outside the original run")
    out.mkdir(parents=True)
    original_hashes = hashes(source)
    save(out / "original-hashes.json", original_hashes)
    original = json.loads((source / "state.json").read_text())
    save(out / "original-audit.json", original["semantic"])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    before = run_manifest.module_hashes()
    started = time.monotonic()
    resolved = ac.resolve_adaptive("medium", {"max_model_calls": 18})
    st = sa.new_state(original["question"], run_id=out.name, profile="medium", config=resolved)
    for key in ("plan", "plan_versions", "evidence", "qualification", "evaluations", "discovery", "substitutions"):
        st[key] = copy.deepcopy(original.get(key, st.get(key)))
    # Inherited evaluations are historical inputs, never new analysis.
    # Keep their provenance; only the current calls add assessment records.
    st["reproduction"] = {"source_dir": str(source), "source_run_id": original["run_id"],
        "code_head": head, "inherited_evaluations": len(st["evaluations"]),
        "original_consumption": original["consumption"],
        "description": "material do accept43; nenhuma nova busca/coleta; "
                       + ("avaliação, escrita e votos com gerador real." if args.model else "síntese histórica reprocessada, sem gerador real.")}
    st["user_context"] = copy.deepcopy(original.get("user_context", {}))
    st["user_context"]["origin"] = "harness"
    if args.observed_version:
        st["environment_observations"] = [{"command": "opencode --version", "value": args.observed_version,
                                          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}]
    # Requalify each obtained source against its original global query;
    # preserve raw documents and reasons, do not edit the frozen corpus.
    excluded = []
    for seg in original.get("segments", []):
        op = next((o for o in original["pending_ops"] if o.get("op_id") == seg.get("op_id")), {})
        crit = next((c for c in st["plan"]["criteria"] if c["id"] == op.get("criterion_id")), {})
        u = seg.get("url")
        if op.get("kind") != "gap_query" or op.get("entity_id") or not crit or crit.get("applies_to") or u not in st["evidence"]:
            continue
        body, _ = ac._substantive_body(st["evidence"][u])
        if ac._hit_gated_by_snippet(st, op, {"url": u, "snippet": body}):
            st["qualification"][u].update(excluded=True, status="irrelevant", reason="reprodução: assunto da pergunta ausente")
            excluded.append(u)
    save(out / "requalification.json", excluded)
    # Fresh counters measure this reproduction; original counters remain
    # in original state/technical diagnosis, not presented as new work.
    for u, body in st["evidence"].items():
        if not u.startswith("user://"):
            ac._counters.record_obtained(st, u, body, st["qualification"].get(u))
            ac._counters.record_usable(st, u, st["qualification"].get(u))
    led = cl.Ledger(st["plan"], run_id=st["run_id"])
    led.set_corpus(st["evidence"], st["qualification"])
    for ev in st["evaluations"]:
        led.evaluate(ev["criterion_id"], ev["state"], ev["justification"], ev.get("origin", ""), ev.get("references", []), ev.get("entity_id"))
    # Selection decisions consume historical assessments, not fake rounds.
    st["rounds"] = copy.deepcopy(original["rounds"])
    ac._maybe_substitute(st, led)
    st["rounds"] = []
    os.environ["HERMES_NATIVE_EMBEDDINGS"] = "0"
    # Prevent source/embedding access in this process. The separate CLI
    # generator is allowed only in --model mode, with tools denied.
    def offline(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            raise RuntimeError("frozen reproduction forbids source network and embeddings")
    sys.addaudithook(offline)
    client = None
    if args.model:
        os.environ["OPENCODE_CONFIG_CONTENT"] = json.dumps({"permission": {"*": "deny"}, "plugin": []})
        transport = model_transport.opencode_client(model=args.model, retries=0, max_calls=18)
        calls = []
        generator_lock = threading.Lock()
        replay_index = 0
        def client(prompt):
            nonlocal replay_index
            # The CLI is a shared host integration. This harness serializes
            # generator requests, keeping all three votes and their batches;
            # it does not assert provider support for concurrent CLI calls.
            with generator_lock:
                index = len(calls) + 1
                (out / f"model-{index:02d}-prompt.txt").write_text(prompt)
                tick = time.monotonic()
                mode = "live"
                try:
                    if args.assessment_replay_from and prompt.startswith("Você avalia evidências"):
                        replay_index += 1
                        prior = args.assessment_replay_from / f"model-{replay_index:02d}-prompt.txt"
                        if prior.read_text() != prompt:
                            raise ValueError("assessor replay prompt differs; cannot attribute same response to changed input")
                        answer = prior.with_name(f"model-{replay_index:02d}-answer.txt").read_text()
                        mode = "assessor_replay_exact_prompt"
                    else:
                        answer = transport(prompt)
                except Exception as exc:
                    calls.append({"index": index, "mode": mode, "outcome": "failed", "error": str(exc)[:300]})
                    save(out / "model-calls.json", calls)
                    raise
                (out / f"model-{index:02d}-answer.txt").write_text(answer)
                calls.append({"index": index, "mode": mode, "outcome": "returned", "seconds": round(time.monotonic()-tick, 3)})
                save(out / "model-calls.json", calls)
                print(f"model call {index}: {mode} returned ({calls[-1]['seconds']}s)", flush=True)
                return answer
        assessor = ac.make_model_assessor(client)
        for n in range(args.assessment_calls):
            _, block = ac._assess_round(st, assessor, led, resolved)
            st["rounds"].append({"round": n, "kind": "frozen_reassessment", "ops": [], "coverage": block.get("proportion")})
            sa.save(out, st)
        writer = ac.make_model_writer(client)
        review = ac.make_review_fn(client)
        audit = lambda r, e: ac._default_auditor(r, e, review_fn=review, generic=True)
    else:
        writer = lambda view: (original["report"]["text"], original["report"]["selection"])
        audit = lambda r, e: {"enabled": False, "accepted": False,
                              "verdict_state": "não revisado semanticamente",
                              "note": "historical audit not reused as approval of changed text"}
    st["stop"] = {"reason": "frozen_reproduction", "partial": True,
                  "detail": "reprodução delimitada do corpus; sem nova coleta"}
    budget = run_budget.Budget(resolved["budget"], profile="medium")
    result = ac._finalize(st, resolved, budget, led.compute(), writer, audit, started, time.monotonic, out)
    save(out / "result.json", result)
    save(out / "reproduction.json", {**st["reproduction"], "module_hashes": before,
        "module_hashes_unchanged": before == run_manifest.module_hashes(),
        "original_unchanged": original_hashes == hashes(source),
        "python": sys.version, "generator": args.model, "source_network": False, "embeddings": "disabled",
        "actual_generator_calls": transport.calls if args.model else 0,
        "assessor_replay_from": str(args.assessment_replay_from) if args.assessment_replay_from else None,
        "generator_concurrency": 1,
        "tokens": "unknown", "cost_usd": "unknown"})
    # Version/hash the actual delivered text after render and verification.
    assert before == run_manifest.module_hashes(), "Product changed during reproduction"
    assert original_hashes == hashes(source), "Original run changed"
    print(json.dumps({"report": result.get("report_path"), "verification": result["verification"].get("overall"),
                      "selection": [e["label"] for e in rr._required_entities(st)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
