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
import hashlib as _hashlib
import hashlib as _hashlib
_LONG_PARA_THRESHOLD = 600
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
# ecosystem's package names.
_PKG_RE = re.compile(
    r"`([a-zA-Z@][\w\-.@]*(?:opencode|plugin|oh-my)[\w\-.@]*)`"
    r"|\b(opencode(?:-[a-z0-9\-]+)+|oh-my-opencode|tavily|morph|daytona"
    r"|wakatime|helicone)\b", re.I)
_LIC_RE = re.compile(r"\b(MIT|Apache-2\.0|SUL-1\.0|BSD|GPL|ISC|NOASSERTION)\b", re.I)

# Sentences that describe the audit's own process rather than a fact about a
# package. They are provenance, not claims.
_PRICE_TOKENS = re.compile(
    r"(\$\d+(?:\.\d+)?(?:/1M|/100K|/GPU-?hr|/month|/hr)|"
    r"\d+(?:[.,]\d+)?\s*(?:req|API credits|credits))", re.I)

_AUDIT_META = re.compile(
    r"(consult\w*\s+(inicial|nesta|posterior|fora)|revalida[çc][ãa]o|"
    r"nesta auditoria|fora do material da run|data da consulta|"
    r"fonte: api github|artefato: )", re.I)

# Ordinal/editorial labels chosen by the report ("3º lugar", "6ª recomendação",
# "recomendação principal").
_ORDINAL = re.compile(
    r"(\d+[ºo°]\s*(lugar|coloca|posi)|\b\d+[ªa]\s*recomenda|"
    r"recomenda[çc][ãa]o\s+principal|lista\s+final|at[ée]\s+cinco|"
    r"alternativa\s+(enxuta|equivalente))", re.I)

# Package alias mapping: claim-side name -> evidence-side identifiers.
_PKG_ALIASES: dict[str, list[str]] = {
    "opencode-daytona": ["@daytona/opencode", "daytona/opencode", "opencode-plugin"],
    "daytona": ["@daytona/opencode", "daytona/opencode", "opencode-plugin"],
}

# Metadata list labels under package headings: Tag, Branch, Commit, Data.
# Captura cada label individualmente (não ganancioso).
_META_LABELS = re.compile(
    r"(?:^\s*-\s*\*\*)?"              # optional bullet + ** start
    r"(tag|branch|commit|data)"             # label (group 1)
    r"(?:\s*\(([^)]*)\))?"                  # optional parenthetical, capture content (group 2)
    r"(?:\s*\*\*?)?"                     # optional ** around label
    r"(?:\s*`([^`]*)`)?"                    # optional inline code after label, captured (group 3)
    r"(?:\s*(HEAD))?"                        # optional HEAD suffix for branch, captured (group 4)
    r"\s*\*?\*?\s*:\s*"                  # optional ** around colon
    r"(.+?)"                                # value (lazy, group 5)
    r"(?=\n(?:\s*-\s*\*\*)|\n|$)",       # stop at next bullet/line/end
    re.I | re.M | re.X)

def _extract_metadata_lists(block_text: str, subject: str,
                            block_id: str | None) -> list[dict]:
    """Extrai listas Tag/Branch/Commit/Data de um bloco de metadados.

    Herda o sujeito do título do pacote. Mantém commit de tag e HEAD de branch
    como relações distintas.
    """
    claims: list[dict] = []
    for m in _META_LABELS.finditer(block_text):
        label = m.group(1).lower()
        value = m.group(2).strip()
        value = __import__('re').sub(r'\*+\s*', '', value).strip()
        value = __import__('re').sub(r'`+', '', value).strip()
        value = __import__('re').sub(r'\s+', ' ', value).strip()
        claim_text = f"{subject}: {label} {value}"
        cid = _next_claim_id()
        _register_claim(block_id, cid, [subject],
                        f"metadado {label} herdado do título do pacote",
                        claim_text, "selected",
                        duplicate_of=None)
        claims.append({
            "id": cid,
            "claim": claim_text,
            "packages": [subject],
            "licences": [],
            "free_assertion": False,
            "priority": 0,
            "anchors": [],
            "evidence": "",
            "spoken_refs": [],
            "metadata_label": label,
            "metadata_value": value,
        })
    return claims


_TABLE_ROW = re.compile(r"^\s*\|([^|]+(?:\|[^|]+)+)\|\s*$")
_FACTUAL_TITLE = re.compile(r"^(.+?)\s+(é\s+(gratuito|livre|pago|grátis)|usa\s+(licença|licença\s+MIT|licença\s+Apache|licença\s+BSD|licença\s+ISC|licença\s+SUL-1\.0))\s*$", re.I)
def _extract_table_rows(table_text: str, block_id: str | None,
                        evidence: dict[str, str]) -> list[dict]:
    """Extrai fatos de linhas de tabela, um claim por sujeito.

    Não junta cinco repositórios numa única afirmação.
    Suporta tabelas com pacotes nas linhas E tabelas comparativas com
    pacotes nos cabeçalhos de coluna.
    """
    claims: list[dict] = []
    lines_tbl = table_text.split("\n")
    header_cells: list[str] = []
    data_lines: list[list[str]] = []
    in_table = False
    for line in lines_tbl:
        m = _TABLE_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if not in_table:
            header_cells = cells
            in_table = True
            continue
        if all(set(c) <= set("-: ") for c in cells if c):
            continue
        if len(cells) < 2:
            continue
        data_lines.append(cells)

    if not header_cells or not data_lines:
        return claims

    header_has_packages = False
    for i, cell in enumerate(header_cells):
        if i == 0:
            continue
        if _PKG_RE.search(cell):
            header_has_packages = True
            break

    if header_has_packages:
        # TABELA COMPARATIVA: pacotes nos cabeçalhos de coluna
        for row in data_lines:
            if len(row) < 2:
                continue
            attribute = row[0].strip("`").strip()
            for col_idx in range(1, min(len(row), len(header_cells))):
                pkg_cell = header_cells[col_idx].strip("`").strip()
                value_cell = row[col_idx].strip("`").strip() if col_idx < len(row) else ""
                if not value_cell or value_cell.lower() in ("-", "—", "", "n/a", "na"):
                    continue
                pkg_match = _PKG_RE.search(pkg_cell)
                packages = [pkg_match.group(0).strip("`").strip()] if pkg_match else [pkg_cell]
                claim_text = f"{packages[0]}: {attribute} {value_cell}"
                cid = _next_claim_id()
                _register_claim(block_id, cid, packages,
                                "tabela comparativa — célula por sujeito",
                                claim_text, "selected",
                                duplicate_of=None)
                # Usar a seleção de evidências já validada para tabelas
                _t_anchors, _t_evidence = _select_evidence(
                    packages, claim_text, evidence or {}, [])
                claims.append({
                    "id": cid,
                    "claim": claim_text,
                    "packages": packages,
                    "licences": [],
                    "free_assertion": False,
                    "priority": 0,
                    "anchors": _t_anchors,
                    "evidence": _t_evidence,
                    "spoken_refs": [],
                    "table_row": True,
                    "table_column_subject": True,
                })
    else:
        # TABELA SIMPLES: pacotes nas linhas
        for row in data_lines:
            if len(row) < 2:
                continue
            subject_cell = None
            subject_idx = None
            for idx, cell in enumerate(row):
                cell_stripped = cell.strip("`").strip()
                if cell_stripped.lower() in ("pacote", "package", "aspecto", "aspect"):
                    continue
                pkg_match = _PKG_RE.search(cell_stripped)
                if pkg_match:
                    subject_cell = pkg_match.group(0).strip("`").strip()
                    subject_idx = idx
                    break
            if subject_cell is None:
                subject_cell = row[0].strip("`").strip()
                subject_idx = 0
            for idx in range(len(row)):
                if idx == subject_idx:
                    continue
                cell_value = row[idx].strip("`").strip()
                if not cell_value or cell_value.lower() in ("-", "—", "", "n/a", "na"):
                    continue
                header_label = header_cells[idx] if idx < len(header_cells) else f"coluna {idx}"
                header_label = header_label.strip("`").strip()
                claim_text = f"{subject_cell}: {header_label} {cell_value}"
                cid = _next_claim_id()
                _register_claim(block_id, cid, [subject_cell],
                                "tabela simples — fato por sujeito",
                                claim_text, "selected",
                                duplicate_of=None)
                # Usar a seleção de evidências já validada para tabelas
                _t_anchors, _t_evidence = _select_evidence(
                    [subject_cell], claim_text, evidence or {}, [])
                claims.append({
                    "id": cid,
                    "claim": claim_text,
                    "packages": [subject_cell],
                    "licences": [],
                    "free_assertion": False,
                    "priority": 0,
                    "anchors": _t_anchors,
                    "evidence": _t_evidence,
                    "spoken_refs": [],
                    "table_row": True,
                    "table_column_subject": False,
                })
    return claims


