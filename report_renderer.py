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
import re

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
    "substitutions": "Substituições de candidatos",
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
    "substitutions": "Candidate substitutions",
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


def _entity_labels(state: dict) -> dict[str, str]:
    """Internal id -> user-facing label (generic, no product literals).

    The model emits bare ids (e1, e2...) in justifications; the visible
    body must show labels. Unknown ids fall back to the original token.
    """
    try:
        return {str(e.get("id")): str(e.get("label") or e.get("id"))
                for e in (state.get("plan") or {}).get("entities", [])
                if isinstance(e, dict) and e.get("id")}
    except Exception:
        return {}


def _replace_entity_ids(text: str, labels: dict) -> str:
    """Map bare entity ids to labels, keeping unknown tokens verbatim.

    Prose only: URL spans (``scheme://...``) are never rewritten, so a
    document path ending in an id (``.../e5``) survives intact.
    """
    import re as _re2
    if not labels:
        return str(text or "")
    try:
        def _sub(m):
            return labels.get(m.group(1), m.group(1))
        _parts = _re2.split(r"([a-zA-Z][a-zA-Z0-9+.-]*://\S+)",
                            str(text or ""))
        for _i in range(0, len(_parts), 2):
            _parts[_i] = _re2.sub(r"\b(e\d{1,4})\b", _sub, _parts[_i])
        return "".join(_parts)
    except Exception:
        return str(text or "")


def _strip_source_legend(text: str) -> str:
    """Drop a standalone source-numbers legend line (no prose value).

    Generic, no product literals: only a legend-like line drops — one
    whose stripped form starts with the marker ("legenda de fontes" /
    "source legend", after blockquote/list prefixes) AND carries a
    citation list ([N]). A line that merely mentions the legend is
    legitimate prose and is preserved. Inline [N] stay.
    """
    import re as _re_leg
    try:
        kept = []
        for ln in str(text or "").split("\n"):
            _s = ln.strip().lstrip(">#-*•\"' ").strip()
            _low = _s.lower()
            _legend_like = (
                _low.startswith("legenda de fontes")
                or _low.startswith("source legend"))
            if _legend_like and _re_leg.search(r"\[\d+\]", _s):
                continue
            kept.append(ln)
        return "\n".join(kept)
    except Exception:
        return str(text or "")


def _normalize_skipped_prefix(text: str, language: str = "pt-BR") -> str:
    """Rewrite a residual English 'Skipped:' lead to the PT user label.

    Generic: the writer prompt requires 'Não verificado:'; old syntheses
    may still carry 'Skipped:' at a line start. Only the prefix is
    replaced; the rest of the line is preserved.
    """
    import re as _re4
    try:
        repl = "Não verificado:" if not str(
            language or "").lower().startswith("en") else "Not verified:"
        return _re4.sub(r"(?m)^Skipped:", repl, str(text or ""))
    except Exception:
        return str(text or "")


def _user_facing_scope(text: str) -> str:
    """Paraphrase residual internal scope jargon for the visible body.

    Generic: old states persist 'desconhecido-legítimo'; the body must
    show 'sem fonte no corpus'. Stored state is never rewritten here —
    only the rendered line.
    """
    try:
        return str(text or "").replace("desconhecido-legítimo",
                                       "sem fonte no corpus")
    except Exception:
        return str(text or "")


def _sanitize_body_text(text: str, entity_labels: dict | None = None,
                        language: str = "pt-BR") -> str:
    """Shared user-facing hygiene for any prose in the visible body.

    Generic, no product literals: ids->labels (prose only, URLs kept),
    residual EN 'Skipped:' lead -> PT label, internal scope jargon ->
    user paraphrase. Stored state is never rewritten — only the line.
    """
    try:
        # Operational residue is retained in the raw synthesis/technical
        # artifact, never echoed as a research finding in the delivery.
        clean = re.sub(r"(?im)^\s*(?:ponytail|agent[_ -]?notes?|internal[_ -]?notes?)\s*:.*(?:\n|$)", "", str(text or ""))
        out = _replace_entity_ids(clean, entity_labels or {})
    except Exception:
        out = str(text or "")
    try:
        out = _normalize_skipped_prefix(out, language)
    except Exception:
        pass
    try:
        out = _user_facing_scope(out)
    except Exception:
        pass
    return out


def _controlled_version_text(state: dict, text: str) -> str:
    """Relabel only an installed-version phrase bound to a harness value."""
    context = state.get("user_context") or {}
    if context.get("origin") != "harness":
        return text
    versions = [str(v) for v in (context.get("facts") or {}).values()
                if re.fullmatch(r"\d+(?:\.\d+)+", str(v))]
    observed = {v for obs in (state.get("environment_observations") or [])
                for v in re.findall(r"\d+(?:\.\d+)+", str(obs.get("value") or ""))}
    for version in versions:
        pattern = (r"(?i)vers[aã]o instalada(?P<context>(?:(?!vers[aã]o instalada)"
                   r"[^.;|\n]){0,100}?" + re.escape(version) + r")")
        def replace(match):
            if any(v in match.group("context") for v in observed - set(versions)):
                return match.group(0)
            return "versão de referência" + match.group("context")
        text = re.sub(pattern, replace, text)
    return text


