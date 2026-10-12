import asyncio
import json
import os
import sys
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
import sync_config
sync_config.sync()

key = os.environ.get("OPENROUTER_API_KEY") or os.environ["OPENAI_API_KEY"]
from langchain_openai import ChatOpenAI

MODEL = "meta/muse-spark-1.3-contributor"


async def probe(label, **kw):
    llm = ChatOpenAI(openai_api_base="https://openrouter.ai/api/v1",
                     openai_api_key=key, model=MODEL, **kw)
    try:
        r = await llm.ainvoke("diga ok")
        print(f"  {label}: OK")
        return True
    except Exception as e:
        msg = str(e)[:200]
        print(f"  {label}: {type(e).__name__}: {msg}")
        return False


async def main():
    print("=== via langchain_openai (o que a lib usa) ===")
    # o que query_processing manda: max_tokens=None + reasoning_effort
    await probe("max_tokens=None effort=medium",
                max_tokens=None, reasoning_effort="medium")
    await probe("max_tokens=None (sem effort)", max_tokens=None)
    await probe("max_tokens=4000", max_tokens=4000)
    # o que pode dar errado: max_completion_tokens vs max_tokens
    await probe("max_completion_tokens=None", max_completion_tokens=None)
    await probe("max_completion_tokens=15", max_completion_tokens=15)
    await probe("max_completion_tokens=16", max_completion_tokens=16)
    # reasoning_effort alto (o nosso EFFORT=high)
    await probe("max_tokens=None effort=high",
                max_tokens=None, reasoning_effort="high")

asyncio.run(main())