def evidence_text(url: str) -> str:
    return _EVIDENCE_STORE.get(url, "")


_EVIDENCE_STORE: dict[str, str] = {}
_COVERAGE_BLOCKS: dict[str, dict] = {}
_COVERAGE_CLAIMS: dict[int, dict] = {}
_COVERAGE_DROPPED: list[dict] = []
_COVERAGE_SCOPE: dict = {}
_COVERAGE_NEXT_CLAIM_ID: int = 0


def _reset_coverage() -> None:
    global _COVERAGE_BLOCKS, _COVERAGE_CLAIMS, _COVERAGE_DROPPED
    global _COVERAGE_SCOPE, _COVERAGE_NEXT_CLAIM_ID
    _COVERAGE_BLOCKS.clear()
    _COVERAGE_CLAIMS.clear()
    _COVERAGE_DROPPED.clear()
    _COVERAGE_SCOPE.clear()
    _COVERAGE_NEXT_CLAIM_ID = 0


def _declare_scope(report: str) -> None:
    """Declara o escopo auditado: corpo anterior ao apêndice de auditoria."""
    global _COVERAGE_SCOPE
    cut = report.find("## 7. Auditoria")
    scope_text = report[:cut] if cut >= 0 else report
    _COVERAGE_SCOPE = {
        "delimiter": "## 7. Auditoria",
        "rule": "corpo anterior ao apêndice de auditoria",
        "hash_sha256": _hashlib.sha256(scope_text.encode("utf-8")).hexdigest(),
        "chars": len(scope_text),
        "delimiter_found": cut >= 0,
        "delimiter_position": cut,
    }


def _claim_words(sentence: str) -> set[str]:
    """Distinctive lowercase words of a sentence, for content-based anchoring."""
    stop = {"opencode", "plugin", "para", "como", "the", "and", "com", "que",
            "nao", "não", "isso", "essa", "este", "uma", "mais", "seus", "suas",
            "documented", "compatibility", "compatível", "about", "with", "from"}
    words = {w.lower() for w in
             re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_.+-]{3,}", sentence)}
    return words - stop


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
        start = max(0, idx - 1200)
        end = min(len(txt), idx + budget - 1200)
        window = ("…" if start > 0 else "") + txt[start:end] + \
                 ("…" if end < len(txt) else "")
        parts.append(window)
    return "\n\n".join(parts) or "(sem evidência)"


def _is_package_doc(url: str, packages: list[str]) -> bool:
    """Verifica se uma URL é documentação do pacote (README, tree, blob, etc.)."""
    url_lower = url.lower()
    if "readme" in url_lower:
        for p in packages:
            if p.lower().replace("-", "") in url_lower.replace("-", ""):
                return True
            if p in _PKG_ALIASES:
                for alias in _PKG_ALIASES[p]:
                    if alias.lower().replace("-", "") in url_lower.replace("-", ""):
                        return True
        return False
    if "/tree/" in url_lower or "/blob/" in url_lower:
        for p in packages:
            if p.lower().replace("-", "") in url_lower.replace("-", ""):
                return True
            if p in _PKG_ALIASES:
                for alias in _PKG_ALIASES[p]:
                    if alias.lower().replace("-", "") in url_lower.replace("-", ""):
                        return True
    for p in packages:
        if p.lower() in url_lower:
            return True
        if p in _PKG_ALIASES:
            for alias in _PKG_ALIASES[p]:
                if alias.lower() in url_lower:
                    return True
    return False