def _source_provenance_text(state: dict, synthesis: str) -> str:
    """Correct availability/origin metadata from observed state, not guesses."""
    obtained = set(_corpus(state))
    included = set(((state.get("report") or {}).get("selection") or {}).get("included_urls") or [])
    uc = state.get("user_context") or {}
    facts = [str(v) for v in (uc.get("facts") or {}).values()]
    from entity_identity import normalized
    from verification_report import _false_absence_ref_usable
    from adaptive_coordinator import _evaluation_refs_have_identity
    selected = _required_entities(state)
    by_id = {e.get("id"): e for e in selected}
    criteria = {c.get("id"): c for c in (state.get("plan") or {}).get("criteria", [])}
    functions = {}
    for ev in state.get("evaluations") or []:
        crit = criteria.get(ev.get("criterion_id")) or {}
        label = normalized(crit.get("label") or "")
        if (ev.get("entity_id") not in by_id or ev.get("state") not in ("partial", "covered")
                or not crit.get("per_candidate") or any(x in label for x in ("custo", "licenc", "depend", "compat", "versao", "manutenc", "limit"))):
            continue
        for ref in ev.get("references") or []:
            url = ref.get("url", ref.get("doc_id", "")) if isinstance(ref, dict) else ""
            if (_false_absence_ref_usable(url, state.get("evidence"), state.get("qualification"))
                    and _evaluation_refs_have_identity(state, by_id[ev["entity_id"]], [ref])):
                functions.setdefault(ev["entity_id"], url)
                break
    lines = []
    synthesis_lines = synthesis.splitlines()
    controlled_versions = [v for v in facts if re.fullmatch(r"\d+(?:\.\d+)+", v)]
    observed_versions = {v for obs in (state.get("environment_observations") or [])
                         for v in re.findall(r"\d+(?:\.\d+)+", str(obs.get("value") or ""))}
    for index, line in enumerate(synthesis_lines):
        low = normalized(line)
        if (uc.get("origin") == "harness" and controlled_versions
                and re.match(r"^\s*#{1,6}\s", line) and "versao instalada" in low):
            section = []
            for following in synthesis_lines[index + 1:]:
                if re.match(r"^\s*#{1,6}\s", following):
                    break
                section.append(following)
            scope = "\n".join(section)
            if ((any(v in scope for v in controlled_versions)
                 or "premissa controlada" in normalized(scope))
                    and not any(v in scope for v in observed_versions - set(controlled_versions))):
                line = re.sub(r"(?i)vers[aã]o instalada", "versão de referência", line)
                low = normalized(line)
        if (obtained - included and "fora do corpus" in low
                and re.search(r"fora (?:desses|destes|daqueles|dos selecionados) (?:documentos|excertos|textos)", low)):
            line = re.sub(r"(?i)fora do corpus", "fora do material enviado à síntese", line)
            low = normalized(line)
        if (len(functions) >= 2 and ("ausencia de base para combin" in low or "sem base para combin" in low)
                and any(x in low for x in ("demais", "outros candidatos", "outras opcoes"))):
            named = [e for e in selected if (form := normalized(e.get("label") or ""))
                     and re.search(r"(?:^| )" + re.escape(form) + r"(?:$| )", low)]
            if len(named) == 1 and named[0].get("id") in functions:
                first = named[0]; other = next((e for e in selected if e.get("id") != first.get("id") and e.get("id") in functions), None)
                if other:
                    line = (f"As funções documentadas de {first['label']} e {other['label']} permitem investigar eventual complementaridade "
                            f"({functions[first['id']]}) ({functions[other['id']]}). "
                            "A pesquisa não demonstrou integração testada entre elas.")
        if uc.get("origin") == "harness" and any(v in line for v in facts):
            line = re.sub(r"(?i)premissa do usu[aá]rio", "premissa controlada do experimento (harness)", line)
            line = _controlled_version_text(state, line)
        if re.search(r"(?i)fora do corpus", line):
            urls = re.findall(r"https?://[^\s)<>]+", line)
            known = [u.rstrip(".,;") for u in urls if u.rstrip(".,;") in obtained]
            if known:
                details = [f"{u}: fonte obtida; " + ("incluída no material da síntese" if u in included else "fora do material enviado à síntese") for u in known]
                line = "Nota de procedência: " + "; ".join(details) + "."
        lines.append(line)
    return "\n".join(lines)


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
        if isinstance(url, str) and url.startswith("user://context/") and crit.get("state") in ("covered", "partial"):
            out.append("(premissa de contexto)")
            continue
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
    if state.get("reproduction"):
        lines.append("**Reprodução de corpus congelado:** " + str(state["reproduction"].get("description", "sem nova coleta")))
    uc = state.get("user_context") or {}
    if uc.get("origin") == "harness":
        lines.append("**Premissas controladas do experimento (harness):** "
                     + "; ".join(f"{k}={v}" for k, v in (uc.get("facts") or {}).items())
                     + ". Não constituem observação do ambiente.")
    for obs in state.get("environment_observations") or []:
        lines.append(f"**Observação local separada:** {obs.get('command')} → {obs.get('value')} ({obs.get('at')}).")
    common_scope, common_n = _common_examined_scope(state)
    if common_scope:
        body = common_scope.strip()
        if body.lower().startswith("alcance examinado:"):
            body = body.split(":", 1)[1].strip()
        body = body[:1].upper() + body[1:] if body else body
        try:
            body = _sanitize_body_text(
                body, _entity_labels(state),
                "en" if labels is _EN else "pt-BR")
        except Exception:
            pass
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
        try:
            justification = _sanitize_body_text(
                justification, _entity_labels(state),
                "en" if labels is _EN else "pt-BR")
        except Exception:
            pass
        cell_evals = crit.get("entity_evaluations") or {}
        if not cell_evals:
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
            lines.append("| Entidade | Estado | Evidência e limites |")
            lines.append("|---|---|---|")
            for eid, est in entity_states.items():
                ev = cell_evals.get(eid) or {}
                detail = _sanitize_body_text(str(ev.get("justification") or labels["not_investigated"]), _entity_labels(state))
                refs = _refs(ev, numbers, labels, cited)
                lines.append(f"| {_labels_by_id.get(eid, eid)} | "
                             f"{_state_label(labels, _cell_state(crit, eid))} | "
                             f"{detail.replace('|', '/').replace(chr(10), ' ')} {refs} |")
        elif cell_evals:
            for eid, ev in cell_evals.items():
                lines.append(_sanitize_body_text(ev.get("justification") or labels["not_investigated"], _entity_labels(state)))
                refs = _refs(ev, numbers, labels, cited)
                if refs:
                    lines.append(f"{labels['references']}: {refs}")
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
                try:
                    _scope = _sanitize_body_text(
                        _scope, _entity_labels(state),
                        "en" if labels is _EN else "pt-BR")
                except Exception:
                    pass
                lines.append(_scope[:1].upper() + _scope[1:]
                             if _scope else _scope)
            elif _key and common_scope and _key == _scope_key(common_scope):
                lines.append("- Idem ao escopo comum do método (§2).")
        for nc in crit.get("na_cells", []) or []:
            _nc_label = _labels_by_id.get(nc.get("entity_id"),
                                          nc.get("entity_id"))
            _nc_just = ((nc.get('justification') or '').strip()
                        or labels['not_investigated'])
            try:
                _nc_just = _sanitize_body_text(
                    _nc_just, _labels_by_id,
                    "en" if labels is _EN else "pt-BR")
            except Exception:
                pass
            lines.append(f"- **N/A** {_nc_label}: {_nc_just}")
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
    "_sent",
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
    try:
        _lim_labels = _entity_labels(state)
    except Exception:
        _lim_labels = {}
    _lim_lang = "en" if labels is _EN else "pt-BR"
    if gaps:
        lines.append(f"### {labels['gaps']}")
        for gap in gaps:
            try:
                _gj = _sanitize_body_text(
                    str(gap.get('justification', '')), _lim_labels,
                    _lim_lang)
            except Exception:
                _gj = str(gap.get('justification', ''))
            lines.append(f"- **{gap.get('label', gap.get('criterion_id'))}** "
                         f"({_state_label(labels, gap.get('state', '?'))}): "
                         f"{_gj}")
            if gap.get("next"):
                try:
                    _nx = _sanitize_body_text(
                        str(gap["next"]), _lim_labels, _lim_lang)
                except Exception:
                    _nx = str(gap["next"])
                lines.append(f"  - {labels['next']}: {_nx}")
    _subs = [s for s in (state.get("substitutions") or [])
             if isinstance(s, dict)]
    if _subs:
        # Swap de finalista visível no corpo (1 linha PT curada por
        # entrada, ids->rótulos): a nota raw segue só no anexo §8.
        lines.append("")
        lines.append(f"### {labels['substitutions']}")
        for _s in _subs:
            _old = _lim_labels.get(str(_s.get("old") or ""),
                                   str(_s.get("old") or "?"))
            _new = _lim_labels.get(str(_s.get("new") or ""),
                                   str(_s.get("new") or "?"))
            try:
                _rs = _sanitize_body_text(
                    str(_s.get("reason") or ""), _lim_labels, _lim_lang)
            except Exception:
                _rs = str(_s.get("reason") or "")
            _line = f"- {_old} → {_new}"
            if _rs.strip():
                _line += f": {_rs.strip()}"
            lines.append(_line)
    contradictions = [c for c in (block.get("criteria") or [])
                      if c.get("state") == "contradictory"]
    if contradictions:
        # §5 é ponteiro: o detalhe vive nos achados (§3); aqui só o
        # estado + remissão, sem duplicar a justificativa verbatim.
        lines.append("")
        lines.append(f"### {labels['contradictions']}")
        for crit in contradictions:
            lines.append(f"- {crit.get('label', crit.get('id'))}: "
                         f"{_state_label(labels, crit.get('state'))} — "
                         f"ver achados na seção 3.")
    unverified = [c for c in (block.get("criteria") or [])
                  if c.get("state") in ("insufficient", "blocked",
                                        "uninvestigated")]
    lines.append("")
    lines.append(f"### {labels['uncertainties']}")
    if unverified:
        for crit in unverified:
            lines.append(f"- {crit.get('label', crit.get('id'))}: "
                         f"{_state_label(labels, crit.get('state'))} — "
                         f"ver achados na seção 3.")
    else:
        lines.append("- Nenhum critério obrigatório ficou sem verificação "
                     "declarada; incertezas residuais seguem nas notas.")
    outside = _counters.counters_snapshot(state).get(
        "outside_corpus_citations") or []
    if outside:
        # Detalhe (URLs) vive no anexo técnico; aqui só a contagem +
        # ponteiro, sem duplicar a lista.
        lines.append("")
        lines.append(f"- {len(outside)} citação(ões) fora do corpus "
                     f"removida(s) do corpo (ver anexo técnico).")
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
            try:
                note = _sanitize_body_text(
                    str(note), _lim_labels, _lim_lang)
            except Exception:
                pass
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
    outside = counters.get("outside_corpus_citations") or []
    if outside:
        lines.append("")
        lines.append(f"### {labels['outside']}")
        for url in outside:
            lines.append(f"- {url}")
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


