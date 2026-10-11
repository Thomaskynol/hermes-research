import json, sys, time, urllib.request

SYS = ("You audit whether a CLAIM is supported by a spoken-transcript EXCERPT. "
       "Return a JSON array, one object per id: {id, verdict, support, justification}. "
       "verdict: sustained | partial | unsupported | explicit_inference. "
       "Check subject, negation, conditions, versions/dates, scope. ASR-garbled "
       "words (Curve/Curve, barra, version numbers) must NOT become confirmed "
       "names/commands/versions: at most partial with justification. "
       "explicit_inference needs its premises quoted. support: short quote or ''."
       "Output ONLY the JSON array.")

key = ""
for line in open("/opt/data/.env", encoding="utf-8"):
    if line.startswith("OPENROUTER_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")

items = json.load(open("/tmp/review_in.json"))
halves = [items[:23], items[23:]]
all_out, usages = [], []
for h in halves:
    body = {"model": "meta/muse-spark-1.3-contributor", "temperature": 0,
            "max_tokens": 12000,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": json.dumps(
                             h, ensure_ascii=False)}]}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=600))
    dt = time.time() - t0
    msg = r["choices"][0]["message"]["content"]
    start = msg.find("[")
    arr = json.loads(msg[start:msg.rfind("]") + 1])
    all_out.extend(arr)
    usages.append({"usage": r.get("usage"), "secs": round(dt, 1),
                   "finish": r["choices"][0].get("finish_reason")})
    print(f"batch: {len(arr)} verdicts, {round(dt,1)}s, "
          f"{json.dumps(r.get('usage'))}", flush=True)

json.dump(all_out, open("/tmp/review_out.json", "w"), ensure_ascii=False, indent=1)
json.dump(usages, open("/tmp/review_cost.json", "w"), indent=1)
print("saved", len(all_out))
