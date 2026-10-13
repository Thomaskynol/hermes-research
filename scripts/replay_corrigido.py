#!/usr/bin/env python3
"""Replay the semantic review over the CORRECTED report.

The corrected report's claims rest on material consulted AFTER the run
(maintainer licences, READMEs, pricing pages). Feeding it only the run's
context makes every corrected claim read as unsupported -- a false positive of
the reviewer, not a defect of the report. This script rebuilds both evidence
maps from disk so the review sees exactly what the report cites.

Offline retrieval: raw.githubusercontent.com + local copies of the pricing
pages already fetched. No new research.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

REPOS = {
    "https://github.com/willytop8/OpenCode-goal-plugin": (
        "willytop8/OpenCode-goal-plugin", "main"),
    "https://github.com/morphllm/opencode-morph-plugin": (
        "morphllm/opencode-morph-plugin", "main"),
    # NOTE: opencode-morph-fast-apply's default branch is `trunk`, NOT `main`.
    # Fetching `main` returns a 14-byte "404: Not Found", which silently left
    # that package without its own evidence -- and the reviewer then correctly
    # reported "nenhuma evidência para pacote distinto opencode-morph-fast-apply".
    "https://github.com/JRedeker/opencode-morph-fast-apply": (
        "JRedeker/opencode-morph-fast-apply", "trunk"),
    "https://github.com/tavily-ai/opencode-tavily": (
        "tavily-ai/opencode-tavily", "main"),
    "https://github.com/code-yeongyu/oh-my-opencode": (
        "code-yeongyu/oh-my-opencode", "dev"),
}
# Daytona's plugin lives in a SUBDIRECTORY of the monorepo; the repo root
# README says nothing about the OpenCode plugin. Fetch the package README too.
SUBDIR_READMES = {
    "https://github.com/daytona/integrations/tree/main/packages/opencode-plugin":
        ("daytona/integrations", "main",
         "packages/opencode-plugin/README.md"),
}

# The corrected report asserts tag/branch/commit/date per package (§3.2.1). Those
# come from the GitHub API, not from a README, so they must be part of the
# evidence map or the reviewer correctly reports "sem versão/commit/data" for
# claims that are in fact sourced.
API_METADATA = {
    "https://api.github.com/repos/willytop8/OpenCode-goal-plugin":
        "willytop8/OpenCode-goal-plugin",
    "https://api.github.com/repos/morphllm/opencode-morph-plugin":
        "morphllm/opencode-morph-plugin",
    "https://api.github.com/repos/JRedeker/opencode-morph-fast-apply":
        "JRedeker/opencode-morph-fast-apply",
    "https://api.github.com/repos/tavily-ai/opencode-tavily":
        "tavily-ai/opencode-tavily",
    "https://api.github.com/repos/code-yeongyu/oh-my-opencode":
        "code-yeongyu/oh-my-opencode",
}

# Version metadata is snapshot to disk: the API is rate-limited to 60 req/hour
# per IP, so a replay that re-fetches is not reproducible, and the values also
# MOVE (oh-my-opencode went v5.1.31 -> v5.1.32 within a day). The snapshot is
# the evidence; refresh it deliberately, not on every replay.
CACHE = WORKDIR / "runs/replay_corrigido_evidence.json"
CACHE_DATA: dict = {}


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    try:
        CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    except Exception:
        pass

# Snapshots live under runs/pricing_snapshots/, NOT /tmp: the scratch dir is
# pruned, which silently left the pricing claims without evidence. The Morph page
# is JS-rendered and rate-limits plain curl (429), so its snapshot may legitimately
# lack the price table -- see the MISSING note below rather than pretending.
PRICING = {
    # Morph is JS-rendered and rate-limits curl, so its evidence is the text
    # dumped from a real browser render, not an HTML fetch.
    "https://www.morphllm.com/pricing":
        "runs/pricing_snapshots/morph_pricing.txt",
    "https://tavily.com/pricing":
        "runs/pricing_snapshots/tavily_pricing.html",
    "https://www.daytona.io/pricing":
        "runs/pricing_snapshots/daytona_pricing.html",
}
# Tokens that must appear in a pricing snapshot for it to count as evidence of
# the prices the report cites. A snapshot missing them is reported, not used.
PRICING_REQUIRED = {
    "https://www.morphllm.com/pricing": ("morph-v3-fast", "200 req", "$9.06"),
    "https://tavily.com/pricing": ("1,000 API credits", "Pay As You Go"),
    "https://www.daytona.io/pricing": ("Start for free", "0.0504"),
}


def fetch(url: str, timeout: int = 25) -> str:
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), url],
                           capture_output=True, text=True, timeout=timeout + 10)
        return r.stdout
    except Exception:
        return ""


def build_extra_evidence() -> dict[str, str]:
    global CACHE_DATA
    CACHE_DATA = _load_cache()
    ev: dict[str, str] = {}
    for base, (repo, br) in REPOS.items():
        readme = fetch(f"https://raw.githubusercontent.com/{repo}/{br}/README.md")
        lic = fetch(f"https://raw.githubusercontent.com/{repo}/{br}/LICENSE.md")
        lic2 = lic or fetch(
            f"https://api.github.com/repos/{repo}/license")
        if readme or lic:
            # 8k, not 2k: the goal-plugin README documents the CLI install
            # command ("opencode plugin opencode-goal-plugin@0.11.0 --global")
            # at byte ~7.5k. A 2k window silently dropped it and the reviewer
            # then correctly reported "não mostra comando de instalação" for a
            # command that IS in the source.
            ev[base] = (readme or "")[:8000] + "\n\n" + (lic2 or "")[:2000]
    for base, (repo, br, path) in SUBDIR_READMES.items():
        txt = fetch(f"https://raw.githubusercontent.com/{repo}/{br}/{path}")
        if txt:
            ev[base] = txt[:8000]
    for url, repo in API_METADATA.items():
        cached = CACHE_DATA.get(url)
        if cached:
            meta, tags, head = cached["meta"], cached["tags"], cached["head"]
        else:
            meta = fetch(f"https://api.github.com/repos/{repo}")
            tags = fetch(f"https://api.github.com/repos/{repo}/tags?per_page=1")
            head = fetch(f"https://api.github.com/repos/{repo}/commits")
            if meta and '"message"' not in meta[:60]:
                CACHE_DATA[url] = {"meta": meta, "tags": tags, "head": head}
        # Unauthenticated api.github.com allows 60 requests/hour for the whole
        # IP. Running the replay a few times exhausts it, and the endpoints then
        # answer with a rate-limit body -- which made the reviewer reject the
        # §3.2.1 version table as "no evidence" for data that WAS sourced.
        # Detect that and say so explicitly instead of feeding an error page in
        # as evidence.
        if '"rate limit' in meta.lower() or '"message": "API rate limit' in meta:
            print(f"  ! api.github.com rate-limited; §3.2.1 values not "
                  f"re-verifiable this run for {repo}", flush=True)
            meta = ""
        if meta:
            # Keep only the fields the report cites, so the reviewer can match
            # tag/branch/commit/date without the payload noise.
            try:
                d = json.loads(meta)
                brief = {
                    "default_branch": d.get("default_branch"),
                    "pushed_at": d.get("pushed_at"),
                    "license": (d.get("license") or {}).get("spdx_id"),
                }
            except Exception:
                brief = {"raw": meta[:800]}
            # Prefix with the repo slug and the version-bearing tokens: the
            # claim extractor anchors a claim to a source by searching for the
            # package name inside the evidence text, so the metadata blob must
            # contain the name it is evidence FOR.
            ev[url] = (f"GitHub metadata for {repo}\n" +
                       json.dumps(brief, ensure_ascii=False) + "\n\n" +
                       "tags: " + tags[:600] + "\n\ncommits: " + head[:900])
            # Also anchor the README-derived entry to the API url, since a
            # claim about version/commit names the package, not the API host.
            for base, (r2, _br) in REPOS.items():
                if r2 == repo:
                    ev[base] = ev.get(base, "") + "\n\n" + ev[url]
    _save_cache(CACHE_DATA)
    for url, local in PRICING.items():
        lp = WORKDIR / local if not local.startswith("/") else Path(local)
        txt = ""
        if lp.exists() and lp.stat().st_size > 1000:
            txt = lp.read_text(encoding="utf-8", errors="ignore")
        else:
            # Prefer the rendered-text snapshot; fall back to the HTML fetch.
            alt = lp.with_suffix(".html")
            if alt.exists() and alt.stat().st_size > 1000:
                txt = alt.read_text(encoding="utf-8", errors="ignore")
        if not txt:
            txt = fetch(url)
        # Only count a snapshot as evidence if it actually contains the figures
        # the report quotes. A 429 page or a JS shell must not be passed off as
        # proof of a price.
        need = PRICING_REQUIRED.get(url, ())
        have = [tok for tok in need if tok in txt]
        if need and len(have) < len(need):
            missing = [tok for tok in need if tok not in txt]
            print(f"  ! {url}: snapshot missing {missing} -- preços desta "
                  f"página NÃO revalidados neste replay", flush=True)
            if not have:
                continue
        if txt:
            ev[url] = txt[:8000]
    return ev


# Two knobs, both off by default so behaviour only changes when asked:
#   REPLAY_VOTES  - majority votes per claim (1 = old single-pass behaviour)
#   REPLAY_SEED   - set to make the replay deterministic
VOTES = int(os.environ.get("REPLAY_VOTES", "3"))
SEED = os.environ.get("REPLAY_SEED", "").strip()


def main() -> int:
    # Load the credential the same way the entry point does: sync_config
    # exports OPENROUTER_API_KEY/OPENAI_API_KEY from /opt/data/.env. Without it
    # the reviewer returns "sem credencial" for every claim and the replay
    # proves nothing.
    import sync_config
    sync_config.sync()
    import semantic_review as sr

    run_ctx = (WORKDIR / "runs/20261012-184601-Pesquise_extensões_gratuitas_p"
               / "context.json")
    report = (WORKDIR / "output/RELATORIO_CORRIGIDO_184601.md").read_text(
        encoding="utf-8")
    original = (WORKDIR / "runs/20261012-184601-Pesquise_extensões_gratuitas_p"
                / "report.md").read_text(encoding="utf-8")
    base_ev = sr.build_evidence(
        json.loads(run_ctx.read_text(encoding="utf-8"))["items"][0]["text"])
    extra = build_extra_evidence()

    print(f"evidencia da run: {len(base_ev)} fontes | "
          f"evidencia complementar: {len(extra)} fontes", flush=True)
    print(f"votos por claim: {VOTES} | seed: {SEED or '(sem seed)'}", flush=True)

    # The corrected file carries an audit appendix (§7-§9) that QUOTES the
    # evidence as prose. Feeding it to the reviewer makes it re-audit its own
    # audit trail, and those lines crowd out the report body through the claim
    # cap. Review the report itself; the appendix is the record of the fixes.
    cut = report.find("## 7. Auditoria")
    body = report[:cut] if cut > 0 else report
    assert "e variante `opencode-morph-fast-apply`" not in body, (
        "the report body still contains the original's fused heading -- "
        "the corrected §3 was not fully applied")

    results = {}
    for label, text in (("ORIGINAL", original), ("CORRIGIDO", body)):
        res = sr.review_report(text, base_ev, enabled=True,
                               extra_evidence=extra, votes=VOTES)
        results[label] = res
        print(f"\n=== {label} ===")
        print("summary:", res["summary"])
        print("verdict_state:", res["verdict_state"],
              "| accepted:", res["accepted"])
        for v in res["verdicts"]:
            if v["verdict"] in ("unsupported", "gap", "partial"):
                print(f"  [{v['verdict'].upper()}] {v['claim'][:100]}")
                if v.get("correction"):
                    print(f"     -> {v['correction'][:150]}")

    out = WORKDIR / "runs/replay_corrigido_semantic.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nsalvo: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
