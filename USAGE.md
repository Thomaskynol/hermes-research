# Hermes GPT Researcher Integration — Quick Reference

## Run a Research Task

```bash
source /opt/data/home/.agent-reach-venv/bin/activate
cd /opt/data/deep_research_outputs/gpt_researcher
python3 gpt_researcher_integration.py "your research question" quick
python3 gpt_researcher_integration.py "your research question" standard
python3 gpt_researcher_integration.py "your research question" detailed
python3 gpt_researcher_integration.py "your research question" deep
```

## Run via Hermes Conversation

Paste this into Hermes execute_code:

```python
import asyncio, sys, os
sys.path.insert(0, "/opt/data/deep_research_outputs/gpt_researcher")
from hermes_tools import terminal
# Use terminal to run the script
# terminal("source /opt/data/home/.agent-reach-venv/bin/activate && cd /opt/data/deep_research_outputs/gpt_researcher && python3 gpt_researcher_integration.py 'your query' standard")
```

Or run directly via terminal:
```
source /opt/data/home/.agent-reach-venv/bin/activate
cd /opt/data/deep_research_outputs/gpt_researcher
python3 gpt_researcher_integration.py "main trends in AI 2026" detailed
```

## Configuration

- **Config file**: `/opt/data/deep_research_outputs/gpt_researcher/config.json`
- **Sync script**: `/opt/data/deep_research_outputs/gpt_researcher/sync_config.py`
- **Auto-sync**: Reads model from `/opt/data/config.yaml`, API key from `/opt/data/.env`
- **Output dir**: `/opt/data/deep_research_outputs/gpt_researcher/output/`

## Depth Presets

| Depth | Duration | Words | Sources |
|-------|----------|-------|---------|
| quick | ~2 min | ~1,200 | ~20 |
| standard | ~5 min | ~3,000 | ~20+ |
| detailed | ~5-10 min | ~3,000+ | ~20+ |
| deep | ~5-10 min | ~4,000+ | ~20+ |

## Notes

- DuckDuckGo search (no API key needed for search)
- OpenRouter API key from .env, NEVER printed
- Model auto-syncs with Hermes config.yaml
- Deep Research may be rate-limited on free OpenRouter tier
