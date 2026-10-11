import json
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
fx = json.load(open(W / "fixtures/transcript_replay.json"))
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

emb = OpenAIEmbeddings(
    model="harrier-oss-v1-0.6b", openai_api_key="custom",
    openai_api_base="http://172.17.0.1:8082/v1",
    check_embedding_ctx_length=False)
sp = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
docs = []
for d in fx["docs"]:
    for i, ch in enumerate(sp.split_text(d["content"])):
        docs.append(Document(page_content=ch,
                             metadata={"source": d["url"], "chunk": i}))
qv = emb.embed_query(fx["sub_query"])
import numpy as np

dv = emb.embed_documents([d.page_content for d in docs])
A = np.array(dv)
sims = (A @ np.array(qv)) / (np.linalg.norm(A, axis=1) * np.linalg.norm(qv))
order = np.argsort(sims)[::-1]
print(f"query: {fx['sub_query'][:60]} | chunks: {len(docs)}")
print("rank sim url chunk excerpt")
for rank, idx in enumerate(order[:12]):
    u = docs[idx].metadata["source"]
    ex = docs[idx].page_content[:60].replace("\n", " ")
    print(f"{rank:>3} {sims[idx]:.3f} {u[-14:]} ch{docs[idx].metadata['chunk']:>2} {ex}")
print(f"acima 0.42: {int((sims > 0.42).sum())}/{len(sims)} | corte pretty: top-10")
