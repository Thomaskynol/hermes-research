#!/usr/bin/env python3
"""Adaptive research coordinator: plan -> collect -> assess -> close gaps.

Real coordinator logic, deterministic at its boundaries. Everything the
outside world provides (search/fetch/assess/write/audit/clock) is injected;
the coordinator itself is NEVER mocked in tests — it is the unit under test.

Round discipline (each round recorded: target gaps, ops, new evidence,
coverage delta, insufficiencies, decision):
  1. recover plan / evidence / pending from state (never trusts memory only);
  2. assess coverage + contradictions via the injected assessor
     (default: no evaluations -> insufficiency preserved, never fabricated);
  3. prioritise gaps by impact x expected gain (assessor hints, stable order);
  4. select specific ops (gap_query / alt_channel / read_source), varying the
     channel when the previous attempt on that gap failed or added nothing;
  5. execute within budget/time/round limits (run_budget + controlled clock);
  6. incorporate (distinct excerpts of one URL preserved; corpus never
     silently swapped; external content has no authority over the rules);
  7. persist atomically + checkpoint; decide continue/end with an explicit
     motive SEPARATE from coverage status and from the semantic verdict.

GPT Researcher (installed 0.16.0, site-packages/gpt_researcher) is only ever
encapsulated: at most ONE conduct_research() as the initial sweep, never
repeated with the original question — later rounds use targeted ops
(gap queries, alternate channels, specific source reads) and keep the
accumulated material. Offline tests inject fakes; the real-path wiring lives
in the production entrypoint (gpt_researcher_integration._adaptive_main).

Stop motives: criteria_ok | saturation | rounds | budget | time | blocked |
failure. Saturation with pending gaps is partial. Legacy flow_end is never
used here and never proves completeness. No fabricated ops for counters:
recorded ops == executed ops. Tokens/costs are measured only from real data,
otherwise recorded as "unknown".
"""
from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlsplit

import adaptive_planner as _planner
import adaptive_state as _state
import coverage_ledger as _ledger
import depth_profiles as _profiles
import research_counters as _counters
import run_budget as _run_budget

try:
    import run_checkpoint as _checkpoint
except ImportError:  # pragma: no cover - stdlib test path always has it
    _checkpoint = None

CHANNELS = ("web", "github", "arxiv", "youtube")

ADAPTIVE_ROUNDS = {"light": 2, "medium": 3, "hard": 4, "deep": 6}
ADAPTIVE_MODEL_CALLS = {"light": 8, "medium": 16, "hard": 32, "deep": 64}


class TransportError(RuntimeError):
    """Boundary failure (search/fetch/model transport) — never favourable."""


def resolve_adaptive(profile: str = "light",
                     overrides: dict | None = None) -> dict:
    """Resolved adaptive config: depth profile + independent round/model/time
    knobs. Records every applied value for the run record."""
    ov = dict(overrides or {})
    adaptive = {}
    for key in ("max_rounds", "max_model_calls", "max_ops_per_round",
                "time_s", "concurrency"):
        if key in ov:
            try:
                adaptive[key] = int(ov[key])
            except (TypeError, ValueError):
                raise ValueError(f"[ADAPTIVE] override {key} must be integer")
    depth_ov = {k: v for k, v in ov.items()
                if k in _profiles.ALLOWED_OVERRIDES}
    resolved = _profiles.resolve(profile, depth_ov)
    canonical = resolved["profile"]
    resolved["max_rounds"] = adaptive.get("max_rounds",
                                          ADAPTIVE_ROUNDS[canonical])
    resolved["max_model_calls"] = adaptive.get(
        "max_model_calls", ADAPTIVE_MODEL_CALLS[canonical])
    resolved["max_ops_per_round"] = adaptive.get(
        "max_ops_per_round", resolved["DEEP_RESEARCH_BREADTH"])
    resolved["time_s"] = adaptive.get("time_s",
                                      resolved["budget"].get("time_s", 600))
    resolved["concurrency"] = adaptive.get(
        "concurrency", resolved["DEEP_RESEARCH_CONCURRENCY"])
    if resolved["max_rounds"] < 0 or resolved["max_model_calls"] < 0:
        raise ValueError("[ADAPTIVE] max_rounds/max_model_calls must be >= 0")
    if resolved["concurrency"] < 1:
        raise ValueError("[ADAPTIVE] concurrency must be >= 1")
    resolved["adaptive"] = True
    return resolved


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8",
                                              "replace")).hexdigest()[:16]


def _visible_text(raw: str) -> tuple[str, int]:
    """Extrai texto visivel de HTML cru (uma linha gigante de markup).

    Paginas Next.js/SSR chegam como HTML bruto: head, scripts e CSS ocupam
    os primeiros milhares de chars e o corte head-only vira metadado, nunca
    conteudo. Remove blocos <head>/<script>/<style> inteiros, depois as tags,
    decodifica entidades e colapsa espacos. So atua quando o texto parece
    HTML (`<html`, `<head>` ou `<!DOCTYPE`); texto simples/markdown passa
    intacto. Retorna (texto, chars_removidos).
    """
    low = raw.lower()
    if "<html" not in low and "<head" not in low and "<!doctype" not in low:
        return raw, 0
    import re as _re
    import html as _html
    no_block = _re.sub(r"<(head|script|style)\b.*?</\1\s*>", " ",
                       raw, flags=_re.DOTALL | _re.IGNORECASE)
    no_tags = _re.sub(r"<[^>]+>", " ", no_block)
    text = _re.sub(r"[ \t\xa0]+", " ", _html.unescape(no_tags))
    text = _re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text).strip()
    return text, max(0, len(raw) - len(text))


def _substantive_excerpt(text: str, limit: int) -> tuple[str, int]:
    """Head excerpt skipping markdown/HTML boilerplate lines.

    README heads are often badges/logos/nav (shields, <img>, empty
    headers): a head-only cut shows the model boilerplate instead of
    substance. Skipped lines are generic document hygiene (image-only,
    badge-link, pure-tag, empty-header lines), never content selection
    by topic. Returns (excerpt, stripped_chars).
    """
    raw = text or ""
    raw, html_stripped = _visible_text(raw)
    kept: list[str] = []
    stripped = html_stripped
    for line in raw.splitlines():
        s = line.strip()
        if not s or set(s) <= set("#-_*|> "):
            stripped += len(line) + 1
            continue
        low = s.lower()
        if low.startswith(("<div", "<img", "<p ", "<p>", "<br", "<a ",
                            "<!--", "</div", "</p", "<h1", "<hr")):
            stripped += len(line) + 1
            continue
        nospace = "".join(s.split())
        if nospace.startswith("![") or nospace.startswith("[!["):
            stripped += len(line) + 1
            continue
        if "img.shields.io" in low or "shields.io" in low:
            stripped += len(line) + 1
            continue
        kept.append(line)
    body = "\n".join(kept)
    excerpt = body[:limit]
    stripped += max(0, len(body) - len(excerpt))
    return excerpt, stripped


def classify_hit(state: dict, url: str, text: str) -> str:
    """new_useful | confirmed | duplicate | nogain (no fabrication).

    Distinct excerpts of one URL are preserved as separate segments; the
    ledger-facing evidence map concatenates them with a separator.
    """
    text = text or ""
    if not text.strip():
        return "nogain"
    digest = _content_hash(text)
    prior = [s for s in state["segments"] if s.get("url") == url]
    if any(s.get("sha") == digest for s in prior):
        return "duplicate"
    if prior:
        return "new_useful"  # same URL, distinct excerpt -> preserved
    for seg in state["segments"]:
        if seg.get("sha") == digest and seg.get("url") != url:
            # Identical bytes on another URL prove republication/duplication,
            # never independent confirmation (independence unknown).
            # shortcut: sem análise de proveniência, independência desconhecida.
            return "duplicate"
    known_texts = {s.get("excerpt", "") for s in state["segments"]}
    if text in known_texts:
        return "duplicate"
    return "new_useful"


_SAME_REPO_LINK_LIMIT = 4
_URL_FINDER = re.compile(r"https?://[^\s)\"'<>`]+")


def _extract_same_repo_links(text: str, repo_url: str,
                             limit: int = _SAME_REPO_LINK_LIMIT) -> list[str]:
    """Links do mesmo repositório GitHub encontrados no texto incorporado.

    Bounded (≤4 por fonte): alimenta ``discovery candidates`` para que
    ``select_ops`` os busque via ``read_source`` — "acompanhar referências"
    (§8 da modelagem). Só o mesmo ``owner/name``; a própria URL é excluída.
    """
    try:
        parts = urlsplit(str(repo_url or ""))
        segs = [s for s in parts.path.split("/") if s]
        if parts.hostname != "github.com" or len(segs) < 2:
            return []
        prefix = f"https://github.com/{segs[0]}/{segs[1]}".lower()
    except Exception:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in _URL_FINDER.findall(text or ""):
        cleaned = match.rstrip(".,;:")
        low = cleaned.lower().rstrip("/")
        if not low.startswith(prefix) or low == prefix:
            continue
        if low in seen:
            continue
        seen.add(low)
        found.append(cleaned)
        if len(found) >= max(1, int(limit)):
            break
    return found


def incorporate(state: dict, url: str, text: str, op_id: str,
                round_no: int, qualification: dict | None = None) -> str:
    """Add obtained material; returns the classification. Duplicates are
    reported, not stored twice; distinct excerpts accumulate."""
    kind = classify_hit(state, url, text or "")
    if kind in ("new_useful", "confirmed"):
        prior = [s for s in state["segments"] if s.get("url") == url]
        digest = _content_hash(text or "")
        state["segments"].append({
            "url": url, "excerpt": text, "sha": digest,
            "op_id": op_id, "round": round_no,
        })
        prev = state["evidence"].get(url, "")
        state["evidence"][url] = (prev + "\n--- segment ---\n" + text
                                  if prev else text)
        if qualification is not None:
            state["qualification"][url] = dict(qualification)
        state["consumption"]["docs"] += 1
        # Counters: obtained/usable are observed here (content really came
        # back + qualification allows it). Metadata/video-without-transcript
        # never increments obtained (research_counters enforces it).
        _counters.record_obtained(state, url, text or "", qualification)
        _counters.record_usable(state, url, qualification)
        if prior:
            _counters.register_relation(
                state, url, url, "version",
                f"trecho distinto da mesma URL ({len(prior)} anterior(es))")
        # Concluída nunca volta ao pool: virar evidência remove de candidates.
        try:
            cands = state.get("discovery", {}).get("candidates", [])
            if url in cands:
                cands.remove(url)
        except Exception:
            pass
        # Link-following (§8 "acompanhar referências"): evidência de repo
        # GitHub pode apontar p/ arquivos/docs do mesmo repo (blob URLs,
        # docs). Extração bounded p/ discovery candidates; select_ops os
        # busca via read_source após falha/nogain. Nunca re-obtém o contido.
        try:
            if state.get("discovery", {}).get("open"):
                for link in _extract_same_repo_links(text or "", url):
                    cands = state["discovery"].setdefault("candidates", [])
                    if link not in cands and link not in state["evidence"]:
                        cands.append(link)
                        state["notes"].append(
                            f"link-following: {link[:80]} (de {url[:60]})")
        except Exception as exc:
            state["notes"].append(f"link-following skipped: {exc}")
    elif kind == "duplicate":
        digest = _content_hash(text or "")
        same = next((s for s in state["segments"]
                     if s.get("sha") == digest), None)
        if same and same.get("url") != url:
            _counters.register_relation(
                state, url, same.get("url", ""), "duplicate",
                "bytes idênticos em outra URL (republicação; independência "
                "desconhecida)")
    return kind


def _gap_hints(evaluation: dict) -> tuple[float, float]:
    try:
        impact = float(evaluation.get("impact", 1))
    except (TypeError, ValueError):
        impact = 1.0
    try:
        gain = float(evaluation.get("expected_gain", 1))
    except (TypeError, ValueError):
        gain = 1.0
    return max(0.0, impact), max(0.0, gain)


def prioritize_gaps(gaps: list[dict]) -> list[dict]:
    """Order by impact x expected gain (stable; no name-based rules)."""
    scored = []
    for i, gap in enumerate(gaps):
        impact, gain = _gap_hints(gap)
        scored.append((-impact * gain, i, gap))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [g for _, _, g in scored]


