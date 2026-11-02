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
    "state_not_applicable": "não aplicável",
    "state_uninvestigated": "não investigado",
    "state_unevaluated": "não avaliado",
    "common_scope": "Alcance examinado comum",
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
    "state_not_applicable": "not applicable",
    "state_uninvestigated": "not investigated",
    "state_unevaluated": "not evaluated",
    "common_scope": "Common examined scope",
}

_STATE_KEY = {"covered": "state_covered", "partial": "state_partial",
              "insufficient": "state_insufficient",
              "contradictory": "state_contradictory",
              "blocked": "state_blocked",
              "not_applicable": "state_not_applicable",
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


def _lookup_number(url, numbers: dict) -> tuple:
    """Corpus (key, number) tolerating a trailing-slash variant.

    Generic, no product literals: writers often emit the same document
    URL with/without a trailing slash while the corpus holds one form.
    Try the normalized URL first, then the slash-toggled alternate, so
    an in-corpus citation never reads as out-of-corpus over a slash.
    Returns (key, number) or (None, None). Global URL identity is
    untouched — the tolerance lives only in this lookup.
    """
    norm = _norm(url)
    if norm is None:
        return None, None
    try:
        if norm in numbers:
            return norm, numbers[norm]
        if norm.endswith("/"):
            alt = norm.rstrip("/")
        else:
            alt = norm + "/"
        if alt in numbers:
            return alt, numbers[alt]
    except Exception:
        pass
    return None, None


def _strip_fonte_placeholder(text: str) -> str:
    """Remove a residual [(fonte)] citation placeholder, keeping the rest.

    Generic, no product literals: the writer must never emit the token
    (its prompt forbids it), but model text may still carry it next to a
    real [N] (``[(fonte)][8]`` -> ``[8]``) or an outside-corpus marker.
    Only the token is removed; numbers and markers stay.
    """
    import re as _re
    try:
        return _re.sub(r"\[\(\s*fonte\s*\)\]", "",
                       str(text or ""), flags=_re.IGNORECASE)
    except Exception:
        return str(text or "")


def _corpus(state: dict) -> list[str]:
    """Obtained corpus in insertion order (URLs, never chunk ids).

    Uses the observed ``obtained`` counter when available, so metadata-only
    records and videos without a transcript never become sources; falls back
    to non-empty evidence for old states without counters.
    user://context/* nunca e corpus (premissa explicita, sem numero).
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
                and not (isinstance(u, str) and u.startswith("user://"))
                and _norm(u) in obtained]
    return [u for u, text in evidence.items()
            if isinstance(text, str) and text.strip()
            and not (isinstance(u, str) and u.startswith("user://"))]


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
        key, num = _lookup_number(url, numbers)
        # Placeholder [(fonte)] never survives: keep only the number or
        # the outside marker (other labels are preserved as written).
        bare_label = (label or "").strip().lower() in ("(fonte)", "fonte")
        if num is not None:
            cited.add(key)
            return f"[{num}]" if bare_label else f"[{label}][{num}]"
        outside.append(url)
        return "(fora do corpus)" if bare_label else f"[{label}] (fora do corpus)"

    def bare(match):
        raw = match.group(0)
        url = raw.rstrip(".,;:\"'”’“‘")
        key, num = _lookup_number(url, numbers)
        if num is not None:
            cited.add(key)
            return f"[{num}]{raw[len(url):]}"
        # URL dentro de literal citado ("plugin": ["x@git+https://..."]) é
        # texto documentado, não citação: preservar em vez de corromper a
        # citação (accept9: 'superpowers@git+[fora do corpus]'). Preservada
        # como literal, nunca registrada em outside.
        line_start = match.string.rfind("\n", 0, match.start()) + 1
        prefix = match.string[line_start:match.start()]
        if (prefix.count('"') % 2 == 1 or prefix.count("`") % 2 == 1
                or prefix.count("“") % 2 == 1 or prefix.count("‘") % 2 == 1):
            return raw.rstrip(".,;:")
        outside.append(url)
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
        key, num = _lookup_number(url, numbers)
        if num is not None:
            cited.add(key)
            out.append(f"[{num}]")
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


def _scope_key(scope: str) -> str:
    """Chave de comparação de escopo: sem acento, caixa e espaços extras."""
    try:
        key = _strip_accents(scope)
    except Exception:
        key = str(scope or "").lower()
    return " ".join(key.split())


def _common_examined_scope(state: dict) -> tuple[str | None, int]:
    """Escopo examinado mais frequente entre os critérios (colapso G2).

    Retorna (escopo, nº de critérios idênticos) quando algum texto se
    repete (≥2×); caso contrário (None, 0) e cada critério mostra o seu.
    Comparação por chave normalizada; exibe o texto original.
    """
    try:
        criteria = ((state.get("question_coverage") or {}).get("criteria")
                    or [])
        counts: dict[str, int] = {}
        original: dict[str, str] = {}
        for crit in criteria:
            scope = str((crit or {}).get("examined_scope") or "").strip()
            if scope:
                key = _scope_key(scope)
                counts[key] = counts.get(key, 0) + 1
                original.setdefault(key, scope)
        if not counts:
            return None, 0
        top = max(counts, key=lambda s: counts[s])
        if counts[top] < 2:
            return None, 0
        return original[top], counts[top]
    except Exception:
        return None, 0


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
    common_scope, common_n = _common_examined_scope(state)
    if common_scope:
        body = common_scope.strip()
        if body.lower().startswith("alcance examinado:"):
            body = body.split(":", 1)[1].strip()
        body = body[:1].upper() + body[1:] if body else body
        lines.append(f"- **{labels['common_scope']} ({common_n} "
                     f"{labels['criteria'].lower()}):** {body}")
        lines.append("")
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
    common_scope, _common_n = _common_examined_scope(state)
    seen_scopes: set[str] = {_scope_key(common_scope)} if common_scope \
        else set()
    for crit in criteria:
        state_of = crit.get("state", "uninvestigated")
        lines.append(f"### {crit.get('label', crit.get('id'))} — "
                     f"{_state_label(labels, state_of)}")
        justification = (crit.get("justification") or "").strip()
        if not justification:
            justification = labels["not_investigated"]
        if not verbose and len(justification) > 600:
            justification = _cut_at_sentence(justification, 600)
        lines.append(justification)
        refs = _refs(crit, numbers, labels, cited)
        if refs:
            lines.append(f"{labels['references']}: {refs}")
        entity_states = crit.get("entity_states")
        try:
            _labels_by_id = {
                e.get("id"): (e.get("label") or e.get("id"))
                for e in (state.get("plan") or {}).get("entities", [])
                if isinstance(e, dict)}
        except Exception:
            _labels_by_id = {}
        if entity_states:
            lines.append("")
            lines.append("| Entidade | Estado |")
            lines.append("|---|---|")
            for eid, est in entity_states.items():
                lines.append(f"| {_labels_by_id.get(eid, eid)} | "
                             f"{_state_label(labels, est)} |")
        if crit.get("examined_scope"):
            _scope = str(crit["examined_scope"])
            # G2: texto idêntico colapsa — o comum vive no bloco de
            # método (1×); aqui só o delta (1ª ocorrência de cada texto
            # distinto; estados por entidade seguem na tabela acima).
            # Escopo igual ao comum ganha marcador idem (nunca some
            # silenciosamente); comparação por chave normalizada.
            _key = _scope_key(_scope)
            if _key and _key not in seen_scopes:
                seen_scopes.add(_key)
                lines.append(_scope[:1].upper() + _scope[1:]
                             if _scope else _scope)
            elif _key and common_scope and _key == _scope_key(common_scope):
                lines.append("- Idem ao escopo comum do método (§2).")
        for nc in crit.get("na_cells", []) or []:
            _nc_label = _labels_by_id.get(nc.get("entity_id"),
                                          nc.get("entity_id"))
            lines.append(
                f"- **N/A** {_nc_label}: "
                f"{(nc.get('justification') or '').strip() or labels['not_investigated']}")
        lines.append("")
    return lines


_DEBUG_NOTE_PREFIXES = (
    "evaluation revised", "semantic boost", "unexplored reconciliado",
    "synthesis criterion", "citação ajustada", "citação ajustada por",
    "tighten citations", "discovery", "substitution", "promotion",
    "truncado", "teto de seleção", "janela de relevancia",
    "ordem semântica", "render: síntese citou",
    "downgrade", "not_applicable", "not-applicable",
    "identity-mismatch", "identity mismatch",
    "veto fora-do-corpus", "partial declarado",
    "boilerplate ignorado", "lote por diversidade",
    "reenvio de quarentena", "proporcional:",
    "per_candidate bound", "resume:",
    "transport failure", "pool reserve", "assessor",
    "fetch failure", "repo minerado", "link-following",
    "rodízio", "op ",
)

_DEBUG_NOTE_SUBSTRINGS = (
    # Jargão interno de estabilização/transporte/semântica (genérico,
    # sem literais de produto): diagnóstico vai ao anexo §8, nunca ao
    # corpo visível (§5). Comparação sem acento e por conteúdo, pois
    # linhas de operação ("op r6-c3-0 ...") trazem o marcador no meio.
    "transport failure", "fetch failure", "fetch failed", "read_source",
    "transient failure", "retrying", "budget counted",
    "pool reserve", "repo minerado", "link-following", "minerad",
    "candidato minerado", "assessor",
    "downgrade", "without new evidence", "rejected for", "kept partial",
    "kept as", "said insuffici",
    "identity mismatch", "sem mencao a entidade", "hit ignorado",
    "ignorado",
    "quarentena", "semantic boost", "vetorizad",
    "per_candidate", "discovery", "proporcional",
    "rodizio", "gap_query", "entidades com gaps",
    "reconciliad", "synthesis criterion", "evaluation revised",
    "tighten",
    "retriever_unavailable", "gateway failed", "fallback failed",
    "searxng", "timeout", "urlerror",
    "html_without_content", "not_a_github",
    "unavailable", "failure", "failed",
    "fora da cobertura", "alem do teto", "cheio (",
)


def _cut_at_sentence(text: str, limit: int = 600) -> str:
    """Cut at a sentence boundary, never mid-word (generic).

    Returns text unchanged when short; otherwise cuts at the last
    sentence terminator (`.`, `!`, `?`) within the limit, falling back
    to the last space wherever it is. A hard cut happens only when the
    window has no space at all, marked explicitly with [[truncado]].
    """
    try:
        s = str(text or "")
        if len(s) <= limit:
            return s
        window = s[:limit]
        import re as _re3
        marks = [m.end() for m in _re3.finditer(r"[.!?…][\s\"”’)]*",
                                                window)]
        if marks:
            return window[:marks[-1]].rstrip() + " […]"
        sp = window.rfind(" ")
        if sp > 0:
            return window[:sp].rstrip() + " […]"
        return window.rstrip() + " [[truncado]]"
    except Exception:
        try:
            return str(text or "")[:limit].rstrip() + " […]"
        except Exception:
            return ""


def _strip_accents(text: str) -> str:
    """Minúsculas sem acento para comparar nota interna (EN/PT)."""
    import unicodedata
    try:
        return "".join(
            ch for ch in unicodedata.normalize(
                "NFKD", str(text or "")) if not unicodedata.combining(ch)
        ).lower()
    except Exception:
        return str(text or "").lower()


def _is_debug_note(note: str) -> bool:
    """Resíduo interno (diagnóstico/auditoria) vs nota ao usuário.

    Diagnóstico e auditoria vivem em state['notes'] + verification.json;
    só notas voltadas ao usuário vão ao corpo (§5). O anexo técnico
    (§8) lista os resíduos classificados — nada é apagado do state.
    Corpo visível só carrega PT com valor de decisão; EN e jargão de
    estabilização/transporte/semântica vão ao anexo. Comparação sem
    acento, por prefixo ou por marcador interno de conteúdo (linhas
    de operação trazem o marcador no meio, ex. "op r6-c3-0 ...").
    shortcut: classificação por prefixo/marcador; se novo emissor
    surgir sem marcador listado, ele aparece no corpo até ser
    classificado.
    """
    try:
        low = _strip_accents(note).strip()
        if any(low.startswith(_strip_accents(p).strip())
               for p in _DEBUG_NOTE_PREFIXES):
            return True
        return any(marker in low for marker in _DEBUG_NOTE_SUBSTRINGS)
    except Exception:
        return False


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
    shown_user = [n for n in notes if not _is_debug_note(n)]
    # Dedup exato: notas de usuário idênticas (string completa) aparecem
    # 1×. Entradas discovery:/alcance que diferem por critério/entidade
    # são preservadas — o detalhe vive no state, o anexo não colapsa por
    # prefixo-contagem.
    try:
        _deduped: list[str] = []
        _seen_notes: set[str] = set()
        for _n in shown_user:
            _k = str(_n or "").strip()
            if _k in _seen_notes:
                continue
            _seen_notes.add(_k)
            _deduped.append(_n)
        shown_user = _deduped
    except Exception:
        pass
    if shown_user:
        shown = shown_user if verbose else shown_user[-5:]
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
                   verbose: bool, cited: set | None = None) -> list[str]:
    lines = [f"## {labels['annex']}", ""]
    lines.append(f"### {labels['verifications']}")
    dims = (verifications or {}).get("dimensions") or {}
    if not dims:
        lines.append(f"- {labels['not_run']} (nenhuma verificação fornecida)")
    else:
        lines.append("| Dimensão | Estado | Evidência |")
        lines.append("|---|---|---|")
        for name, dim in dims.items():
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
    if cited is not None:
        # O snapshot é lido antes de o coordinator registrar as citações
        # (record_cited roda depois do render), então a tabela do próprio
        # relatório mostrava cited=0 enquanto o texto citava [1]..[n]
        # (accept11: counters.json=7, tabela=0). Conta as URLs citadas
        # neste render.
        counters.setdefault("counts", {})["cited"] = len(cited)
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
    # M9 reading metric: share of the collected corpus actually sent to the
    # assessor/writer in excerpts. New-URL saturation is not exhausted
    # analysis — the metric never alters coverage.
    reading = state.get("reading") or {}
    collected = reading.get("collected_chars") or 0
    excerpted = reading.get("excerpted_chars") or 0
    lines.append("")
    if collected or excerpted:
        pct = min(100.0, excerpted / collected * 100.0) if collected else 0.0
        _unique = int(reading.get("docs_excerpted_unique") or 0)
        _batches = int(reading.get("docs_excerpted", 0) or 0)
        _analyzed = int(counters["counts"].get("analyzed", 0))
        lines.append(
            f"**Leitura:** {pct:.1f}% dos caracteres do corpus incluídos "
            f"em excertos avaliados ({excerpted}/{collected} chars; "
            f"{_batches} batches de excerto em {_unique} docs únicos de "
            f"{reading.get('docs_collected', 0)} coletados; avaliados "
            f"únicos pelo assessor: {_analyzed})")
        lines.append("saturação de URLs novas ≠ análise esgotada; batches "
                     "contam repetições entre chamadas, únicos não")
    else:
        lines.append("**Leitura:** não medida")
    _debug = [n for n in (state.get("notes") or [])
              if isinstance(n, str) and _is_debug_note(n)]
    try:
        _dd: list[str] = []
        _seen_d: set[str] = set()
        for _n in _debug:
            _k = str(_n or "").strip()
            if _k in _seen_d:
                continue
            _seen_d.add(_k)
            _dd.append(_n)
        _debug = _dd
    except Exception:
        pass
    if _debug:
        lines.append("")
        lines.append("### Notas técnicas (diagnóstico interno)")
        for note in _debug:
            lines.append(f"- {note}")
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


def _veto_outside_corpus(state: dict, synthesis: str) -> str:
    """Veto a 'fora do corpus' quando há doc da entidade no corpus.

    Genérico (sem literais): se a síntese afirma ausência no corpus mas
    alguma entidade exigida tem documento utilizável que a nomeia no corpo
    (identidade estrita, sem contar slug de URL), a afirmação é sobre a
    janela do writer, nunca sobre o corpus integral — reescreve SOMENTE
    as frases que dispararam o veto para 'fora da seleção do writer
    (LACUNA de análise; ler a seguir)' e registra nota. Frases de outras
    entidades seguem intactas.
    """
    try:
        low = str(synthesis or "").lower()
        if "fora do corpus" not in low:
            return synthesis
        try:
            import verification_report as _vr
            _mentioned = _vr._entity_mentioned
        except Exception:
            _mentioned = None
        plan = state.get("plan") or {}
        evidence = state.get("evidence") or {}
        qualification = state.get("qualification") or {}
        entities = [e for e in (plan.get("entities") or [])
                    if isinstance(e, dict)]
        if not entities:
            return synthesis

        def _has_doc(_ent: dict) -> str:
            _label = str(_ent.get("label") or "")
            _eid = _ent.get("id")
            for url, text in (evidence or {}).items():
                if not isinstance(url, str) or url.startswith("user://"):
                    continue
                try:
                    _q = (qualification.get(url) or {})
                    if _q.get("excluded"):
                        continue
                    body = str(_q.get("usable_text") or text or "")
                except Exception:
                    body = str(text or "")
                if not body.strip():
                    continue
                try:
                    if _mentioned is not None:
                        _hit = bool(_mentioned(_label, _eid, body))
                    else:
                        _hit = bool(_label and _label.lower()
                                    in body.lower())
                except Exception:
                    _hit = False
                if _hit:
                    return str(_ent.get("source_url") or url)
            return ""

        import re as _re0
        import re as _re2
        sentences = _re0.split(r"(?<=[.!?])\s+|\n+", str(synthesis or ""))
        out = str(synthesis or "")
        rewrote = 0
        for sent in sentences:
            if "fora do corpus" not in sent.lower():
                continue
            _hint = ""
            for _ent in entities:
                try:
                    if _mentioned is not None:
                        _named = bool(_mentioned(
                            str(_ent.get("label") or ""), _ent.get("id"),
                            sent))
                    else:
                        _lb = str(_ent.get("label") or "").strip().lower()
                        _named = bool(_lb and _lb in sent.lower())
                except Exception:
                    _named = False
                if not _named:
                    continue
                _hint = _has_doc(_ent)
                if _hint:
                    break
                # Entidade citada sem doc: esta frase não dispara veto.
                _hint = ""
            if not _hint:
                continue
            repl = ("fora da seleção do writer (LACUNA de análise; ler a "
                    "seguir" + (f": {_hint}" if _hint else "") + ")")
            try:
                _fixed = _re2.sub(r"fora do corpus", repl, sent,
                                  flags=_re2.IGNORECASE)
            except Exception:
                continue
            if _fixed != sent and sent and sent in out:
                out = out.replace(sent, _fixed, 1)
                rewrote += 1
        if not rewrote:
            return synthesis
        try:
            state.setdefault("notes", []).append(
                "veto fora-do-corpus: afirmação de ausência reescrita para "
                "fora da seleção (há doc da entidade no corpus)")
        except Exception:
            pass
        return out
    except Exception:
        return synthesis


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
    try:
        synthesis = _veto_outside_corpus(state, synthesis)
    except Exception:
        pass
    synthesis, outside = _rewrite_refs(synthesis, numbers, cited)
    synthesis = _strip_fonte_placeholder(synthesis)
    # Citação x entidade: remove citação conjuntiva frouxa (só um dos docs
    # trata da entidade) quando resta citação que sustenta; sem máscara
    # (frase só com citação frouxa segue para a auditoria sinalizar).
    try:
        import verification_report as _verify
        _n_to_url = {n: url for url, n in numbers.items()}
        synthesis, _tight_notes = _verify._tighten_citations(
            synthesis, _n_to_url, dict(state.get("evidence") or {}),
            state.get("plan") or {})
        synthesis = _strip_fonte_placeholder(synthesis)
        _recorded_tight = set(n for n in (state.get("notes") or [])
                              if isinstance(n, str))
        for _note in _tight_notes:
            if _note not in _recorded_tight:
                state.setdefault("notes", []).append(_note)
                _recorded_tight.add(_note)
    except Exception as exc:
        state.setdefault("notes", []).append(
            f"tighten citations skipped: {exc}")
    render_report.last_synthesis = synthesis  # type: ignore[attr-defined]
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
             ""]
    # Definição estável da cobertura: numerador/denominador explícitos para
    # que o percentual seja auditável contra o plano final (M6). Ausente em
    # runs antigas -> linha omitida, nunca inventada.
    if block.get("denominator") is not None:
        lines += [f"**Cobertura:** {block.get('numerator')}/"
                  f"{block.get('denominator')} células obrigatórias — "
                  f"{block.get('definition', '')}", ""]
    if block.get("na"):
        lines += [f"**N/A:** {block.get('na')} célula(s) fora do escopo "
                  f"documentado — fora do denominador, listadas nos Achados, "
                  f"nunca contam como cobertura.", ""]
    lines += [f"## {labels['summary']}", ""]
    if synthesis.strip():
        # Numeração única: a síntese traz seus próprios '## N' internos;
        # rebaixados para '###' para não colidir com as seções do renderer
        # (§§1-9). Defesa no renderer, nunca edição manual do artefato.
        import re as _re
        _demoted = _re.sub(r"(?m)^##(?!#)", "###", synthesis.strip())
        lines.append(_demoted)
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
        # §6 não relista: detalhe por lacuna vive na §5 (D4 editorial);
        # aqui só a contagem + ponteiro, sem duplicar o next genérico.
        _open = [g for g in gaps if g.get("state") not in ("covered",)]
        lines.append("")
        lines.append(f"**{labels['next']}:** ver detalhes por lacuna na "
                     f"seção 5 ({len(_open)} pendente(s)); priorizar células "
                     f"com fonte própria indicada.")
        _pri = [g for g in gaps if g.get("entity_id")][:3]
        for gap in _pri:
            lines.append(f"- {gap.get('entity_label', gap.get('label'))}: "
                         f"{gap.get('next', 'investigar com nova evidência')}")
    lines.append("")
    lines.extend(_sources_section(state, labels))
    lines.append("")
    lines.extend(_annex_section(state, labels, verifications, verbose, cited))
    lines.append("")
    lines.extend(_closure_section(state, labels, verbose))
    lines.append("")
    render_report.last_cited_urls = sorted(cited)  # type: ignore[attr-defined]
    render_report.last_numbers = dict(numbers)  # type: ignore[attr-defined]
    return "\n".join(lines)


render_report.last_cited_urls = []  # type: ignore[attr-defined]
render_report.last_numbers = {}  # type: ignore[attr-defined]
render_report.last_synthesis = ""  # type: ignore[attr-defined]
