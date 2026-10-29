#!/usr/bin/env python3
"""Portuguese structured report renderer (Markdown, stdlib only).

The model text is the *synthesis*; this renderer is the delivery. It fixes the
sections required by modelagem §13, numbers sources from the REAL corpus and
never lets a model-invented URL become a source: out-of-corpus citations are
removed from the body and recorded in ``state['notes']``.

Size follows the profile: ``hard``/``deep`` render the full method, per-round
detail and every note; ``light`` stays concise without hiding uncertainties.
"""
from __future__ import annotations

import time

import research_counters as _counters

_PT = {
    "title": "Relatório de pesquisa",
    "summary": "1. Resposta direta / resumo executivo",
    "method": "2. Escopo, critérios, método e configuração efetiva",
    "findings": "3. Achados por critério",
    "calculations": "4. Comparações e cálculos",
    "limits": "5. Limitações, contradições, incertezas e não investigados",
    "conclusion": "6. Conclusão e próximos passos",
    "sources": "7. Fontes",
    "annex": "8. Anexo: verificações e contadores",
    "closure": "9. Encerramento e rodadas",
    "question": "Pergunta",
    "date": "Data",
    "scope": "Escopo",
    "method_label": "Método",
    "profile": "Perfil",
    "breadth": "Amplitude",
    "depth": "Profundidade",
    "rounds": "Rodadas",
    "concurrency": "Concorrência",
    "budget": "Orçamento",
    "criteria": "Critérios",
    "entities": "Entidades",
    "state": "Estado",
    "justification": "Justificativa",
    "references": "Referências",
    "not_investigated": "não investigado",
    "no_synthesis": ("Sem síntese do modelo para este recorte; os achados e "
                     "limitações abaixo vêm do estado real da execução."),
    "no_plan": "Sem plano de cobertura: a pergunta não foi avaliada.",
    "no_calculations": "Nenhum cálculo reproduzível foi registrado.",
    "gaps": "Lacunas obrigatórias pendentes",
    "contradictions": "Contradições identificadas",
    "uncertainties": "Incertezas e material não verificado",
    "notes": "Notas da execução",
    "next": "Próximo passo",
    "stop": "Motivo de parada",
    "rounds_run": "Rodadas concluídas",
    "sources_note": ("Numeração estável do corpus obtido; nenhuma fonte é "
                     "inventada pelo modelo."),
    "title_col": "Título",
    "obtained_col": "Obtida em",
    "type_col": "Tipo",
    "scope_col": "Alcance lido",
    "no_title": "não registrado",
    "counters": "Contadores de seis estágios",
    "verifications": "Verificações independentes",
    "not_run": "não executada",
    "outside": "Citações fora do corpus (removidas do corpo)",
    "verified_by": "Relatório gerado pelo renderer a partir do estado real; "
                   "texto do modelo preservado como síntese.",
    "state_covered": "coberto",
    "state_partial": "parcial",
    "state_insufficient": "insuficiente",
    "state_contradictory": "contraditório",
    "state_blocked": "bloqueado",
    "state_uninvestigated": "não investigado",
    "state_unevaluated": "não avaliado",
}

