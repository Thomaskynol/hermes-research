import asyncio
import json
import os
import sys
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
import sync_config
sync_config.sync()

import reasoning_effort
reasoning_effort.install()

# Instrument: log every outbound chat completion's model + max_tokens.
from gpt_researcher.utils import llm as llm_utils
orig = llm_utils.create_chat_completion
calls = []


async def spy(*a, **k):
    args = orig.__wrapped__ if hasattr(orig, "__wrapped__") else None
    import inspect
    try:
        bound = inspect.signature(orig).bind_partial(*a, **k).arguments
    except Exception:
        bound = {}
    rec = {"model": bound.get("model"), "max_tokens": bound.get("max_tokens"),
           "reasoning_effort": bound.get("reasoning_effort")}
    calls.append(rec)
    print(f"[CALL] model={rec['model']} max_tokens={rec['max_tokens']} "
          f"effort={rec['reasoning_effort']}", flush=True)
    return await orig(*a, **k)


for mod in (llm_utils,):
    mod.create_chat_completion = spy
from gpt_researcher.actions import query_processing, report_generation
query_processing.create_chat_completion = spy
report_generation.create_chat_completion = spy

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import Tone


async def main():
    r = GPTResearcher(query="melhores plugins pro opencode e videos",
                      report_type="quick_report",
                      config_path=str(W / "config.json"),
                      report_format="markdown", tone=Tone.Objective, verbose=False)
    await r.conduct_research()
    rep = await r.write_report()
    print("\nreport words:", len(rep.split()))
    print("\n=== chamadas capturadas ===")
    for c in calls:
        flag = " <== PROBLEMA" if isinstance(c["max_tokens"], int) and c["max_tokens"] < 16 else ""
        print(f"  {c['model']} max_tokens={c['max_tokens']}{flag}")
    Path("/tmp/calls.json").write_text(json.dumps(calls, indent=1))

asyncio.run(main())