def _writer_included_norms(state: dict) -> set:
    """URLs reais na janela do writer (genérico, sem literais).

    shortcut: rótulo F3 só vale fora da seleção real; sem leitura,
    conjunto vazio (nunca afirma inclusão).
    """
    try:
        sel = (state.get("report") or {}).get("selection") or {}
        inc = sel.get("included_urls") or []
        out = set()
        for u in inc:
            try:
                n = _norm(u)
            except Exception:
                n = None
            out.add(str(u or ""))
            if n:
                out.add(n)
        return out
    except Exception:
        return set()


def _reconciliation_notes(state: dict, synthesis: str,
                          numbers: dict | None = None) -> list[str]:
    """Cruza findings (entity_states/refs) com LACUNAs da síntese.

    Genérico, sem literais: para cada célula covered com refs válidas
    no corpus, se a síntese traz LACUNA para a mesma entidade, emite
    nota explícita com alcance (janela do writer vs texto integral)
    em vez de silêncio. Nota é PT user-facing (vai ao §5, nunca ao
    anexo debug).
    """
    try:
        synth = str(synthesis or "")
        if "lacuna" not in synth.lower():
            return []
        nums = numbers if isinstance(numbers, dict) else _numbers(state)
        block = state.get("question_coverage") or {}
        criteria = block.get("criteria") or []
        if not criteria:
            return []
        try:
            import verification_report as _vr
            _mentioned = _vr._entity_mentioned
        except Exception:
            _mentioned = None
        try:
            _ents = [(e.get("id"), str(e.get("label") or e.get("id")))
                     for e in (state.get("plan") or {}).get("entities", [])
                     if isinstance(e, dict) and e.get("id")]
        except Exception:
            _ents = []
        _label_by_id = dict(_ents)
        import re as _re_s
        sents = _re_s.split(r"(?<=[.!?])\s+|\n+", synth)
        notes: list[str] = []
        seen: set = set()
        for crit in criteria:
            if not isinstance(crit, dict):
                continue
            es = crit.get("entity_states") or {}
            refs = crit.get("references") or []
            valid_urls: list[str] = []
            try:
                for r in refs:
                    u = (r.get("url", r.get("doc_id", ""))
                         if isinstance(r, dict) else str(r or ""))
                    if not u:
                        continue
                    k, _n = _lookup_number(u, nums)
                    if k is not None:
                        valid_urls.append(u)
            except Exception:
                valid_urls = []
            if not valid_urls:
                continue
            crit_label = str(crit.get("label") or crit.get("id") or "")
            for eid, st in (es.items() if isinstance(es, dict) else []):
                if st != "covered":
                    continue
                elabel = str(_label_by_id.get(eid, eid or ""))
                if not elabel:
                    continue
                hit = False
                try:
                    for sent in sents:
                        low = str(sent or "").lower()
                        if "lacuna" not in low:
                            continue
                        try:
                            if _mentioned is not None:
                                _named = bool(_mentioned(
                                    elabel, eid, str(sent or "")))
                                if not _named:
                                    _named = bool(
                                        elabel.lower() in low)
                            else:
                                _named = bool(elabel.lower() in low)
                        except Exception:
                            _named = bool(elabel.lower() in low)
                        if _named:
                            hit = True
                            break
                except Exception:
                    hit = False
                if not hit:
                    continue
                key = (str(eid), str(crit.get("id") or crit_label))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    _rn = [str(nums.get(_norm(u), "?"))
                           for u in valid_urls[:3]]
                    _refs_s = "[" + "][".join(_rn) + "]" if _rn else ""
                except Exception:
                    _refs_s = ""
                notes.append(
                    f"Nota: os achados registram cobertura de {elabel} "
                    f"em {crit_label} com {_refs_s} a partir da seleção "
                    f"analisada; a síntese declara lacuna a partir dos "
                    f"excertos avaliados. Vale o texto integral da fonte.")
        return notes
    except Exception:
        return []


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
        try:
            _included = _writer_included_norms(state)
        except Exception:
            _included = set()
        sentences = _re0.split(r"(?<=[.!?])\s+|\n+", str(synthesis or ""))
        out = str(synthesis or "")
        rewrote = 0
        for sent in sentences:
            if "fora do corpus" not in sent.lower():
                continue
            if "fora da seleção" in sent.lower():
                continue
            _hint = ""
            _matched = None
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
                    _matched = _ent
                    break
                # Entidade citada sem doc: esta frase não dispara veto.
                _hint = ""
            if not _hint:
                continue
            try:
                _src = str((_matched or {}).get("source_url") or "")
                _in_sel = False
                for _cand in (_src, _hint):
                    if not _cand:
                        continue
                    if _cand in _included:
                        _in_sel = True
                        break
                    try:
                        if _norm(_cand) in _included:
                            _in_sel = True
                            break
                    except Exception:
                        pass
                if _in_sel:
                    continue
            except Exception:
                pass
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