def _model_remaining(state: dict, resolved: dict) -> int:
    try:
        return int(resolved.get("max_model_calls", 0) or 0) - int(
            state.get("consumption", {}).get("model_calls", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _check_model_budget(state: dict, resolved: dict) -> bool:
    """True when one more model-boundary call is allowed."""
    try:
        limit = int(resolved.get("max_model_calls", 0) or 0)
    except (TypeError, ValueError):
        return False
    used = int(state.get("consumption", {}).get("model_calls", 0) or 0)
    return used < limit


def _note_model_call(state: dict) -> None:
    state["consumption"]["model_calls"] = int(
        state.get("consumption", {}).get("model_calls", 0) or 0) + 1


def _update_ledger_counts(state: dict, ledger) -> None:
    """Observed stage counts from real events only (never inferred).

    The six-stage contract lives in ``state['counters']`` (document units):
    discovered/obtained/usable/analyzed/used_in_synthesis/cited. The ledger
    keeps its own stage names (qualified/used) and receives the mapped values
    when the counter structure has observed events; otherwise the legacy
    evidence/evaluation view is used (no regression for old states).
    """
    try:
        snapshot = _counters.counters_snapshot(state)
        counts = snapshot.get("counts", {})
        if any(int(counts.get(s, 0) or 0) for s in _counters.STAGES):
            ledger.set_observed_counts({
                "discovered": counts.get("discovered", 0),
                "obtained": counts.get("obtained", 0),
                "qualified": counts.get("usable", 0),
                "analyzed": counts.get("analyzed", 0),
                "used": counts.get("used_in_synthesis", 0),
                "cited": counts.get("cited", 0),
            })
            return
        ev = state.get("evidence", {}) or {}
        qual = state.get("qualification", {}) or {}
        cands = state.get("discovery", {}).get("candidates", []) or []
        evals = state.get("evaluations", []) or []
        obtained = sum(1 for t in ev.values()
                       if isinstance(t, str) and t.strip())
        qualified = sum(1 for u in ev if u in qual)
        analyzed_urls: set[str] = set()
        used_urls: set[str] = set()
        for e in evals:
            if not isinstance(e, dict):
                continue
            for r in (e.get("references", []) or []):
                u = (r or {}).get("url", (r or {}).get("doc_id", ""))
                if isinstance(u, str) and u:
                    analyzed_urls.add(u)
                    if e.get("state") in ("covered", "partial"):
                        used_urls.add(u)
        report_text = (state.get("report", {}) or {}).get("text", "") or ""
        cited = sum(1 for u in set(list(ev) + list(cands))
                  if u and u in report_text)
        ledger.set_observed_counts({
            "discovered": len(set(list(ev) + list(cands))),
            "obtained": obtained,
            "qualified": qualified,
            "analyzed": len(analyzed_urls),
            "used": len(used_urls),
            "cited": cited,
        })
    except Exception:
        pass


def select_ops(state: dict, gaps: list[dict], cap: int) -> list[dict]:
    """One specific op per top gap; vary channel/target after flat attempts.

    Identical queries are never repeated after a useful gain that did not
    resolve the gap: the follow-up varies the channel and marks the
    refinement so the budget is not spent on byte-identical requests.
    """
    ops = []
    seen_targets: set[tuple] = set()
    for gap in gaps[:max(0, cap)]:
        cid = gap.get("criterion_id", "")
        attempts = state["attempts"].get(cid, [])
        last_channel = attempts[-1].get("channel") if attempts else None
        last_outcome = attempts[-1].get("outcome") if attempts else None
        n = len(attempts)
        unfetched = [c for c in state["discovery"].get("candidates", [])
                     if c not in state["evidence"]]
        base_label = gap.get("label", cid)
        base_q = f"{state['question']} — {base_label}"
        if unfetched and (attempts and last_outcome in ("failed", "nogain")):
            kind, channel = "read_source", (last_channel or CHANNELS[0])
            target = unfetched[0]
        elif not attempts:
            kind, channel = "gap_query", CHANNELS[0]
            target = base_q
        elif last_outcome in ("failed", "nogain", "duplicate", "time",
                              "budget"):
            idx = (CHANNELS.index(last_channel) + 1) % len(CHANNELS) \
                if last_channel in CHANNELS else 1
            kind, channel = "alt_channel", CHANNELS[idx]
            target = f"{base_q} (canal {channel}, tentativa {n})"
        elif last_outcome in ("new_useful", "confirmed"):
            # Useful gain without resolution: do not repeat the byte-identical
            # query; vary channel + mark refinement.
            idx = (CHANNELS.index(last_channel) + 1) % len(CHANNELS) \
                if last_channel in CHANNELS else 1
            kind, channel = "alt_channel", CHANNELS[idx]
            target = f"{base_q} (aprofundamento {n}, canal {channel})"
        else:
            kind, channel = "gap_query", (last_channel or CHANNELS[0])
            target = f"{base_q} (tentativa {n})" if n else base_q
        # Never emit byte-identical (target, channel) twice in one batch.
        key = (target, channel, kind)
        suffix = 0
        while key in seen_targets:
            suffix += 1
            target = f"{target} #{suffix}"
            key = (target, channel, kind)
        seen_targets.add(key)
        op_id = f"r{len(state['rounds'])}-{cid}-{len(attempts)}"
        ops.append({"op_id": op_id, "kind": kind, "channel": channel,
                    "target": target, "criterion_id": cid,
                    "status": "in-progress"})
    return ops


def _default_assess(plan, evidence, qualification) -> list:
    """Default assessor: no evaluations (insufficiency preserved, never mapped
    by heuristics). Real deployments inject a model-backed assessor."""
    return []


def _default_writer(view: dict) -> tuple[str, dict]:
    """Deterministic fallback synthesis (explicitly partial).

    This template only renders criteria states/justifications; it does NOT
    synthesize the corpus body. It must never claim full-corpus processing.
    Real deployments inject a model-backed writer; this stays as an
    explicitly-identified fallback when the model budget is exhausted or
    the writer transport fails.
    """
    lines = [f"# {view['question']}", ""]
    cov = view.get("question_coverage", {})
    lines.append(f"Coverage: {cov.get('status', '?')} "
                 f"(proportion={cov.get('proportion')}) — "
                 f"stop: {view.get('stop', {}).get('reason', '?')}.")
    lines.append("")
    for crit in cov.get("criteria", []):
        refs = "; ".join(r.get("url", "") for r in crit.get("references", []))
        lines.append(f"## {crit.get('label', crit.get('id'))} "
                     f"[{crit.get('state')}]")
        lines.append(crit.get("justification") or "not investigated.")
        if refs:
            lines.append(f"Refs: {refs}")
        lines.append("")
    gaps = cov.get("gaps", [])
    if gaps:
        lines.append("Insufficient / pending: " +
                     ", ".join(g.get("criterion_id", "?") for g in gaps))
    lines.append("")
    lines.append("_Fallback parcial determinístico: template por critérios; "
                 "corpo do corpus não sintetizado aqui._")
    return "\n".join(lines), {"included_urls": sorted(view.get("evidence", {})),
                              "cuts": ("fallback parcial: template imprime "
                                       "apenas estados/justificativas; sem "
                                       "síntese do corpo do corpus"),
                              "fallback": True}


def _extract_json(raw_s: str):
    """Parse model JSON tolerating fences/prose around it (no new calls).

    Real models often wrap the payload in ```json fences or add a short
    preamble; rejecting that as invalid wastes budget and fails runs for a
    formatting detail. Extraction never invents content: it parses a
    substring of the actual response.
    """
    import json as _json
    import re as _re
    text = (raw_s or "").strip()
    fence = _re.search(r"```(?:json)?\s*(.*?)\s*```", text, _re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return _json.loads(text)
    except Exception:
        pass
    decoder = _json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except Exception:
                continue
    raise ValueError("no JSON value found in model response")


def make_model_assessor(model_client, max_docs: int = 24,
                        excerpt_chars: int = 1200,
                        json_budget: int = 12000):
    """Model-backed assessor injectable at the boundary.

    Receives (plan, evidence, qualification, attempts?) and returns a
    validated structured list. The model sees the plan, the REALLY
    selected material (truncated excerpts), qualification and attempt
    history. Return is validated (criterion/state/justification/origin/
    references); invalid entries are dropped (insufficiency preserved,
    never fabricated). Insufficiency/contradiction/failure preserved.
    Transport failures propagate as TransportError.

    Selection (auditable, per call): up to max_docs COMPLETE units
    (never an arbitrary JSON slice), each with url/excerpt/sha/status/
    cuts. Order prioritizes not-yet-sent material (so later rounds with
    >24 docs evaluate new evidence in bounded batches, never the same
    fixed prefix), then insertion order. The exact selection (urls,
    hashes, excerpts, cuts) is exposed as assess.last_selection for the
    caller to validate references against (storage outside the selection
    never justifies covered in that call). Open-discovery proposals
    (propose_entity) are preserved for plan versioning.
    """
    import json as _json

    _sent: set[str] = set()

    def assess(plan, evidence, qualification, attempts=None):
        evidence = dict(evidence or {})
        qualification = dict(qualification or {})
        attempts = dict(attempts or {})
        # Order: unsent first (new material from later rounds reaches the
        # model in bounded batches), then already-sent, each in insertion
        # order (stable; no name-based rules). No fixed prefix: batches
        # rotate as _sent grows.
        ordered = [u for u in evidence if u not in _sent] + \
                  [u for u in evidence if u in _sent]
        # Real selection: complete units within the JSON budget.
        items, cuts = [], []
        used_budget = 0
        for url in ordered[:max_docs]:
            text = evidence.get(url) or ""
            qual = qualification.get(url, {}) or {}
            excerpt, _stripped = _substantive_excerpt(text, excerpt_chars)
            if _stripped:
                cuts.append(f"boilerplate ignorado {url}: {_stripped} chars")
            if len(text or "") > len(excerpt) + _stripped:
                cuts.append(f"truncado {url} "
                            f"{len(text)}->{len(excerpt)} chars")
            entry = {
                "url": url,
                "excerpt": excerpt,
                "sha": _content_hash(excerpt or ""),
                "raw_chars": len(text or ""),
                "status": qual.get("status", "?"),
                "excluded": bool(qual.get("excluded", False)),
            }
            blob = _json.dumps(entry, ensure_ascii=False)
            if used_budget + len(blob) > json_budget and items:
                cuts.append(f"teto JSON {json_budget} chars atingido; "
                            f"{len(ordered)-len(items)} fontes fora")
                break
            items.append(entry)
            used_budget += len(blob)
            _sent.add(url)
        if len(ordered) > len(items):
            cuts.append(f"lote {len(items)}/{len(ordered)} fontes nesta "
                        f"chamada; restante em lotes posteriores")
        selection = {"urls": [i["url"] for i in items],
                     "hashes": {i["url"]: i["sha"] for i in items},
                     "raw_chars": {i["url"]: i["raw_chars"] for i in items},
                     "cuts": "; ".join(cuts) if cuts else "sem cortes",
                     "batch": f"{len(items)}/{len(ordered)}"}
        assess.last_selection = selection
        prompt = (
            "Você avalia evidências contra um plano. Retorne SOMENTE JSON: "
            "uma lista de avaliações.\n"
            f"Plano: {_json.dumps(plan, ensure_ascii=False)[:6000]}\n"
            f"Material selecionado: {_json.dumps(items, ensure_ascii=False)}\n"
            f"Tentativas: {_json.dumps(attempts, ensure_ascii=False)[:3000]}\n"
            "Cada avaliação: {criterion_id, entity_id?, state "
            "(covered|partial|insufficient|contradictory|blocked), "
            "justification, origin, references:[{url}], "
            "propose_entity?: {entity:{id,label?}, criteria?}}. "
            "Sem evidência utilizável -> insufficient/blocked; "
            "divergência real -> contradictory; nunca invente cobertura. "
            "Referencie SOMENTE urls do material selecionado acima."
        )
        try:
            raw = model_client(prompt)
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"assessor transport failed: {exc}")
        raw_s = str(raw or "").strip()
        try:
            parsed = _extract_json(raw_s)
        except Exception as exc:
            raise TransportError(f"assessor returned invalid JSON: {exc}")
        if isinstance(parsed, dict) and isinstance(
                parsed.get("evaluations"), list):
            parsed = parsed["evaluations"]
        if not isinstance(parsed, list):
            raise TransportError("assessor must return a JSON list")
        out = []
        known_c = {c.get("id") for c in (plan or {}).get("criteria", []) or []}
        for ev in parsed:
            if not isinstance(ev, dict) or ev.get("criterion_id") not in known_c:
                continue
            if ev.get("state") not in ("covered", "partial", "insufficient",
                                       "contradictory", "blocked"):
                continue
            if not str(ev.get("justification", "") or "").strip():
                continue
            if not str(ev.get("origin", "") or "").strip():
                continue
            refs = ev.get("references", []) or []
            if ev.get("state") in ("covered", "partial") and not refs:
                continue
            entry = {
                "criterion_id": ev["criterion_id"],
                "entity_id": ev.get("entity_id"),
                "state": ev["state"],
                "justification": ev["justification"],
                "origin": ev["origin"],
                "references": refs if isinstance(refs, list) else [],
            }
            # Open discovery atravessa o assessor de aplicação (sem fixar
            # nomes): proposta validada no versionamento do plano.
            if isinstance(ev.get("propose_entity"), dict):
                entry["propose_entity"] = ev["propose_entity"]
            out.append(entry)
        return out

    assess.last_selection = None  # type: ignore[attr-defined]
    return assess


def make_model_writer(model_client, max_chars: int = 12000):
    """Model-backed synthesis in Portuguese from the real corpus.

    Receives the coordinator view (question/plan/evidence/coverage) and
    returns (text, selection). Selection records included_urls actually
    used and cuts actually applied (truncation/budget). Verdict↔text link
    is preserved by the caller via audited_sha. On transport failure the
    caller falls back to _default_writer (explicitly identified).
    """
    import json as _json

    def write(view: dict):
        question = view.get("question", "")
        cov = view.get("question_coverage", {}) or {}
        evidence = dict(view.get("evidence", {}) or {})
        # Real selection, rastreável: unidades completas por documento,
        # corte de 2000 chars por documento SEMPRE registrado; limites
        # contam cabeçalhos+separadores reais; included_urls só com
        # material do prompt final.
        per_doc = 2000
        included, cuts, budget = [], [], int(max_chars)
        parts = []
        total = 0
        sep = "\n\n"
        for url in sorted(evidence):
            text = evidence[url] or ""
            raw_len = len(text)
            chunk = text[:per_doc]
            if raw_len > len(chunk):
                cuts.append(f"truncado {url} {raw_len}->{len(chunk)} chars "
                            f"(corte por documento {per_doc})")
            if not chunk.strip():
                continue
            header = f"Fonte {url}:\n"
            block = header + chunk
            if total + len(block) > budget:
                allowed = max(0, budget - total - len(header))
                chunk = chunk[:allowed]
                block = header + chunk
                cuts.append(f"truncado {url} ao teto {budget} chars "
                            f"(cabeçalho+separador contam)")
                if not chunk.strip():
                    cuts.append(f"teto de seleção {budget} chars atingido; "
                                f"{len(evidence)-len(included)} fontes fora")
                    break
            parts.append(block)
            included.append(url)
            total += len(block) + (len(sep) if parts else 0)
            if total >= budget:
                cuts.append(f"teto de seleção {budget} chars atingido; "
                            f"{len(evidence)-len(included)} fontes fora")
                break
        corpus_s = sep.join(parts)
        # Sem corte arbitrário no JSON/serialização: unidades completas;
        # qualquer teto já foi aplicado por bloco acima e registrado.
        prompt = (
            "Responda em português à pergunta usando SOMENTE o corpus abaixo. "
            "Estruture por critérios, cite URLs, marque lacunas e contradições; "
            "não invente fatos.\n"
            f"Pergunta: {question}\n"
            f"Cobertura: {_json.dumps(cov, ensure_ascii=False)[:4000]}\n"
            f"Corpus selecionado:\n{corpus_s}\n"
            "Retorne SOMENTE o relatório em markdown."
        )
        try:
            text = str(model_client(prompt) or "")
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"writer transport failed: {exc}")
        if not text.strip():
            raise TransportError("writer returned empty text")
        selection = {"included_urls": included,
                     "cuts": "; ".join(cuts) if cuts else "sem cortes",
                     "fallback": False,
                     "chars": len(corpus_s)}
        return text, selection

    return write


def make_review_fn(model_client):
    """Review transport for semantic_review.review_report (injectable).

    Receives (payload, model) where payload is the list of
    {id, claim, packages, licences, free_assertion, evidence} dicts and
    returns a list of {id, verdict, support, correction} dicts, using the
    same verdict protocol the built-in OpenRouter transport speaks
    (sustained/partial/unsupported/gap + technical failures). Transport
    failures raise (the caller converts to per-item transport_error, never
    favourable). Budget authorization/counting lives in _finalize, which
    wraps the auditor; this function performs one model call per batch.
    """
    import json as _json
    import semantic_review as _sr

    def review_fn(payload, model):
        prompt = (
            _sr.SYSTEM + "\n"
            "Julge cada afirmação contra o texto de evidência fornecido. "
            "Retorne SOMENTE uma lista JSON com {id, verdict, support, "
            "correction}. Veredictos válidos: sustained, partial, "
            "unsupported, gap.\n" +
            _json.dumps(payload, ensure_ascii=False))
        try:
            raw = model_client(prompt)
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"review transport failed: {exc}")
        raw_s = str(raw or "").strip()
        try:
            parsed = _extract_json(raw_s)
        except Exception as exc:
            raise TransportError(f"review returned invalid JSON: {exc}")
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise TransportError("review must return a JSON list")
        return parsed

    return review_fn


