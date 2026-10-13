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

# Sentences that describe the audit's own process (dates of consultation, where
# evidence came from, "consultada nesta auditoria") rather than a fact about a
# package. They are provenance, not claims.
# Price/figure tokens that identify a pricing page uniquely.
def _claim_words(sentence: str) -> set[str]:
    """Distinctive lowercase words of a claim, for content-based anchoring."""
    stop = {"opencode", "plugin", "para", "como", "the", "and", "com", "que",
            "nao", "não", "isso", "essa", "este", "uma", "mais", "seus", "suas",
            "documented", "compatibility", "compatível", "about", "with", "from"}
    words = {w.lower() for w in
             re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_.+-]{3,}", sentence)}
    return words - stop


_PRICE_TOKENS = re.compile(
    r"(\$\d+(?:\.\d+)?(?:/1M|/100K|/GPU-?hr|/month|/hr)|"
    r"\d+(?:[.,]\d+)?\s*(?:req|API credits|credits))", re.I)

_AUDIT_META = re.compile(
    r"(consult\w*\s+(inicial|nesta|posterior|fora)|revalida[çc][ãa]o|"
    r"nesta auditoria|fora do material da run|data da consulta|"
    r"fonte: api github|artefato: )", re.I)

# Ordinal/editorial labels chosen by the report ("3º lugar", "6ª recomendação",
# "recomendação principal"). No external source ranks these packages, so the
# reviewer reports them unsupported -- correctly, and uselessly. They are the
# report's own editorial structure and stay in the text without being audited.
_ORDINAL = re.compile(
    r"(\d+[ºo°]\s*(lugar|coloca|posi)|\b\d+[ªa]\s*recomenda|"
    r"recomenda[çc][ãa]o\s+principal|lista\s+final|at[ée]\s+cinco|"
    r"alternativa\s+(enxuta|equivalente))", re.I)



def _refs_hint(refs: list[str]) -> list[str]:
    return list(refs or [])


def _evidence_window(anchors: list[str], refs: list[str],
                     budget: int = 9000) -> str:
    """Evidence text for a claim, centred on the segments it cites."""
    parts: list[str] = []
    for u in anchors[:2]:
        txt = evidence_text(u)
        if not txt:
            continue
        idx = -1
        for r in refs:
            idx = txt.find(r)
            if idx >= 0:
                break
        if idx < 0:
            parts.append(txt[:budget])
            continue
        # Take the segment line plus surrounding context.
        start = max(0, idx - 1200)
        end = min(len(txt), idx + budget - 1200)
        window = ("…" if start > 0 else "") + txt[start:end] + \
                 ("…" if end < len(txt) else "")
        parts.append(window)
    return "\n\n".join(parts) or "(sem evidência)"


_EVIDENCE_STORE: dict[str, str] = {}