def _required_entities(state: dict) -> list[dict]:
    """Entidades exigidas pelo plano (genérico, sem literais)."""
    try:
        from entity_identity import comparison_entities
        return comparison_entities(state.get("plan") or {})
    except Exception:
        return []


def _all_gaps(state: dict) -> list[dict]:
    """Lacunas do bloco + topo do estado, sem duplicar critério."""
    try:
        block = state.get("question_coverage") or {}
        gaps = [g for g in (block.get("gaps") or [])
                if isinstance(g, dict)]
        seen = {g.get("criterion_id") for g in gaps}
        for gap in state.get("gaps") or []:
            if isinstance(gap, dict) \
                    and gap.get("criterion_id") not in seen:
                gaps.append(gap)
                seen.add(gap.get("criterion_id"))
        return gaps
    except Exception:
        return []


def _cell_state(criterion: dict, entity_id) -> str:
    """Estado exibido de UMA célula entidade×critério (fonte única).

    Genérico, sem literais: entity_states manda quando a entidade foi
    avaliada; sem avaliação por entidade (critério global), vale o
    estado do critério — o mesmo que o §3 mostra no cabeçalho. §3 e
    matriz usam esta função: matriz == §3 por construção, nunca
    'não avaliado' fantasma onde o §3 registra veredito.
    """
    try:
        applies = (criterion or {}).get("applies_to")
        if applies and entity_id not in applies:
            return "not_applicable"
        es = (criterion or {}).get("entity_states") or {}
        if isinstance(es, dict) and entity_id in es:
            return str(es.get(entity_id) or "unevaluated")
        return str((criterion or {}).get("state", "unevaluated")
                   or "unevaluated")
    except Exception:
        return "unevaluated"