def _default_auditor(report: str, evidence: dict, review_fn=None,
                     generic: bool = False) -> dict:
    """Real-path auditor: lazy semantic_review with its quorum/tie/failure
    protections. Never hides question gaps (recorded separately).

    Honors SEMANTIC_REVIEW=0 (explicit disable, no model call). Budget
    authorization/counting lives in _finalize (per effective transport:
    lotes/votos/reparos/retentativas); this function never bypasses it.
    """
    import os as _os
    if _os.environ.get("SEMANTIC_REVIEW", "").strip() == "0":
        return {"enabled": False,
                "verdict_state": "não revisado semanticamente",
                "accepted": False,
                "note": "revisão semântica desativada via SEMANTIC_REVIEW=0"}
    try:
        import semantic_review as _sr
    except ImportError:
        return {"enabled": False,
                "verdict_state": "não revisado semanticamente",
                "accepted": False,
                "note": "semantic_review unavailable; question gaps kept"}
    try:
        result = _sr.review_report(report, dict(evidence or {}), enabled=True,
                                   review_fn=review_fn, generic=generic)
    except Exception as exc:  # failure is visible, never favourable
        return {"enabled": True, "verdict_state": "revisão incompleta",
                "accepted": False, "note": f"auditor failure: {exc}"}
    return result


def _assess_round(state: dict, assess_fn, ledger, resolved: dict | None = None
                  ) -> tuple[list, dict]:
    """Feed the ledger with the REAL corpus/qualification, apply ONLY the
    assessor's explicit evaluations, compute the block. Returns (evals, block).
    The coordinator never maps evidence to criteria itself.

    Model budget is enforced BEFORE the assessor transport: exhausted
    budget yields no call (insufficiency preserved). Failures/invalid
    attempts are counted. Transport failures propagate as TransportError
    so the caller can preserve evidence and produce a partial/failure
    result (never silent).
    """
    ledger.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
    _update_ledger_counts(state, ledger)
    # Default assessor uses no model: never spends budget, never blocked.
    is_default_assessor = (assess_fn is _default_assess)
    if not is_default_assessor and resolved is not None and not _check_model_budget(
            state, resolved):
        state["notes"].append(
            "assessor skipped: max_model_calls exhausted (insufficiency kept)")
        return [], ledger.compute()
    if not is_default_assessor:
        _note_model_call(state)
    # Contrato único com adaptação explícita de assinatura ANTES da
    # execução: uma só chamada, nunca retentativa após TypeError interno.
    # Falhas internas contam (budget já debitado), nunca geram chamadas
    # ocultas.
    import inspect as _inspect
    try:
        _sig = _inspect.signature(assess_fn)
        _params = list(_sig.parameters.values())
        _has_var = any(p.kind == _inspect.Parameter.VAR_POSITIONAL
                       for p in _params)
        _n_pos = sum(1 for p in _params if p.kind in (
            _inspect.Parameter.POSITIONAL_ONLY,
            _inspect.Parameter.POSITIONAL_OR_KEYWORD))
        _use_four = _has_var or _n_pos >= 4
    except (TypeError, ValueError):
        _use_four = True
    try:
        if _use_four:
            evals = assess_fn(state["plan"], dict(state["evidence"]),
                              dict(state["qualification"]),
                              dict(state.get("attempts", {}))) or []
        else:
            evals = assess_fn(state["plan"], dict(state["evidence"]),
                              dict(state["qualification"])) or []
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(f"assessor failed: {exc}")
    # Seleção analisada DAQUELA chamada (quando o assessor a expõe):
    # referência fora da seleção nunca justifica covered nessa avaliação.
    _sel_urls: set[str] | None = None
    try:
        _sel = getattr(assess_fn, "last_selection", None)
        if isinstance(_sel, dict) and isinstance(_sel.get("urls"), list):
            _sel_urls = set(_sel["urls"])
            # analyzed = documents really sent to the assessor (document
            # units, never chunks); union across calls, never inferred.
            _counters.record_analyzed(state, _sel["urls"])
    except Exception:
        _sel_urls = None
    # Structured validation: every evaluation must be a dict with a known
    # criterion, valid state, justification + origin; references must
    # resolve via the ledger (invalid -> kept as insufficiency, never
    # forced into coverage). Insufficiency/contradiction/failure preserved.
    # NOTE: o ledger só é alimentado após o merge de monotonia abaixo
    # (avaliações mescladas, não as brutas da rodada): rebaixamento sem
    # evidência nova rejeitado no merge nunca chega ao ledger, então
    # block/proportion refletem os estados mantidos.
    applied = []
    for ev in evals:
        if not isinstance(ev, dict) or "criterion_id" not in ev:
            state["notes"].append(
                f"assessor evaluation malformed (not a dict/criterion): kept")
            continue
        st = ev.get("state", "insufficient")
        if st not in ("uninvestigated", "insufficient", "partial", "covered",
                      "contradictory", "blocked"):
            state["notes"].append(
                f"assessor evaluation for {ev.get('criterion_id')} has "
                f"unknown state {st!r}: kept as insufficiency")
            continue
        if st in ("covered", "partial") and _sel_urls is not None:
            _refs = ev.get("references", []) or []
            _ref_urls = {(r or {}).get("url", (r or {}).get("doc_id", ""))
                         for r in _refs if isinstance(r, dict)}
            if not _ref_urls or not _ref_urls.issubset(_sel_urls):
                state["notes"].append(
                    f"assessor evaluation for {ev.get('criterion_id')} "
                    f"references material outside the analyzed selection: "
                    f"kept as insufficiency")
                continue
        applied.append(ev)
    # Open discovery: the assessor (model in production) may propose entities
    # the plan did not know. The coordinator only applies them as a new,
    # validated plan version — user requirements never shrink (enforced).
    for ev in evals:
        proposal = (ev or {}).get("propose_entity")
        if proposal and state["discovery"]["open"]:
            _apply_discovery(state, ledger, proposal, ev)
    # Persistência acumulada por célula (critério,entidade): a resposta
    # incremental do assessor nunca apaga avaliações válidas anteriores;
    # revisões/invalidações são explícitas em notes. Cobertura é monotônica
    # salvo evidência nova: rebaixamento (covered/partial -> estado inferior)
    # cujas referências não incluem material incorporado após a avaliação
    # anterior é rejeitado (o assessor não pode mudar de ideia sobre o
    # mesmo corpus sem fato novo). contradictory/blocked continuam livres
    # (juízo novo sobre conflito ou bloqueio de acesso).
    _RANK = {"uninvestigated": 0, "insufficient": 1, "partial": 2,
             "covered": 3}
    try:
        _merged: dict[tuple, dict] = {}
        for _prev in (state.get("evaluations", []) or []):
            if isinstance(_prev, dict) and "criterion_id" in _prev:
                _merged[(_prev.get("criterion_id"),
                         _prev.get("entity_id"))] = _prev
        _seen_keys = set(state.get("_assessed_evidence_keys") or [])
        _new_urls = set(dict(state.get("evidence", {}) or {})) - _seen_keys
        for _ev in applied:
            _key = (_ev.get("criterion_id"), _ev.get("entity_id"))
            _old = _merged.get(_key)
            if _old is not None and _old.get("state") != _ev.get("state"):
                _orank = _RANK.get(_old.get("state"))
                _nrank = _RANK.get(_ev.get("state"))
                _refs = {(r or {}).get("url", (r or {}).get("doc_id", ""))
                         for r in (_ev.get("references", []) or [])
                         if isinstance(r, dict)}
                _refs.discard("")
                if (_orank is not None and _nrank is not None
                        and _nrank < _orank and not (_refs & _new_urls)):
                    state["notes"].append(
                        f"downgrade without new evidence rejected for "
                        f"{_key}: kept {_old.get('state')} "
                        f"(assessor said {_ev.get('state')})")
                    continue
                state["notes"].append(
                    f"evaluation revised for {_key}: "
                    f"{_old.get('state')} -> {_ev.get('state')} "
                    f"(origin={_ev.get('origin', '')[:80]})")
            _merged[_key] = _ev
        # O ledger é alimentado com as avaliações mescladas (pós-monotonia),
        # nunca com as brutas: proporção/bloco refletem os estados mantidos.
        # Inválidas estruturais (ex. ref irresolvível) viram insuficiência,
        # nunca cobertura — mesmo invariante de antes, aplicado no merge.
        _final: list[dict] = []
        for _key, _ev in _merged.items():
            try:
                ledger.evaluate(_ev["criterion_id"], _ev.get("state", ""),
                                _ev.get("justification", ""),
                                _ev.get("origin", ""),
                                _ev.get("references", []),
                                _ev.get("entity_id"))
                _final.append(_ev)
            except (ValueError, KeyError):
                state["notes"].append(
                    f"assessor evaluation for {_ev.get('criterion_id')} "
                    f"rejected ({_ev.get('state')}): kept as insufficiency")
        state["evaluations"] = _final
        state["_assessed_evidence_keys"] = sorted(
            set(dict(state.get("evidence", {}) or {})))
    except Exception:
        state["evaluations"] = applied
    # Counts after evaluations: analyzed/used reflect what was applied.
    _update_ledger_counts(state, ledger)
    block = ledger.compute()
    state["gaps"] = list(block.get("gaps") or [])
    return list(state.get("evaluations", []) or []), block


