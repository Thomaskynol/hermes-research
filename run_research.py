#!/usr/bin/env python3
"""Single-process research runner.

    python run_research.py "the query"
    python run_research.py "the query" --report-type research_report
    python run_research.py "the query" --json

sync_config is imported and called in-process (never shelled out to), so the env
vars it sets are the ones this process -- and the research -- sees.
"""
import argparse
import asyncio
import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path

import sync_config
import retriever_timeout  # noqa: F401  rebinds gpt_researcher.retrievers.CustomRetriever
import reasoning_effort  # noqa: F401  opens the reasoning_effort allow-list, via install()
import run_trace
from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import ReportType, Tone

CONFIG_PATH = "/opt/data/deep_research_outputs/gpt_researcher/config.json"
OUTPUT_DIR = Path("/opt/data/deep_research_outputs/gpt_researcher/output")
CITATION = re.compile(r"\[[^\]]+\]\(https?://[^)]+\)")


def report_path(query, report_type):
    """Name reports like the ones already in output/: <type>_<query>_report.md."""
    slug = query[:50].strip().replace(" ", "_")
    return OUTPUT_DIR / f"{report_type}_{slug}_report.md"


async def research(query, report_type, tracer=None):
    """Run the research, return the numbers that say what happened."""
    # Before GPTResearcher builds a Config: install() exports REASONING_EFFORT,
    # which Config reads in its constructor. Idempotent, and placed here rather
    # than in main() so every path into research() gets it.
    reasoning_effort.install()
    uninstall_probes = None
    if tracer is not None:
        uninstall_probes = run_trace.install_probe_wrapping(tracer)
    researcher = GPTResearcher(
        query=query,
        report_type=report_type,
        config_path=CONFIG_PATH,
        report_format="markdown",
        tone=Tone.Objective,
        verbose=True,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    # write_report() only returns the text; nothing persists it, so the report
    # was being discarded once the process exited. Same shape as test_research.py.
    out = report_path(query, report_type)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(f"[RUN] report written: {out}", file=sys.stderr)
    context = researcher.get_research_context()
    if tracer is not None:
        # The accessible integration seam: what the library exposes back.
        # Stages inside site-packages (EmbeddingsFilter k=20/threshold,
        # max_results cut, generation context) are NOT captured here.
        tracer.record("context.json", {
            "source_urls": researcher.get_source_urls(),
            "context_items": [
                {"chars": len(str(c)), "text": str(c)} for c in context
            ],
        })
        tracer.record("report.md", report)
        if uninstall_probes is not None:
            uninstall_probes()  # flushes retrievers.json
    return {
        "total_urls": len(researcher.get_source_urls()),
        "scraped_data_success": sum(1 for c in context if str(c).strip()),
        "scraped_data_total": len(context),
        "total_words": len(report.split()),
        "citations": len(CITATION.findall(report)),
        "research_gaps": list(getattr(researcher, "research_gaps", None) or []),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query")
    ap.add_argument("--report-type", default=ReportType.ResearchReport.value)
    ap.add_argument(
        "--json", dest="as_json", action="store_true",
        help="numbers as JSON on stdout, all human output on stderr",
    )
    args = ap.parse_args()

    # --json owns stdout: sync_config and the library both print to it.
    quiet_stdout = (
        contextlib.redirect_stdout(sys.stderr) if args.as_json
        else contextlib.nullcontext()
    )
    with quiet_stdout:
        sync_config.sync()

        model = os.environ["SMART_LLM"]
        paid = model.startswith("openrouter:") or not sync_config._is_local_url(
            os.environ.get("OPENAI_BASE_URL", "")
        )
        print(f"[RUN] model: {model}", file=sys.stderr)
        print(
            "[RUN] cost: PAID (remote model)" if paid else "[RUN] cost: $0 (local)",
            file=sys.stderr,
        )
        sys.stderr.flush()

        start = time.monotonic()
        tracer = None
        trace_root = os.environ.get(run_trace.RUNS_ENV, "")
        if trace_root:
            tracer = run_trace.RunTracer(args.query, args.report_type, trace_root)
        stats = asyncio.run(research(args.query, args.report_type, tracer))
        stats["elapsed_seconds"] = round(time.monotonic() - start, 1)

    stats["model"] = model
    stats["query"] = args.query
    stats["report_type"] = args.report_type
    stats["report_file"] = str(report_path(args.query, args.report_type))
    found = stats["total_urls"] > 0 and stats["scraped_data_success"] > 0
    stats["status"] = "ok" if found else "NO SOURCES"
    if tracer is not None:
        stats["token_usage"] = "not_exposed"
        stats["not_instrumented"] = {
            "chunk_selection": "EmbeddingsFilter in site-packages "
                               "(context/compression.py:135, k defaults to 20 "
                               "from langchain_classic, threshold 0.42)",
            "context_cut": "max_results cut in site-packages "
                           "(skills/context_manager.py:63)",
            "generation_context": "assembled inside write_report(); "
                                  "only the returned text is observable",
            "non_custom_retrievers": "searx/duckduckgo/arxiv run inside the "
                                     "library; only the vast side is wrapped",
        }
        tracer.record("stats.json", stats)

    if args.as_json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"[DONE] {stats['elapsed_seconds']}s  status={stats['status']}")
        print(
            f"[DONE] total_urls={stats['total_urls']}"
            f"  scraped_data_success={stats['scraped_data_success']}"
            f"/{stats['scraped_data_total']}"
            f"  total_words={stats['total_words']}"
            f"  citations={stats['citations']}"
        )
        if stats["research_gaps"]:
            print(f"[DONE] research_gaps={stats['research_gaps']}")
        if not found:
            print("[DONE] NO SOURCES: no source was retrieved. "
                  "The report is not evidence of anything.")
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