def _combo_entities(state: dict) -> list[dict]:
    """Entidades com cobertura para cruzar pares (exigidas ou não).

    Pares da síntese comparam-se ao conjunto coberto nos achados (§3),
    que inclui explorados fora da seleção; a matriz (item só-exigidos)
    continua em _required_entities.
    """
    try:
        from entity_identity import context_entity_ids
        contexts = context_entity_ids(state.get("plan") or {})
        return [e for e in (state.get("plan") or {}).get("entities", [])
                if isinstance(e, dict) and e.get("id") and e.get("id") not in contexts]
    except Exception:
        return []


def _combination_premises(state: dict, synthesis: str) -> list[str]:
    """Linhas compactas das combinações com premissa por entidade nomeada.

    Extrai da síntese final (já com [N]) as sentenças de combinação
    (INFERÊNCIA) que citam ≥2 premissas e nomeiam ≥2 exigidos por forma
    cheia ou base inequívoca (nunca overlap frouxo de tokens); devolve
    metadados (par × nº de premissas × refs), nunca a frase verbatim.
    Cada entidade nomeada precisa de um doc citado que a vincule
    (mesmo vínculo do verificador); entidade sem fonte é sinalizada
    na linha ("sem fonte: X"), nunca silenciosamente coberta pela
    contagem de premissas. Sem par válido, lista vazia (o chamador
    declara LACUNA com alcance). Vale para N candidatos.
    """
    try:
        import re as _re_c
        req = _required_entities(state)
        if len(req) < 2:
            return []
        try:
            import verification_report as _vr
        except Exception:
            return []
        try:
            _num = _numbers(state)
        except Exception:
            return []
        n_to_url = {int(n): u for u, n in (_num or {}).items()
                    if str(n).isdigit()}
        try:
            from entity_identity import source_identity as _sid
        except Exception:
            _sid = None
        emap = {e.get("id"): e for e in (state.get("plan") or {}).get("entities", [])
                if isinstance(e, dict)}
        ev = dict(state.get("evidence") or {})

        def _covers(label, eid, url) -> bool:
            body = ev.get(url) or ""
            if not body:
                return False
            if _sid is not None:
                try:
                    proven = _sid(emap.get(eid) or {}, body, url)
                except Exception:
                    proven = None
                if proven is True:
                    return True
                if proven is False:
                    return False
            try:
                return bool(_vr._entity_mentioned(label, eid, body))
            except Exception:
                return False

        out: list[str] = []
        for sent in _re_c.split(r"(?<=[.!?])\s+|\n+",
                                str(synthesis or "")):
            if "infer" not in sent.lower():
                continue
            named = _vr.strict_named_in_sentence(sent, req)
            if len(named) < 2:
                continue
            try:
                refs = sorted({int(n) for n in _re_c.findall(r"\[(\d+)\]", sent)})
            except Exception:
                continue
            if len(refs) < 2:
                continue
            urls = [n_to_url.get(n) for n in refs]
            urls = [u for u in urls if u]
            missing = [lb for lb, eid in named
                       if not any(_covers(lb, eid, u) for u in urls)]
            shown = "[" + "][".join(str(n) for n in refs[:4]) + "]"
            line = (f"- {' × '.join(lb for lb, _ in named[:3])}: "
                    f"{len(refs)} premissas citadas {shown}")
            if missing:
                line += "; sem fonte: " + ", ".join(missing)
            out.append(line)
        return out
    except Exception:
        return []


def _synthesis_recommends_entities(state: dict, synthesis: str) -> bool:
    """A síntese já recomenda entidades exigidas (genérico, sem literais)?

    Vale se há ≥2 frases de recomendação citando ≥1 exigido; sem isso
    o template anexa o fallback determinístico a partir dos achados.
    """
    try:
        import re as _re_r
        req = _required_entities(state)
        if not req:
            return True
        try:
            import verification_report as _vr
            _mentioned = _vr._entity_mentioned
        except Exception:
            _mentioned = None
        recs = [s for s in _re_r.split(r"(?<=[.!?])\s+|\n+",
                                        str(synthesis or ""))
                if any(k in s.lower() for k in
                       ("recomend", "suger", "próximo passo",
                        "próximos passos"))]
        if len(recs) < 2:
            return False
        for sent in recs:
            for ent in req:
                lb = str(ent.get("label") or ent.get("id") or "")
                if not lb:
                    continue
                try:
                    hit = bool(_mentioned(lb, ent.get("id"), sent)) \
                        if _mentioned is not None else False
                    if not hit:
                        hit = lb.lower() in sent.lower()
                except Exception:
                    hit = lb.lower() in sent.lower()
                if hit:
                    return True
        return False
    except Exception:
        return True


def _recommendation_fallback(state: dict, labels: dict,
                             numbers: dict) -> list[str]:
    """Fallback determinístico da recomendação (genérico, sem literais).

    Ranqueia os exigidos por (covered, partial, refs válidas) com 1
    frase por entidade só com estados e refs já auditados — nenhum
    fato novo, PT claro, sem jargão.
    """
    try:
        import re as _re_f
        block = state.get("question_coverage") or {}
        criteria = [c for c in (block.get("criteria") or [])
                    if isinstance(c, dict)]
        req = _required_entities(state)
        if not req or not criteria:
            return []
        lines = ["- Adequação ao pedido a partir dos achados por candidato (sem ranking por contagens):"]
        for ent in req:
            eid = ent.get("id")
            lb = str(ent.get("label") or eid or "")
            cov_l: list[str] = []
            par_l: list[str] = []
            seen: set = set()
            refs: list[str] = []
            for crit in criteria:
                cell = _cell_state(crit, eid)
                if cell not in ("covered", "partial"):
                    continue
                if cell == "covered":
                    cov_l.append(str(crit.get("label") or crit.get("id")))
                else:
                    par_l.append(str(crit.get("label") or crit.get("id")))
                for r in crit.get("references") or []:
                    u = (r.get("url", r.get("doc_id", ""))
                         if isinstance(r, dict) else str(r or ""))
                    if not u:
                        continue
                    try:
                        _k, _n = _lookup_number(u, numbers)
                    except Exception:
                        _k, _n = None, None
                    if _k is not None and _n not in seen:
                        seen.add(_n)
                        refs.append(str(_n))
            details = []
            for crit in criteria:
                ev = (crit.get("entity_evaluations") or {}).get(eid) or {}
                if ev.get("state") in ("covered", "partial") and ev.get("justification"):
                    details.append(f"{crit.get('label')}: {ev['justification']} {_refs(ev, numbers, labels, set())}")
            if not cov_l and not par_l:
                lines.append(f"- {lb}: sem cobertura nos achados; "
                             f"verificar fonte própria antes de usar.")
                continue
            _cov = ", ".join(cov_l[:3]) if cov_l else "nenhum critério"
            _par = ", ".join(par_l[:3]) if par_l else "nenhum critério"
            _rf = "[" + "][".join(refs[:4]) + "]" if refs else "—"
            if details:
                lines.append(f"- **{lb}**: " + " ".join(details[:2])
                             + " Adoção condicionada às dependências, compatibilidade e limitações abaixo.")
            else:
                lines.append(f"- {lb}: coberto em {_cov}; parcial em {_par}; fontes {_rf}. "
                             "Sem justificativa funcional por candidato para recomendar adoção.")
        return lines
    except Exception:
        return []