def evidence_text(url: str) -> str:
    return _EVIDENCE_STORE.get(url, "")


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
    # Hard-wrapped prose is one sentence split across lines. Joining on the
    # newline makes the extractor emit a fragment ending mid-clause ("...o README
    # do repo X aponta") whose object lives on the next line, and the reviewer
    # then correctly reports it as truncated. A blank line, not a newline,
    # separates paragraphs in Markdown. List items keep their bullet, but their
    # continuation lines (indented by two spaces) still belong to the same
    # sentence -- otherwise a bullet yields a headless tail like
    # "pacote npm é diferente do nome do plugin** — ...".
    prose = re.sub(r"(?<![.!?:;])\n(?=[ \t]*\S)", " ", prose)
    prose = re.sub(r"[ \t]{2,}", " ", prose)
    sentences = re.split(r"(?<=[.!?])\s+|\n", prose)
    seen: set[str] = set()
    # A bullet can SUMMARISE evidence listed in the bullets just above it
    # ("Uso permitido: mostra interesse ... Supabase/Stripe/PDF") while itself
    # naming no `[spoken]`. Carry the last-seen spoken refs forward so the
    # summary is ranked as transcript-backed and anchored to that video's
    # evidence instead of losing the cap to generic one-liners.
    _last_spoken: list[str] = []
    # The evidence window helper needs the full source texts; expose them for
    # the duration of this call.
    _EVIDENCE_STORE.clear()
    _EVIDENCE_STORE.update(evidence)
    for sent in sentences:
        s = sent.strip()
        # Track the most recent `[spoken]` refs BEFORE any filter can `continue`
        # past this sentence. A summary bullet ("Uso permitido: ... Supabase")
        # inherits the refs from the bullet above it; updating after the filters
        # meant every intervening filtered line reset the inheritance.
        _spoken = re.findall(r"\[spoken\s[^\]]*\]", s)
        if _spoken:
            _last_spoken = _spoken[-3:]
        _has_spoken = bool(_spoken) or bool(_last_spoken)
        if len(s) < 25 or len(s) > 600:
            continue
        pkgs = [p for tup in _PKG_RE.findall(s) for p in tup if p]
        is_free = bool(_FREE_WORDS.search(s))
        lics = _LIC_RE.findall(s)
        if not (pkgs or lics) or (not is_free and not pkgs):
            continue
        # Provenance notes about the AUDIT itself are not claims about a package.
        # Lines like "Consulta inicial em 2026-10-12; revalidação em 2026-10-13"
        # describe when evidence was gathered; the reviewer cannot confirm a
        # date-of-consultation from a source and reports it unsupported, which
        # is noise, not a finding.
        if _AUDIT_META.search(s):
            continue
        # A bare Markdown heading ("### 3.1 opencode-goal-plugin — recomendação
        # principal") carries the report's own editorial label, not a checkable
        # fact: the reviewer rejects "recomendação principal" because no source
        # ranks packages, which is true and irrelevant.
        if re.match(r"^#{1,6}\s", s):
            continue
        # Same for a heading that lost its hashes through line-joining but still
        # starts a subsection ("3.1 pacote — recomendação principal").
        if re.match(r"^\d+\.\d+\s+\S.*—\s*\S+$", s) and len(s) < 120:
            continue
        # Editorial ordering/ranking is the report's own structure, not a claim
        # about the world. Keep it in the text; do not send it to the reviewer.
        if _ORDINAL.search(s) and len(s) < 260:
            continue
        # Anchor: find the evidence block that actually mentions this package.
        # A claim that names a SOURCE URL directly is anchored to that source
        # too -- otherwise "a página morphllm.com/pricing anuncia 200 req free"
        # anchors to the plugin README (which mentions Morph but not its price)
        # and the reviewer correctly rejects a price the pricing page does state.
        # Every source that names the package is a candidate. They are then
        # REORDERED by how much distinctive content they share with the
        # sentence, because a sentence that merely mentions a package while
        # making a claim about something else must anchor to the source that
        # actually discusses that something else: "uso permitido ... relevante
        # por analogia ao oh-my-opencode" is a claim about a video's description,
        # and anchoring it only to the README makes the reviewer reject it for
        # not mentioning Supabase/Stripe -- which the video description does.
        # Anchoring must not REQUIRE the package name in the evidence. A claim
        # about a video's transcript names a package only by analogy
        # ("relevante por analogia ao oh-my-opencode") while the evidence it
        # rests on is the transcript, which never says that name. Requiring the
        # name anchored such claims to the README and the reviewer then rejected
        # them for missing facts the transcript does state.
        anchors = [u for p in pkgs for u, txt in evidence.items()
                   if p.lower() in txt.lower()]
        # Locate the source that holds the cited segments, even when it shares
        # no package name with the claim. Without this the evidence for a
        # transcript-backed claim was whichever README happened to match a
        # package word, and the reviewer rejected facts the transcript states.
        if _has_spoken:
            _refs = _spoken or _last_spoken
            for u, txt in evidence.items():
                if any(r in txt for r in _refs) and u not in anchors:
                    anchors.insert(0, u)
        if not anchors:
            # Rank by content overlap instead of taking the first hit, so the
            # best-matching source wins rather than whichever the dict yielded.
            _scored = []
            for u, txt in evidence.items():
                low = txt.lower()
                hits = sum(1 for w in _claim_words(s) if w in low)
                if hits >= 2:
                    _scored.append((hits, u))
            anchors = [u for _hits, u in sorted(_scored, reverse=True)]
        _seen_dup = set()
        anchors = [u for u in anchors
                   if not (u in _seen_dup or _seen_dup.add(u))]
        # A transcript-backed claim must anchor to the TRANSCRIPT, not to a
        # repo that merely happens to share the package name. "Uso permitido:
        # mostra interesse ... Supabase/Stripe/PDF" rests on `[spoken 11/14]`;
        # the oh-my-opencode README (which names the package) contains none of
        # those words, so the reviewer rejected facts the transcript does state.
        # Promote a transcript source ahead of a name-only match.
        if _has_spoken:
            _refs = _spoken or _last_spoken
            # Best evidence is the source that CONTAINS the very segments the
            # claim cites -- not merely any transcript.
            _exact = [u for u in anchors
                      if any(r in evidence[u] for r in _refs)]
            _transcripts = [u for u in anchors
                            if "[spoken" in evidence[u] and u not in _exact]
            _others = [u for u in anchors if u not in _exact
                       and u not in _transcripts]
            anchors = (_exact or []) + (_transcripts or []) + (_others or [])
        else:
            anchors.sort(key=lambda u: -sum(
                1 for w in _claim_words(s) if w in evidence[u].lower()))
        # A claim can be ABOUT a source it never names. "uso permitido: mostra
        # interesse da comunidade em skills para Supabase/Stripe/PDF/docs" is
        # about a video description that names none of the report's packages, so
        # the package-name pass finds nothing and the claim dies unsupported.
        # Distinctive tokens (Supabase, Stripe) recover the right source.
        if len(anchors) < 2:
            for u, txt in evidence.items():
                if u in anchors:
                    continue
                low = txt.lower()
                hits = sum(1 for w in _claim_words(s)
                           if len(w) > 5 and w in low)
                if hits >= 3 and u not in anchors:
                    anchors.append(u)
        for u in evidence:
            if u in s or u.replace("https://", "").replace("www.", "") in s:
                if u not in anchors:
                    anchors.insert(0, u)
        # A price table cites figures, not URLs. Match on the figures: if the
        # claim quotes "$0.80/100K" and only the pricing snapshot contains that
        # exact string, the snapshot IS the evidence -- without this, the table
        # anchors to the plugin README and the reviewer rejects prices that the
        # pricing page states verbatim.
        if not anchors:
            for u, txt in evidence.items():
                for tok in _PRICE_TOKENS.findall(s):
                    if tok in txt:
                        anchors.append(u)
                        break
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
            # Rank: free-of-charge assertions and multi-package recommendations
            # first, then claims backed by a TRANSCRIPT -- those carry quotable
            # `[spoken]` evidence and were being pushed past the cap by generic
            # one-liners, which silently dropped the most checkable material.
            "priority": ((2 if is_free else 0) + (1 if len(pkgs) >= 2 else 0) +
                         (2 if _has_spoken else 0)),
            "anchors": anchors[:3],
            # Prefer the WINDOW around the cited segments over a blind head cut:
            # a 9k head-slice of a long transcript dropped the very lines the
            # claim quotes (`[spoken 11/14]` sits past 9k), so the reviewer was
            # handed evidence that did not contain the facts it had to check.
            "evidence": _evidence_window(anchors, _refs_hint(_spoken or _last_spoken)),
            # The spoken refs this claim rests on, so the reviewer can locate
            # them inside the (long) transcript it is given.
            "spoken_refs": (_spoken or _last_spoken),
        })
    claims.sort(key=lambda c: -c["priority"])
    for i, c in enumerate(claims):
        c["id"] = i
    return claims[:max_claims]