_EN = {
    "title": "Research report",
    "summary": "1. Direct answer / executive summary",
    "method": "2. Scope, criteria, method and effective configuration",
    "findings": "3. Findings by criterion",
    "calculations": "4. Comparisons and calculations",
    "limits": "5. Limitations, contradictions, uncertainties and gaps",
    "conclusion": "6. Conclusion and next steps",
    "sources": "7. Sources",
    "annex": "8. Annex: verifications and counters",
    "closure": "9. Closure and rounds",
    "question": "Question",
    "date": "Date",
    "scope": "Scope",
    "method_label": "Method",
    "profile": "Profile",
    "breadth": "Breadth",
    "depth": "Depth",
    "rounds": "Rounds",
    "concurrency": "Concurrency",
    "budget": "Budget",
    "criteria": "Criteria",
    "entities": "Entities",
    "state": "State",
    "justification": "Justification",
    "references": "References",
    "not_investigated": "not investigated",
    "no_synthesis": ("No model synthesis for this scope; findings and "
                     "limitations below come from the real run state."),
    "no_plan": "No coverage plan: the question was not evaluated.",
    "no_calculations": "No reproducible calculation was recorded.",
    "gaps": "Pending mandatory gaps",
    "contradictions": "Identified contradictions",
    "uncertainties": "Uncertainties and unverified material",
    "notes": "Run notes",
    "next": "Next step",
    "stop": "Stop reason",
    "rounds_run": "Completed rounds",
    "sources_note": ("Stable numbering of the obtained corpus; no source is "
                     "invented by the model."),
    "title_col": "Title",
    "obtained_col": "Obtained at",
    "type_col": "Type",
    "scope_col": "Read scope",
    "no_title": "not recorded",
    "counters": "Six-stage counters",
    "verifications": "Independent verifications",
    "not_run": "not run",
    "outside": "Citations outside the corpus (removed from the body)",
    "verified_by": "Report rendered from the real run state; model text kept "
                   "as synthesis.",
    "state_covered": "covered",
    "state_partial": "partial",
    "state_insufficient": "insufficient",
    "state_contradictory": "contradictory",
    "state_blocked": "blocked",
    "state_uninvestigated": "not investigated",
    "state_unevaluated": "not evaluated",
}

_STATE_KEY = {"covered": "state_covered", "partial": "state_partial",
              "insufficient": "state_insufficient",
              "contradictory": "state_contradictory",
              "blocked": "state_blocked",
              "uninvestigated": "state_uninvestigated",
              "unevaluated": "state_unevaluated"}


def _labels(language: str) -> dict:
    return _EN if str(language or "").lower().startswith("en") else _PT


def _norm(url) -> str | None:
    try:
        from scripts import citation_audit as ca
    except ImportError:  # pragma: no cover
        import citation_audit as ca  # type: ignore
    return ca.normalize_url(url)


def _corpus(state: dict) -> list[str]:
    """Obtained corpus in insertion order (URLs, never chunk ids).

    Uses the observed ``obtained`` counter when available, so metadata-only
    records and videos without a transcript never become sources; falls back
    to non-empty evidence for old states without counters.
    """
    evidence = state.get("evidence") or {}
    raw = state.get("counters")
    if isinstance(raw, dict) and isinstance(raw.get("documents"), dict):
        try:
            obtained = set(_counters.counters_snapshot(
                state)["documents"]["obtained"])
        except Exception:
            obtained = set()
        return [u for u, text in evidence.items()
                if isinstance(text, str) and text.strip()
                and _norm(u) in obtained]
    return [u for u, text in evidence.items()
            if isinstance(text, str) and text.strip()]


def _numbers(state: dict) -> dict[str, int]:
    return {_norm(url): i for i, url in enumerate(_corpus(state), 1)
            if _norm(url)}


