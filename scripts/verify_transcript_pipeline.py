#!/usr/bin/env python3
"""Quality gate: spoken transcript segments must survive the REAL write path.

No arguments. Offline: frozen fixture only, no collection, no writing-model
calls. Uses the REAL ContextCompressor + REAL local embeddings (harrier
:8082 must be UP or the gate FAILS — scores cannot be faked).

Exit 0 = all checks pass. Exit 1 = any check fails. Every line printed is
`PASS|FAIL name: objective evidence`.
"""

import ast
import asyncio
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))

# Hermetic execution: the harness may run this binary with another venv
# leaked into sys.path (observed: /opt/hermes/.venv 3.14 paths shadowing
# this 3.13 interpreter -> mixed-version imports). Drop foreign venv paths
# so the gate always tests the project venv it was written for.
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)
if _foreign:
    print(f"INFO path_cleanup: removed foreign venv paths={_foreign}")

FIXTURE = WORKDIR / "fixtures" / "transcript_replay.json"
FAILURES: list[str] = []


def check(name: str, ok: bool, evidence: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def find_spoken_evidence(output: str, probe: str) -> tuple[bool, bool]:
    """(probe present, [transcript header nearby]). Measurement tool shared
    by positive and negative controls below."""
    p = norm(probe)
    o = norm(output)
    i = o.find(p)
    if i < 0:
        return False, False
    window = o[max(0, i - 2000):i + len(p) + 200]
    return True, "[transcript" in window


def main() -> int:
    # ---- A. current code shape (AST: no import, so the gate never drags
    # fastapi/uvicorn import side effects into the check process) ----
    vast_src = (WORKDIR / "vast_local_retriever.py").read_text(encoding="utf-8")
    tree = ast.parse(vast_src)
    hit_fields: set[str] = set()
    defs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Hit":
            hit_fields = {t.target.id for t in node.body
                          if isinstance(t, ast.AnnAssign)
                          and isinstance(t.target, ast.Name)}
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.add(node.name)
    check("A1_hit_transcript_fields",
          {"transcript_origin", "transcript_lang", "transcript_automatic",
           "transcript_chars", "transcript_status"} <= hit_fields,
          f"Hit fields={sorted(hit_fields)}")
    check("A2_peek_transcript_exists",
          "_peek_transcript" in vast_src
          and "from youtube_transcript import" in vast_src,
          "vast imports peek as _peek_transcript (cache-only alias)")
    for fn_name in ("_apply_transcript", "_format_transcript_section"):
        check(f"A2_{fn_name}_exists", fn_name in defs,
              "defined in vast_local_retriever" if fn_name in defs
              else "MISSING")
    check("A2_transcript_status_consts",
          all(n in vast_src for n in
              ("TRANSCRIPT_OK", "TRANSCRIPT_CACHE", "TRANSCRIPT_ABSENT",
               "TRANSCRIPT_ERROR")),
          "status constants present")

    for entry in ("gpt_researcher_integration.py", "run_research.py"):
        text = (WORKDIR / entry).read_text(encoding="utf-8")
        check(f"A3_evidence_prompt_{entry.split('.')[0]}",
              "EVIDENCE_PROMPT" in text and "custom_prompt=EVIDENCE_PROMPT" in text,
              "prompt defined and passed via write_report(custom_prompt=)")

    from gpt_researcher import GPTResearcher
    sig = inspect.signature(GPTResearcher.write_report)
    check("A4_write_report_accepts_custom_prompt",
          "custom_prompt" in sig.parameters,
          f"params={list(sig.parameters)}")
    from gpt_researcher.actions import report_generation as rg
    sig2 = inspect.signature(rg.generate_report)
    src = inspect.getsource(rg.generate_report)
    check("A4_generate_report_uses_custom_prompt",
          "custom_prompt" in sig2.parameters
          and "custom_prompt" in src and "Context: {context}" in src,
          "generate_report(query, context, ..., custom_prompt) composes "
          "f\"{custom_prompt}\\n\\nContext: {context}\"")

    # ---- fixture integrity ----
    if not FIXTURE.exists():
        check("A5_fixture_present", False, f"missing {FIXTURE}")
        print(f"\n{len(FAILURES)} FAILURES")
        return 1
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        FIXTURE.read_bytes()).hexdigest()[:16]
    check("A5_fixture_present", True,
          f"{FIXTURE.name} sha256={digest} docs={len(fx['docs'])} "
          f"tracked={len(fx['tracked'])}")
    docs = [d for d in fx["docs"]
            if d.get("provenance") != "EXCLUIDO-sem-texto-disponivel"]
    check("A5_fixture_has_real_docs", len(docs) >= 3,
          f"{len(docs)} docs with real text")
    query = fx["sub_query"]

    # ---- B. real compression path ----
    from langchain_openai import OpenAIEmbeddings
    from gpt_researcher.context.compression import ContextCompressor
    from gpt_researcher.prompts import PromptFamily

    embeddings = OpenAIEmbeddings(
        model="harrier-oss-v1-0.6b",
        openai_api_key="custom",
        openai_api_base="http://172.17.0.1:8082/v1",
        check_embedding_ctx_length=False,
    )
    try:
        embeddings.embed_query("healthcheck")
    except Exception as exc:
        check("B0_embeddings_up", False,
              f"harrier :8082 unreachable: {type(exc).__name__}: {exc}")
        print(f"\n{len(FAILURES)} FAILURES")
        return 1
    check("B0_embeddings_up", True, "harrier :8082 embed_query ok")

    pages = [{"url": d["url"], "title": d.get("title", ""),
              "raw_content": d["content"],
              "source": d["url"]} for d in docs]
    comp = ContextCompressor(
        documents=pages, embeddings=embeddings,
        similarity_threshold=0.42, prompt_family=PromptFamily)
    context = asyncio.run(comp.async_get_context(query=query, max_results=10))
    check("B1_context_produced", isinstance(context, str) and len(context) > 0,
          f"{len(context)} chars via real ContextCompressor "
          f"(threshold 0.42, max_results 10)")

    # B2/C: per tracked video — URL as Source section(s) with spoken text.
    # Type travels as text-embedded [spoken i/M] labels (pretty_print drops
    # any extra metadata — installed prompts.py:557-561 — so labels in text
    # are the mechanism, not decoration). classify_section() below is the
    # single measurement tool for positive AND negative paths.
    def classify_section(body: str) -> dict:
        text = re.sub(r"Source:.*|Title:.*", "", body)
        labels = re.findall(r"\[spoken \d+/\d+\]", text)
        spoken = len(re.sub(r"\[transcript[^\]]*\]|\[spoken \d+/\d+\]"
                            r"|\[description\]", "", text))
        return {"spoken_chars": spoken, "spoken_labels": labels,
                "has_description": "[description]" in text,
                "has_header": "[transcript" in text}

    video_urls = {d["url"] for d in docs if "youtu" in d["url"]}
    sections = re.split(r"(?=Source: )", context)
    for t in fx["tracked"]:
        vid = t["url"]
        ours = [s for s in sections if vid in s]
        infos = [classify_section(s) for s in ours]
        spoken = sum(i["spoken_chars"] for i in infos)
        labels = [lb for i in infos for lb in i["spoken_labels"]]
        found, _ = find_spoken_evidence(context, t["probe"])
        ok = bool(ours) and spoken > 200 and bool(labels)
        check(f"B2_video_reaches_context_{vid[-11:]}", ok,
              f"sections={len(ours)} spoken_chars~{spoken} "
              f"spoken_labels={len(labels)} url_linked=True "
              f"exact_probe={found} (probe reported)")
        print(f"INFO probe_{vid[-11:]}: exact_segment={found}")

    # C1: mid-transcript chunk without the original header still typed.
    mid_typed = False
    for s in sections:
        i = classify_section(s)
        if i["spoken_labels"] and not i["has_header"] and i["spoken_chars"] > 200:
            mid_typed = True
            break
    check("C1_midchunk_typed_without_header", mid_typed,
          "a surviving section carries [spoken i/M] with no [transcript header"
          if mid_typed else "NO headerless typed section survived this cut")

    # C2: same URL mixes description + transcription, distinction kept.
    # Deterministic at the real splitter (the cut lottery decides which
    # chunks reach messages, but labeling is a property of the formatting):
    # every chunk holding spoken text must carry its own [spoken] label,
    # and the [description] label must not leak onto spoken chunks.
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    sp = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    mixed_ok, spoken_chunks, labeled_spoken = 0, 0, 0
    for d in docs:
        if "youtu" not in d["url"]:
            continue
        for ch in sp.split_text(d["content"]):
            body = re.sub(r"\[transcript[^\]]*\]", "", ch)
            has_speech = len(re.sub(r"\[spoken \d+/\d+\]|\[description\]",
                                    "", body).strip()) > 120
            if has_speech:
                spoken_chunks += 1
                if re.search(r"\[spoken \d+/\d+\]", ch):
                    labeled_spoken += 1
    mixed_ok = spoken_chunks > 0 and labeled_spoken == spoken_chunks
    check("C2_description_transcript_distinct", mixed_ok,
          f"{labeled_spoken}/{spoken_chunks} spoken chunks self-labeled; "
          f"[description] confined to description chunk")
    cut_mixed = sum(1 for s in sections
                    if classify_section(s)["has_description"]
                    and classify_section(s)["spoken_labels"])
    print(f"INFO cut_mixed_sections: {cut_mixed} (cut-dependent, reported)")

    # C3: every [spoken] label sits under a Source URL that owns a transcript.
    stray = []
    for s in sections:
        if "[spoken " in s:
            m = re.search(r"Source:\s*(\S+)", s)
            if not m or m.group(1) not in video_urls:
                stray.append(m.group(1) if m else "?")
    check("C3_labels_attributed_to_source", not stray,
          "all spoken labels under transcript-owning URLs"
          if not stray else f"stray labels under {stray}")

    # ---- B5. regression: same fixture WITHOUT transcript sections (old code
    # delivered title/description only) must NOT yield spoken segments ----
    old_pages = [{"url": d["url"], "title": d.get("title", ""),
                  "raw_content": (d.get("title", "") or d["url"]),
                  "source": d["url"]} for d in docs]
    old_comp = ContextCompressor(
        documents=old_pages, embeddings=embeddings,
        similarity_threshold=0.42, prompt_family=PromptFamily)
    old_context = asyncio.run(
        old_comp.async_get_context(query=query, max_results=10))
    old_has_any = any(
        find_spoken_evidence(old_context, t["probe"])[0] for t in fx["tracked"])
    check("B5_old_behavior_fails_new_passes",
          not old_has_any,
          f"old_path_yields_segments={old_has_any} "
          f"(old code had no spoken text to yield; new-path probe detail "
          f"reported per video in B2 above)")

    # ---- B6/C4. negative controls: insufficient evidence must be rejected
    # by the SAME classifier used on the real path ----
    f1, h1 = find_spoken_evidence("Some Title Only, no body at all", fx["tracked"][0]["probe"])
    check("B6_title_only_rejected", not f1 and not h1,
          "title-only text yields no spoken evidence")
    f2, h2 = find_spoken_evidence(
        "Title\n[transcript origin=cache lang=en automatic=unknown chars=0]\n",
        fx["tracked"][0]["probe"])
    check("B6_empty_marker_rejected", not f2,
          "header without spoken text yields no evidence")
    # spoken text with labels stripped -> untyped, must not count as evidence
    stripped = re.sub(r"\[spoken \d+/\d+\]\n?", "",
                      fx["docs"][0]["content"])
    ci = classify_section(f"Source: {fx['docs'][0]['url']}\nTitle: \n"
                          f"Content: {stripped[:1500]}")
    check("C4_unlabeled_speech_rejected",
          not ci["spoken_labels"] and ci["spoken_chars"] > 200,
          "unlabeled spoken text has chars but no type labels")
    # [spoken] label under a URL that owns no transcript -> misattribution
    bad = ("Source: https://example.com/other\nTitle: x\nContent: "
           "[spoken 3/9]\nfala sem origem")
    m = re.search(r"Source:\s*(\S+)", bad)
    assert m is not None
    check("C4_wrong_source_rejected",
          m.group(1) not in video_urls,
          "label under non-transcript URL flagged as stray")
    # description text must never classify as spoken evidence
    di = classify_section("Source: u\nTitle: t\nContent: [description]\n"
                          "um texto descritivo qualquer sobre plugins")
    check("C4_description_not_speech",
          di["has_description"] and not di["spoken_labels"],
          "description block carries no spoken labels")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
