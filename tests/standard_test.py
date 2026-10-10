#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, "/opt/data/deep_research_outputs/gpt_researcher")
import sync_config
sync_config.sync()

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import Tone, ReportType
from pathlib import Path

async def main():
    print("[TEST] Starting STANDARD research test...")
    
    researcher = GPTResearcher(
        query="What are the main trends in AI agents in 2026?",
        report_type="research_report",  # standard
        config_path="/opt/data/deep_research_outputs/gpt_researcher/config.json",
        report_format="markdown",
        tone=Tone.Objective,
        verbose=True,
    )
    
    print("[TEST] Conducting research...")
    await researcher.conduct_research()
    print("[TEST] Research done, writing report...")
    report = await researcher.write_report()
    word_count = len(report.split())
    print(f"\n[SUCCESS] Standard report generated! Words: {word_count}")
    
    Path("/opt/data/deep_research_outputs/gpt_researcher/tests").mkdir(parents=True, exist_ok=True)
    Path("/opt/data/deep_research_outputs/gpt_researcher/tests/standard_report.md").write_text(report)
    print("[TEST] Report saved")

if __name__ == "__main__":
    asyncio.run(main())