def _rewrite_refs(text: str, numbers: dict[str, int],
                  cited: set) -> tuple[str, list[str]]:
    """Turn corpus URLs into [n]; strip (and report) out-of-corpus URLs."""
    import re
    outside: list[str] = []

    def md(match):
        label, url = match.group(1), match.group(2)
        norm = _norm(url)
        if norm in numbers:
            cited.add(norm)
            return f"[{label}][{numbers[norm]}]"
        outside.append(url)
        return f"[{label}] (fora do corpus)"

    def bare(match):
        raw = match.group(0)
        url = raw.rstrip(".,;:\"'")
        norm = _norm(url)
        if norm in numbers:
            cited.add(norm)
            return f"[{numbers[norm]}]"
        outside.append(url)
        # URL dentro de literal citado ("plugin": ["x@git+https://..."]) é
        # texto documentado, não citação: preservar em vez de corromper a
        # citação (accept9: 'superpowers@git+[fora do corpus]').
        line_start = match.string.rfind("\n", 0, match.start()) + 1
        prefix = match.string[line_start:match.start()]
        if prefix.count('"') % 2 == 1 or prefix.count("`") % 2 == 1:
            return raw.rstrip(".,;:")
        return "[fora do corpus]"

    src = text or ""
    text = re.sub(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", md, src)
    text = re.sub(r"https?://[^\s`)\]]+", bare, text)
    return text, outside


def _fmt(value, default="—") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _state_label(labels: dict, state_of: str) -> str:
    return labels.get(_STATE_KEY.get(state_of, "state_uninvestigated"),
                      state_of or "?")


def _refs(crit: dict, numbers: dict[str, int], labels: dict,
          cited: set) -> str:
    out = []
    for ref in crit.get("references", []) or []:
        url = (ref or {}).get("url", (ref or {}).get("doc_id", ""))
        norm = _norm(url)
        if norm in numbers:
            cited.add(norm)
            out.append(f"[{numbers[norm]}]")
        elif url:
            out.append(f"({labels['not_investigated']}: {url})")
    return ", ".join(out)


def _source_rows(state: dict) -> list[dict]:
    snapshot = _counters.counters_snapshot(state)
    meta = snapshot.get("meta") or {}
    rows = []
    for n, url in enumerate(_corpus(state), 1):
        info = meta.get(_norm(url)) or {}
        qual = (state.get("qualification") or {}).get(url) or {}
        raw = info.get("raw_chars")
        usable = info.get("usable_chars")
        if raw is None:
            raw = len((state.get("evidence") or {}).get(url) or "")
            usable = len(qual.get("usable_text") or "")
        rows.append({
            "n": n, "url": url,
            "title": info.get("title") or qual.get("title"),
            "obtained_at": info.get("obtained_at"),
            "type": info.get("type") or _counters.classify_type(url, "", qual),
            "status": info.get("status") or qual.get("status"),
            "scope": f"{usable}/{raw} chars",
        })
    return rows


def _channel_line(state: dict, labels: dict) -> str:
    """User-visible collection outcome per channel (accept1 honesty gap).

    Transport failures lived only in verification.json; the user-facing
    report never said web search had failed 9 times. Counts come from the
    observed round ops (channel/outcome), never inferred.
    """
    seen: dict = {}
    for rnd in state.get("rounds") or []:
        for op in (rnd or {}).get("ops") or []:
            if not isinstance(op, dict):
                continue
            ch = op.get("channel") or "?"
            bucket = seen.setdefault(ch, {"ok": 0, "fail": 0, "other": 0})
            out = op.get("outcome")
            if out in ("new_useful", "confirmed", "duplicate"):
                bucket["ok"] += 1
            elif out == "failed":
                bucket["fail"] += 1
            else:
                bucket["other"] += 1
    if not seen:
        return f"- **Coleta por canal:** {labels.get('unknown', 'desconhecida')}"
    parts = [f"{ch}: {b['ok']} ok / {b['fail']} falha(s)"
             + (f" / {b['other']} outro(s)" if b["other"] else "")
             for ch, b in sorted(seen.items())]
    return "- **Coleta por canal:** " + "; ".join(parts)


def _method_section(state: dict, labels: dict, verbose: bool) -> list[str]:
    config = dict(state.get("config_applied") or {})
    resolved = dict(state.get("resolved") or {})
    plan = state.get("plan") or {}
    budget = config.get("budget") or resolved.get("budget") or {}
    consumption = state.get("consumption") or {}
    used = consumption.get("budget_used")
    criteria = plan.get("criteria") or []
    entities = plan.get("entities") or []
    rounds_done = max(0, len(state.get("rounds") or []) - 1)
    lines = [f"## {labels['method']}", "",
             f"- **{labels['question']}:** {state.get('question', '')}",
             f"- **{labels['date']}:** {_fmt(state.get('created_at'))} "
             f"(gerado em {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})",
             f"- **{labels['profile']}:** {_fmt(state.get('profile'))}",
             f"- **{labels['breadth']}:** "
             f"{_fmt(config.get('DEEP_RESEARCH_BREADTH', resolved.get('DEEP_RESEARCH_BREADTH')))} "
             f"| **{labels['depth']}:** "
             f"{_fmt(config.get('DEEP_RESEARCH_DEPTH', resolved.get('DEEP_RESEARCH_DEPTH')))}",
             f"- **{labels['rounds']}:** {_fmt(config.get('max_rounds', resolved.get('max_rounds')))} "
             f"({labels['rounds_run']}: {rounds_done})",
             f"- **{labels['concurrency']}:** "
             f"{_fmt(config.get('concurrency', resolved.get('concurrency')))}",
             f"- **{labels['budget']}:** limites={budget or 'unknown'}; "
             f"consumido={used if used is not None else 'unknown'}; "
             f"tokens={consumption.get('tokens', 'unknown')}; "
             f"custo={consumption.get('cost_usd', 'unknown')}",
             f"- **{labels['criteria']}:** {len(criteria)} | "
             f"**{labels['entities']}:** {len(entities)}",
             _channel_line(state, labels), ""]
    if verbose:
        if criteria:
            lines.append("")
            lines.append("| Critério | Obrigatório | Entidades |")
            lines.append("|---|---|---|")
            for crit in criteria:
                lines.append(f"| {crit.get('label', crit.get('id'))} | "
                             f"{bool(crit.get('required', True))} | "
                             f"{crit.get('applies_to') or 'todas'} |")
        if entities:
            lines.append("")
            lines.append(f"- Entidades do plano: "
                         f"{', '.join(e.get('label', e.get('id', '?')) for e in entities)}")
    return lines


def _findings_section(state: dict, labels: dict, numbers: dict,
                      verbose: bool, cited: set) -> list[str]:
    block = state.get("question_coverage") or {}
    criteria = block.get("criteria") or []
    lines = [f"## {labels['findings']}", ""]
    if not criteria:
        lines.append(labels["no_plan"])
        return lines
    for crit in criteria:
        state_of = crit.get("state", "uninvestigated")
        lines.append(f"### {crit.get('label', crit.get('id'))} — "
                     f"{_state_label(labels, state_of)}")
        justification = (crit.get("justification") or "").strip()
        if not justification:
            justification = labels["not_investigated"]
        if not verbose and len(justification) > 600:
            justification = justification[:600].rstrip() + " […]"
        lines.append(justification)
        refs = _refs(crit, numbers, labels, cited)
        if refs:
            lines.append(f"{labels['references']}: {refs}")
        entity_states = crit.get("entity_states")
        if entity_states:
            lines.append("")
            lines.append("| Entidade | Estado |")
            lines.append("|---|---|")
            for eid, est in entity_states.items():
                lines.append(f"| {eid} | {_state_label(labels, est)} |")
        lines.append("")
    return lines


def _limits_section(state: dict, labels: dict, verbose: bool) -> list[str]:
    block = state.get("question_coverage") or {}
    gaps = list(block.get("gaps") or [])
    for gap in state.get("gaps") or []:
        if gap.get("criterion_id") not in {g.get("criterion_id") for g in gaps}:
            gaps.append(gap)
    lines = [f"## {labels['limits']}", ""]
    if gaps:
        lines.append(f"### {labels['gaps']}")
        for gap in gaps:
            lines.append(f"- **{gap.get('label', gap.get('criterion_id'))}** "
                         f"({_state_label(labels, gap.get('state', '?'))}): "
                         f"{gap.get('justification', '')}")
            if gap.get("next"):
                lines.append(f"  - {labels['next']}: {gap['next']}")
    contradictions = [c for c in (block.get("criteria") or [])
                      if c.get("state") == "contradictory"]
    if contradictions:
        lines.append("")
        lines.append(f"### {labels['contradictions']}")
        for crit in contradictions:
            lines.append(f"- {crit.get('label', crit.get('id'))}: "
                         f"{crit.get('justification', '')}")
    unverified = [c for c in (block.get("criteria") or [])
                  if c.get("state") in ("insufficient", "blocked",
                                        "uninvestigated")]
    lines.append("")
    lines.append(f"### {labels['uncertainties']}")
    if unverified:
        for crit in unverified:
            lines.append(f"- {crit.get('label', crit.get('id'))}: "
                         f"{_state_label(labels, crit.get('state'))} — "
                         f"{crit.get('justification') or labels['not_investigated']}")
    else:
        lines.append("- Nenhum critério obrigatório ficou sem verificação "
                     "declarada; incertezas residuais seguem nas notas.")
    outside = _counters.counters_snapshot(state).get(
        "outside_corpus_citations") or []
    if outside:
        lines.append("")
        lines.append(f"### {labels['outside']}")
        for url in outside:
            lines.append(f"- {url}")
    notes = [n for n in (state.get("notes") or []) if isinstance(n, str)]
    if notes:
        shown = notes if verbose else notes[-5:]
        lines.append("")
        lines.append(f"### {labels['notes']}")
        for note in shown:
            lines.append(f"- {note}")
    return lines


def _sources_section(state: dict, labels: dict) -> list[str]:
    rows = _source_rows(state)
    lines = [f"## {labels['sources']}", "", labels["sources_note"], ""]
    if not rows:
        lines.append("Nenhuma fonte com conteúdo obtido.")
        return lines
    lines.append(f"| # | URL | {labels['title_col']} | "
                 f"{labels['obtained_col']} | {labels['type_col']} | "
                 f"{labels['scope_col']} |")
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| [{row['n']}] | {row['url']} | "
            f"{_fmt(row['title'], labels['no_title'])} | "
            f"{_fmt(row['obtained_at'])} | {_fmt(row['type'])} | "
            f"{row['scope']} ({_fmt(row['status'])}) |")
    return lines


