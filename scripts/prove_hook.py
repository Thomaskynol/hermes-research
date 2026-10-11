import json
import sys
from pathlib import Path

W = Path("/opt/data/deep_research_outputs/gpt_researcher")
sys.path.insert(0, str(W))
from gpt_researcher_integration import run_provenance_audit

fx = json.load(open(W / "fixtures/transcript_replay.json"))
# frozen writer input: Source sections as the writer received them
messages = "\n".join(
    f"Source: {d['url']}\nTitle: {d.get('title', '')}\nContent: {d['content'][:3000]}"
    for d in fx["docs"])
report = (W / "runs/replay_entry_20261011.md").read_text(encoding="utf-8")

print("== controle positivo (relatorio congelado real) ==")
out = run_provenance_audit(report, messages, Path("/tmp/hook_pos.md"))
print("report_findings:", len(out["report_findings"]),
      "| message_findings:", len(out["message_findings"]),
      "| manifest:", len(out["manifest_urls"]))

print("== controle negativo (referencia invalida injetada) ==")
bad = report + ("\n- PlugX does everything. "
                "Source: `https://www.youtube.com/watch?v=AAAAAAAAAAA`, "
                "[spoken 1/9]\n")
out2 = run_provenance_audit(bad, messages, Path("/tmp/hook_neg.md"))
for f in out2["report_findings"]:
    print("detectado:", f["code"], f["url"])
assert any(f["code"] == "SOURCE_NOT_IN_MANIFEST"
           for f in out2["report_findings"]), "negativo NAO detectado!"
print("hook OK: fluxo real chama o validador e detecta referencia invalida")
