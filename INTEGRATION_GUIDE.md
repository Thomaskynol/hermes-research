# Hermes + GPT Researcher Integration Guide

**Date**: 2026-09-12  
**Status**: INSTALLED, INTEGRATION IN PROGRESS  
**Approach**: Python API direct import (not MCP server — GPT Researcher v0.16.0 has no dedicated MCP binary)

---

## Installation Steps Completed

### 1. Environment
- **Python**: 3.13.5 (system), venv: `/opt/data/home/.agent-reach-venv`
- **pip**: available in venv
- GPT Researcher installed via: `pip install gpt-researcher` (v0.16.0)

### 2. Dependencies Installed (automatic with pip)
- gpt-researcher 0.16.0
- langchain 1.3.18 (required by gpt-researcher — KEEP)
- langgraph, langgraph-checkpoint, langgraph-sdk
- langchain-openrouter 0.2.8
- ollama 0.6.2 (for local LLM)
- duckduckgo-search (for DDG search)
- pydantic, langchain-core, langchain-ollama
- mcp package (included)
- 200+ transitive dependencies
- Note: This updated openai from 3.6.0 → 2.54.0, sse-starlette from 2.1.3 → 3.4.11 (langgraph-api has minor incompatibility but functional)

### 3. Bug Fixed
- `NameError: name 'Any' is not defined` in `gpt_researcher/actions/query_processing.py`
  - **Fix**: Added `from typing import Any, List` at top of file
  - **File**: `/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages/gpt_researcher/actions/query_processing.py`
  - **Note**: This is a packaging bug in v0.16.0 (import was not included)

### 4. Config File Format
- GPT Researcher uses **JSON** config (NOT YAML)
- Config path passed via `config_path` parameter to GPTResearcher constructor
- Key settings: RETRIEVER, EMBEDDING, SMART_LLM, FAST_LLM, DEEP_RESEARCH_DEPTH, etc.

### 5. Integration Method
- **No dedicated MCP server binary** in v0.16.0
- Integration via Python API: `from gpt_researcher import GPTResearcher`
- Hermes can call GPT Researcher as a Python module via:
  - MCP server that wraps the Python API
  - Direct Python script that Hermes calls via terminal
  - Custom integration layer

---

## Integration Options for Hermes

### Option A: Python Script Wrapper (RECOMMENDED)
Create a Hermes-accessible script that uses GPT Researcher API:
```python
#!/usr/bin/env python3
import asyncio
import sys
import os
from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import ReportType, Tone

async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "default research query"
    depth = sys.argv[2] if len(sys.argv) > 2 else "standard"  # standard, detailed, deep, quick
    
    config_path = "/opt/data/deep_research_outputs/gpt_researcher/config.json"
    
    researcher = GPTResearcher(
        query=query,
        report_type=depth,  # standard, detailed, deep, quick
        config_path=config_path,
        report_format="markdown",
        tone=Tone.Objective,
    )
    await researcher.conduct_research()
    report = await researcher.write_report()
    print(report)

if __name__ == "__main__":
    asyncio.run(main())
```

### Option B: MCP Server Wrapping GPT Researcher API
Create a simple MCP server that uses GPT Researcher internally:
```python
# Hermes can call MCP tools that wrap GPT Researcher API calls
# Similar to how hermes_deep_research_bridge.py worked for ODR
```

### Option C: Direct Import in Hermes Conversations
Use `execute_code` tool to import GPT Researcher directly:
```python
from gpt_researcher import GPTResearcher
import asyncio
researcher = GPTResearcher(query="...", config_path="...")
await researcher.conduct_research()
report = await researcher.write_report()
```

---

## How It Syncs with Hermes Model & API Key

The config.json at `/opt/data/deep_research_outputs/gpt_researcher/config.json` will contain:
```json
{
    "SMART_LLM": "openrouter:inclusionai/ling-3.0-flash-vl:free",
    "FAST_LLM": "openrouter:inclusionai/ling-3.0-flash-vl:free",
    "OPENAI_BASE_URL": "http://localhost:11434/v1"  // or OpenRouter URL
}
```

**Auto-sync approach** (like ODR did):
1. Script reads `/opt/data/config.yaml` for current model
2. Updates config.json with `SMART_LLM` and `FAST_LLM` set to Hermes' current model
3. Reads API key from `/opt/data/.env` (OpenRouter key stays there, never printed)
4. Sets `OPENAI_BASE_URL` to OpenRouter API endpoint from env

**Critical**: The API key must NEVER appear in chat output, logs, or printed anywhere.
- Read from `/opt/data/.env` programmatically
- Set as environment variable at runtime only
- Never log, print, or expose in error messages

---

## Search Backends Available

GPT Researcher supports these backends (set RETRIEVER in config):
- **duckduckgo** — DuckDuckGo search (free, no API key) ← RECOMMENDED
- **google** — Google search
- **bing** — Bing search
- **serper** — Serper API
- **searx** — SearXNG (local, but DOWN)
- **tavily** — Tavily API (needs key)
- **arxiv** — arXiv API
- **pubmed_central** — PubMed

With DuckDuckGo as RETRIEVER, no external API keys needed for search.

---

## Report Types (Depth Levels)

| Report Type | Duration | Words | Sources | Depth |
|-------------|----------|-------|---------|-------|
| quick | ~2 min | ~1,200 | ~20 | shallow |
| standard | ~5 min | ~3,000 | ~20+ | medium |
| detailed | ~5-10 min | ~3,000+ | ~20+ | deep |
| deep | ~5-10 min | ~4,000+ | ~20+ | recursive tree |
| multi_agents | 6-20 min | 100+ | 100+ | parallel agents |

---

## Next Steps

1. Create integration script (Option A or B above)
2. Configure config.json with Hermes model sync
3. Test with quick research
4. Test with all depth levels
5. Debug any issues
6. Final verification