def _annex_section(state: dict, labels: dict, verifications: dict | None,
                   verbose: bool) -> list[str]:
    lines = [f"## {labels['annex']}", ""]
    lines.append(f"### {labels['verifications']}")
    dims = (verifications or {}).get("dimensions") or {}
    if not dims:
        lines.append(f"- {labels['not_run']} (nenhuma verificação fornecida)")
    else:
        lines.append("| Dimensão | Estado | Evidência |")
        lines.append("|---|---|---|")
        for name in ("execution", "question", "review", "support"):
            dim = dims.get(name) or {}
            evidence = dim.get("evidence") or {}
            if verbose:
                shown = ", ".join(f"{k}={v}" for k, v in evidence.items())
                if len(shown) > 400:
                    shown = shown[:400] + " […]"
            else:
                shown = f"{len(evidence)} campo(s)"
            lines.append(f"| {name} | {_fmt(dim.get('status'), labels['not_run'])} "
                         f"| {shown} |")
        for dim in dims.values():
            for note in dim.get("notes") or []:
                lines.append(f"- {dim.get('dimension')}: {note}")
    counters = _counters.counters_snapshot(state)
    lines.append("")
    lines.append(f"### {labels['counters']}")
    lines.append("| Estágio | Documentos |")
    lines.append("|---|---:|")
    for stage in _counters.STAGES:
        lines.append(f"| {stage} | {counters['counts'].get(stage, 0)} |")
    relations = counters.get("relations") or []
    if relations:
        lines.append("")
        lines.append("| Relação | Documentos | Tipo |")
        lines.append("|---|---|---|")
        for rel in relations:
            lines.append(f"| {rel.get('kind')} | {rel.get('url')} ↔ "
                         f"{rel.get('related_to')} | {rel.get('detail', '')} |")
    return lines