def _apply_discovery(state: dict, ledger, proposal: dict, ev: dict) -> None:
    """Incorporate a newly discovered candidate as a tracked entity."""
    try:
        import copy as _copy
        entity = proposal.get("entity") or {}
        criteria = proposal.get("criteria") or []
        eid = entity.get("id")
        if not isinstance(eid, str) or not eid.strip():
            return
        if any(e.get("id") == eid for e in state["plan"].get("entities", [])):
            return  # already tracked: no duplicate, no version spam
        new_plan = _copy.deepcopy(state["plan"])
        new_plan.setdefault("entities", []).append({
            "id": eid, "label": entity.get("label", eid),
            "required": True})
        for c in criteria:
            if isinstance(c, dict) and c.get("id"):
                c = dict(c)
                c.setdefault("applies_to", [eid])
                new_plan.setdefault("criteria", []).append(c)
        from coverage_ledger import validate_plan as _validate
        _validate(new_plan)
        _state.record_plan_version(
            state, new_plan,
            f"open discovery: candidate {eid} from {ev.get('criterion_id')}")
        # Rebuild the ledger on the new plan, re-applying prior evaluations
        # against the same corpus (references re-validated, never trusted).
        fresh = _ledger.Ledger(new_plan, run_id=state["run_id"])
        fresh.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
        kept = []
        for prev in state.get("evaluations", []):
            try:
                fresh.evaluate(prev["criterion_id"], prev.get("state", "insufficient"),
                               prev.get("justification", ""), prev.get("origin", ""),
                               prev.get("references", []), prev.get("entity_id"))
                kept.append(prev)
            except (ValueError, KeyError):
                pass
        state["evaluations"] = kept
        ledger.plan = fresh.plan
        ledger._evals = fresh._evals
        ledger._evidence = fresh._evidence
        ledger._qualification = fresh._qualification
        ledger._counts = fresh._counts
        ledger.version = fresh.version
    except (ValueError, KeyError, TypeError) as exc:
        state["notes"].append(f"discovery proposal rejected: {exc}")


def _reconcile_resume(state: dict, checkpoint, run_dir) -> None:
    """Reconcile checkpoint + state before selecting new ops.

    - Every url in state.evidence is concluded: kept, never re-obtained.
    - Checkpoint-only urls (noted but without evidence, e.g. crash between
      note and state save) become explicit retries.
    - In-progress pending ops were already marked interrupted by load().
    """
    concluded = set((state.get("evidence") or {}).keys())
    ck_urls: set[str] = set()
    if checkpoint is not None:
        try:
            ck_urls = set((checkpoint.load().get("sources") or {}).keys())
        except Exception:
            ck_urls = set()
    orphan = sorted(ck_urls - concluded)
    if orphan:
        state["notes"].append(
            f"resume: {len(orphan)} checkpoint source(s) without evidence "
            f"-> explicit retry (no exactly-once): {orphan[:3]}")
        # Record as candidates so gap selection can retry them explicitly.
        cands = state.setdefault("discovery", {}).setdefault("candidates", [])
        for u in orphan:
            if u not in cands and u not in concluded:
                cands.append(u)
    # Pending in-progress were marked interrupted on load(); ensure none
    # stays in-progress silently.
    for op in state.get("pending_ops", []) or []:
        if op.get("status") == "in-progress":
            op["status"] = "interrupted"
            op["note"] = ("marked interrupted during resume reconcile "
                          "(outcome unknown, safe to retry)")


def _counting_model_client(state: dict, resolved: dict, raw_client):
    """Wrap the planner frontier: limit BEFORE each call, count every
    attempt (including failures/invalid). Raises TransportError when the
    ceiling is hit instead of calling the provider."""
    def wrapped(prompt: str):
        if not _check_model_budget(state, resolved):
            raise TransportError(
                f"max_model_calls={resolved.get('max_model_calls')} exhausted")
        _note_model_call(state)
        try:
            if callable(raw_client):
                return raw_client(prompt)
            gen = getattr(raw_client, "generate", None)
            if callable(gen):
                return gen(prompt)
            raise TransportError("[PLAN] model_client must be callable")
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"planner transport failed: {exc}")
    return wrapped


def _control_status(control, state: dict, phase: str, *,
                    round_no: int | None = None,
                    elapsed_s: float | None = None,
                    stop: dict | None = None) -> None:
    """Observable status write; a control failure never kills the research."""
    if control is None:
        return
    write = getattr(control, "write_status", None)
    if not callable(write):
        return
    kwargs: dict = {"phase": phase, "counters": state.get("counters")}
    if round_no is not None:
        kwargs["round_no"] = round_no
    if elapsed_s is not None:
        kwargs["elapsed_s"] = elapsed_s
    if stop is not None:
        kwargs["stop"] = stop
    try:
        write(**kwargs)
    except Exception as exc:  # noqa: BLE001 - status is observability only
        state.setdefault("notes", []).append(
            f"control status failed ({phase}): {exc}")


def _control_command(state: dict, control) -> str | None:
    """Poll the external control (duck-typed); pause/cancel only.

    ``resume`` is deliberately ignored here: retomada uses ``resume=True``
    and the persisted state, never a control file.
    """
    if control is None:
        return None
    poll = getattr(control, "poll", None)
    if not callable(poll):
        return None
    try:
        command = poll()
    except Exception as exc:  # noqa: BLE001 - control never kills the run
        state.setdefault("notes", []).append(f"control poll failed: {exc}")
        return None
    return command if command in ("pause", "cancel") else None


def _control_stop(state: dict, command: str, now, t_start) -> dict:
    state["stop"] = {
        "reason": "paused" if command == "pause" else "cancelled",
        "partial": True,
        "detail": f"control {command} requested",
    }
    try:
        state["elapsed_s"] = round(now() - t_start, 3)
    except Exception:
        pass
    return state["stop"]


def _mark_ops_not_run(state: dict, ops: list[dict], command: str) -> None:
    """Ops not started when the external command arrived stay explicit."""
    for op in ops:
        if op.get("status") == "in-progress":
            _record_op_outcome(
                state, op, "failed", command,
                note=(f"op {op.get('op_id')} not executed: control "
                      f"{command} requested"))


def _finalize_for_control(state: dict, command: str, resolved: dict, budget,
                          block: dict | None, write, audit, t_start, now,
                          run_dir, control) -> dict:
    """Stop by external command: preserve state, finalize with what exists."""
    _control_stop(state, command, now, t_start)
    state.setdefault("notes", []).append(
        f"control {command}: external stop; state preserved for resume")
    if run_dir is not None:
        try:
            _state.save(run_dir, state)
        except Exception as exc:  # noqa: BLE001
            state.setdefault("notes", []).append(
                f"persist before control finalize failed: {exc}")
    return _finalize(state, resolved, budget, block, write, audit,
                     t_start, now, run_dir, control=control)


def run_adaptive(question: str, *, profile: str = "light",
                 plan: dict | None = None, plan_source: str | dict | None = None,
                 purpose: str = "", constraints: dict | None = None,
                 model_client=None, search_fn=None, fetch_fn=None,
                 assess_fn=None, writer_fn=None, auditor_fn=None,
                 clock=None, budget=None, run_dir=None, run_id: str = "",
                 overrides: dict | None = None,
                 quantitative: list | None = None,
                 checkpoint=None, resume: bool = False,
                 control=None) -> dict:
    """Execute the adaptive loop. All external effects are injected.

    resume=True continues a persisted run_dir state (checkpoint): completed
    work is kept (duplicates detected, never double-counted), interrupted ops
    were marked 'interrupted' by load(), and no second run/plan/config mixes
    in (question + run_id verified).

    control (duck-typed: ``poll()`` / ``write_status()``) enables external
    pause/cancel. ``pause``/``cancel`` preserve state and finalize with the
    material already obtained (reserve respected); ``resume`` is ignored here
    because retomada is ``resume=True`` + persisted state.

    Returns the final result (also persisted in run_dir when given).
    Raises nothing for domain outcomes (they become stop motives); raises
    ValueError only for programming/config misuse.
    """
    now = clock or time.monotonic
    t_start = now()
    resolved = resolve_adaptive(profile, overrides)
    budget_given = budget is not None
    if budget is None:
        budget = _run_budget.Budget(resolved.get("budget"), profile=resolved["profile"])
    # Reconcile persisted consumption/time on resume: accumulated values
    # travel in state (never reset on session change). Unknown stays unknown.
    if resume and run_dir is not None:
        try:
            state = _state.load(run_dir, run_id or None)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"[ADAPTIVE] resume found no usable state: {exc}")
        if state.get("question", "") != question:
            raise ValueError("[ADAPTIVE] resume question differs from stored "
                             "state — runs never mix")
        if state.get("mode") != "adaptive":
            raise ValueError("[ADAPTIVE] stored state is not adaptive")
        resolved = dict(state.get("config_applied") or {})
        if not resolved:
            resolved = resolve_adaptive(profile, overrides)
        # Resume keeps the stored run/plan/config (never mixes). The only
        # accepted change is an explicit limit extension, recorded as such.
        if overrides:
            allowed = {"max_rounds", "time_s", "max_model_calls", "max_ops_per_round"}
            for key in overrides:
                if key not in allowed:
                    raise ValueError(
                        f"[ADAPTIVE] resume only accepts limit extensions "
                        f"{sorted(allowed)}; got {key!r}")
                try:
                    new_val = int(overrides[key])
                except (TypeError, ValueError):
                    raise ValueError(f"[ADAPTIVE] override {key} must be integer")
            for key in allowed & set(overrides):
                old = resolved.get(key)
                resolved[key] = int(overrides[key])
                state["notes"].append(
                    f"resume extended {key}: {old} -> {resolved[key]} (recorded, "
                    f"not silent)")
        # Accumulated wall-clock: resume continues, never restarts.
        try:
            prev_elapsed = float(state.get("elapsed_s", 0.0) or 0.0)
        except (TypeError, ValueError):
            prev_elapsed = 0.0
        t_start = now() - prev_elapsed
        if not budget_given:
            budget = _run_budget.Budget(resolved.get("budget"),
                                        profile=resolved.get("profile", profile))
            # Resume inherits consumed budget (no pierced ceiling across runs).
            cons = state.get("consumption", {})
            try:
                budget.reseed({"queries": cons.get("queries", 0),
                               "extractions": cons.get("fetches", 0),
                               "unique_sources": len(state.get("evidence", {}))})
            except Exception:
                pass
        # Reconcile checkpoint + state BEFORE new ops: completed sources in
        # state are reused (never re-obtained); checkpoint-only urls without
        # evidence are explicit retries (no exactly-once promise).
        try:
            _reconcile_resume(state, checkpoint, run_dir)
        except Exception as exc:
            state["notes"].append(f"resume reconcile note failed: {exc}")
        state["notes"].append("resumed from checkpoint; completed work kept, "
                              "interrupted ops marked, no silent repetition")
        _control_status(control, state, "plan")
        plan, plan_meta = state["plan"], state.get("plan_meta", {})
        if plan is None:
            raise ValueError("[ADAPTIVE] stored state has no plan to resume")
        ledger = _ledger.Ledger(plan, run_id=state["run_id"])
        ledger.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
        _update_ledger_counts(state, ledger)
        kept = []
        for prev in state.get("evaluations", []):
            try:
                ledger.evaluate(prev["criterion_id"], prev.get("state", "insufficient"),
                                prev.get("justification", ""), prev.get("origin", ""),
                                prev.get("references", []), prev.get("entity_id"))
                kept.append(prev)
            except (ValueError, KeyError):
                pass
        state["evaluations"] = kept
        _update_ledger_counts(state, ledger)
        block = ledger.compute()
        prev_proportion = block.get("proportion")
        if checkpoint is None and _checkpoint is not None:
            checkpoint = _checkpoint.Checkpoint(run_dir)
        assess = assess_fn or _default_assess
        write = writer_fn or _default_writer
        audit = auditor_fn or _default_auditor
        stop = _resume_loop(state, ledger, assess, write, audit, resolved,
                            budget, search_fn, fetch_fn, now, t_start,
                            checkpoint, run_dir, block, prev_proportion,
                            control=control)
        return stop
    state = _state.new_state(question, run_id=run_id, profile=resolved["profile"],
                             config={k: resolved[k] for k in
                                     ("profile", "report_type", "MAX_ITERATIONS",
                                      "DEEP_RESEARCH_BREADTH", "DEEP_RESEARCH_DEPTH",
                                      "DEEP_RESEARCH_CONCURRENCY", "TOTAL_WORDS",
                                      "vast_max", "yt_live", "max_rounds",
                                      "max_model_calls", "max_ops_per_round",
                                      "time_s", "concurrency", "budget")})
    state["quantitative_specs"] = [dict(s) for s in (quantitative or [])
                                   if isinstance(s, dict)]
    if checkpoint is None and run_dir is not None and _checkpoint is not None:
        checkpoint = _checkpoint.Checkpoint(run_dir)
    if run_dir is not None:
        _state.save(run_dir, state)
    _control_status(control, state, "plan")

    # -- plan (limits BEFORE transport; every attempt counted) --------
    try:
        if plan is not None:
            plan, plan_meta = _planner.plan_from_explicit(plan)
        elif plan_source is not None:
            plan, plan_meta = _planner.plan_from_explicit(plan_source)
        elif model_client is not None:
            if not _check_model_budget(state, resolved):
                raise _planner.PlanError(
                    "[PLAN] max_model_calls=0 blocks planner transport")
            counting = _counting_model_client(state, resolved, model_client)
            plan, plan_meta = _planner.generate_plan(
                question, counting, purpose, constraints)
        else:
            raise _planner.PlanError(
                "[PLAN] no plan and no model_client — cannot invent one")
    except _planner.PlanError as exc:
        state["stop"] = {"reason": "failure", "partial": True,
                          "detail": f"plan failed: {exc}"}
        state["notes"].append(f"plan failure (no fictitious plan): {exc}")
        if run_dir is not None:
            try:
                _state.save(run_dir, state)
            except Exception as exc2:
                state["notes"].append(f"persist after plan failure failed: {exc2}")
        return _finalize(state, resolved, budget, None, None, None,
                         t_start, now, run_dir, control=control)
    except TransportError as exc:
        # Planner transport failure (including budget block): partial/failure
        # with preserved state, never an escape.
        state["stop"] = {"reason": "failure", "partial": True,
                          "detail": f"planner transport failed: {exc}"}
        state["notes"].append(f"planner transport failure: {exc}")
        if run_dir is not None:
            try:
                _state.save(run_dir, state)
            except Exception as exc2:
                state["notes"].append(f"persist after plan failure failed: {exc2}")
        return _finalize(state, resolved, budget, None, None, None,
                         t_start, now, run_dir, control=control)
    # model_calls already counted per-transport via the wrapper (repairs and
    # failures included); plan_meta is record-only, never double-counted.
    _state.record_plan_version(state, plan, plan_meta.get("repair_log", [""])[0]
                               if plan_meta.get("repair_log") else "plan adopted")
    state["plan_meta"] = plan_meta
    disc = (plan.get("open_discovery") or {})
    state["discovery"]["open"] = bool(disc.get("needed", False))
    if run_dir is not None:
        _state.save(run_dir, state)

    ledger = _ledger.Ledger(plan, run_id=state["run_id"])
    assess = assess_fn or _default_assess
    write = writer_fn or _default_writer
    audit = auditor_fn or _default_auditor

    # -- initial collection (ONE sweep; later rounds are targeted ops) ------
    # initial_paths entries may be plain query strings (channel defaults to
    # CHANNELS[0]) or {"query": ..., "channel": ...} dicts so the plan can
    # direct the first sweep at the pertinent families (§8: explorar
    # amplamente). Unknown channels fall back to the default with a note.
    initial_queries = list((plan.get("initial_paths") or [question])) or [question]
    init_ops = []
    for i, q in enumerate(initial_queries):
        channel, target = CHANNELS[0], q
        if isinstance(q, dict):
            target = q.get("query", q.get("target", ""))
            want = str(q.get("channel", "") or "").lower()
            channel = want if want in CHANNELS else CHANNELS[0]
            if want and want not in CHANNELS:
                state["notes"].append(
                    f"initial path {i}: unknown channel {want!r}, "
                    f"using {CHANNELS[0]}")
        init_ops.append({"op_id": f"init-{i}", "kind": "initial",
                         "channel": channel, "target": target,
                         "criterion_id": "", "status": "in-progress"})
    for op in init_ops:
        state["pending_ops"].append(dict(op))
    _control_status(control, state, "round", round_no=0,
                    elapsed_s=round(now() - t_start, 3))
    command = _control_command(state, control)
    if command:
        return _finalize_for_control(state, command, resolved, budget, None,
                                     write, audit, t_start, now, run_dir,
                                     control)
    command = _execute_ops(state, init_ops, search_fn, fetch_fn, budget,
                           resolved, now, t_start, checkpoint, round_no=0,
                           run_dir=run_dir, control=control)
    if command is None:
        command = _control_command(state, control)
    if command:
        # Coverage from the accumulated corpus/evaluations only; no extra
        # model call (finalization reserve stays intact).
        ledger.set_corpus(dict(state["evidence"]), dict(state["qualification"]))
        _update_ledger_counts(state, ledger)
        return _finalize_for_control(state, command, resolved, budget,
                                     ledger.compute(), write, audit, t_start,
                                     now, run_dir, control)
    try:
        applied, block = _assess_round(state, assess, ledger, resolved)
    except TransportError as exc:
        state["notes"].append(f"assessor failure after collection: {exc}")
        _update_ledger_counts(state, ledger)
        block = ledger.compute()
        applied = []
        # Falha preserva avaliações acumuladas (nunca apaga sem evidência
        # invalidante).
        state["stop"] = {"reason": "failure", "partial": True,
                         "detail": f"assessor failed: {exc}"}
        state["rounds"].append({
            "round": 0, "kind": "initial",
            "target_gaps": [], "ops": _summarize_ops(state, init_ops),
            "new_evidence": len(state["segments"]),
            "coverage": {"status": block["status"],
                         "proportion": block.get("proportion")},
            "delta": None,
            "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
            "decision": f"assessor failed, evidence preserved: {exc}",
        })
        state["consumption"]["rounds"] = 1
        try:
            state["elapsed_s"] = round(now() - t_start, 3)
        except Exception:
            pass
        if run_dir is not None:
            try:
                _state.save(run_dir, state)
            except Exception as exc2:
                state["notes"].append(f"persist after assess failure failed: {exc2}")
        if checkpoint is not None:
            try:
                checkpoint.note_query_done("initial-sweep",
                                           n_sources=len(state["evidence"]))
            except Exception as exc2:
                state["notes"].append(f"checkpoint initial-sweep failed: {exc2}")
        return _finalize(state, resolved, budget, block, write, audit,
                         t_start, now, run_dir)
    # state["evaluations"] já acumulado em _assess_round; não sobrescrever.
    prev_proportion = block.get("proportion")
    prev_segments = 0
    state["rounds"].append({
        "round": 0, "kind": "initial",
        "target_gaps": [], "ops": _summarize_ops(state, init_ops),
        "new_evidence": len(state["segments"]) - prev_segments,
        "coverage": {"status": block["status"], "proportion": prev_proportion},
        "delta": None, "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
        "decision": "assessed initial sweep",
    })
    state["consumption"]["rounds"] = 1
    if checkpoint is not None:
        try:
            checkpoint.note_query_done("initial-sweep",
                                       n_sources=len(state["evidence"]))
        except Exception as exc:
            state["notes"].append(f"checkpoint initial-sweep failed: {exc}")
    try:
        state["elapsed_s"] = round(now() - t_start, 3)
    except Exception:
        pass
    if run_dir is not None:
        try:
            _state.save(run_dir, state)
        except Exception as exc:
            state["notes"].append(f"persist initial round failed: {exc}")

    # -- adaptive rounds ----------------------------------------------------
    return _resume_loop(state, ledger, assess, write, audit, resolved,
                        budget, search_fn, fetch_fn, now, t_start,
                        checkpoint, run_dir, block, prev_proportion)


