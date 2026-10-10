#!/usr/bin/env python3
"""Hermes GPT Researcher Integration Script.

Usage:
    python3 gpt_researcher_integration.py "your research query" [depth]

Depth options: quick, standard, detailed, deep
Example:
    python3 gpt_researcher_integration.py "AI trends in 2026" detailed
"""
import asyncio
import sys
import os
from pathlib import Path

# Load API keys from .env (maps OPENROUTER_API_KEY → OPENAI_API_KEY)
ENV_FILE = Path("/opt/data/.env")
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not value or value == "sk-or-...ebe2":
            continue
        os.environ[key] = value

# Sync config — reads model/base_url from Hermes config.yaml,
# sets OPENAI_BASE_URL + SMART_LLM/FAST_LLM + EMBEDDING for local vs remote
sys.path.insert(0, "/opt/data/deep_research_outputs/gpt_researcher")
import sync_config
import retriever_timeout  # noqa: F401  rebinds gpt_researcher.retrievers.CustomRetriever
import reasoning_effort  # noqa: F401  opens the reasoning_effort allow-list, via install()
import run_trace
sync_config.sync()
# Before GPTResearcher builds a Config: install() exports REASONING_EFFORT, which
# Config reads in its constructor. After sync_config.sync(), which sets SMART_LLM.
reasoning_effort.install()

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import Tone

DEPTH_MAP = {
    "quick": "quick",
    "standard": "research_report",
    "detailed": "detailed_report",
    "deep": "deep",
}
OUTPUT_DIR = Path("/opt/data/deep_research_outputs/gpt_researcher/output")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gpt_researcher_integration.py \"query\" [depth]")
        print("Depth: quick (default), standard, detailed, deep")
        return
    
    query = sys.argv[1]
    depth = sys.argv[2] if len(sys.argv) > 2 else "quick"
    report_type = DEPTH_MAP.get(depth, "quick")
    
    print(f"[GPT RESEARCHER] Query: {query}")
    print(f"[GPT RESEARCHER] Depth: {depth} ({report_type})")
    print(f"[GPT RESEARCHER] Model: {os.environ.get('SMART_LLM', 'N/A')}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_query = query.replace(" ", "_")[:50]
    output_file = OUTPUT_DIR / f"{depth}_{safe_query}_report.md"
    
    researcher = GPTResearcher(
        query=query,
        report_type=report_type,
        config_path="/opt/data/deep_research_outputs/gpt_researcher/config.json",
        report_format="markdown",
        tone=Tone.Objective,
        verbose=True,
    )

    # Opt-in tracing (RUN_TRACE_DIR set): same artifacts as run_research.py.
    # Unset = byte-identical behavior to before.
    tracer = None
    uninstall_probes = None
    trace_root = os.environ.get(run_trace.RUNS_ENV, "")
    if trace_root:
        tracer = run_trace.RunTracer(query, report_type, trace_root)
        uninstall_probes = run_trace.install_probe_wrapping(tracer)

    await researcher.conduct_research()
    report = await researcher.write_report()
    output_file.write_text(report)

    if tracer is not None:
        costs = run_trace.record_library_state(tracer, researcher)
        tracer.record("report.md", report)
        tracer.record("stats.json", {
            "query": query, "depth": depth, "report_type": report_type,
            "report_file": str(output_file),
            "total_urls": len(researcher.get_source_urls()),
            "token_usage": costs,
            "not_instrumented": {
                "chunk_selection": "EmbeddingsFilter in site-packages "
                                   "(context/compression.py:135)",
                "context_cut": "max_results cut in site-packages "
                               "(skills/context_manager.py:63)",
                "generation_context": "prompt assembly inside "
                                      "skills/researcher.py not captured",
                "non_custom_retrievers": "searx/duckduckgo/arxiv run inside "
                                         "the library",
            },
        })
        if uninstall_probes is not None:
            uninstall_probes()  # flushes retrievers.json
    
    word_count = len(report.split())
    print(f"\n[SUCCESS] Report saved: {output_file}")
    print(f"[SUCCESS] Words: {word_count}")

if __name__ == "__main__":
    asyncio.run(main())