def _closure_section(state: dict, labels: dict, verbose: bool) -> list[str]:
    stop = state.get("stop") or {}
    rounds = state.get("rounds") or []
    lines = [f"## {labels['closure']}", "",
             f"- **{labels['stop']}:** {_fmt(stop.get('reason'))} — "
             f"{_fmt(stop.get('detail'), '')}",
             f"- **{labels['rounds_run']}:** {max(0, len(rounds) - 1)}",
             f"- **Parcial:** {bool(stop.get('partial'))}"]
    if verbose and rounds:
        lines.append("")
        lines.append("| Rodada | Tipo | Lacunas-alvo | Evidência nova | "
                     "Delta | Decisão |")
        lines.append("|---|---|---|---|---|---|")
        for rnd in rounds:
            lines.append(
                f"| {rnd.get('round')} | {rnd.get('kind')} | "
                f"{', '.join(rnd.get('target_gaps') or []) or '—'} | "
                f"{rnd.get('new_evidence')} | {rnd.get('delta')} | "
                f"{str(rnd.get('decision', ''))[:120]} |")
    return lines


def render_report(state: dict, *, synthesis_text: str,
                  verifications: dict | None = None,
                  quantitative: list | None = None,
                  language: str = "pt-BR") -> str:
    """Render the delivery Markdown from the real run state."""
    labels = _labels(language)
    verbose = str(state.get("profile", "")).lower() in ("hard", "deep")
    numbers = _numbers(state)
    cited: set = set()
    synthesis = synthesis_text or ""
    synthesis, outside = _rewrite_refs(synthesis, numbers, cited)
    if outside:
        recorded = set(n for n in (state.get("notes") or [])
                       if isinstance(n, str))
        for url in outside:
            note = (f"render: síntese citou URL fora do corpus e ela foi "
                    f"removida das fontes: {url}")
            if note not in recorded:
                state.setdefault("notes", []).append(note)
                recorded.add(note)
    block = state.get("question_coverage") or {}
    status = block.get("status", "unevaluated")
    lines = [f"# {labels['title']}: {state.get('question', '')}", "",
             labels["verified_by"], "",
             f"**Status da cobertura:** {_state_label(labels, status)} "
             f"(proportion={block.get('proportion')}) · "
             f"**{labels['stop']}:** {_fmt((state.get('stop') or {}).get('reason'))}",
             "", f"## {labels['summary']}", ""]
    if synthesis.strip():
        lines.append(synthesis.strip())
    else:
        lines.append(labels["no_synthesis"])
    lines.append("")
    lines.extend(_method_section(state, labels, verbose))
    lines.append("")
    lines.extend(_findings_section(state, labels, numbers, verbose, cited))
    if quantitative:
        lines.append(f"## {labels['calculations']}")
        lines.append("")
        try:
            import quantitative as _quant
            for result in quantitative:
                if isinstance(result, dict) and "formula_id" in result:
                    lines.append(_quant.to_markdown_block(result))
                    lines.append("")
                else:
                    lines.append(f"- Resultado inválido ignorado: {result!r}")
        except ValueError as exc:
            lines.append(f"- Cálculo inválido: {exc}")
        lines.append("")
    lines.extend(_limits_section(state, labels, verbose))
    lines.append("")
    lines.append(f"## {labels['conclusion']}")
    lines.append("")
    if block.get("complete"):
        lines.append("Os critérios obrigatórios estão cobertos pelas "
                     "evidências registradas; ver ressalvas e verificações.")
    else:
        lines.append("A investigação é **parcial**: há critérios obrigatórios "
                     "sem cobertura suficiente (ver seção 5). A conclusão não "
                     "pode ser apresentada como completa.")
    gaps = block.get("gaps") or []
    if gaps:
        lines.append("")
        lines.append(f"**{labels['next']}:**")
        for gap in gaps:
            lines.append(f"- {gap.get('label', gap.get('criterion_id'))}: "
                         f"{gap.get('next', 'investigar com nova evidência')}")
    lines.append("")
    lines.extend(_sources_section(state, labels))
    lines.append("")
    lines.extend(_annex_section(state, labels, verifications, verbose))
    lines.append("")
    lines.extend(_closure_section(state, labels, verbose))
    lines.append("")
    render_report.last_cited_urls = sorted(cited)  # type: ignore[attr-defined]
    return "\n".join(lines)


render_report.last_cited_urls = []  # type: ignore[attr-defined]