def _template_section(state: dict, labels: dict, numbers: dict,
                      synthesis: str) -> list[str]:
    """Template pós-processado do writer (genérico, sem literais).

    Garante a forma sem depender só do modelo: resposta direta ≤15
    linhas no topo, matriz entidade×critério (só exigidos; demais em
    'explorados fora da seleção'), diferenças/combinações com ≥2
    premissas citadas, recomendação proporcional ao perfil e LACUNAs
    com alcance explícito. Tudo derivado do estado real + rótulos do
    plano; usa '###' para não colidir com as seções '##' do renderer.
    """
    lines: list[str] = []
    try:
        block = state.get("question_coverage") or {}
        criteria = [c for c in (block.get("criteria") or [])
                    if isinstance(c, dict)]
        req = _required_entities(state)
        req_ids = {e.get("id") for e in req}
        scoped = [c for c in criteria if c.get("per_candidate")
                  or set(c.get("entity_states") or {}) & req_ids
                  or set(c.get("applies_to") or []) & req_ids]
        global_criteria = [c for c in criteria if c not in scoped]
        lines.append("### Resposta direta")
        _rd = [f"- **Veredito:** "
               f"{_state_label(labels, block.get('status', 'unevaluated'))} "
               f"(proportion={block.get('proportion')})"]
        for ent in req[:12]:
            eid = ent.get("id")
            cov = par = sem = 0
            for crit in scoped:
                es = (crit.get("entity_states") or {}).get(eid)
                if es == "covered":
                    cov += 1
                elif es == "partial":
                    par += 1
                else:
                    sem += 1
            _rd.append(f"- {ent.get('label') or eid}: {cov} coberto(s), "
                       f"{par} parcial(is), {sem} sem cobertura de "
                       f"{len(scoped)} critério(s)")
        lines.extend(_rd[:15])
        lines.append("")
        lines.append("### Matriz entidade×critério")
        if req and criteria:
            lines.append("| Critério | "
                         + " | ".join(str(e.get("label") or e.get("id"))
                                       for e in req) + " |")
            lines.append("|---" * (len(req) + 1) + "|")
            for crit in scoped:
                cells = []
                for ent in req:
                    eid = ent.get("id")
                    ev = (crit.get("entity_evaluations") or {}).get(eid) or {}
                    detail = _cut_at_sentence(str(ev.get("justification") or ""), 210)
                    refs = _refs(ev, numbers, labels, set())
                    cells.append((_state_label(labels, _cell_state(crit, eid))
                                  + (f": {detail} {refs}" if detail else "")).replace("|", "/").replace("\n", " "))
                lines.append(f"| {crit.get('label') or crit.get('id')} | "
                             + " | ".join(cells) + " |")
        if global_criteria:
            lines.extend(["", "### Critérios globais e contexto", ""])
            for crit in global_criteria:
                lines.append(f"- **{crit.get('label') or crit.get('id')}** — "
                             f"{_state_label(labels, crit.get('state'))}: "
                             f"{_sanitize_body_text(crit.get('justification') or labels['not_investigated'], _entity_labels(state))} "
                             f"{_refs(crit, numbers, labels, set())}")
        try:
            _by_id = {e.get("id"): (e.get("label") or e.get("id"))
                       for e in (state.get("plan") or {}).get("entities", [])
                       if isinstance(e, dict)}
        except Exception:
            _by_id = {}
        _expl = [str(e.get("label") or e.get("id")) for e in
                 (state.get("plan") or {}).get("entities", [])
                 if isinstance(e, dict) and e.get("required", True) is False]
        for s in (state.get("substitutions") or []):
            if isinstance(s, dict):
                _o = str(_by_id.get(s.get("old"), s.get("old") or "?"))
                if _o not in _expl:
                    _expl.append(_o)
        if _expl:
            shown = ", ".join(_expl[:3])
            more = f" e mais {len(_expl) - 3}" if len(_expl) > 3 else ""
            lines.append(f"- Alternativas fora da seleção (investigação variável): "
                         f"{shown}{more}; detalhes no anexo técnico.")
        lines.append("")
        lines.append("### Diferenças e combinações")
        _comb = _combination_premises(state, synthesis)
        if _comb:
            lines.extend(_comb[:5])
        else:
            lines.append("- Sem combinações com ≥2 premissas citadas nos "
                         "excertos avaliados (LACUNA de combinação).")
        lines.append("")
        lines.append("### Recomendação")
        prof = str(state.get("profile") or "medium")
        lines.append(f"- Recomendação (perfil {prof}): priorizar células "
                     f"com fonte própria indicada.")
        _open = [g for g in _all_gaps(state)
                 if g.get("state") not in ("covered",)]
        if prof.lower() != "light" and _open:
            lines.append(f"- {len(_open)} lacuna(s) aberta(s); detalhe por "
                         f"lacuna na seção 5.")
        if prof.lower() in ("hard", "deep"):
            _tally: list[tuple] = []
            for ent in req:
                n = sum(1 for c in criteria
                        if _cell_state(c, ent.get("id"))
                        in ("covered", "partial"))
                _tally.append((n, str(ent.get("label") or ent.get("id"))))
            _tally.sort(reverse=True)
            _top = ", ".join(f"{lb} ({n})" for n, lb in _tally[:3])
            if _top:
                lines.append(f"- Entidades com mais cobertura: {_top}.")
        if not _synthesis_recommends_entities(state, synthesis):
            lines.extend(_recommendation_fallback(state, labels, numbers))
        lines.append("")
        lines.append("### LACUNAs com alcance")
        if _open:
            for g in _open:
                lines.append(
                    f"- {g.get('label', g.get('criterion_id'))} "
                    f"({_state_label(labels, g.get('state', '?'))}): "
                    f"alcance: excertos avaliados; vale o texto "
                    f"integral da fonte.")
        else:
            lines.append("- Sem lacunas obrigatórias pendentes.")
    except Exception:
        pass
    return lines


