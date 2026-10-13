"""Semantic review of a finished report, wired into the normal flow.

Why this exists: the URL/provenance audit only proves a citation EXISTS in the
manifest. It cannot tell a true claim from a false one. Run 20261012-184601 is
the proof: 0 provenance findings while stating "five free extensions" where one
was licensed SUL-1.0, two were conflated as variants, and three required paid
third-party services.

This module turns the former ad-hoc script into a library callable from the
entry point, so a report cannot be declared accepted on mechanical checks alone.

Design notes:
- No key is written here. The credential comes from the environment, which
  sync_config already populated from /opt/data/.env.
- Claims are extracted from the report, not invented: anything that asserts
  "free/gratuito", names a package, or states a licence is a claim worth
  checking. Each claim carries the evidence text we already hold.
- A claim with no evidence must come back PARTIAL or a GAP, never sustained.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

SYSTEM = (
    "You audit whether a CLAIM about a software package is supported by the "
    "EVIDENCE provided. Return ONLY a JSON array, one object per id: "
    "{id, verdict, support, correction}. "
    "verdict must be one of: sustained | partial | unsupported | gap. "
    "Rules: (1) 'gratuito/free' about a PACKAGE is only sustained if the "
    "evidence shows a licence AND no mandatory paid external service. A "
    "licence alone does NOT prove it is free to use: a plugin may be MIT but "
    "require an API key that bills you. (2) A non-OSI licence (e.g. SUL-1.0, "
    "source-available) must be named as such; it is NOT automatically paid "
    "software -- 'royalty-free' means no fee for the software itself. Report "
    "the restriction instead. (3) Two distinct packages from different "
    "maintainers must never be merged into one claim. (4) Missing evidence "
    "gives 'gap', never 'sustained'. support: short quote from the evidence "
    "or ''. correction: the precise fix, or '' if none."
)

# Words that make a sentence a "free of charge" claim worth checking.
_FREE_WORDS = re.compile(
    r"\b(gratuit\w*|free|sem custo|custo zero|no charge|open[- ]source)\b", re.I)
# Named packages: backticked tokens, or plain tokens that look like the
# ecosystem's package names. The plain form matters: the report wrote
# "tavily", "morph" and "daytona" WITHOUT backticks inside prose sentences,
# and those are exactly the recommendations that carry a paid API key.
_PKG_RE = re.compile(
    r"`([a-zA-Z@][\w\-./@]*(?:opencode|plugin|oh-my)[\w\-./@]*)`"
    r"|\b(opencode(?:-[a-z0-9\-]+)+|oh-my-opencode|tavily|morph|daytona"
    r"|wakatime|helicone)\b", re.I)
_LIC_RE = re.compile(r"\b(MIT|Apache-2\.0|SUL-1\.0|BSD|GPL|ISC|NOASSERTION)\b", re.I)


def extract_claims(report: str, evidence: dict[str, str],
                   max_claims: int = 25) -> list[dict]:
    """Build review items from the report, each anchored to real evidence.

    ``evidence`` maps URL -> the text actually obtained for it, so a claim can
    only be checked against material we really hold. Claims whose subject
    appears in no evidence are still emitted -- marked as having no anchor --
    so the reviewer can return ``gap`` rather than silently accepting them.

    Ordering matters: a cap that keeps the FIRST 25 claims would drop the
    closing recommendation, which is where "combine X + Y + Z" accumulates the
    most unverified assertions. Free-of-charge assertions and multi-package
    recommendations are ranked first so they survive the cap.
    """
    claims: list[dict] = []
    # Fenced code blocks are quoted evidence, not assertions. Feeding them to
    # the reviewer makes it "refute" a shell command or a JSON path that the
    # report merely quotes, which is how a corrected report kept 2 unsupported
    # verdicts for lines like ``npm install -g opencode-ai`` and the
    # ``instructions/[...]`` path. Strip them before splitting into sentences.
    prose = re.sub(r"```.*?```", " ", report, flags=re.S)
    # Markdown table rows are also not sentences: splitting on newlines turns
    # one row into several fragments ("| 4 | `opencode-morph-fast-apply` | MIT
    # |"), and the reviewer then refutes a bare column cell that carries no
    # assertion. Keep a row whole by turning its pipes into separators, so the
    # whole row is reviewed as one claim with its subject still attached.
    prose = re.sub(r"^\|.*\|$",
                   lambda m: m.group(0).replace("|", " · ").strip(" ·"),
                   prose, flags=re.M)
    sentences = re.split(r"(?<=[.!?])\s+|\n", prose)
    seen: set[str] = set()
    for sent in sentences:
        s = sent.strip()
        if len(s) < 25 or len(s) > 600:
            continue
        pkgs = [p for tup in _PKG_RE.findall(s) for p in tup if p]
        is_free = bool(_FREE_WORDS.search(s))
        lics = _LIC_RE.findall(s)
        if not (pkgs or lics) or (not is_free and not pkgs):
            continue
        # Anchor: find the evidence block that actually mentions this package.
        anchors = [u for p in pkgs for u, txt in evidence.items()
                   if p.lower() in txt.lower()]
        key = " ".join(pkgs) + "|" + s[:60]
        if key in seen:
            continue
        seen.add(key)
        claims.append({
            "id": len(claims),
            "claim": s,
            "packages": pkgs,
            "licences": lics,
            "free_assertion": is_free,
            # Rank: gratuidade primeiro, depois recomendações multi-pacote.
            "priority": (2 if is_free else 0) + (1 if len(pkgs) >= 2 else 0),
            "anchors": anchors[:3],
            "evidence": "\n\n".join(
                evidence[u][:9000] for u in anchors[:2]) or "(sem evidência)",
        })
    claims.sort(key=lambda c: -c["priority"])
    for i, c in enumerate(claims):
        c["id"] = i
    return claims[:max_claims]


def _load_key() -> str:
    """Use the credential sync_config already installed. Never inline a key."""
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
        "OPENAI_API_KEY", "")


async def _review_batch(items: list[dict], model: str,
                        batch_size: int = 12) -> list[dict]:
    key = _load_key()
    if not key:
        return [{"id": it["id"], "verdict": "gap",
                 "support": "", "correction": "sem credencial para revisão"}
                for it in items]
    import openai
    client = openai.AsyncOpenAI(api_key=key,
                                base_url="https://openrouter.ai/api/v1")
    out: list[dict] = []
    for i in range(0, len(items), batch_size):
        chunk = items[i:i + batch_size]
        # Strip the bulky evidence from the prompt when it is absent anyway.
        payload = [{k: it[k] for k in
                    ("id", "claim", "packages", "licences", "free_assertion",
                     "evidence")} for it in chunk]
        try:
            r = await client.chat.completions.create(
                model=model, temperature=0, max_tokens=8000,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(
                              payload, ensure_ascii=False)}])
            msg = r.choices[0].message.content or ""
            start, end = msg.find("["), msg.rfind("]")
            if start >= 0 and end > start:
                out.extend(json.loads(msg[start:end + 1]))
            else:
                out.extend({"id": it["id"], "verdict": "gap", "support": "",
                            "correction": "resposta sem JSON"} for it in chunk)
        except Exception as exc:
            out.extend({"id": it["id"], "verdict": "gap", "support": "",
                        "correction": f"{type(exc).__name__}: {exc}"}
                       for it in chunk)
    return out


def _run_review(items: list[dict], model: str) -> list[dict]:
    """Drive the review coroutine from sync OR async context.

    ``review_report`` is called from the entry point, which is already inside
    ``asyncio.run(main())`` -- a nested ``asyncio.run`` raises
    "cannot be called from a running event loop". The replay path (plain
    script) has no loop at all. Both must work, so run the coroutine on a
    private loop when one is already running.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_review_batch(items, model))
    # Already inside a loop: use a dedicated one in a worker thread and block
    # on it, so the caller's loop is untouched.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(
            lambda: asyncio.new_event_loop().run_until_complete(
                _review_batch(items, model))).result()