def _select_evidence(pkgs: list[str], sentence: str, evidence: dict,
                     spoken_refs: list[str] = None) -> tuple[list[str], str]:
    """Selecione âncoras e texto de evidência para uma afirmação.

    Aplica a mesma lógica de seleção validada: fonte explicitamente citada
    (Priority 1), documentação do pacote (Priority 2), depois correspondência
    por nome e tokens distintos. Retorna (anchors, evidence_text).
    """
    if spoken_refs is None:
        spoken_refs = []
    expanded_pkgs = list(pkgs)
    for p in pkgs:
        if p in _PKG_ALIASES:
            expanded_pkgs.extend(_PKG_ALIASES[p])
    anchors = [u for p in expanded_pkgs for u, txt in evidence.items()
               if p.lower() in txt.lower()]

    # Tenta sufixo do pacote (ex: "opencode-daytona" → "daytona" no texto)
    if not anchors:
        for p in pkgs:
            if p.startswith("opencode-"):
                suffix = p[len("opencode-"):]
                for u, txt in evidence.items():
                    if u in anchors:
                        continue
                    if suffix.lower() in txt.lower():
                        anchors.append(u)

    if spoken_refs:
        for u, txt in evidence.items():
            if any(r in txt for r in spoken_refs) and u not in anchors:
                anchors.insert(0, u)
    if not anchors:
        _scored = []
        for u, txt in evidence.items():
            low = txt.lower()
            hits = sum(1 for w in _claim_words(sentence) if w in low)
            if hits >= 2:
                _scored.append((hits, u))
        anchors = [u for _hits, u in sorted(_scored, reverse=True)]
    _seen_dup = set()
    anchors = [u for u in anchors
               if not (u in _seen_dup or _seen_dup.add(u))]

    # Transcript-backed claim must anchor to the TRANSCRIPT
    if spoken_refs:
        _exact = [u for u in anchors
                  if any(r in evidence[u] for r in spoken_refs)]
        _transcripts = [u for u in anchors
                        if "[spoken" in evidence[u] and u not in _exact]
        _others = [u for u in anchors if u not in _exact
                   and u not in _transcripts]
        anchors = (_exact or []) + (_transcripts or []) + (_others or [])
    else:
        anchors.sort(key=lambda u: -sum(
            1 for w in _claim_words(sentence) if w in evidence[u].lower()))

    # Distinctive tokens recover the right source
    if len(anchors) < 2:
        for u, txt in evidence.items():
            if u in anchors:
                continue
            low = txt.lower()
            hits = sum(1 for w in _claim_words(sentence)
                       if len(w) > 5 and w in low)
            if hits >= 3 and u not in anchors:
                anchors.append(u)

    # PRIORITY 1: EXPLICITLY CITED SOURCES
    explicitly_cited = []
    for u in evidence:
        if u in sentence or u.replace("https://", "").replace("www.", "") in sentence:
            explicitly_cited.append(u)
    for u in explicitly_cited:
        if u not in anchors:
            anchors.append(u)
    new_anchors = []
    seen_cited = set()
    for u in explicitly_cited:
        if u in anchors and u not in seen_cited:
            new_anchors.append(u)
            seen_cited.add(u)
    for u in anchors:
        if u not in seen_cited:
            new_anchors.append(u)
    anchors = new_anchors

    # PRIORITY 2: PACKAGE DOCUMENTATION
    doc_anchors = [u for u in anchors if u not in explicitly_cited
                   and _is_package_doc(u, pkgs)]
    other_anchors = [u for u in anchors if u not in explicitly_cited
                     and u not in doc_anchors]
    anchors = explicitly_cited + doc_anchors + other_anchors

    # Remove duplicates while preserving order
    seen_anchors2 = set()
    unique_anchors = []
    for u in anchors:
        if u not in seen_anchors2:
            unique_anchors.append(u)
            seen_anchors2.add(u)
    anchors = unique_anchors

    # Price table: match on figures
    if not anchors:
        for u, txt in evidence.items():
            for tok in _PRICE_TOKENS.findall(sentence):
                if tok in txt:
                    anchors.append(u)
                    break

    evidence_text = _evidence_window(anchors, spoken_refs)
    return anchors, evidence_text


def _classify_block(text: str) -> tuple[str, str]:
    """Classifica um bloco de origem e retorna (classificação, motivo).

    Não classifica como 'não factual' apenas porque não passou numa regex
    ou excedeu um tamanho. Quando não consegue processar conteúdo factual,
    registra extração incompleta.
    """
    stripped = text.strip()
    if not stripped:
        return "vazio", "bloco sem conteúdo"
    lines = stripped.split("\n")
    first_line = lines[0]
    rest = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    if re.match(r"^#{1,6}\s", first_line):
        if rest and len(rest) > 25:
            return "paragrafo", "bloco com heading + conteúdo factual"
        return "titulo", "título de seção — pode conter contexto factual"
    if _AUDIT_META.search(stripped):
        return "metadado_auditoria", "descreve o processo de auditoria, não um fato sobre pacote"
    if _ORDINAL.search(stripped) and len(stripped) < 260:
        return "editorial", "rótulo editorial/ordenação do próprio relatório"
    if re.match(r"^\d+\.\d+\s+\S.*—\s*\S+$", stripped) and len(stripped) < 120:
        return "subsecao_editorial", "subseção com rótulo editorial"
    if "|" in stripped and stripped.count("|") >= 2:
        return "tabela", "linha de tabela — pode conter fatos por linha e sujeito"
    return "paragrafo", "bloco de texto factual ou misto"


def _split_into_blocks(text: str) -> list[tuple[str, int, str]]:
    """Divide o texto em blocos por cabeçalho markdown.

    Retorna lista de (secao, posicao_caracter, texto_do_bloco).
    """
    blocks: list[tuple[str, int, str]] = []
    lines = text.split("\n")
    current_section = "(início do documento)"
    current_start = 0
    current_lines: list[str] = []

    def flush():
        nonlocal current_start, current_lines
        if current_lines:
            block_text = "\n".join(current_lines).strip()
            if block_text:
                blocks.append((current_section, current_start, block_text))
            current_lines = []

    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s", line.strip()):
            flush()
            current_section = line.strip()
            current_start = i
        current_lines.append(line)
    flush()
    return blocks


def _register_block(section: str, position: int, text: str) -> str:
    """Registra um bloco de origem e retorna seu ID."""
    block_id = f"blk_{len(_COVERAGE_BLOCKS)}"
    classification, reason = _classify_block(text)
    _COVERAGE_BLOCKS[block_id] = {
        "id": block_id,
        "section": section,
        "position": position,
        "original_text": text,
        "classification": classification,
        "classification_reason": reason,
        "claim_ids": [],
        "extraction_state": "processed",
    }
    return block_id


def _register_dropped(block_id: str | None, text: str, reason: str,
                      state: str = "dropped") -> None:
    """Registra conteúdo que não virou afirmação."""
    _COVERAGE_DROPPED.append({
        "block_id": block_id,
        "text": text[:200],
        "reason": reason,
        "state": state,
    })


def _next_claim_id() -> int:
    """Retorna o próximo ID estável de afirmação (antes da ordenação)."""
    global _COVERAGE_NEXT_CLAIM_ID
    cid = _COVERAGE_NEXT_CLAIM_ID
    _COVERAGE_NEXT_CLAIM_ID += 1
    return cid


def _register_claim(block_id: str | None, claim_id: int, subject: list[str],
                    context: str, text: str, selection_state: str,
                    duplicate_of: int | None = None,
                    defer_reason: str | None = None) -> None:
    """Registra uma afirmação no registro de cobertura."""
    _COVERAGE_CLAIMS[claim_id] = {
        "id": claim_id,
        "block_id": block_id,
        "subject": subject,
        "context": context,
        "text": text,
        "selection_state": selection_state,
        "duplicate_of": duplicate_of,
        "defer_reason": defer_reason,
        "review_state": "not_reviewed",
    }
    if block_id is not None and block_id in _COVERAGE_BLOCKS:
        _COVERAGE_BLOCKS[block_id]["claim_ids"].append(claim_id)


