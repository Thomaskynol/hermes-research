import asyncio
import json
import sys
import time
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
fx = json.load(open(W / "fixtures/transcript_replay.json"))
query = fx["sub_query"]
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.prompts import PromptFamily

EVIDENCE_PROMPT = (
    "Evidence rule for YouTube videos in the provided context: a video title and "
    "description are NOT verified video content. A transcript supports ONLY what is "
    "explicitly registered as spoken content. Never claim to have watched a video. "
    "Never reconstruct commands, files, or values absent from the transcript."
)

key = ""
for line in open("/opt/data/.env", encoding="utf-8"):
    if line.startswith("OPENROUTER_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")

messages = None


async def main():
    global messages
    emb = OpenAIEmbeddings(
        model="harrier-oss-v1-0.6b", openai_api_key="custom",
        openai_api_base="http://172.17.0.1:8082/v1",
        check_embedding_ctx_length=False)
    pages = [{"url": d["url"], "title": d.get("title", ""),
              "raw_content": d["content"], "source": d["url"]} for d in fx["docs"]]
    comp = ContextCompressor(
        documents=pages, embeddings=emb,
        similarity_threshold=0.42, prompt_family=PromptFamily)
    context = await comp.async_get_context(query=query, max_results=10)

    # Same LLM construction the research uses for openrouter:*
    # (ChatOpenAI on https://openrouter.ai/api/v1).
    llm = ChatOpenAI(openai_api_base="https://openrouter.ai/api/v1",
                     openai_api_key=key,
                     model="meta/muse-spark-1.3-contributor",
                     temperature=0.35,
                     max_tokens=8000,
                     request_timeout=600)
    messages = [
        SystemMessage(content="Answer ONLY from the context. Distinguish "
                              "description, spoken transcript content, and "
                              "unobserved visual content."),
        HumanMessage(content=f"{EVIDENCE_PROMPT}\n\nContext: {context}\n\n"
                             "Question: What do the two videos with transcripts "
                             "actually show about plugin configuration? Quote one "
                             "spoken passage per video with its URL, and state "
                             "what you cannot verify."),
    ]
    t0 = time.time()
    resp = await llm.ainvoke(messages)
    dt = time.time() - t0
    out = {"model": "meta/muse-spark-1.3-contributor", "seconds": round(dt, 1),
           "finish_reason": getattr(resp, "finish_reason", None)
           or resp.response_metadata.get("finish_reason"),
           "usage": getattr(resp, "usage_metadata", None),
           "messages_sent": [{"role": m.type, "content": m.content}
                             for m in messages],
           "answer": resp.content or ""}
    Path("/tmp/gen7.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str)[:300000],
        encoding="utf-8")
    print("finish:", out["finish_reason"], "| secs:", out["seconds"])
    print("usage:", json.dumps(out["usage"], default=str))
    print("answer chars:", len(out["answer"]))
    print("---- answer ----")
    print(out["answer"][:3000])

asyncio.run(main())