def _resume_loop(state: dict, ledger, assess, write, audit, resolved: dict,
                 budget, search_fn, fetch_fn, now, t_start, checkpoint,
                 run_dir, block: dict, prev_proportion,
                 control=None) -> dict:
    """Shared gap-round loop for fresh and resumed runs."""
    stop = None
    prev_segments = len(state.get("segments", []) or [])
    while len(state["rounds"]) - 1 < resolved["max_rounds"]:
        elapsed = now() - t_start
        try:
            state["elapsed_s"] = round(elapsed, 3)
        except Exception:
            pass
        _control_status(control, state, "round",
                        round_no=len(state["rounds"]), elapsed_s=elapsed)
        command = _control_command(state, control)
        if command:
            stop = _control_stop(state, command, now, t_start)
            break
        open_gaps = block.get("gaps", [])
        # Explicit round/time motives (orçamento genérico não os esconde).
        if len(state["rounds"]) - 1 >= resolved["max_rounds"]:
            stop = {"reason": "rounds", "partial": bool(open_gaps),
                    "detail": f"max_rounds={resolved['max_rounds']} consumed"}
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        if elapsed >= resolved["time_s"]:
            stop = {"reason": "time", "partial": bool(open_gaps),
                    "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        # Reserve finalization (write+audit cost): if fewer than 2 model
        # calls remain and gaps are pending, stop now so the reserve holds.
        if open_gaps and _model_remaining(state, resolved) < 2 and len(
                state["rounds"]) > 0:
            # Still allow the loop to assess if no assess happened yet?
            # For the initial-only case the assess already ran; reserve now.
            stop = {"reason": "budget", "partial": True,
                    "detail": (f"max_model_calls={resolved['max_model_calls']} "
                               f"reserved for finalization")}
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        novelty = _novelty(state)
        decision = _profiles.decide_stop(
            aspects_covered=block.get("proportion"),
            novelty_last_rounds=novelty,
            budget={"rounds_used": len(state["rounds"]) - 1,
                    "rounds_budget": resolved["max_rounds"],
                    "time_used_s": elapsed, "time_budget_s": resolved["time_s"]},
            blocked=_all_blocked(block),
            gaps=[g.get("criterion_id") for g in open_gaps])
        stop = _map_stop(decision, block, state, resolved, budget,
                         elapsed, now, t_start)
        if stop is not None:
            state["rounds"][-1]["decision"] = stop["detail"]
            break
        ordered = prioritize_gaps(open_gaps)
        ops = select_ops(state, ordered, resolved["max_ops_per_round"])
        if not ops:
            stop = {"reason": "saturation", "partial": bool(open_gaps),
                    "detail": "no selectable ops for open gaps"}
            break
        for op in ops:
            state["pending_ops"].append(dict(op))
        if run_dir is not None:
            try:
                _state.save(run_dir, state)
            except Exception as exc:
                state["notes"].append(f"persist pending ops failed: {exc}")
        command = _execute_ops(state, ops, search_fn, fetch_fn, budget,
                               resolved, now, t_start, checkpoint,
                               round_no=len(state["rounds"]),
                               run_dir=run_dir, control=control)
        if command is None:
            command = _control_command(state, control)
        if command:
            stop = _control_stop(state, command, now, t_start)
            break
        try:
            applied, block = _assess_round(state, assess, ledger, resolved)
        except TransportError as exc:
            state["notes"].append(f"assessor failure in gap round: {exc}")
            _update_ledger_counts(state, ledger)
            block = ledger.compute()
            new_prop = block.get("proportion")
            delta = _prop_delta(prev_proportion, new_prop)
            prev_proportion = new_prop
            gained = len(state.get("segments", []) or []) - prev_segments
            prev_segments = len(state.get("segments", []) or [])
            state["rounds"].append({
                "round": len(state["rounds"]), "kind": "gap",
                "target_gaps": [o["criterion_id"] for o in ops],
                "ops": _summarize_ops(state, ops),
                "new_evidence": gained,
                "coverage": {"status": block["status"], "proportion": new_prop},
                "delta": delta,
                "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
                "decision": f"assessor failed, evidence preserved: {exc}",
            })
            state["consumption"]["rounds"] += 1
            try:
                state["elapsed_s"] = round(now() - t_start, 3)
            except Exception:
                pass
            if run_dir is not None:
                try:
                    _state.save(run_dir, state)
                except Exception as exc2:
                    state["notes"].append(
                        f"persist after assess failure failed: {exc2}")
            state["stop"] = {"reason": "failure", "partial": True,
                             "detail": f"assessor failed: {exc}"}
            return _finalize(state, resolved, budget, block, write, audit,
                             t_start, now, run_dir)
        # state["evaluations"] já acumulado em _assess_round; não sobrescrever.
        new_prop = block.get("proportion")
        delta = (_prop_delta(prev_proportion, new_prop))
        prev_proportion = new_prop
        gained = len(state.get("segments", []) or []) - prev_segments
        prev_segments = len(state.get("segments", []) or [])
        state["rounds"].append({
            "round": len(state["rounds"]), "kind": "gap",
            "target_gaps": [o["criterion_id"] for o in ops],
            "ops": _summarize_ops(state, ops),
            "new_evidence": gained,
            "coverage": {"status": block["status"], "proportion": new_prop},
            "delta": delta, "insufficiencies": [g["criterion_id"] for g in block.get("gaps", [])],
            "decision": "continue",
        })
        state["consumption"]["rounds"] += 1
        if checkpoint is not None:
            try:
                checkpoint.note_learning(
                    f"round {len(state['rounds']) - 1}: {block['status']} "
                    f"{new_prop} delta={delta}")
            except Exception as exc:
                state["notes"].append(f"checkpoint learning failed: {exc}")
        try:
            state["elapsed_s"] = round(now() - t_start, 3)
        except Exception:
            pass
        if run_dir is not None:
            try:
                _state.save(run_dir, state)
            except Exception as exc:
                state["notes"].append(f"persist gap round failed: {exc}")
        command = _control_command(state, control)
        if command:
            stop = _control_stop(state, command, now, t_start)
            state["rounds"][-1]["decision"] = f"control {command} after round"
            break

    if stop is None:  # max_rounds consumed by the loop guard
        open_gaps = block.get("gaps", [])
        stop = {"reason": "rounds", "partial": bool(open_gaps),
                "detail": f"max_rounds={resolved['max_rounds']} consumed"}
    state["stop"] = stop
    try:
        state["elapsed_s"] = round(now() - t_start, 3)
    except Exception:
        pass
    if run_dir is not None:
        try:
            _state.save(run_dir, state)
        except Exception as exc:
            state["notes"].append(f"persist stop failed: {exc}")
    return _finalize(state, resolved, budget, block, write, audit,
                     t_start, now, run_dir, control=control)


def _prop_delta(old, new) -> float | None:
    if old is None or new is None:
        return None
    try:
        return round(float(new) - float(old), 4)
    except (TypeError, ValueError):
        return None


def _novelty(state: dict) -> float:
    """Fraction of new findings in the last round (low = repetition)."""
    if not state["rounds"]:
        return 1.0
    last = state["rounds"][-1]
    ops = last.get("ops", [])
    if not ops:
        return 1.0
    useful = sum(1 for o in ops if o.get("outcome") in ("new_useful", "confirmed"))
    return useful / max(1, len(ops))


def _all_blocked(block: dict) -> bool:
    crits = block.get("criteria", [])
    if not crits:
        return False
    return all(c.get("state") == "blocked" for c in crits if c.get("required", True))


def _map_stop(decision: dict, block: dict, state: dict, resolved: dict,
              budget, elapsed: float, now, t_start) -> dict | None:
    """Translate decide_stop + hard limits into an explicit motive.

    The legacy 95% coverage threshold never becomes criteria_ok on its
    own: criteria_ok requires block.complete (every mandatory pair
    covered). A 0.95 proportion with pending mandatory gaps keeps the
    run partial and consistent across plan/coverage/stop/partial/report.
    """
    open_gaps = block.get("gaps", [])
    pending = bool(open_gaps)
    reason = decision.get("stop_reason")
    if reason == "coverage":
        if block.get("complete"):
            return {"reason": "criteria_ok", "partial": False,
                    "detail": f"proportion={block.get('proportion')}"}
        # Measured 0.95 but mandatory work remains: not complete, keep
        # going (rounds/budget/time will stop as partial). Never report
        # criteria_ok with pending gaps.
        return None
    if reason == "novelty":
        return {"reason": "saturation", "partial": pending,
                "detail": f"novelty={_novelty(state):.2f} with "
                          f"{len(open_gaps)} gaps pending"}
    if reason == "blocked":
        return {"reason": "blocked", "partial": pending,
                "detail": "all required criteria blocked"}
    if reason == "budget":
        if elapsed >= resolved["time_s"]:
            return {"reason": "time", "partial": pending,
                    "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
        return {"reason": "budget", "partial": pending,
                "detail": f"rounds/time budget consumed "
                          f"(elapsed={elapsed:.1f}s)"}
    if state["consumption"]["model_calls"] >= resolved["max_model_calls"] and pending:
        return {"reason": "budget", "partial": True,
                "detail": f"max_model_calls={resolved['max_model_calls']}"}
    if state["consumption"]["queries"] >= int(
            resolved.get("budget", {}).get("queries", 0) or 0) and \
            int(resolved.get("budget", {}).get("queries", 0) or 0) > 0 and pending:
        return {"reason": "budget", "partial": True,
                "detail": "query budget consumed"}
    if budget is not None and budget.exhausted() and pending:
        return {"reason": "budget", "partial": True,
                "detail": str(budget.exhausted())}
    if elapsed >= resolved["time_s"]:
        return {"reason": "time", "partial": pending,
                "detail": f"elapsed={elapsed:.1f}s >= {resolved['time_s']}s"}
    if reason == "continue":
        return None
    return None


def _summarize_ops(state: dict, ops: list[dict]) -> list[dict]:
    return [{"op_id": o.get("op_id"), "kind": o.get("kind"),
             "channel": o.get("channel"), "target": o.get("target"),
             "outcome": o.get("outcome", "unknown"),
             "new": o.get("outcome") in ("new_useful", "confirmed")}
            for o in ops]


def _unique_limit(resolved: dict, budget) -> int:
    try:
        lim = int((resolved.get("budget") or {}).get("unique_sources", 0) or 0)
    except (TypeError, ValueError):
        lim = 0
    if not lim and budget is not None:
        try:
            lim = int(budget.limits.get("unique_sources", 0) or 0)
        except (TypeError, ValueError):
            lim = 0
    return lim


def _persist_progress(state: dict, run_dir, checkpoint, url: str, text: str,
                      channel: str) -> None:
    """Crash-durable progress after each concluded source.

    State is saved atomically (tmp+rename); checkpoint notes the source.
    Failures are recorded in notes (never silent), never favourable.
    """
    if checkpoint is not None:
        try:
            checkpoint.note_source(url, source=channel, content=text)
        except Exception as exc:
            state["notes"].append(f"checkpoint note failed for {url[:60]}: {exc}")
    if run_dir is not None:
        try:
            import time as _t
            # Elapsed is kept in state so resume accumulates, never resets.
            state["elapsed_s"] = float(state.get("elapsed_s", 0.0) or 0.0)
            _state.save(run_dir, state)
        except Exception as exc:
            state["notes"].append(f"progress persist failed: {exc}")


def _execute_ops(state: dict, ops: list[dict], search_fn, fetch_fn, budget,
                 resolved: dict, now, t_start, checkpoint, round_no: int,
                 run_dir=None, control=None) -> str | None:
    """Execute ops within limits: sequential path at concurrency=1, real
    bounded pool above it (see ``_execute_ops_parallel``).

    The declared limit is ``resolved['concurrency']``. It bounds OUR op
    transports (search/fetch); per-source internal request caps remain the
    transport's own responsibility (declared, not a global ceiling).
    """
    try:
        concurrency = int(resolved.get("concurrency", 1) or 1)
    except (TypeError, ValueError):
        concurrency = 1
    if concurrency <= 1 or len(ops) <= 1:
        return _execute_ops_sequential(
            state, ops, search_fn, fetch_fn, budget, resolved, now, t_start,
            checkpoint, round_no, run_dir, control=control)
    return _execute_ops_parallel(
        state, ops, search_fn, fetch_fn, budget, resolved, now, t_start,
        checkpoint, round_no, run_dir, concurrency, control=control)


def _execute_ops_sequential(state: dict, ops: list[dict], search_fn, fetch_fn,
                            budget, resolved: dict, now, t_start, checkpoint,
                            round_no: int, run_dir=None,
                            control=None) -> str | None:
    """Run ops sequentially within limits (concurrency recorded; the offline
    path executes sequentially — no fabricated parallelism).

    - read_source reads its target directly (never via search).
    - channel alters the effective access (passed to search; recorded per
      attempt; unavailable channels recorded, never silently relabelled).
    - Completed sources are reused, never re-obtained; progress is
      persisted after each concluded source so a real mid-round
      interruption recovers without silent repetition.
    """
    for op in ops:
        command = _control_command(state, control)
        if command:
            _mark_ops_not_run(state, ops, command)
            return command
        if now() - t_start >= resolved["time_s"]:
            op["status"], op["outcome"] = "failed", "time"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "time"})
            continue
        kind = op.get("kind", "gap_query")
        # --- read_source: direct target read, no search -----------------
        if kind == "read_source":
            target = op.get("target", "")
            if not isinstance(target, str) or not target:
                op["status"], op["outcome"] = "failed", "failed"
                state["attempts"].setdefault(
                    op.get("criterion_id", ""), []).append(
                    {"channel": op.get("channel"), "outcome": "failed",
                     "note": "read_source without target"})
                continue
            if target in state["evidence"] and not state.get(
                    "discovery", {}).get("open"):
                op["status"], op["outcome"] = "done", "duplicate"
                state["attempts"].setdefault(
                    op.get("criterion_id", ""), []).append(
                    {"channel": op.get("channel"), "outcome": "duplicate",
                     "note": f"reused concluded {target[:60]}"})
                for pending in state["pending_ops"]:
                    if pending.get("op_id") == op.get("op_id"):
                        pending["status"] = op["status"]
                        pending["outcome"] = "duplicate"
                continue
            lim = _unique_limit(resolved, budget)
            if lim and len(state.get("evidence", {})) >= lim:
                op["status"], op["outcome"] = "failed", "budget"
                state["notes"].append(
                    f"unique_sources limit {lim} hit; read_source "
                    f"{target[:80]} skipped")
                state["attempts"].setdefault(
                    op.get("criterion_id", ""), []).append(
                    {"channel": op.get("channel"), "outcome": "budget"})
                continue
            if not budget.spend("extractions"):
                op["status"], op["outcome"] = "failed", "budget"
                state["notes"].append(
                    f"op {op['op_id']}: extraction budget hit (read_source)")
                state["attempts"].setdefault(
                    op.get("criterion_id", ""), []).append(
                    {"channel": op.get("channel"), "outcome": "budget"})
                continue
            state["consumption"]["ops"] += 1
            try:
                payload = _run_fetch(fetch_fn, op, target)
            except TransportError as exc:
                state["consumption"]["fetches"] += 1
                op["status"], op["outcome"] = "failed", "failed"
                state["attempts"].setdefault(
                    op.get("criterion_id", ""), []).append(
                    {"channel": op.get("channel"), "outcome": "failed",
                     "note": f"canal {op.get('channel')}: {str(exc)[:160]}"})
                state["notes"].append(
                    f"op {op['op_id']} read_source failure "
                    f"(canal {op.get('channel')}) for {target[:80]}: {exc}")
                continue
            text, qual = _coerce_payload(payload, target)
            state["consumption"]["fetches"] += 1
            outcome = incorporate(state, target, text, op["op_id"], round_no,
                                  qualification=qual)
            if outcome in ("new_useful", "confirmed"):
                _persist_progress(state, run_dir, checkpoint, target, text,
                                  op.get("channel", ""))
            else:
                # Even duplicates/partials persist qualification progress.
                _persist_progress(state, run_dir, checkpoint, target, text,
                                  op.get("channel", ""))
            if state.get("discovery", {}).get("open") and target not in state[
                    "discovery"]["candidates"]:
                state["discovery"]["candidates"].append(target)
            op["status"] = "done" if outcome != "failed" else "failed"
            op["outcome"] = outcome if outcome in (
                "new_useful", "confirmed", "duplicate", "nogain") else "nogain"
            # incorporate never returns failed/budget; map unknown to nogain.
            if op["outcome"] not in ("new_useful", "confirmed", "duplicate",
                                     "nogain"):
                op["outcome"] = "nogain"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": op["outcome"]})
            for pending in state["pending_ops"]:
                if pending.get("op_id") == op.get("op_id"):
                    pending["status"] = op["status"]
                    pending["outcome"] = op["outcome"]
            continue
        # --- search-backed ops (initial/gap_query/alt_channel) -----------
        if not budget.spend("queries"):
            op["status"], op["outcome"] = "failed", "budget"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "budget"})
            continue
        state["consumption"]["queries"] += 1
        state["consumption"]["ops"] += 1
        try:
            hits = _run_search(search_fn, op)
        except TransportError as exc:
            op["status"], op["outcome"] = "failed", "failed"
            state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
                {"channel": op.get("channel"), "outcome": "failed",
                 "note": f"canal {op.get('channel')}: {str(exc)[:160]}"})
            state["notes"].append(
                f"op {op['op_id']} transport failure "
                f"(canal {op.get('channel')}): {exc}")
            continue
        # discovered = URLs really seen in search results (observed event).
        _counters.record_discovered(
            state, [h.get("url") if isinstance(h, dict) else h
                    for h in (hits or [])])
        best = "nogain"
        for hit in (hits or [])[:resolved["vast_max"]]:
            url = hit.get("url") if isinstance(hit, dict) else hit
            if not isinstance(url, str) or not url:
                continue
            if url in state["evidence"] and not state.get(
                    "discovery", {}).get("open"):
                # Reuse concluded source; never re-obtain.
                if best == "nogain":
                    best = "duplicate"
                continue
            lim = _unique_limit(resolved, budget)
            if lim and len(state.get("evidence", {})) >= lim:
                state["notes"].append(
                    f"unique_sources limit {lim} hit; skipped {url[:80]}")
                if best == "nogain":
                    best = "budget"
                break
            if not budget.spend("extractions"):
                state["notes"].append(f"op {op['op_id']}: extraction budget hit")
                if best == "nogain":
                    best = "budget"
                break
            try:
                payload = _run_fetch(fetch_fn, op, url)
            except TransportError as exc:
                state["consumption"]["fetches"] += 1
                state["notes"].append(
                    f"op {op['op_id']} fetch failure for {url[:80]}: {exc}")
                best = "failed" if best == "nogain" else best
                continue
            text, qual = _coerce_payload(payload, url)
            state["consumption"]["fetches"] += 1
            outcome = incorporate(state, url, text, op["op_id"], round_no,
                                  qualification=qual)
            if outcome in ("new_useful", "confirmed"):
                _persist_progress(state, run_dir, checkpoint, url, text,
                                  op.get("channel", ""))
            if outcome == "new_useful":
                best = "new_useful"
            elif outcome == "confirmed" and best != "new_useful":
                best = "confirmed"
            elif outcome == "duplicate" and best == "nogain":
                best = "duplicate"
            # open discovery: unknown candidates enter the pool, and (when the
            # plan allows) become new tracked entities via plan versioning
            if state["discovery"]["open"] and url not in [
                    c for c in state["discovery"]["candidates"]]:
                state["discovery"]["candidates"].append(url)
        op["status"] = "done" if best != "failed" else "failed"
        op["outcome"] = best
        state["attempts"].setdefault(op.get("criterion_id", ""), []).append(
            {"channel": op.get("channel"), "outcome": best})
        for pending in state["pending_ops"]:
            if pending.get("op_id") == op.get("op_id"):
                pending["status"] = op["status"]
                pending["outcome"] = best
    return None