def get_coverage_report() -> dict:
    """Retorna o registro completo de cobertura da última extração."""
    total_blocks = len(_COVERAGE_BLOCKS)
    total_claims = len(_COVERAGE_CLAIMS)
    selected_claims = sum(1 for c in _COVERAGE_CLAIMS.values()
                          if c["selection_state"] == "selected")
    deferred_claims = sum(1 for c in _COVERAGE_CLAIMS.values()
                          if c["selection_state"] == "deferred_by_cap")
    excluded_duplicates = sum(1 for c in _COVERAGE_CLAIMS.values()
                              if c["selection_state"] == "excluded_duplicate")
    processed_blocks = sum(1 for b in _COVERAGE_BLOCKS.values()
                           if b["extraction_state"] == "processed")
    incomplete_blocks = sum(1 for b in _COVERAGE_BLOCKS.values()
                            if b["extraction_state"] == "incomplete")
    reviewed_claims = sum(1 for c in _COVERAGE_CLAIMS.values()
                          if c["review_state"] != "not_reviewed")
    incomplete_claims = sum(1 for c in _COVERAGE_CLAIMS.values()
                            if c["selection_state"] == "incomplete")

    return {
        "scope": dict(_COVERAGE_SCOPE),
        "counts": {
            "blocks_total": total_blocks,
            "blocks_processed": processed_blocks,
            "blocks_incomplete": incomplete_blocks,
            "claims_total": total_claims,
            "claims_selected": selected_claims,
            "claims_deferred_by_cap": deferred_claims,
            "claims_excluded_duplicate": excluded_duplicates,
            "claims_incomplete": incomplete_claims,
            "claims_reviewed": reviewed_claims,
            "dropped_items": len(_COVERAGE_DROPPED),
        },
        "blocks": list(_COVERAGE_BLOCKS.values()),
        "claims": list(_COVERAGE_CLAIMS.values()),
        "dropped": list(_COVERAGE_DROPPED),
        "coverage_complete": (
            deferred_claims == 0 and incomplete_blocks == 0 and incomplete_claims == 0
        ),
    }


def _find_block_for_position(char_pos: int,
                             block_map: list[tuple[str, int, str]]) -> str | None:
    """Encontra o bloco que contém a posição de caractere dada."""
    if not block_map:
        return None
    best_bid = None
    for bid, pos, _text in block_map:
        if pos <= char_pos:
            best_bid = bid
        else:
            break
    return best_bid


def _extract_metadata_lists(block_text: str, subject: str,
                            block_id: str | None) -> list[dict]:
    """Extrai listas Tag/Branch/Commit/Data de um bloco de metadados.

    Herda o sujeito do título do pacote. Mantém commit de tag e HEAD de branch
    como relações distintas.
    """
    claims: list[dict] = []
    for m in _META_LABELS.finditer(block_text):
        label = m.group(1).lower()
        value = m.group(2).strip()
        value = __import__('re').sub(r'\*+\s*', '', value).strip()
        value = __import__('re').sub(r'`+', '', value).strip()
        value = __import__('re').sub(r'\s+', ' ', value).strip()
        claim_text = f"{subject}: {label} {value}"
        cid = _next_claim_id()
        _register_claim(block_id, cid, [subject],
                        f"metadado {label} herdado do título do pacote",
                        claim_text, "selected",
                        duplicate_of=None)
        claims.append({
            "id": cid,
            "claim": claim_text,
            "packages": [subject],
            "licences": [],
            "free_assertion": False,
            "priority": 0,
            "anchors": [],
            "evidence": "",
            "spoken_refs": [],
            "metadata_label": label,
            "metadata_value": value,
        })
    return claims


def _extract_factual_title(section_heading: str, block_id: str | None,
                           evidence: dict = None) -> list[dict]:
    """Extrai proposição de título factual (ex: 'Pacote X é gratuito').

    Diferencia 'Pacote X' (apenas contexto) de 'Pacote X é gratuito' (fato).
    """
    claims: list[dict] = []
    m = _FACTUAL_TITLE.match(section_heading.strip())
    if m:
        full_title = m.group(0).strip()
        pkg_match = _PKG_RE.search(section_heading)
        packages = [pkg_match.group(0).strip("`").strip()] if pkg_match else []
        cid = _next_claim_id()
        _register_claim(block_id, cid, packages,
                        "título factual — proposição sobre o pacote",
                        full_title, "selected",
                        duplicate_of=None)
        # Usar a seleção de evidências já validada para títulos
        anchors, evidence_text = _select_evidence(
            packages, full_title, evidence or {}, [])
        claims.append({
            "id": cid,
            "claim": full_title,
            "packages": packages,
            "licences": [],
            "free_assertion": False,
            "priority": 0,
            "anchors": anchors,
            "evidence": evidence_text,
            "spoken_refs": [],
            "factual_title": True,
        })
    return claims


def _split_long_paragraph(text: str, block_id: str | None) -> list[dict]:
    """Divide parágrafo longo preservando fatos, ou registra extração incompleta.

    O filtro de tamanho não é justificativa de exclusão não factual.
    """
    claims: list[dict] = []
    if len(text) <= _LONG_PARA_THRESHOLD:
        return claims

    # Tenta dividir por pontos seguidos de espaço + letra maiúscula
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÿ0-9])", text)
    if len(sentences) > 1:
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            cid = _next_claim_id()
            _register_claim(block_id, cid, [],
                            "parágrafo longo dividido em sentenças",
                            s, "selected",
                            duplicate_of=None)
            claims.append({
                "id": cid,
                "claim": s,
                "packages": [],
                "licences": [],
                "free_assertion": False,
                "priority": 0,
                "anchors": [],
                "evidence": "",
                "spoken_refs": [],
                "split_from_long_para": True,
            })
        return claims

    # Não conseguiu dividir: registra extração incompleta
    cid = _next_claim_id()
    _register_claim(block_id, cid, [],
                    "parágrafo longo não divisível — extração incompleta",
                    text[:200], "incomplete",
                    defer_reason="parágrafo acima do limite sem divisão de sentenças")
    claims.append({
        "id": cid,
        "claim": text[:200],
        "packages": [],
        "licences": [],
        "free_assertion": False,
        "priority": 0,
        "anchors": [],
        "evidence": "",
        "spoken_refs": [],
        "incomplete_extraction": True,
    })
    return claims