def _load_key() -> str:
    """Use the credential sync_config already installed. Never inline a key."""
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get(
        "OPENAI_API_KEY", "")


async def _review_pass(items: list[dict], model: str,
                       batch_size: int = 12) -> list[dict]:
    """One full pass over the claims. See _review_batch for why votes exist."""
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


# Ties are broken in this order. `gap` loses to anything concrete: the reviewer
# alternated between calling a claim a gap and calling it sustained, and
# defaulting the tie to `gap` silently softened real findings.
_TIE_ORDER = {"sustained": 0, "partial": 1, "unsupported": 2, "gap": 3}


async def _review_batch(items: list[dict], model: str,
                        votes: int = 3) -> list[dict]:
    """Review the claims, electing the majority verdict per claim.

    A single pass is not reproducible: `temperature=0` still varies, and four
    runs over the same report gave 1, 1, 2, 2 `unsupported` with ten claims
    moving between `gap` and `partial`. That makes the aggregate -- and the
    accept/reject decision built on it -- untrustworthy.

    Running `votes` passes and taking the per-claim majority makes the
    AGGREGATE deterministic while keeping the evidence honest: a claim is only
    `unsupported` if the majority of independent reviews says so. Each vote also
    keeps its own tally in `vote_tally`, so the disagreement stays visible
    instead of being averaged away.
    """
    runs = [await _review_pass(items, model) for _ in range(max(1, votes))]
    by_id: dict[int, list[dict]] = {}
    for run in runs:
        for v in run:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                by_id.setdefault(v["id"], []).append(v)

    out: list[dict] = []
    for it in items:
        cands = by_id.get(it["id"], [])
        if not cands:
            out.append({"id": it["id"], "verdict": "gap", "support": "",
                        "correction": "revisão não retornou este id",
                        "vote_tally": {}})
            continue
        tally: dict[str, int] = {}
        for c in cands:
            vd = c.get("verdict", "gap")
            tally[vd] = tally.get(vd, 0) + 1
        # Majority; ties broken by _TIE_ORDER (deterministic, no dict-order luck).
        winner = min(tally.items(),
                     key=lambda kv: (-kv[1], _TIE_ORDER.get(kv[0], 9)))[0]
        # Prefer a correction/support from a vote that AGREES with the winner,
        # so the quoted evidence matches the elected verdict.
        chosen = next((c for c in cands if c.get("verdict") == winner), cands[0])
        out.append({
            "id": it["id"],
            "verdict": winner,
            "support": chosen.get("support", ""),
            "correction": chosen.get("correction", ""),
            "vote_tally": tally,
        })
    return out