def _pair_reconciliation_notes(state: dict, synthesis: str) -> list[str]:
    """Pares de combinação da síntese × pares dos achados (§3).

    Genérico, sem literais: cada sentença de combinação (INFERÊNCIA)
    que nomeia ≥2 entidades exigidas precisa co-ocorrer com estado
    positivo (covered/partial) em algum critério dos achados; senão
    vira nota explícita com alcance (janela do writer vs texto
    integral). Nota PT user-facing (vai ao §5, nunca ao anexo debug).
    """
    try:
        import itertools as _it
        import re as _re_p
        req = _combo_entities(state)
        if len(req) < 2:
            return []
        sents = [s for s in _re_p.split(r"(?<=[.!?])\s+|\n+",
                                        str(synthesis or ""))
                 if "infer" in s.lower()]
        if not sents:
            return []
        try:
            import verification_report as _vr
            _mentioned = _vr._entity_mentioned
        except Exception:
            _mentioned = None

        def _hit(lb: str, eid, sent: str) -> bool:
            try:
                if _mentioned is not None \
                        and bool(_mentioned(lb, eid, sent)):
                    return True
            except Exception:
                pass
            try:
                return bool(lb and lb.lower() in sent.lower())
            except Exception:
                return False

        block = state.get("question_coverage") or {}
        criteria = [c for c in (block.get("criteria") or [])
                    if isinstance(c, dict)]
        notes: list[str] = []
        seen: set = set()
        for sent in sents:
            named: list[tuple] = []
            for ent in req:
                lb = str(ent.get("label") or ent.get("id") or "")
                if lb and _hit(lb, ent.get("id"), sent) \
                        and ent.get("id") not in {n[0] for n in named}:
                    named.append((ent.get("id"), lb))
            for (a_id, a_lb), (b_id, b_lb) in _it.combinations(named, 2):
                key = tuple(sorted((str(a_id), str(b_id))))
                if key in seen:
                    continue
                seen.add(key)
                ok = any((c.get("entity_states") or {}).get(a_id)
                         in ("covered", "partial")
                         and (c.get("entity_states") or {}).get(b_id)
                         in ("covered", "partial") for c in criteria)
                if ok:
                    continue
                notes.append(
                    f"Nota: os achados não registram cobertura conjunta "
                    f"de {a_lb} e {b_lb} na seleção analisada; a "
                    f"combinação na síntese parte dos excertos avaliados. "
                    f"Vale o texto integral da fonte.")
        return notes
    except Exception:
        return []


def render_technical_annex(state: dict,
                           verifications: dict | None = None,
                           verbose: bool = False,
                           language: str = "pt-BR",
                           cited: set | None = None) -> str:
    """Anexo técnico separado do principal (genérico, sem literais).

    Reúne o que polui a entrega ao usuário: verificações, contadores,
    alcance de leitura, outside detalhado, notas de diagnóstico e
    tabela de rodadas (verbose). Chamador: render_report() compõe a
    entrega em arquivo único (§§1-9); para entrega separada, o
    coordinator pode gravar este retorno em arquivo de anexo à parte
    e entregar só o principal (tudo antes de "## 8.").
    """
    labels = _labels(language)
    lines = _annex_section(state, labels, verifications, verbose, cited)
    alternatives = [str(e.get("label") or e.get("id"))
                    for e in ((state.get("plan") or {}).get("entities") or [])
                    if isinstance(e, dict) and e.get("required", True) is False]
    if alternatives:
        lines.extend(["", "### Alternativas registradas fora da seleção", ""])
        lines.extend(f"- {label}" for label in alternatives)
    lines.append("")
    lines.extend(_closure_section(state, labels, verbose))
    return "\n".join(lines)


def _reword_inferred_comparison(sentence: str) -> str:
    """Coerência documentado x inferido (accept43, defeitos 1-2).

    A relação apurada de documentos distintos, sem trecho que documente
    o vínculo, é INFERÊNCIA — nunca "documentada". Só o verificador
    decide (missing_entity_sources/inferred_comparisons); aqui só a
    redação da frase sinalizada muda, sem tocar entidades, citações ou
    notas. Relações com vínculo documentado nunca chegam aqui.
    """
    import re as _re
    out = _re.sub(r"\b[Ss]obreposiç(?:ão|ões)\s+parcial\s+documentad[ao]s?\b",
                  "INFERÊNCIA de sobreposição parcial", sentence, count=1)
    out = _re.sub(r"\b[Ss]obreposiç(?:ão|ões)\s+documentad[ao]s?\b",
                  "INFERÊNCIA de sobreposição", out, count=1)
    out = _re.sub(r"\b[Cc]omplementaridade\s+documentad[ao]s?\b",
                  "INFERÊNCIA de complementaridade", out, count=1)
    out = out.replace("INFERÊNCIA de INFERÊNCIA de", "INFERÊNCIA de")
    return out