def _is_editorial_only(s: str) -> bool:
    """Verifica se a sentença é apenas preferência editorial sem fato."""
    return bool(_ORDINAL.search(s) and len(s) < 260)


def _extract_factual_justification(s: str) -> str | None:
    """Extrai a justificativa factual de uma recomendação editorial.

    Ex: 'Recomendação principal: escolha `opencode-alpha` porque não exige
    nenhum serviço externo pago.' → justificativa: 'não exige nenhum serviço
    externo pago'
    """
    s_clean = _ORDINAL.sub("", s).strip()
    s_clean = re.sub(r"^[,:;\s–—-]+", "", s_clean).strip()
    if not s_clean:
        return None
    if _PKG_RE.search(s_clean) or _LIC_RE.search(s_clean) or _FREE_WORDS.search(s_clean):
        return s_clean
    return None


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
    # ═════════════════════════════════════════════════════════════════════════
    # COBERTURA — inicializa registro e declara escopo antes de qualquer filtro
    # ═════════════════════════════════════════════════════════════════════════
    _reset_coverage()
    _declare_scope(report)
    _EVIDENCE_STORE.clear(); _EVIDENCE_STORE.update(evidence or {})

    # Divide o escopo em blocos por cabeçalho e registra cada um
    scope_text = report[:report.find("## 7. Auditoria")] if "## 7. Auditoria" in report else report
    blocks = _split_into_blocks(scope_text)
    block_map: list[tuple[str, int, str]] = []  # (block_id, position, text)
    for section, position, text in blocks:
        bid = _register_block(section, position, text)
        block_map.append((bid, position, text))

    # ════════════════════════════════════════════════════════════════════
    # EXTRAÇÃO DE TABELAS ANTES DO re.sub DE PIPES
    # Linhas de tabela são processadas como claims separadas por sujeito
    # ════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════
    # EXTRAÇÃO DE TABELAS — cada tabela contígua processada separadamente
    # com seu próprio cabeçalho, respeitando o escopo declarado.
    # ═══════════════════════════════════════════════════════════════════
    _table_claims: list[dict] = []
    _table_lines_to_remove: set[str] = set()
    _scope_lines = scope_text.split("\n")
    _i = 0
    while _i < len(_scope_lines):
        line = _scope_lines[_i]
        if _TABLE_ROW.match(line):
            # Coletar linhas contíguas da mesma tabela
            table_lines = []
            while _i < len(_scope_lines) and _TABLE_ROW.match(_scope_lines[_i]):
                table_lines.append(_scope_lines[_i])
                _table_lines_to_remove.add(_scope_lines[_i])
                _i += 1
            # Encontrar o bloco que contém esta tabela
            table_block_id = None
            table_text = "\n".join(table_lines)
            # Posição da tabela (índice de linha) no scope_text para encontrar o bloco.
            # _split_into_blocks usa índice de linha como posição, não posição de caractere.
            table_start = _i - len(table_lines)
            for b_id, b_pos, b_text in block_map:
                if b_pos <= table_start < b_pos + len(b_text.split("\n")):
                    table_block_id = b_id
                    break
            # Extrair claims da tabela com seleção de evidências
            tc_list = _extract_table_rows(table_text, table_block_id, evidence)
            for tc in tc_list:
                _table_claims.append(tc)
        else:
            _i += 1

    claims: list[dict] = list(_table_claims)

    # PRÉ-PROCESSAMENTO DE METADADOS POR LINHA (antes da junção de linhas)
    # Cada linha "- **Tag:** v1.2.3" é um fato separado; não pode ser
    # diluída pelo re.sub que junta linhas adjacentes.
    scope_lines = scope_text.split("\n")
    _current_package_subject: str | None = None
    for line_idx, raw_line in enumerate(scope_lines):
        line = raw_line.strip()
        if not line:
            continue
        # Detectar heading de pacote para herdar sujeito
        heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            pkg_match = _PKG_RE.search(heading_text)
            if pkg_match:
                _current_package_subject = pkg_match.group(0).strip("`")
            continue
        # Linha de metadado: Tag:, Branch:, Commit:, Data:
        meta_match = _META_LABELS.search(line)
        if meta_match and _current_package_subject:
            label = meta_match.group(1).lower()
            qualifier = meta_match.group(2)  # content inside parens, e.g. "tag v1.2.3"
            inline_code = meta_match.group(3)  # backticked code after label, e.g. "main"
            head = meta_match.group(4)  # "HEAD" or None
            value = meta_match.group(5).strip()
            value = re.sub(r"\*+\s*", "", value).strip()
            value = re.sub(r"`+", "", value).strip()
            value = re.sub(r"\s+", " ", value).strip()
            if value:
                # Preserve qualifiers: "commit (tag v1.2.3): AAA",
                # "branch `main` HEAD: BBB", "tag v1.2.3"
                if label == "tag":
                    parts = [label]
                    if qualifier:
                        parts.append(f"({qualifier})")
                    parts.append(value)
                    claim_text = f"{_current_package_subject}: {' '.join(parts)}"
                elif head:
                    parts = [label]
                    if inline_code:
                        parts.append(f"`{inline_code}`")
                    parts.append(head)
                    claim_text = f"{_current_package_subject}: {' '.join(parts)}: {value}"
                else:
                    parts = [label]
                    if qualifier:
                        parts.append(f"({qualifier})")
                    claim_text = f"{_current_package_subject}: {' '.join(parts)}: {value}"
                cid = _next_claim_id()
                # Match block by line index range, not first textual match:
                # find the block whose line range contains this line's index.
                bid = None
                for b_id, b_pos, b_text in block_map:
                    if b_pos <= line_idx < b_pos + len(b_text.split("\n")):
                        bid = b_id
                        break
                _register_claim(bid, cid, [_current_package_subject],
                                f"metadado {label} herdado do título do pacote",
                                claim_text, "selected")
                claims.append({
                    "id": cid,
                    "claim": claim_text,
                    "packages": [_current_package_subject],
                    "licences": [],
                    "free_assertion": False,
                    "priority": 0,
                    # Usar a seleção de evidências já validada para metadados
                })
                _m_anchors, _m_evidence = _select_evidence(
                    [_current_package_subject], claim_text, evidence or {}, [])
                claims[-1]["anchors"] = _m_anchors
                claims[-1]["evidence"] = _m_evidence

    # Remover linhas de tabela do report para evitar processamento duplo
    # no escopo (que é derivado de report abaixo).
    if _table_lines_to_remove:
        _report_lines = report.split("\n")
        report = "\n".join(
            l for l in _report_lines if l not in _table_lines_to_remove)

    # Fenced code blocks are quoted evidence, not assertions.
    scope_text = report[:report.find('## 7. Auditoria')] if '## 7. Auditoria' in report else report
    prose = re.sub(r"```.*?```", " ", scope_text, flags=re.S)
    # Markdown table rows are kept whole (one row = one claim candidate).
    prose = re.sub(r"^\|.*\|$",
                   lambda m: m.group(0).replace("|", " · ").strip(" ·"),
                   prose, flags=re.M)
    # Hard-wrapped prose is one sentence split across lines.
    prose = re.sub(r"(?<![.!?:;])\n(?=[ \t]*\S)", " ", prose)
    prose = re.sub(r"[ \t]{2,}", " ", prose)
    sentences = re.split(r"(?<=[.!?])(?<![0-9])\s+|\n", prose)
    seen: set[str] = set()
    _last_spoken: list[str] = []
    _EVIDENCE_STORE.update(evidence)
    _last_pkgs: list[str] = []

    # Track current package subject for inheriting to metadata lists
    _current_package_subject: str | None = None

    for sent in sentences:
        s = sent.strip()
        # Track the most recent `[spoken]` refs BEFORE any filter can `continue`
        _spoken = re.findall(r"\[spoken\s[^\]]*\]", s)
        _spoken = [ref for ref in _spoken if not re.match(r"\[spoken\s+[iI]\s*/\s*[mM]\]", ref)]
        if _spoken:
            _last_spoken = _spoken[-3:]
        _has_spoken = bool(_spoken) or bool(_last_spoken)

        # Reset spoken refs when package context changes significantly
        current_pkgs = [p for tup in _PKG_RE.findall(s) for p in tup if p]
        if current_pkgs and set(current_pkgs) != set(_last_pkgs):
            _last_spoken = []
        _last_pkgs = current_pkgs

        _bid = None

        # Skip table-row remnants (already processed by _extract_table_rows).
        # After re.sub of pipes, table rows look like: "· pkg · MIT · gratuito ·"
        # These contain spurious package-like tokens from cells (—, 5, etc.).
        if " · " in s and s.count(" · ") >= 2:
            _register_dropped(_bid, s, "linha de tabela já processada pelo extrator de tabela", "dropped")
            continue

        # Determine the block of origin by matching sentence text to block text
        for bid, pos, btext in block_map:
            if s in btext:
                _bid = bid
                break
        if _bid is None and block_map:
            for bid, pos, btext in block_map:
                if any(w in btext for w in s.split() if len(w) > 5):
                    _bid = bid
                    break

        # Track package subject from headings for metadata inheritance
        heading_match = re.match(r"^#{1,6}\s*(.+)$", s)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            pkg_match = _PKG_RE.search(heading_text)
            if pkg_match:
                _current_package_subject = pkg_match.group(0).strip("`")
            # Check if this is a factual title
            factual_claims = _extract_factual_title(heading_text, _bid, evidence)
            for fc in factual_claims:
                claims.append(fc)
            continue

        # Table rows - check BEFORE pipe substitution (original line may have pipes)
        # We check the original sentence which may contain pipes from table rows
        table_claims = _extract_table_rows(s, _bid, evidence)
        if table_claims:
            for tc in table_claims:
                claims.append(tc)
            continue

        # Check for long paragraph that needs splitting BEFORE size filter.
        # O filtro de tamanho não é justificativa de exclusão não factual.
        if len(s) > _LONG_PARA_THRESHOLD:
            split_claims = _split_long_paragraph(s, _bid)
            for sc in split_claims:
                claims.append(sc)
            continue

        if len(s) < 25:
            _register_dropped(_bid, s, "muito curto (< 25 chars)", "dropped")
            continue

        pkgs = [p for tup in _PKG_RE.findall(s) for p in tup if p]
        is_free = bool(_FREE_WORDS.search(s))
        lics = _LIC_RE.findall(s)

        # Editorial-only label: separate justification from preference
        if _is_editorial_only(s) and not pkgs and not lics and not is_free:
            just = _extract_factual_justification(s)
            if just:
                cid = _next_claim_id()
                _register_claim(_bid, cid, [],
                                "justificativa factual de recomendação editorial",
                                just, "selected",
                                duplicate_of=None)
                claims.append({
                    "id": cid,
                    "claim": just,
                    "packages": [],
                    "licences": [],
                    "free_assertion": False,
                    "priority": 0,
                    "anchors": [],
                    "evidence": "",
                    "spoken_refs": [],
                    "factual_justification": True,
                })
            _register_dropped(_bid, s, "rótulo editorial/ordenação", "dropped")
            continue

        if not (pkgs or lics) or (not is_free and not pkgs):
            _register_dropped(_bid, s, "sem pacote, licença ou afirmação de gratuito", "dropped")
            continue

        # Provenance notes about the AUDIT itself are not claims about a package.
        if _AUDIT_META.search(s):
            _register_dropped(_bid, s, "metadado de auditoria (provenance)", "dropped")
            continue

        # Bare Markdown heading
        if re.match(r"^#{1,6}\s", s):
            _register_dropped(_bid, s, "título de seção (markdown heading)", "dropped")
            continue

        # Subsection heading
        if re.match(r"^\d+\.\d+\s+\S.*—\s*\S+$", s) and len(s) < 120:
            _register_dropped(_bid, s, "subseção com rótulo editorial", "dropped")
            continue

        # Usar a seleção de evidências já validada
        _s_anchors, _s_evidence_text = _select_evidence(
            pkgs, s, evidence or {}, _spoken or _last_spoken)
        anchors = _s_anchors

        # Dedup key: full normalized text + subject context, so different
        # propositions with the same prefix are NOT treated as duplicates.
        norm_text = re.sub(r"\s+", " ", s).strip()
        key = " ".join(sorted(pkgs)) + "|" + norm_text
        if key in seen:
            _register_dropped(_bid, s, "duplicata (mesmo texto e sujeito)", "excluded_duplicate")
            # Registrar a duplicata apontando para a original (apenas no ledger,
            # não devolvê-la para revisão nem consumir o limite)
            cid = _next_claim_id()
            original_id = None
            for existing_cid, existing in _COVERAGE_CLAIMS.items():
                if existing["text"] == s:
                    original_id = existing_cid
                    break
            _register_claim(_bid, cid, pkgs, "duplicata de " + str(original_id),
                           s, "excluded_duplicate",
                           duplicate_of=original_id,
                           defer_reason="afirmação duplicada")
            continue
        seen.add(key)

        cid = _next_claim_id()
        _register_claim(_bid, cid, pkgs, "extraída do bloco de origem", s, "selected")
        claims.append({
            "id": cid,
            "claim": s,
            "packages": pkgs,
            "licences": lics,
            "free_assertion": is_free,
            "priority": ((2 if is_free else 0) + (1 if len(pkgs) >= 2 else 0) +
                         (2 if _has_spoken else 0)),
            "anchors": anchors[:3],
            "evidence": _s_evidence_text,
            "spoken_refs": (_spoken or _last_spoken),
        })

    # Sort by priority (stable sort preserves insertion order for ties)
    claims.sort(key=lambda c: -c["priority"])
    # IDs são estáveis (atribuídos via _next_claim_id durante a extração);
    # não reatribuir após ordenação para preservar vínculo com _COVERAGE_CLAIMS.

    # Register selection state based on the EFFECTIVE slice after priority sort.
    # Stable IDs are preserved; selection state reflects which claims survived
    # the cap, not whether cid < max_claims.
    effective_selected = {c["id"] for c in claims[:max_claims]}
    for c in claims:
        cid = c["id"]
        if cid in _COVERAGE_CLAIMS:
            # Não sobrescrever claims já marcadas como duplicata ou incompleta
            current_state = _COVERAGE_CLAIMS[cid]["selection_state"]
            if current_state in ("excluded_duplicate", "incomplete"):
                continue
            if cid in effective_selected:
                _COVERAGE_CLAIMS[cid]["selection_state"] = "selected"
            else:
                existing = _COVERAGE_CLAIMS[cid]
                _register_claim(existing["block_id"], cid,
                              existing["subject"],
                              existing["context"],
                              existing["text"],
                              "deferred_by_cap",
                              duplicate_of=existing.get("duplicate_of"),
                              defer_reason=f"fora do limite de {max_claims} afirmações")

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
        return [{"id": it["id"], "verdict": "credential_error",
                 "support": "", "correction": "sem credencial para revisão"}
                for it in items]
    import openai
    client = openai.AsyncOpenAI(api_key=key,
                                base_url="https://openrouter.ai/api/v1")
    out: list[dict] = []
    for i in range(0, len(items), batch_size):
        chunk = items[i:i + batch_size]
        payload = [{k: it[k] for k in
                    ("id", "claim", "packages", "licences", "free_assertion",
                     "evidence")} for it in chunk]
        try:
            r = await client.chat.completions.create(
                model=model, temperature=0, max_tokens=8000,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(
                              payload, ensure_ascii=False)}])
            choice0 = r.choices[0] if r.choices else None
            msg_obj = choice0.message if choice0 else None
            msg = (msg_obj.content if msg_obj else "") or ""
            start, end = msg.find("["), msg.rfind("]")
            if start >= 0 and end > start:
                out.extend(json.loads(msg[start:end + 1]))
            else:
                out.extend({"id": it["id"], "verdict": "invalid_json", "support": "",
                            "correction": "resposta sem JSON válido - revisão incompleta"} for it in chunk)
        except Exception as exc:
            out.extend({"id": it["id"], "verdict": "transport_error", "support": "",
                        "correction": f"{type(exc).__name__}: {exc} - revisão incompleta"} for it in chunk)
    return out