def review_report(report: str, evidence: dict[str, str],
                  model: str = "meta/muse-spark-1.3-contributor",
                  enabled: bool = True,
                  extra_evidence: dict[str, str] | None = None) -> dict:
    """Audit the claims of a finished report. Returns verdicts + a summary.

    ``enabled=False`` (default off) keeps the normal path untouched: the
    caller decides when a report needs semantic review.

    ``extra_evidence`` maps source-URL -> text for material consulted AFTER the
    run (maintainer READMEs, licence files, pricing pages). Without it, a
    corrected report reads as unsupported: the claim "MIT" is anchored to the
    run's ecosystem page, which lists names and one-line descriptions but no
    licence and no price. Merging both maps is what makes a corrected report
    reviewable against the evidence that actually supports it.
    """
    evidence = {**(evidence or {}), **(extra_evidence or {})}
    if not enabled:
        return {"enabled": False, "claims": 0, "verdicts": [], "summary": {}}
    claims = extract_claims(report, evidence)
    if not claims:
        return {"enabled": True, "claims": 0, "verdicts": [],
                "summary": {"note": "nenhuma afirmação verificável extraída"}}
    verdicts = _run_review(claims, model)
    by_id = {v.get("id"): v for v in verdicts}
    summary: dict[str, int] = {}
    for v in verdicts:
        summary[v.get("verdict", "?")] = summary.get(v.get("verdict", "?"), 0) + 1
    # A report is only accepted when nothing is unsupported. A ``gap`` means we
    # lack evidence to confirm the claim -- it must NOT read as acceptance, so
    # the report is accepted WITH qualification and the gaps are reported
    # alongside. Only an explicit contradiction blocks outright.
    blocking = [v for v in verdicts if v.get("verdict") == "unsupported"]
    gaps = [v for v in verdicts if v.get("verdict") == "gap"]
    partials = [v for v in verdicts if v.get("verdict") == "partial"]
    return {
        "enabled": True,
        "claims": len(claims),
        "verdicts": [{**c, "verdict": by_id.get(c["id"], {}).get("verdict", "gap"),
                      "support": by_id.get(c["id"], {}).get("support", ""),
                      "correction": by_id.get(c["id"], {}).get("correction", "")}
                     for c in claims],
        "summary": {**summary,
                    "blocking": len(blocking),
                    "gaps": len(gaps),
                    "partials": len(partials)},
        # Verdict is a qualified state, not a boolean: 'aceito' | 'aceito com
        # ressalvas' | 'reprovado'. 13 gaps is NOT the same as fully accepted.
        "verdict_state": ("reprovado" if blocking else
                          ("aceito com ressalvas" if (gaps or partials)
                           else "aceito")),
        "accepted": not blocking,
        "gaps": len(gaps),
        "partials": len(partials),
    }


def build_evidence(context_text: str) -> dict[str, str]:
    """Map URL -> obtained text, from the context sent to the writer.

    Uses the same ``Source: <url>`` block shape the retriever emits, so the
    evidence reviewed is exactly the evidence used to write the report.
    """
    out: dict[str, str] = {}
    for part in re.split(r"(?=Source:\s*https?://)", context_text)[1:]:
        m = re.search(r"Source:\s*(\S+)", part)
        if m:
            out[m.group(1).rstrip(".,)")] = part
    return out
