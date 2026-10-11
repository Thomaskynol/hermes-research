#!/usr/bin/env python3
"""Replay gpt_researcher_integration.py with FROZEN collection.

- Stub HTTP server replays a frozen custom-retriever payload (docs rebuilt
  with the REAL vast._format_transcript_section; see provenance in fixture).
- RETRIEVER=custom isolates the transcript path (recorded replay config).
- Wraps researcher.write_report on OUR instance to capture exactly what the
  write path receives (context string + custom_prompt) before delegating.
- Generation uses the model resolved for research (recorded). Restores
  config.json afterwards. No site-packages edits.
"""
import asyncio
import json
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
import vast_local_retriever as vast
import youtube_transcript as yt
import hashlib
import sqlite3

STUB_PORT = 18099
fx = json.load(open(W / "fixtures/transcript_replay.json"))

con = sqlite3.connect("/opt/data/cache/yt_transcripts.db")
payload = []
for d in fx["docs"]:
    if "youtu" in d["url"]:
        h = hashlib.sha256(d["url"].encode()).hexdigest()
        text, lang = con.execute(
            "SELECT text,lang FROM transcripts WHERE url_hash=?", (h,)).fetchone()
        res = yt.TranscriptResult(
            text=text, lang=lang, chars=len(text), segments=0,
            dupes_removed=0, method="cache", reason=None, automatic=None)
        section, _ = vast._format_transcript_section(res, vast.RAW_CONTENT_LIMIT)
        raw = "[description]\n" + section
    else:
        raw = d["content"]
    payload.append({"url": d["url"], "raw_content": raw,
                    "title": d.get("title", "")})
print(f"stub payload: {len(payload)} docs")


class Stub(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


async def main():
    import os
    # Import FIRST: gpt_researcher_integration runs sync_config.sync() at
    # import, which resets RETRIEVER_ENDPOINT to vast :8001 and rewrites
    # config.json. Stub env + replay config must come AFTER.
    from gpt_researcher import GPTResearcher
    from gpt_researcher.utils.enum import Tone
    from gpt_researcher_integration import EVIDENCE_PROMPT
    os.environ["RETRIEVER_ENDPOINT"] = f"http://127.0.0.1:{STUB_PORT}/"
    key = ""
    for line in open("/opt/data/.env", encoding="utf-8"):
        if line.startswith("OPENROUTER_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
    os.environ["OPENROUTER_API_KEY"] = key

    cfg = W / "config.json"
    bak = W / "config.json.replay-bak"
    shutil.copy(cfg, bak)
    from gpt_researcher import GPTResearcher as _GR
    orig_write = _GR.write_report
    try:
        c = json.loads(cfg.read_text(encoding="utf-8"))
        c["RETRIEVER"] = "custom"
        # Model resolved for research = current chat model (state.db,
        # permanently authorized). Committed config still names the dead
        # space-bunny (0 endpoints); replay records the substitution.
        c["SMART_LLM"] = "openrouter:meta/muse-spark-1.3-contributor"
        c["FAST_LLM"] = "openrouter:meta/muse-spark-1.3-contributor"
        c["STRATEGIC_LLM"] = "openrouter:meta/muse-spark-1.3-contributor"
        cfg.write_text(json.dumps(c, indent=2), encoding="utf-8")

        captured = {}

        async def spy_write(self, *a, **k):
            captured["args"] = [str(x)[:200] for x in a]
            captured["custom_prompt"] = str(k.get("custom_prompt", ""))[:300]
            return await orig_write(self, *a, **k)

        GPTResearcher.write_report = spy_write
        r = GPTResearcher(
            query="melhores plugins pro opencode, como instalar cada um, "
                  "e videos do youtube mostrando a configuracao",
            report_type="quick_report", config_path=str(cfg),
            report_format="markdown", tone=Tone.Objective, verbose=False)
        await r.conduct_research()
        report = await r.write_report(custom_prompt=EVIDENCE_PROMPT)
        out = {"captured_write_report": captured,
               "source_urls": r.get_source_urls(),
               "report_chars": len(report)}
        Path("/tmp/replay_out.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1)[:6000],
            encoding="utf-8")
        Path("/tmp/replay_report.md").write_text(report[:60000], encoding="utf-8")
        print("write_report captured:", json.dumps(captured)[:400])
        print("sources:", len(out["source_urls"]), "| report chars:", len(report))
        # token usage, when exposed by the library
        try:
            print("costs:", json.dumps(r.costs)[:300])
        except Exception as e:
            print("costs: not exposed (%s)" % type(e).__name__)
    finally:
        shutil.move(str(bak), str(cfg))
        GPTResearcher.write_report = orig_write


srv = HTTPServer(("127.0.0.1", STUB_PORT), Stub)
threading.Thread(target=srv.serve_forever, daemon=True).start()
asyncio.run(main())
srv.shutdown()