# Valid semantic verdicts (count toward quorum/consensus)
_VALID_VERDICTS = {"sustained", "partial", "unsupported", "gap"}

# Technical failure verdicts (do NOT count toward quorum/consensus)
_FAILURE_VERDICTS = {"review_failure", "credential_error", "transport_error", "invalid_json", "missing_result"}

_TIE_ORDER = {"sustained": 0, "partial": 1, "unsupported": 2, "gap": 3}


async def _review_batch(items: list[dict], model: str,
                        votes: int = 3) -> list[dict]:
    """Review the claims, electing the majority verdict per claim."""
    runs = [await _review_pass(items, model) for _ in range(max(1, votes))]

    # Normalize each run: per passage, per claim, ensure exactly one result
    normalized_runs = []
    for run in runs:
        by_claim: dict[int, list[dict]] = {}
        for v in run:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                by_claim.setdefault(v["id"], []).append(v)

        normalized = []
        for it in items:
            claim_id = it["id"]
            entries = by_claim.get(claim_id, [])
            if not entries:
                normalized.append({
                    "id": claim_id,
                    "verdict": "missing_result",
                    "support": "",
                    "correction": "resposta vazia para esta afirmação",
                })
            elif len(entries) > 1:
                normalized.append({
                    "id": claim_id,
                    "verdict": "invalid_json",
                    "support": "",
                    "correction": f"resultado duplicado na mesma passagem ({len(entries)} entradas para ID {claim_id})",
                })
            else:
                normalized.append(entries[0])

        normalized_runs.append(normalized)

    # Aggregate normalized runs
    by_id: dict[int, list[dict]] = {}
    for run in normalized_runs:
        for v in run:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                by_id.setdefault(v["id"], []).append(v)

    out: list[dict] = []
    for it in items:
        cands = by_id.get(it["id"], [])
        if not cands:
            out.append({"id": it["id"], "verdict": "missing_result", "support": "",
                        "correction": "revisão não retornou este id",
                        "vote_tally": {}, "valid_count": 0, "failure_count": 0})
            continue

        valid_cands = [c for c in cands if c.get("verdict") in _VALID_VERDICTS]
        failure_cands = [c for c in cands if c.get("verdict") in _FAILURE_VERDICTS]

        valid_count = len(valid_cands)
        failure_count = len(failure_cands)

        tally: dict[str, int] = {}
        for c in cands:
            vd = c.get("verdict", "gap")
            tally[vd] = tally.get(vd, 0) + 1

        if valid_count < 2:
            failure_types = [c.get("verdict") for c in failure_cands]
            out.append({
                "id": it["id"],
                "verdict": "review_incomplete",
                "support": "",
                "correction": f"quórum insuficiente ({valid_count}/3 julgamentos válidos); falhas: {failure_types}",
                "vote_tally": tally,
                "valid_count": valid_count,
                "failure_count": failure_count,
            })
            continue

        valid_tally: dict[str, int] = {}
        for c in valid_cands:
            vd = c.get("verdict", "gap")
            valid_tally[vd] = valid_tally.get(vd, 0) + 1

        max_count = max(valid_tally.values())
        winners = [verdict for verdict, count in valid_tally.items() if count == max_count]

        if len(winners) > 1:
            winner = "disputed_tie"
        else:
            winner = winners[0]

        chosen = next((c for c in valid_cands if c.get("verdict") == winner),
                      valid_cands[0] if valid_cands else cands[0])
        out.append({
            "id": it["id"],
            "verdict": winner,
            "support": chosen.get("support", ""),
            "correction": chosen.get("correction", ""),
            "vote_tally": tally,
            "valid_count": valid_count,
            "failure_count": failure_count,
        })
    return out