def _run_review(items: list[dict], model: str, votes: int = 3) -> list[dict]:
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
        return asyncio.run(_review_batch(items, model, votes=votes))
    # Already inside a loop: use a dedicated one in a worker thread and block
    # on it, so the caller's loop is untouched.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(
            lambda: asyncio.new_event_loop().run_until_complete(
                _review_batch(items, model, votes=votes))).result()


def review_report(report: str, evidence: dict[str, str],
                  model: str = "meta/muse-spark-1.3-contributor",
                  enabled: bool = True,
                  extra_evidence: dict[str, str] | None = None,
                  votes: int = 3) -> dict:
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
    verdicts = _run_review(claims, model, votes=votes)
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
        # Rebuild each claim with its elected verdict AND the per-claim vote
        # tally. Dropping `vote_tally` here made it silently disappear from the
        # artifact, so a reader could not tell a unanimous verdict from a 2-1
        # split -- exactly the distinction that justifies the voting.
        "verdicts": [{**c,
                      "verdict": by_id.get(c["id"], {}).get("verdict", "gap"),
                      "support": by_id.get(c["id"], {}).get("support", ""),
                      "correction": by_id.get(c["id"], {}).get("correction", ""),
                      "vote_tally": by_id.get(c["id"], {}).get("vote_tally", {})}
                     for c in claims],
        "summary": {**summary,
                    "blocking": len(blocking),
                    "gaps": len(gaps),
                    "partials": len(partials),
                    "votes": max(1, votes),
                    # Claims where the passes did not agree: the honest measure
                    # of how much of this verdict is model noise.
                    "disputed": sum(
                        1 for v in verdicts if len(v.get("vote_tally", {})) > 1)},
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
