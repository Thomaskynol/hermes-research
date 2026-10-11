#!/usr/bin/env python3
"""Rebuild fixtures/transcript_replay.json using the REAL skill formatter.

Reads cache texts + library_sources, formats video docs through
vast._format_transcript_section (the exact function the skill uses), so the
verifier's "new" scenario matches skill code byte-for-byte on the transcript
part. Descriptions were not preserved in run artifacts -> video docs carry an
empty [description] block (declared in provenance, not hidden).
"""
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
import vast_local_retriever as vast
import youtube_transcript as yt

RUN = "20261010-211818-melhores_plugins_pro_opencode"
R = W / "runs" / RUN
cr = json.load(open(R / "custom_responses.json"))
lib = json.load(open(R / "library_sources.json"))["value"]
libmap = {x["url"]: x for x in lib if isinstance(x, dict) and x.get("url")}
con = sqlite3.connect("/opt/data/cache/yt_transcripts.db")
pool = cr["responses"][4]

docs, excluded = [], []
for i in pool["items"]:
    u = i["url"]
    if "youtu" in u and i["has_transcript_section"]:
        h = hashlib.sha256(u.encode()).hexdigest()
        text, lang = con.execute(
            "SELECT text,lang FROM transcripts WHERE url_hash=?", (h,)).fetchone()
        res = yt.TranscriptResult(
            text=text, lang=lang, chars=len(text), segments=0,
            dupes_removed=0, method="cache", reason=None, automatic=None)
        section, _ = vast._format_transcript_section(res, vast.RAW_CONTENT_LIMIT)
        docs.append({"url": u, "source": "youtube", "title": "",
                     "provenance": "cache-texto + vast._format_transcript_section",
                     "content": "[description]\n" + section})
    else:
        m = libmap.get(u)
        if m and m.get("raw_content"):
            docs.append({"url": u, "source": i.get("source", ""),
                         "title": m.get("title", ""),
                         "provenance": "library_sources",
                         "content": f"{m.get('title', '')}\n{m['raw_content']}"})
        else:
            excluded.append(u)

real = [d for d in docs]
tracked = []
for d in real:
    if "youtu" in d["url"] and len(tracked) < 2:
        tx = d["content"]
        probe = re.sub(r"\s+", " ", tx[len(tx) // 3:len(tx) // 3 + 80]).strip()
        tracked.append({"url": d["url"], "probe": probe})
print("track:", [(t["url"][-14:], t["probe"][:50]) for t in tracked])

fx = {"sub_query": pool["sub_query"],
      "provenance": ("run 211818 pool#5; video docs formatted by the REAL "
                     "vast._format_transcript_section (method=cache); "
                     "[description] block empty (descriptions not preserved "
                     "in artifacts). Excluded (no text anywhere): " + str(excluded)),
      "tracked": tracked, "docs": real}
out = W / "fixtures" / "transcript_replay.json"
out.write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"fixture: {len(real)} docs, {len(excluded)} excluidos -> {out}")
