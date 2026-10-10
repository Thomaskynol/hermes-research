#!/usr/bin/env python3
"""Unit tests for the YouTube transcript enrichment fix (YT_ENRICH_FIX_BRIEF.md).

Causa (c): o slice [:YT_ENRICH_MAX] + selecao-antes-do-enriquecimento deixava a
maioria dos videos fora do yt_hits. O fix e cache-first (fase A, sem limite)
para TODOS os videos do `selected` + live com o teto 3 inalterado (fase B), com
a transcricao como secao ADICIONADA rotulada (nunca substituicao) e status
explicito por hit.

Sem rede, sem yt-dlp, sem modelo: _fetch_transcript/_peek_transcript/_cascade_fetch
sao stubbed via monkeypatch. Roda com `pytest tests/test_yt_enrich_fix.py`.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/opt/data/deep_research_outputs/gpt_researcher")

import run_trace
import vast_local_retriever as vast
import youtube_transcript as yt


def run(coro):
    return asyncio.run(coro)


def make_result(url, chars=1000, method="live", lang="en", automatic=None):
    return yt.TranscriptResult(
        text="fala transcrita do video " * 40,
        lang=lang, chars=chars, segments=10, dupes_removed=2,
        method=method, reason=None, automatic=automatic,
    )


def make_hit(url, source="youtube", title="Titulo", desc="descricao base"):
    return vast.Hit(
        url=url, title=title,
        raw_content=f"YouTube: {title}\n{desc}", source=source,
    )


# --- 1. youtube_transcript.py: campo automatic --------------------------------

def test_miss_automatic_is_unknown():
    assert yt._miss("en", "sem legenda").automatic is None


def test_detect_automatic_returns_unknown_not_guess():
    # Sem sinal barato e confiavel no VTT: unknown honesto, nunca chute.
    assert yt._detect_automatic("WEBVTT\nKind: captions\n00:00:00.000 --> x\nola") is None
    assert yt._detect_automatic("") is None


def test_peek_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "TRANSCRIPT_DB", str(tmp_path / "t.db"))
    assert yt.peek_transcript("https://www.youtube.com/watch?v=AAAAAAAAAAA") is None
    assert yt.peek_transcript("") is None


def test_peek_hit_returns_cache_result(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "TRANSCRIPT_DB", str(tmp_path / "t.db"))
    url = "https://www.youtube.com/watch?v=BBBBBBBBBBB"
    yt._cache_put_sync(yt._normalize_url(url), "texto da legenda", "en", 5, 1)
    res = yt.peek_transcript(url)
    assert res is not None
    assert res.method == yt.METHOD_CACHE
    assert res.text == "texto da legenda"
    assert res.automatic is None


# --- 2. vast: secao rotulada ADICIONA, nao substitui ---------------------------

def test_apply_transcript_keeps_title_desc_url():
    hit = make_hit("https://www.youtube.com/watch?v=CCCCCCCCCCC")
    before = hit.raw_content
    vast._apply_transcript(hit, make_result(hit.url, chars=1000, method="live"))
    assert hit.raw_content.startswith(before)  # descricao-base intacta
    assert "[transcript origin=live lang=en automatic=unknown chars=1000]" in hit.raw_content
    assert "fala transcrita" in hit.raw_content
    assert hit.title == "Titulo"
    assert hit.url == "https://www.youtube.com/watch?v=CCCCCCCCCCC"
    assert hit.transcript_origin == "live"
    assert hit.transcript_lang == "en"
    assert hit.transcript_automatic is None
    assert hit.transcript_chars == 1000
    assert hit.transcript_status == vast.TRANSCRIPT_OK


def test_apply_transcript_cache_status():
    hit = make_hit("https://www.youtube.com/watch?v=DDDDDDDDDDD")
    vast._apply_transcript(hit, make_result(hit.url, method="cache"))
    assert hit.transcript_status == vast.TRANSCRIPT_CACHE


def test_apply_transcript_pre_truncates_to_limit(monkeypatch):
    monkeypatch.setattr(vast, "RAW_CONTENT_LIMIT", 200)
    hit = make_hit("https://www.youtube.com/watch?v=EEEEEEEEEEE")
    res = make_result(hit.url, chars=5000)
    vast._apply_transcript(hit, res)
    assert len(hit.raw_content) <= 200 + len("[transcript") + 200  # secao cortada, base intacta
    assert hit.transcript_status.startswith(vast.TRANSCRIPT_OK)
    assert "transcript_truncated_at_200" in hit.transcript_status


# --- 3. _read_transcript: status explicito -------------------------------------

def test_read_transcript_success_appends(monkeypatch):
    async def fake(url, **kw):
        return make_result(url, chars=500, method="live")

    monkeypatch.setattr(vast, "_fetch_transcript", fake)
    hit = make_hit("https://www.youtube.com/watch?v=FFFFFFFFFFF")
    base = hit.raw_content
    run(vast._read_transcript(hit, 9999999999.0, __import__("collections").Counter()))
    assert hit.raw_content.startswith(base)
    assert "[transcript origin=live" in hit.raw_content
    assert hit.transcript_status == vast.TRANSCRIPT_OK


def test_read_transcript_miss_labels_fallback(monkeypatch):
    async def fake(url, **kw):
        return yt._miss("en", "yt-dlp nao produziu legenda em en (rc=0)")

    monkeypatch.setattr(vast, "_fetch_transcript", fake)
    hit = make_hit("https://www.youtube.com/watch?v=GGGGGGGGGGG")
    base = hit.raw_content
    run(vast._read_transcript(hit, 9999999999.0, __import__("collections").Counter()))
    assert hit.raw_content == base  # fallback: descricao intacta, sem secao
    assert "[transcript" not in hit.raw_content
    assert hit.transcript_status == vast.TRANSCRIPT_ABSENT


def test_read_transcript_error_labels_error(monkeypatch):
    async def fake(url, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(vast, "_fetch_transcript", fake)
    hit = make_hit("https://www.youtube.com/watch?v=HHHHHHHHHHH")
    base = hit.raw_content
    run(vast._read_transcript(hit, 9999999999.0, __import__("collections").Counter()))
    assert hit.raw_content == base
    assert hit.transcript_status == vast.TRANSCRIPT_ERROR


def test_read_transcript_skips_phase_a_hits(monkeypatch):
    calls = []

    async def fake(url, **kw):
        calls.append(url)
        return make_result(url)

    monkeypatch.setattr(vast, "_fetch_transcript", fake)
    hit = make_hit("https://www.youtube.com/watch?v=IIIIIIIIIII")
    vast._apply_transcript(hit, make_result(hit.url, method="cache"))
    run(vast._read_transcript(hit, 9999999999.0, __import__("collections").Counter()))
    assert calls == []  # fase A ja resolveu: sem refetch


# --- 4. enrich_results: fase A sem limite, fase B teto 3 ------------------------

def _patch_enrich(monkeypatch, cached_urls, live_text=True):
    async def fake_fetch(url, **kw):
        if live_text:
            return make_result(url, chars=800, method="live")
        return yt._miss("en", "sem legenda")

    def fake_peek(url):
        if url in cached_urls:
            return make_result(url, chars=700, method="cache")
        return None

    monkeypatch.setattr(vast, "_fetch_transcript", fake_fetch)
    monkeypatch.setattr(vast, "_peek_transcript", fake_peek)
    monkeypatch.setattr(vast, "ENRICH_ENABLED", False)  # sem leitura de pagina
    monkeypatch.setattr(vast, "_cascade_fetch", None)


def test_phase_a_enriches_all_selected_beyond_cap(monkeypatch):
    # 5 videos no selected, TODOS em cache: todos ganham transcricao (o fix da
    # causa (c) -- antes so [:3] entravam no yt_hits).
    urls = [f"https://www.youtube.com/watch?v=CACHE{i:07d}" for i in range(5)]
    _patch_enrich(monkeypatch, set(urls))
    hits = [make_hit(u) for u in urls]
    run(vast.enrich_results(hits, "q"))
    for hit in hits:
        assert hit.transcript_chars == 700, hit.url
        assert hit.transcript_status == vast.TRANSCRIPT_CACHE, hit.url
        assert "[transcript origin=cache" in hit.raw_content, hit.url


def test_phase_b_live_cap_unchanged(monkeypatch):
    # Nada em cache: so 3 vao a rede (YT_ENRICH_MAX intacto); o resto fica com
    # a descricao e o status explicito -- sem silencio.
    assert vast.YT_ENRICH_MAX == 3
    urls = [f"https://www.youtube.com/watch?v=LIVE{i:08d}" for i in range(5)]
    _patch_enrich(monkeypatch, set())
    hits = [make_hit(u) for u in urls]
    run(vast.enrich_results(hits, "q"))
    ok = [h for h in hits if h.transcript_status == vast.TRANSCRIPT_OK]
    absent = [h for h in hits if h.transcript_status == vast.TRANSCRIPT_ABSENT]
    assert len(ok) == 3
    assert len(absent) == 2
    for hit in absent:
        assert "[transcript" not in hit.raw_content  # so descricao, rotulada pelo status


def test_phase_b_live_miss_labels_absent(monkeypatch):
    urls = [f"https://www.youtube.com/watch?v=MISS{i:08d}" for i in range(2)]
    _patch_enrich(monkeypatch, set(), live_text=False)
    hits = [make_hit(u) for u in urls]
    run(vast.enrich_results(hits, "q"))
    for hit in hits:
        assert hit.transcript_status == vast.TRANSCRIPT_ABSENT
        assert hit.raw_content.startswith("YouTube: Titulo\ndescricao base")


def test_enrich_disabled_keeps_old_behavior(monkeypatch):
    monkeypatch.setattr(vast, "YT_ENRICH_ENABLED", False)
    monkeypatch.setattr(vast, "ENRICH_ENABLED", False)
    monkeypatch.setattr(vast, "_cascade_fetch", None)
    hit = make_hit("https://www.youtube.com/watch?v=JJJJJJJJJJJ")
    base = hit.raw_content
    run(vast.enrich_results([hit], "q"))
    assert hit.raw_content == base
    assert hit.transcript_status == ""


# --- 5. Ordenacao: pagina nunca sobrescreve transcricao -------------------------

def test_read_page_never_overwrites_transcript(monkeypatch):
    class FakePage:
        text = "PAGINA HTML ANTI-BOT"
        level = 3
        from_cache = False
        chars = 20
        reason = None

    async def fake_fetch(url):
        return FakePage()

    monkeypatch.setattr(vast, "_cascade_fetch", fake_fetch)
    monkeypatch.setattr(vast, "ENRICH_ENABLED", True)
    hit = make_hit("https://www.youtube.com/watch?v=KKKKKKKKKKK")
    vast._apply_transcript(hit, make_result(hit.url, method="cache"))
    enriched = hit.raw_content
    run(vast._read_page(hit, 9999999999.0, __import__("collections").Counter()))
    assert hit.raw_content == enriched
    assert "PAGINA HTML ANTI-BOT" not in hit.raw_content


def test_read_page_still_serves_videos_without_transcript(monkeypatch):
    class FakePage:
        text = "descricao estendida da pagina " * 20
        level = 2
        from_cache = False
        chars = 560
        reason = None

    async def fake_fetch(url):
        return FakePage()

    monkeypatch.setattr(vast, "_cascade_fetch", fake_fetch)
    monkeypatch.setattr(vast, "ENRICH_ENABLED", True)
    hit = make_hit("https://www.youtube.com/watch?v=LLLLLLLLLLL")
    run(vast._read_page(hit, 9999999999.0, __import__("collections").Counter(), gate=None))
    assert "descricao estendida da pagina" in hit.raw_content


# --- 6. Trace + prompt ----------------------------------------------------------

def test_hit_to_record_carries_transcript_fields():
    hit = make_hit("https://www.youtube.com/watch?v=MMMMMMMMMMM")
    vast._apply_transcript(hit, make_result(hit.url, method="live"))
    rec = run_trace.hit_to_record(hit, "kept")
    assert rec["transcript_origin"] == "live"
    assert rec["transcript_lang"] == "en"
    assert rec["transcript_automatic"] is None
    assert rec["transcript_chars"] == 1000
    assert rec["transcript_status"] == vast.TRANSCRIPT_OK
    assert rec["selection_verdict"] == "kept"


def test_evidence_prompt_parity_and_content():
    import gpt_researcher_integration as integ
    import run_research as runner

    assert runner.EVIDENCE_PROMPT == integ.EVIDENCE_PROMPT
    p = integ.EVIDENCE_PROMPT
    for needle in (
        "NOT verified video content",
        "ONLY what is explicitly registered as spoken content",
        "Never claim to have watched",
        "Never reconstruct commands",
        "cite THOSE sources",
        "never orders",
    ):
        assert needle in p, needle
    assert "\n\n" not in p.strip()  # um paragrafo