def render_report(state: dict, *, synthesis_text: str,
                  verifications: dict | None = None,
                  quantitative: list | None = None,
                  language: str = "pt-BR", include_annex: bool = True) -> str:
    """Render the delivery Markdown from the real run state."""
    labels = _labels(language)
    verbose = str(state.get("profile", "")).lower() in ("hard", "deep")
    numbers = _numbers(state)
    cited: set = set()
    synthesis = _source_provenance_text(state, synthesis_text or "")
    try:
        synthesis = _veto_outside_corpus(state, synthesis)
    except Exception:
        pass
    try:
        _recs = list(_reconciliation_notes(state, synthesis, numbers))
        _recs += _pair_reconciliation_notes(state, synthesis)
        for _rn in _recs:
            _rec_seen = set(n for n in (state.get("notes") or [])
                            if isinstance(n, str))
            if _rn not in _rec_seen:
                state.setdefault("notes", []).append(_rn)
    except Exception:
        pass
    synthesis, outside = _rewrite_refs(synthesis, numbers, cited)
    synthesis = _strip_fonte_placeholder(synthesis)
    try:
        synthesis = _strip_source_legend(synthesis)
    except Exception:
        pass
    try:
        synthesis = _sanitize_body_text(
            synthesis, _entity_labels(state), language)
    except Exception:
        pass
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
        _scope_check = _verify.check_support(
            synthesis, numbers, dict(state.get("evidence") or {}), state.get("plan") or {})
        _comparison_notes = {}
        _flagged = [(_item.get("sentence") or "")
                    for _item in ((_scope_check.get("missing_entity_sources") or [])
                                  + (_scope_check.get("inferred_comparisons") or []))]
        for _old in dict.fromkeys(s for s in _flagged if s):
            _new = _reword_inferred_comparison(_old)
            if _new != _old and _old in synthesis:
                synthesis = synthesis.replace(_old, _new, 1)
                _note = ("comparação reescrita como inferência (relação sem "
                         "vínculo documentado nas fontes citadas)")
                if _note not in set(n for n in (state.get("notes") or [])
                                     if isinstance(n, str)):
                    state.setdefault("notes", []).append(_note)
        for _item in _scope_check.get("missing_entity_sources") or []:
            _sent = _reword_inferred_comparison(_item["sentence"])
            _comparison_notes.setdefault(_sent, []).append(
                "**Referência pendente:** " + ", ".join(_item.get("missing_entities") or [])
                + "; a atribuição nessa comparação não foi confirmada.")
        for _item in _scope_check.get("inferred_comparisons") or []:
            _sent = _reword_inferred_comparison(_item["sentence"])
            _comparison_notes.setdefault(_sent, []).append(
                "**Escopo da comparação:** a relação comparativa é inferência a partir "
                "das funções citadas e não demonstra integração testada.")
        for _sentence, _notes in _comparison_notes.items():
            if _sentence in synthesis:
                synthesis = synthesis.replace(_sentence, _sentence + "\n  - " + " ".join(_notes), 1)
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
    if state.get("reproduction"):
        lines[2:2] = ["**REPRODUÇÃO — corpus congelado, sem nova coleta.** "
                      + str(state["reproduction"].get("description", "")), ""]
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
    lines.extend(_template_section(state, labels, numbers, synthesis))
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
            try:
                _cnx = _sanitize_body_text(
                    str(gap.get('next', 'investigar com nova evidência')),
                    _entity_labels(state), language)
            except Exception:
                _cnx = str(gap.get('next', 'investigar com nova evidência'))
            lines.append(f"- {gap.get('entity_label', gap.get('label'))}: "
                         f"{_cnx}")
    lines.append("")
    lines.extend(_sources_section(state, labels))
    lines.append("")
    if include_annex:
        lines.append(render_technical_annex(
            state, verifications, verbose, language, cited))
    else:
        overall = (verifications or {}).get("overall", "not_run")
        review = (((verifications or {}).get("dimensions") or {}).get("review") or {}).get("evidence") or {}
        states = {"failed": "falhou", "partial": "parcial", "ok": "concluída", "not_run": "não executada"}
        lines.append(f"**Verificação:** {states.get(overall, overall)}. "
                     f"Revisão: {review.get('verdict_state') or 'não informada'}. "
                     "[Detalhes técnicos](technical_annex.md).")
    lines.append("")
    render_report.last_cited_urls = sorted(cited)  # type: ignore[attr-defined]
    render_report.last_numbers = dict(numbers)  # type: ignore[attr-defined]
    result = "\n".join(lines)
    if (state.get("user_context") or {}).get("origin") == "harness":
        result = re.sub(r"(?i)vers[aã]o instalada informada pelo usu[aá]rio",
                        "versão de referência da premissa controlada", result)
        result = _controlled_version_text(state, result)
        for fact in ((state.get("user_context") or {}).get("facts") or {}).values():
            value = str(fact or "")
            if value:
                result = re.sub(
                    r"(?i)vers[aã]o (?:instalada|de refer[eê]ncia)\s+(" + re.escape(value) +
                    r")\s+(?:informada|fornecida) pelo usu[aá]rio",
                    r"versão de referência \1 da premissa controlada", result)
    return result


render_report.last_cited_urls = []  # type: ignore[attr-defined]
render_report.last_numbers = {}  # type: ignore[attr-defined]
render_report.last_synthesis = ""  # type: ignore[attr-defined]
