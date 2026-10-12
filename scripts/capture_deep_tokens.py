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

# Patch langchain's ChatOpenAI so we see the EXACT payload field the provider
# rejects (max_completion_tokens), which gpt_researcher's own wrapper maps
# max_tokens onto for reasoning models.
from langchain_openai import ChatOpenAI
_orig = ChatOpenAI._generate if hasattr(ChatOpenAI, "_generate") else None
import langchain_openai.chat_models.base as base_mod
seen = []
_orig_agenerate = ChatOpenAI._agenerate


async def spy_agenerate(self, messages, stop=None, run_manager=None, **kwargs):
    payload = {k: kwargs.get(k) for k in
               ("max_tokens", "max_completion_tokens", "reasoning_effort")}
    if payload.get("max_completion_tokens") is None:
        # langchain maps self.max_tokens -> max_completion_tokens for reasoning
        payload["max_completion_tokens"] = getattr(self, "max_completion_tokens", None) or getattr(self, "max_tokens", None)
    seen.append({"model": getattr(self, "model_name", None), **payload})
    return await _orig_agenerate(self, messages, stop=stop,
                                 run_manager=run_manager, **kwargs)


ChatOpenAI._agenerate = spy_agenerate

from gpt_researcher import GPTResearcher
from gpt_researcher.utils.enum import Tone

os.environ["DEPTH_OVERRIDES_JSON"] = "{}"


async def main():
    # Deep path, small breadth to reach the deep_research skill quickly.
    r = GPTResearcher(query="melhores plugins pro opencode",
                      report_type="deep",
                      config_path=str(W / "config.json"),
                      report_format="markdown", tone=Tone.Objective, verbose=False)
    try:
        await r.conduct_research()
    except Exception as e:
        print("conduct_research raised:", type(e).__name__, str(e)[:200])
    print("\n=== payloads vistos (deep) ===")
    bad = 0
    for s in seen:
        mct = s.get("max_completion_tokens")
        flag = ""
        if isinstance(mct, int) and 0 < mct < 16:
            flag = "  <== PROBLEMA (<16)"
            bad += 1
        print(f"  {s['model']} max_completion_tokens={mct} "
              f"max_tokens={s.get('max_tokens')} effort={s.get('reasoning_effort')}{flag}")
    print(f"\nchamadas com max_completion_tokens<16: {bad}")
    Path("/tmp/deep_payloads.json").write_text(json.dumps(seen, indent=1))

asyncio.run(main())
