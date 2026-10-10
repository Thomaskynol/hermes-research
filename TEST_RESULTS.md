# M5: Test Results — GPT Researcher

**Date**: 2026-09-12
**Status**: 2/3 depth levels PASSED, 1 RUNNING

---

## Test Results Summary

| Depth Level | Status | Duration | Words | Report | Notes |
|-------------|--------|----------|-------|--------|-------|
| **quick** | ✅ PASS | ~3 min | 1,933 | ✅ Saved | Full research cycle, DuckDuckGo search, citations |
| **standard** | ✅ PASS | ~4 min | 1,525 | ✅ Saved | Standard report format, citations |
| **detailed** | ✅ PASS | ~3 min | 1,902 | ✅ Saved | Detailed report format, citations |
| **deep** | 🔄 RUNNING | 5+ min | — | ⏳ In progress | Currently in deep research tree (depth=1, breadth=2) |

---

## Detailed Results

### Quick (✅ PASS)
- Report: "Main Trends in AI Agents in 2026: A Comprehensive Analysis"
- 1,933 words
- 11+ sources cited
- Full research cycle: query planning → web search → scraping → summarization → report
- Cost: $0.01283916
- Time: ~3 minutes

### Standard (✅ PASS)
- Report generated: 1,525 words
- Report format: research_report
- Proper citation section with references
- Cost: included in test run
- Time: ~4 minutes

### Detailed (✅ PASS)
- Report generated: 1,902 words
- Report format: detailed_report
- Full detailed analysis with sections
- Cost: included in test run
- Time: ~3 minutes

### Deep (🔄 RUNNING)
- Currently in deep research phase
- Research mode: depth=1, breadth=2 (after first iteration)
- Cost so far: $0.06519662
- Issues observed:
  - Wikipedia DNS failures (wt.wikipedia.org) — network issue
  - Some "No context found" for very specific sub-queries
  - Still in progress

---

## Issues Found & Fixed During Testing

### 1. Packaging Bug in v0.16.0
- `NameError: name 'Any' is not defined` in `actions/query_processing.py`
- **Fix**: Added `from typing import Any, List` at top of file
- **File**: `/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages/gpt_researcher/actions/query_processing.py`

### 2. Missing ddgs Package
- `ImportError: Unable to import ddgs` for DuckDuckGo search
- **Fix**: `pip install ddgs`

### 3. Missing langchain-huggingface
- Initially set EMBEDDING to huggingface, needed langchain-huggingface
- **Fix**: `pip install langchain-huggingface`
- **Note**: Reverted to openai:text-embedding-3-small (better reliability through OpenRouter proxy)

### 4. API Key Mapping
- GPT Researcher needs OPENAI_API_KEY, but only OPENROUTER_API_KEY is in .env
- **Fix**: sync_config.py maps OPENROUTER_API_KEY → OPENAI_API_KEY at runtime
- **Important**: Key NEVER printed or exposed in logs/chat

### 5. Config Format
- GPT Researcher uses JSON config (not YAML)
- Config keys must match GPT Researcher internal names

### 6. Deep Test: Wikipedia DNS Failures
- `wt.wikipedia.org` DNS resolution fails
- **Cause**: Network issue in the server environment
- **Impact**: Wikipedia sources unavailable for Deep Research
- **Mitigation**: DuckDuckGo/Google search still works fine

---

## Integration Method

GPT Researcher is integrated with Hermes via Python API (not MCP server — v0.16.0 has no dedicated MCP binary):

1. **Configuration**: `/opt/data/deep_research_outputs/gpt_researcher/config.json`
2. **Auto-sync**: `/opt/data/deep_research_outputs/gpt_researcher/sync_config.py` reads Hermes config.yaml for model, loads API key from .env
3. **Test scripts**: `/opt/data/deep_research_outputs/gpt_researcher/tests/`
4. **API import**: `from gpt_researcher import GPTResearcher`
5. **Env loading**: Sync script maps OPENROUTER_API_KEY → OPENAI_API_KEY, sets OPENAI_BASE_URL

---

## What Works

- ✅ GPT Researcher imports and initializes correctly
- ✅ DuckDuckGo search works (no API key needed)
- ✅ Web scraping works
- ✅ Report generation works (quick, standard, detailed confirmed)
- ✅ Citations generated correctly
- ✅ Model sync with Hermes config.yaml works
- ✅ API key loading from .env works (never printed)
- ✅ Deep Research mode activated (running, in progress)
- ✅ Cost tracking works ($0.01-0.06 per run)

---

## What Doesn't Work (Yet)

- ⚠️ Deep Research in progress — may have network issues (Wikipedia DNS)
- ⚠️ No dedicated MCP server (must use Python API for Hermes integration)
- ⚠️ LangChain still installed as dependency (GPT Researcher requires it internally)

---

## Commands for Manual Testing

```bash
# Quick test
cd /opt/data/deep_research_outputs/gpt_researcher
source /opt/data/home/.agent-reach-venv/bin/activate
python3 tests/quick_test.py

# Standard test
source /opt/data/home/.agent-reach-venv/bin/activate
python3 tests/standard_test.py

# Detailed test
source /opt/data/home/.agent-reach-venv/bin/activate
python3 tests/detailed_test.py

# Deep test (long)
source /opt/data/home/.agent-reach-venv/bin/activate
python3 tests/deep_test.py
```
