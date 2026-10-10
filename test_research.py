#!/usr/bin/env python3
"""Test GPT Researcher at different depth levels."""
import asyncio
import sys
import os
import json
from pathlib import Path

# Ensure venv is active
sys.path.insert(0, "/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages")

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import ReportType, Tone

CONFIG_PATH = "/opt/data/deep_research_outputs/gpt_researcher/config.json"
OUTPUT_DIR = "/opt/data/deep_research_outputs/gpt_researcher/tests"

# Create output dir
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

REPORT_TYPES = {
    "quick": "quick",           # Fast test (~2 min)
    "standard": "research_report",  # Standard report (~5 min)
    "detailed": "detailed_report",  # Detailed report (~5-10 min)
    "deep": "deep",             # Deep research (~5-10 min)
}

async def run_test(depth_name, report_type):
    query = "What are the main trends in AI agents in 2026?"
    output_file = Path(OUTPUT_DIR) / f"{depth_name}_report.md"
    
    print(f"\n{'='*60}")
    print(f"TESTING: {depth_name} ({report_type})")
    print(f"Query: {query}")
    print(f"Output: {output_file}")
    print(f"{'='*60}")
    
    try:
        researcher = GPTResearcher(
            query=query,
            report_type=report_type,
            config_path=CONFIG_PATH,
            report_format="markdown",
            tone=Tone.Objective,
            verbose=True,
        )
        
        print("[TEST] Starting research...")
        await researcher.conduct_research()
        print("[TEST] Research complete, writing report...")
        
        report = await researcher.write_report()
        
        # Save report
        output_file.write_text(report)
        
        word_count = len(report.split())
        print(f"\n[SUCCESS] {depth_name} completed!")
        print(f"  Words: {word_count}")
        print(f"  File: {output_file}")
        return True
        
    except Exception as e:
        print(f"\n[FAILURE] {depth_name} failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    # Always start with quick (fastest, validates everything work)
    depths_to_test = [("quick", "quick")]
    
    # If quick succeeds, also try standard
    # If standard succeeds, also try detailed
    # If detailed succeeds, also try deep
    # This is the incremental approach
    
    results = {}
    for depth_name, report_type in depths_to_test:
        success = await run_test(depth_name, report_type)
        results[depth_name] = success
        if not success:
            print(f"\nStopping tests due to failure in {depth_name}")
            break
    
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    for depth, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {depth}: {status}")

if __name__ == "__main__":
    asyncio.run(main())