def _run_review(items: list[dict], model: str, votes: int = 3) -> list[dict]:
    """Drive the review coroutine from sync OR async context."""
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_review_batch(items, model, votes=votes))
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                lambda: asyncio.new_event_loop().run_until_complete(
                    _review_batch(items, model, votes=votes)))
            return future.result()
    except Exception as exc:
        return [{"__audit_failure__": True, "error": f"{type(exc).__name__}: {exc}"}]


def review_report(report: str, evidence: dict[str, str],
                  model: str = "nvidia/nemotron-3-ultra-550b-a55b:free",
                  enabled: bool = True,
                  extra_evidence: dict[str, str] | None = None,
                  votes: int = 3,
                  max_claims: int = 25) -> dict:
    """Audit the claims of a finished report. Returns verdicts + a summary.

    ``enabled=False`` keeps the normal path untouched.
    ``extra_evidence`` maps source-URL -> text for material consulted AFTER the
    run. Merging both maps makes a corrected report reviewable against the
    evidence that actually supports it.
    """
    evidence = {**(evidence or {}), **(extra_evidence or {})}
    if not enabled:
        return {"enabled": False, "claims": 0, "verdicts": [], "summary": {},
                "verdict_state": "não revisado semanticamente"}
    claims = extract_claims(report, evidence, max_claims=max_claims)
    if not claims:
        return {"enabled": True, "claims": 0, "verdicts": [],
                "summary": {"note": "nenhuma afirmação verificável extraída",
                            "coverage": get_coverage_report()},
                "coverage": get_coverage_report(),
                "verdict_state": "revisão incompleta",
                "accepted": False,
                "gaps": 0,
                "partials": 0,
                "claims_reviewed": 0}
    verdicts = _run_review(claims, model, votes=votes)
    # Check for auditor failure
    if verdicts and isinstance(verdicts[0], dict) and verdicts[0].get("__audit_failure__"):
        return {
            "enabled": True,
            "claims": len(claims),
            "verdicts": [],
            "summary": {"error": "revisão incompleta",
                        "detail": verdicts[0].get("error", "unknown")},
            "verdict_state": "revisão incompleta",
            "accepted": False,
            "gaps": 0,
            "partials": 0,
        }
    by_id = {v.get("id"): v for v in verdicts}
    summary: dict[str, int] = {}
    for v in verdicts:
        summary[v.get("verdict", "?")] = summary.get(v.get("verdict", "?"), 0) + 1

    incomplete_claims = [v for v in verdicts if v.get("verdict") == "review_incomplete"]
    failed_claims = [v for v in verdicts if v.get("verdict") in _FAILURE_VERDICTS]
    missing_claims = [v for v in verdicts if v.get("verdict") == "missing_result"]
    disputed_claims = [v for v in verdicts if v.get("verdict") == "disputed_tie"]
    blocking = [v for v in verdicts if v.get("verdict") == "unsupported"]
    gaps = [v for v in verdicts if v.get("verdict") == "gap"]
    partials = [v for v in verdicts if v.get("verdict") == "partial"]

    # Update review_state in coverage registry with actual integration results
    for v in verdicts:
        cid = v.get("id")
        if cid is not None and cid in _COVERAGE_CLAIMS:
            vd = v.get("verdict", "?")
            if vd == "review_incomplete":
                _COVERAGE_CLAIMS[cid]["review_state"] = "review_incomplete"
            elif vd in _FAILURE_VERDICTS:
                _COVERAGE_CLAIMS[cid]["review_state"] = "technical_failure"
            elif vd == "disputed_tie":
                _COVERAGE_CLAIMS[cid]["review_state"] = "disputed_tie"
            else:
                _COVERAGE_CLAIMS[cid]["review_state"] = vd

    # Re-obter coverage APÓS atualizar os estados de revisão
    coverage = get_coverage_report()
    claims_reviewed = sum(1 for c in _COVERAGE_CLAIMS.values()
                          if c["review_state"] != "not_reviewed")

    # A report is accepted only if:
    # - No unsupported claims (blocking)
    # - No incomplete reviews (technical failures prevented quorum)
    # - No disputed ties (conservative policy: tie = not approved)
    # - Gaps and partials are allowed but reported as qualifications
    # - Coverage must be complete (no deferred claims, no incomplete blocks)
    has_blocking = len(blocking) > 0
    has_incomplete = len(incomplete_claims) > 0
    has_disputed = len(disputed_claims) > 0
    has_coverage_gap = not coverage["coverage_complete"]

    # Also check for claims marked incomplete in coverage registry
    has_incomplete_extraction = any(
        c.get("selection_state") == "incomplete" or
        c.get("review_state") == "incomplete_extraction"
        for c in _COVERAGE_CLAIMS.values()
    )

    if has_incomplete or has_coverage_gap or has_incomplete_extraction:
        verdict_state = "revisão incompleta"
    elif has_blocking:
        verdict_state = "reprovado"
    elif has_disputed:
        verdict_state = "revisão incompleta"
    elif gaps or partials:
        verdict_state = "aceito com ressalvas"
    else:
        verdict_state = "aceito"

    accepted = not (has_blocking or has_incomplete or has_disputed
                    or has_coverage_gap or has_incomplete_extraction)

    return {
        "enabled": True,
        "claims": len(claims),
        "claims_reviewed": claims_reviewed,
        "verdicts": [{**c,
                      "verdict": by_id.get(c["id"], {}).get("verdict", "gap"),
                      "support": by_id.get(c["id"], {}).get("support", ""),
                      "correction": by_id.get(c["id"], {}).get("correction", ""),
                      "vote_tally": by_id.get(c["id"], {}).get("vote_tally", {}),
                      "valid_count": by_id.get(c["id"], {}).get("valid_count", 0),
                      "failure_count": by_id.get(c["id"], {}).get("failure_count", 0)}
                     for c in claims],
        "summary": {**summary,
                    "blocking": len(blocking),
                    "gaps": len(gaps),
                    "partials": len(partials),
                    "incomplete": len(incomplete_claims),
                    "disputed_ties": len(disputed_claims),
                    "technical_failures": len(failed_claims),
                    "missing_results": len(missing_claims),
                    "votes": max(1, votes),
                    "disputed": sum(
                        1 for v in verdicts if len(v.get("vote_tally", {})) > 1),
                    "coverage": coverage},
        "verdict_state": verdict_state,
        "accepted": accepted,
        "gaps": len(gaps),
        "partials": len(partials),
        "coverage": coverage,
    }


def build_evidence(context_text: str) -> dict[str, str]:
    """Map URL -> obtained text, from the context sent to the writer."""
    out: dict[str, str] = {}
    for part in re.split(r"(?=Source:\s*https?://)", context_text)[1:]:
        m = re.search(r"Source:\s*(\S+)", part)
        if m:
            out[m.group(1).rstrip(".,)")] = part
    return out