def _record_op_outcome(state: dict, op: dict, status: str, outcome: str,
                       note: str | None = None,
                       attempt_note: str | None = None) -> None:
    """Apply one op outcome (status/outcome/attempt/pending) deterministically."""
    op["status"], op["outcome"] = status, outcome
    if note:
        state["notes"].append(note)
    attempt = {"channel": op.get("channel"), "outcome": outcome}
    if attempt_note:
        attempt["note"] = attempt_note
    state["attempts"].setdefault(op.get("criterion_id", ""), []).append(attempt)
    for pending in state["pending_ops"]:
        if pending.get("op_id") == op.get("op_id"):
            pending["status"] = status
            pending["outcome"] = outcome


def _execute_ops_parallel(state: dict, ops: list[dict], search_fn, fetch_fn,
                          budget, resolved: dict, now, t_start, checkpoint,
                          round_no: int, run_dir, concurrency: int,
                          control=None) -> str | None:
    """Real bounded concurrency in three phases (deterministic state order).

    Phase 1 (sequential): time check, reuse/skip decisions and budget
    authorization BEFORE any transport (queries and read_source extractions;
    search-result extractions are authorized under the shared budget lock at
    scheduling time, so the aggregate ceiling is never exceeded).
    Phase 2 (pool of ``concurrency``): transports only — searches, then
    fetches. A transport error becomes a per-op result; it never kills the
    pool. Identical URLs inside one batch are fetched once (declared dedupe).
    Phase 3 (sequential, op order): incorporate, qualification, persistence
    and counters, so the final state is reproducible.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    command = _control_command(state, control)
    if command:
        _mark_ops_not_run(state, ops, command)
        return command

    def over_time() -> bool:
        try:
            return now() - t_start >= resolved["time_s"]
        except Exception:
            return False

    prepared: list[dict] = []
    search_tasks: list[int] = []
    fetch_tasks: list[tuple[int, str]] = []
    claim_owner: dict[str, int] = {}

    # -- phase 1: decisions + budget authorization (no transport) --------
    for idx, op in enumerate(ops):
        item = {"op": op, "mode": None, "skip": None, "note": None,
                "hits": None, "search_error": None, "fetches": {},
                "budget_skips": set(), "time_cut": False}
        prepared.append(item)
        if over_time():
            item["skip"] = "time"
            continue
        kind = op.get("kind", "gap_query")
        if kind == "read_source":
            target = op.get("target", "")
            if not isinstance(target, str) or not target:
                item["skip"] = "failed"
                item["note"] = "read_source without target"
                continue
            if target in state["evidence"] and not state.get(
                    "discovery", {}).get("open"):
                item["skip"] = "duplicate"
                item["note"] = f"reused concluded {target[:60]}"
                continue
            lim = _unique_limit(resolved, budget)
            if lim and len(state.get("evidence", {})) >= lim:
                item["skip"] = "budget"
                item["note"] = (f"unique_sources limit {lim} hit; read_source "
                                f"{target[:80]} skipped")
                continue
            if not budget.spend("extractions"):
                item["skip"] = "budget"
                item["note"] = (f"op {op['op_id']}: extraction budget hit "
                                f"(read_source)")
                continue
            state["consumption"]["ops"] += 1
            item["mode"] = "read"
            fetch_tasks.append((idx, target))
            continue
        if not budget.spend("queries"):
            item["skip"] = "budget"
            continue
        state["consumption"]["queries"] += 1
        state["consumption"]["ops"] += 1
        item["mode"] = "search"
        search_tasks.append(idx)

    # -- phase 2a: searches in the bounded pool --------------------------
    def run_search(idx: int):
        try:
            return idx, _run_search(search_fn, prepared[idx]["op"]), None
        except Exception as exc:  # per-op failure, pool survives
            return idx, None, exc

    if search_tasks:
        with ThreadPoolExecutor(
                max_workers=min(concurrency, len(search_tasks))) as pool:
            futures = [pool.submit(run_search, idx) for idx in search_tasks]
            for future in as_completed(futures):
                idx, hits, exc = future.result()
                item = prepared[idx]
                if exc is not None:
                    item["search_error"] = exc
                else:
                    item["hits"] = list(hits or [])
                    _counters.record_discovered(
                        state, [h.get("url") if isinstance(h, dict) else h
                                for h in item["hits"]])

    # -- phase 2b: authorize + schedule fetches (sequential, op order) ---
    lim = _unique_limit(resolved, budget)
    for idx, item in enumerate(prepared):
        if item["mode"] != "search" or item["hits"] is None:
            continue
        op = item["op"]
        for hit in item["hits"][:resolved["vast_max"]]:
            url = hit.get("url") if isinstance(hit, dict) else hit
            if not isinstance(url, str) or not url:
                continue
            if over_time():
                item["time_cut"] = True
                break
            if url in state["evidence"] and not state.get(
                    "discovery", {}).get("open"):
                continue  # reuse concluded source; phase 3 marks duplicate
            if url in claim_owner:
                continue  # same batch: fetched once (declared dedupe)
            if lim and len(state.get("evidence", {})) + len(claim_owner) >= lim:
                state["notes"].append(
                    f"unique_sources limit {lim} hit; skipped {url[:80]}")
                item["budget_skips"].add(url)
                break
            if not budget.spend("extractions"):
                state["notes"].append(
                    f"op {op['op_id']}: extraction budget hit")
                item["budget_skips"].add(url)
                break
            claim_owner[url] = idx
            fetch_tasks.append((idx, url))
        if item["time_cut"]:
            for later in prepared[idx + 1:]:
                if later["mode"] is not None:
                    later["time_cut"] = True
            break

    # -- phase 2c: fetches in the bounded pool ---------------------------
    def run_fetch(idx: int, url: str):
        try:
            return idx, url, _run_fetch(fetch_fn, prepared[idx]["op"], url), None
        except Exception as exc:  # per-op failure, pool survives
            return idx, url, None, exc

    if fetch_tasks:
        with ThreadPoolExecutor(
                max_workers=min(concurrency, len(fetch_tasks))) as pool:
            futures = [pool.submit(run_fetch, idx, url)
                       for idx, url in fetch_tasks]
            for future in as_completed(futures):
                idx, url, payload, exc = future.result()
                prepared[idx]["fetches"][url] = (
                    ("error", str(exc)) if exc is not None else ("ok", payload))

    # -- phase 3: deterministic application in op order ------------------
    for idx, item in enumerate(prepared):
        op = item["op"]
        if item["skip"]:
            status = "done" if item["skip"] == "duplicate" else "failed"
            _record_op_outcome(state, op, status, item["skip"],
                               note=item.get("note"))
            continue
        if item["mode"] == "read":
            target = op["target"]
            result = item["fetches"].get(target)
            if result is None:
                _record_op_outcome(state, op, "failed", "time",
                                   note=f"op {op['op_id']}: deadline during "
                                        f"transport")
                continue
            state["consumption"]["fetches"] += 1
            status, payload = result
            if status == "error":
                _record_op_outcome(
                    state, op, "failed", "failed",
                    note=(f"op {op['op_id']} read_source failure "
                          f"(canal {op.get('channel')}) for {target[:80]}: "
                          f"{payload}"),
                    attempt_note=f"canal {op.get('channel')}: {payload[:160]}")
                continue
            text, qual = _coerce_payload(payload, target)
            outcome = incorporate(state, target, text, op["op_id"], round_no,
                                  qualification=qual)
            _persist_progress(state, run_dir, checkpoint, target, text,
                              op.get("channel", ""))
            if state.get("discovery", {}).get("open") and target not in state[
                    "discovery"]["candidates"]:
                state["discovery"]["candidates"].append(target)
            mapped = outcome if outcome in (
                "new_useful", "confirmed", "duplicate", "nogain") else "nogain"
            _record_op_outcome(state, op, "done", mapped)
            continue
        # search-backed
        if item["search_error"] is not None:
            _record_op_outcome(
                state, op, "failed", "failed",
                note=(f"op {op['op_id']} transport failure "
                      f"(canal {op.get('channel')}): {item['search_error']}"),
                attempt_note=(f"canal {op.get('channel')}: "
                              f"{str(item['search_error'])[:160]}"))
            continue
        best = "nogain"
        for hit in (item["hits"] or [])[:resolved["vast_max"]]:
            url = hit.get("url") if isinstance(hit, dict) else hit
            if not isinstance(url, str) or not url:
                continue
            if url in state["evidence"] and not state.get(
                    "discovery", {}).get("open"):
                if best == "nogain":
                    best = "duplicate"
                continue
            if url in item["budget_skips"]:
                if best == "nogain":
                    best = "budget"
                break
            result = item["fetches"].get(url)
            if result is None:
                owner = claim_owner.get(url)
                owner_result = (prepared[owner]["fetches"].get(url)
                                if owner is not None else None)
                if owner_result and owner_result[0] == "error":
                    state["notes"].append(
                        f"op {op['op_id']}: fetch compartilhado falhou para "
                        f"{url[:80]} ({owner_result[1]})")
                    if best == "nogain":
                        best = "failed"
                elif best == "nogain":
                    best = "time" if item.get("time_cut") else "failed"
                continue
            state["consumption"]["fetches"] += 1
            status, payload = result
            if status == "error":
                state["notes"].append(
                    f"op {op['op_id']} fetch failure for {url[:80]}: {payload}")
                if best == "nogain":
                    best = "failed"
                continue
            text, qual = _coerce_payload(payload, url)
            outcome = incorporate(state, url, text, op["op_id"], round_no,
                                  qualification=qual)
            if outcome in ("new_useful", "confirmed"):
                _persist_progress(state, run_dir, checkpoint, url, text,
                                  op.get("channel", ""))
            if outcome == "new_useful":
                best = "new_useful"
            elif outcome == "confirmed" and best != "new_useful":
                best = "confirmed"
            elif outcome == "duplicate" and best == "nogain":
                best = "duplicate"
            if state["discovery"]["open"] and url not in [
                    c for c in state["discovery"]["candidates"]]:
                state["discovery"]["candidates"].append(url)
        if item.get("time_cut") and best in ("nogain", "failed"):
            best = "time"
        _record_op_outcome(state, op, "failed" if best == "failed" else "done",
                           best)
    # Pause/cancel during a parallel batch is honoured after phase 3: the
    # already-fetched payloads are incorporated (no wasted budget), never
    # re-obtained on resume.
    return _control_command(state, control)


def _run_search(search_fn, op: dict) -> list:
    if search_fn is None:
        return []
    try:
        return search_fn(op["target"], op.get("channel", "web")) or []
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(f"search failed: {exc}")


def _run_fetch(fetch_fn, op: dict, url: str):
    if fetch_fn is None:
        raise TransportError("no fetch_fn injected (offline: nothing to read)")
    try:
        return fetch_fn(url)
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(f"fetch failed for {url[:80]}: {exc}")


def _string_qual_via_shared(text: str, url: str) -> dict | None:
    """Reuse the existing evidence qualification for raw strings.

    Pure error strings (e.g. 'ERROR: HTTP 403 Forbidden...') are never
    usable evidence; partials/metadata keep their scope. Returns None when
    the shared qualifier is unavailable (caller falls back to minimal).
    """
    try:
        import semantic_review as _sr
        qfn = getattr(_sr, "_qualify_evidence_entry", None)
        if callable(qfn):
            q = qfn(url, text or "")
            return {"status": q.get("status", "usable"),
                    "reason": q.get("reason", "shared qualification"),
                    "usable_text": q.get("usable_text", ""),
                    "excluded": bool(q.get("excluded", False))}
    except Exception:
        pass
    return None


def _coerce_payload(payload, url: str) -> tuple[str, dict | None]:
    """Accept str | {text,...} payloads. Qualification is recorded, never
    invented: unknown payloads get a minimal usable record only when they
    carry non-empty text, otherwise excluded. String payloads reuse the
    shared qualification (error-only never usable)."""
    if isinstance(payload, str):
        text = payload
        if not text.strip():
            return text, {"status": "empty", "reason": "empty payload",
                          "usable_text": "", "excluded": True}
        shared = _string_qual_via_shared(text, url)
        if shared is not None:
            return text, shared
        qual = {"status": "usable", "reason": "injected corpus text",
                "usable_text": text, "excluded": False}
        return text, qual
    if isinstance(payload, dict):
        text = payload.get("text", "") or ""
        qual = {k: payload[k] for k in ("status", "reason", "usable_text",
                                       "excluded", "title", "evidence_type",
                                       "content_kind", "content_bearing")
                if k in payload}
        status = str(qual.get("status", "") or "").strip().lower()
        # Pure error payloads are never usable evidence by default, even
        # when they carry text (e.g. "HTTP 403 Forbidden"). Useful metadata
        # stays in the record; usable_text is cleared.
        if status in ("error", "failed", "fetch_error", "timeout",
                      "access_failure", "access-failure", "blocked"):
            qual["excluded"] = True
            qual["usable_text"] = ""
            qual.setdefault("reason", "error payload excluded by default")
            return text, qual
        # Even without an explicit error status, an error-only TEXT is
        # never usable (same shared rule as string payloads).
        if text.strip() and "status" not in qual:
            shared = _string_qual_via_shared(text, url)
            if shared is not None and shared.get("excluded"):
                return text, shared
        if "excluded" not in qual:
            qual["excluded"] = not bool(text.strip())
        qual.setdefault("usable_text", text if not qual["excluded"] else "")
        qual.setdefault("status", "usable" if text.strip() else "empty")
        # Incoherent usable-with-empty-text can never sustain coverage.
        if not (qual.get("usable_text") or "").strip():
            qual["excluded"] = True
            if qual.get("status") in ("usable", "partial"):
                qual["status"] = "empty"
                qual["usable_text"] = ""
        return text, qual
    return "", {"status": "empty", "reason": "unrecognised payload",
                "usable_text": "", "excluded": True}


def _finalize(state: dict, resolved: dict, budget, block: dict | None,
              write, audit, t_start: float, now, run_dir,
              control=None) -> dict:
    """Finalisation with reserved budget: write + audit counted BEFORE the
    call; exhausted budget yields a deterministic partial fallback without
    exceeding the ceiling. Writer failures become partial/failure (never a
    normal delivery); persistence errors are recorded, never silent.
    Tokens/costs come from real data only, else 'unknown'."""
    if block is None:
        block = _ledger.empty_question_coverage(state["run_id"])
    try:
        _elapsed = round(now() - t_start, 3)
    except Exception:
        _elapsed = None
    _control_status(control, state, "finalize", elapsed_s=_elapsed,
                    stop=dict(state.get("stop") or {}))
    state["question_coverage"] = block
    view = {"question": state["question"], "plan": state["plan"],
            "evidence": dict(state["evidence"]),
            "question_coverage": block, "stop": state["stop"],
            "rounds": state["rounds"]}
    # -- write (1 model-boundary call when a real writer is used) ----
    if write is None:
        write = _default_writer
    write_is_default = (write is _default_writer)
    if write_is_default:
        # Deterministic fallback: no model, never spends budget.
        try:
            report_text, selection = _default_writer(view)
        except Exception as exc:
            state["stop"] = {"reason": "failure", "partial": True,
                             "detail": f"writer failed: {exc}"}
            report_text, selection = "", {"included_urls": [], "cuts": str(exc)}
            state["notes"].append(f"writer failure: {exc}")
    elif not _check_model_budget(state, resolved):
        state["notes"].append(
            "write skipped: max_model_calls exhausted -> fallback parcial")
        report_text, selection = _default_writer(view)
        selection = dict(selection or {})
        selection["fallback"] = True
        selection["cuts"] = (str(selection.get("cuts", "")) +
                             " | reserva: teto esgotado, fallback sem chamar modelo")
    else:
        _note_model_call(state)
        try:
            report_text, selection = write(view)
        except TransportError as exc:
            state["stop"] = {"reason": "failure", "partial": True,
                             "detail": f"writer failed: {exc}"}
            report_text, selection = _default_writer(view)
            selection = dict(selection or {})
            selection["fallback"] = True
            selection["cuts"] = (str(selection.get("cuts", "")) +
                                 f" | writer transport falhou: {exc}")
            state["notes"].append(f"writer transport failure: {exc}")
        except Exception as exc:
            state["stop"] = {"reason": "failure", "partial": True,
                             "detail": f"writer failed: {exc}"}
            report_text, selection = _default_writer(view)
            selection = dict(selection or {})
            selection["fallback"] = True
            state["notes"].append(f"writer failure: {exc}")
    state["report"] = {"text": report_text,
                       "sha": _content_hash(report_text or ""),
                       "selection": selection,
                       "words": len((report_text or "").split())}
    # used_in_synthesis = documents really included in the writer prompt.
    # The deterministic fallback has no writer prompt: nothing is counted
    # (honest zero, recorded as fallback), never inferred.
    try:
        if not (selection or {}).get("fallback"):
            _counters.record_used_in_synthesis(
                state, (selection or {}).get("included_urls") or [])
    except Exception as exc:
        state["notes"].append(f"counters used_in_synthesis failed: {exc}")
    # -- audit (transportes efetivos: lotes/votos/reparos/retentativas)
    # Teto imposto ANTES dos transportes reais; quórum/empates/falhas/
    # extração do semantic_review preservados. Teto zero => nenhuma chamada
    # remota; sem saldo p/ revisão completa => não-revisado + parcial.
    # Granularidade declarada: cada voto (_review_pass) é 1 unidade de
    # orçamento; lotes (chunks) dentro do voto são autorizados
    # individualmente via _AUDIT_BUDGET_CHECK (sem chamada quando sem
    # saldo). Uma unidade de operação não equivale a 1 request real —
    # ver docs/OFFLINE_VALIDATION.md (limitação explícita, sem teto
    # global fictício p/ requests internos da biblioteca).
    if audit is None:
        audit = _default_auditor
    audit_is_default = (audit is _default_auditor)
    if audit_is_default:
        import os as _os
        if _os.environ.get("SEMANTIC_REVIEW", "").strip() == "0":
            semantic = {"enabled": False,
                        "verdict_state": "não revisado semanticamente",
                        "accepted": False,
                        "note": "revisão semântica desativada via "
                        "SEMANTIC_REVIEW=0"}
        elif not _check_model_budget(state, resolved):
            state["notes"].append(
                "audit skipped: max_model_calls exhausted (verdict unknown)")
            semantic = {"enabled": False,
                        "verdict_state": "não revisado semanticamente",
                        "accepted": False,
                        "note": "audit skipped: model budget exhausted "
                        "(sem revisão completa sem saldo)"}
        else:
            try:
                import semantic_review as _sr
                _orig_pass = _sr._review_pass
                _orig_check = getattr(_sr, "_AUDIT_BUDGET_CHECK", None)

                def _budget_ok() -> bool:
                    return bool(_check_model_budget(state, resolved))

                async def _counting_pass(items, model, batch_size=12):
                    if not _check_model_budget(state, resolved):
                        raise TransportError(
                            "audit budget exhausted: voto não autorizado")
                    _note_model_call(state)
                    return await _orig_pass(items, model, batch_size)

                _sr._AUDIT_BUDGET_CHECK = _budget_ok
                _sr._review_pass = _counting_pass  # type: ignore
                try:
                    semantic = audit(report_text, dict(state["evidence"]))
                finally:
                    _sr._review_pass = _orig_pass  # type: ignore
                    _sr._AUDIT_BUDGET_CHECK = _orig_check
            except TransportError as exc:
                try:
                    import semantic_review as _sr2
                    _sr2._review_pass = _orig_pass  # type: ignore
                    _sr2._AUDIT_BUDGET_CHECK = _orig_check
                except Exception:
                    pass
                semantic = {"enabled": True,
                            "verdict_state": "revisão incompleta",
                            "accepted": False,
                            "note": f"auditor failure: {exc}"}
            except Exception as exc:
                try:
                    import semantic_review as _sr2
                    _sr2._review_pass = _orig_pass  # type: ignore
                    _sr2._AUDIT_BUDGET_CHECK = _orig_check
                except Exception:
                    pass
                semantic = {"enabled": True,
                            "verdict_state": "revisão incompleta",
                            "accepted": False, "note": f"auditor failure: {exc}"}
    elif not _check_model_budget(state, resolved):
        state["notes"].append(
            "audit skipped: max_model_calls exhausted (verdict unknown)")
        semantic = {"enabled": False, "verdict_state": "não revisado semanticamente",
                    "accepted": False,
                    "note": "audit skipped: model budget exhausted"}
    else:
        _note_model_call(state)
        try:
            semantic = audit(report_text, dict(state["evidence"]))
        except TransportError as exc:
            semantic = {"enabled": True, "verdict_state": "revisão incompleta",
                        "accepted": False, "note": f"auditor failure: {exc}"}
        except Exception as exc:
            semantic = {"enabled": True, "verdict_state": "revisão incompleta",
                        "accepted": False, "note": f"auditor failure: {exc}"}
    if not isinstance(semantic, dict):
        semantic = {"enabled": True, "verdict_state": "revisão incompleta",
                    "accepted": False, "note": "auditor returned non-dict"}
    # Trace report<->audited text: the verdict belongs to exactly this hash.
    semantic.setdefault("audited_sha", _content_hash(report_text or ""))
    state["semantic"] = semantic
    # -- delivery render + four independent verifications -----------------
    # The model text is the synthesis; the renderer is the delivery. Body
    # references come from the real corpus/ledger only (out-of-corpus model
    # URLs are removed and recorded in notes by the renderer).
    report_markdown = report_text or ""
    verification = {}
    quantitative_results: list = []
    try:
        import quantitative as _quant
        for spec in state.get("quantitative_specs") or []:
            try:
                quantitative_results.append(_quant.compute(spec))
            except ValueError as exc:
                state["notes"].append(f"quantitative spec rejected: {exc}")
    except Exception as exc:
        state["notes"].append(f"quantitative module unavailable: {exc}")
    state["quantitative"] = quantitative_results
    try:
        import report_renderer as _renderer
        import verification_report as _verify
        verification = _verify.verify_all(state, ledger=None, audit=semantic,
                                          report_text=None)
        report_markdown = _renderer.render_report(
            state, synthesis_text=report_text or "", verifications=verification,
            quantitative=quantitative_results or None)
        state["verification"] = verification
        cited_urls = list(getattr(_renderer.render_report,
                                  "last_cited_urls", []) or [])
        _counters.record_cited_urls(state, cited_urls)
        # Re-run support against the DELIVERED markdown (references were
        # renumbered/removed), keeping the other dimensions intact.
        verification["dimensions"]["support"] = _verify.verify_support(
            state, report_markdown, semantic)
        verification["overall"] = _verify.aggregate(
            verification["dimensions"])
        state["verification"] = verification
    except Exception as exc:
        state["notes"].append(f"report render failed: {exc}")
        state["verification"] = verification or {}
        try:
            _counters.record_cited(state, report_text or "")
        except Exception:
            pass
    state["report"]["markdown"] = report_markdown
    state["report"]["markdown_sha"] = _content_hash(report_markdown)
    state["report"]["synthesis_sha"] = _content_hash(report_text or "")
    # Semantic NEVER moves question coverage: the block above is untouched.
    # Consistency: partial is true whenever mandatory gaps remain
    # (block incomplete) or the stop itself is partial. criteria_ok with
    # an incomplete block never clears partial (that combination must not
    # happen after _map_stop, but if it does, partial stays true).
    partial = bool(state["stop"].get("partial", True)) or not block.get(
        "complete", False)
    if state["stop"].get("reason") == "criteria_ok" and block.get(
            "complete", False) and not state["stop"].get("partial", False):
        partial = False
    # Consumption AFTER write/audit accounting (reserve respected).
    try:
        elapsed_final = round(now() - t_start, 3)
    except Exception:
        elapsed_final = float(state.get("elapsed_s", 0.0) or 0.0)
    try:
        state["elapsed_s"] = elapsed_final
    except Exception:
        pass
    consumption = dict(state["consumption"])
    try:
        used = budget.snapshot().get("used", {}) if budget is not None else {}
        consumption["budget_used"] = used
    except Exception:
        consumption["budget_used"] = "unknown"
    consumption["tokens"] = "unknown"  # shortcut: no per-call attribution on
    consumption["cost_usd"] = "unknown"  # this path (run_budget documents it)
    result = {
        "run_id": state["run_id"], "mode": "adaptive",
        "profile": state["profile"], "resolved": resolved,
        "plan": state["plan"], "plan_versions": state["plan_versions"],
        "question_coverage": block, "stop": state["stop"],
        "partial": partial,
        "rounds": state["rounds"], "consumption": consumption,
        "report": state["report"], "semantic": semantic,
        "report_markdown": report_markdown,
        "quantitative": quantitative_results,
        "verification": verification,
        "counters": _counters.counters_snapshot(state),
        "elapsed_s": elapsed_final,
    }
    if run_dir is not None:
        try:
            _state.save(run_dir, state)
        except Exception as exc:
            state["notes"].append(f"persist state failed: {exc}")
            if state["stop"].get("reason") != "failure":
                state["stop"] = {"reason": "failure", "partial": True,
                                 "detail": f"persist failed: {exc}"}
                result["stop"] = state["stop"]
                result["partial"] = True
        try:
            from pathlib import Path as _P
            report_path = _P(run_dir) / "report.md"
            report_path.write_text(report_markdown or "", encoding="utf-8")
            result["report_path"] = str(report_path)
            if verification:
                try:
                    import verification_report as _verify_write
                    _verify_write.write_verification(run_dir, verification)
                except Exception as exc:
                    state["notes"].append(
                        f"persist verification failed: {exc}")
            import json as _json
            (_P(run_dir) / "result.json").write_text(
                _json.dumps({k: v for k, v in result.items()
                             if k != "resolved"}, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception as exc:
            # Persistence failures are never silent: recorded + visible.
            state["notes"].append(f"persist artifacts failed: {exc}")
            try:
                _state.save(run_dir, state)
            except Exception:
                pass
    _control_status(control, state, "done", elapsed_s=result["elapsed_s"],
                    stop=result["stop"])
    return result
