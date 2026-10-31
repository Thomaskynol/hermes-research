#!/usr/bin/env python3
"""Four independent delivery verifications (modelagem §12), stdlib only.

Each dimension answers its own question and is never promoted by another:

    execution  were the ops executed and were failures recorded?
    question   were the mandatory targets/criteria investigated? (ledger)
    review     were selected claims extracted and reviewed, without silent
               omissions? (semantic audit coverage)
    support    does the real corpus sustain what the report says? (citations)

A semantic approval NEVER moves ``question`` to ok; a citation outside the
corpus NEVER counts as support. Unknown stays unknown, never 0.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

DIMENSIONS = ("execution", "question", "review", "support")
STATUSES = ("ok", "partial", "failed", "not_run")

#: PT/EN function words dropped from sentence/doc overlap (accent-insensitive).
_STOPWORDS = frozenset("""
a o e é de da do das dos que em um uma para por com não na no nas nos se ao
aos à às como mais mas foi são ser está estão também seu sua seus suas este
esta isso isto pelo pela entre sobre quando onde qual quais os as já não
the a an and or of to in on at for with is are was were be been being this
that these those it its as by from has have had not no but if then than so
such which who whom whose will would can could may might must should do does
did done there their they we our you your he she his her them us
""".split())


def _content_tokens(text) -> list[str]:
    """Lowercase, accent-stripped content words (PT/EN stopwords removed)."""
    import unicodedata as _ud
    norm = "".join(c for c in _ud.normalize("NFKD", str(text or "").lower())
                   if not _ud.combining(c))
    return [w for w in re.split(r"[^a-z0-9]+", norm)
            if len(w) >= 2 and w not in _STOPWORDS]


def _doc_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("usable_text") or value.get("text") or "")
    return ""


#: Minimal PT->EN product glossary for the support overlap (calibration
#: accept15). Only pairs where the EN term names the same product fact in
#: the corpus (license/version/install/plan/test/review/cost/...).
#: LIMITATION (lexical bridge only): the same word in another sense still
#: matches — e.g. "bun test" of the project's own development vs
#: user-facing tests. Sense disambiguation is out of scope on purpose.
_PT_EN_SUPPORT: dict[str, tuple[str, ...]] = {
    "planejamento": ("planning",),
    "implementacao": ("implementation",),
    "testes": ("test", "tests", "testing"),
    "teste": ("test", "tests"),
    "revisao": ("review",),
    "compatibilidade": ("compatibility", "compatible"),
    "compativel": ("compatible",),
    "versao": ("version",),
    "licenca": ("license",),
    "custo": ("cost",),
    "preco": ("price",),
    "gratuito": ("free",),
    "gratis": ("free",),
    "pago": ("paid",),
    "manutencao": ("maintenance",),
    "limitacao": ("limitation", "limitations"),
    "limitacoes": ("limitation", "limitations"),
    "campo": ("field",),
    "desconhecido": ("unknown",),
    "rejeita": ("rejects", "reject"),
    "rejeitar": ("reject",),
    "ignorar": ("ignore", "ignoring"),
    "ignora": ("ignore", "ignoring"),
    "instala": ("install",),
    "instalacao": ("install", "installation"),
    "instalar": ("install",),
    "exige": ("requires", "require"),
    "exigir": ("require",),
    "descoberta": ("discovery",),
    "convencao": ("convention",),
    "configuracao": ("configuration",),
    "componentes": ("components",),
    "comandos": ("commands",),
    "comando": ("command",),
    "remoto": ("remote",),
    "remotos": ("remote",),
    "agente": ("agent",),
    "agentes": ("agents",),
    "fluxos": ("workflows",),
    "desenvolvimento": ("development",),
    "leitura": ("reads", "read"),
    "tipos": ("types",),
    "injecao": ("inject",),
    "atualizacao": ("update",),
    "atualiza": ("update",),
    "suporte": ("support",),
    "documentado": ("documented",),
    "publicacao": ("publishing",),
    "confiavel": ("trusted",),
    "usa": ("uses", "use"),
    "plano": ("plan",),
}


def _expand_support_tokens(tokens: set[str]) -> set[str]:
    """Claim tokens plus EN equivalents (recall only, denominator kept)."""
    out = set(tokens)
    for tok in tokens:
        out.update(_PT_EN_SUPPORT.get(tok, ()))
    return out


#: Uncertainty language about a version: its absence from the doc is the
#: claim's content, not a mismatch ("compatibilidade com 2.1.4
#: desconhecida" must not fail for not containing "2.1.4").
_VERSION_UNCERTAIN = (
    "desconhec", "unknown", "nao informa", "não informa",
    "nao menciona", "não menciona", "sem mencao", "sem menção",
    "nao consta", "não consta", "sem evidencia", "sem evidência",
    "nao declara", "não declara", "ausente", "ausencia", "ausência",
    "nao ha", "não há", "nao cobre", "não cobre", "sem registro",
)


def _mentions_version_gap(sentence: str) -> bool:
    """True when the sentence declares the version unknown/absent."""
    import unicodedata as _ud
    norm = "".join(c for c in _ud.normalize(
        "NFKD", str(sentence or "").lower()) if not _ud.combining(c))
    return any(m in norm for m in _VERSION_UNCERTAIN)


#: Dotted releases (0.6.0, 2.1.4) and host generations (V1/V2/V3).
_VERSION_RE = re.compile(
    r"\b\d+\.\d+(?:\.\d+)?(?:[-+][a-z0-9.]+)?\b|\bV\d+\b",
    re.IGNORECASE)


def _text_versions(text: str) -> set[str]:
    """Normalized version tags in a sentence/doc (v/@ stripped, lowered)."""
    out = set()
    for raw in _VERSION_RE.findall(str(text or "")):
        norm = raw.lower().lstrip("v@")
        if norm:
            out.add(norm)
    return out


def _window_hash(text: str) -> str:
    """Hash curto do texto efetivamente auditado (mesmo formato do assessor).

    Reusa o formato de ``assess.last_selection`` (sha256[:16] do excerto):
    quando o state expõe ``hashes`` da seleção, eles são registrados
    lado a lado; aqui vai o hash do texto auditado (usable_text integral).
    """
    try:
        return hashlib.sha256((text or "").encode("utf-8",
                                                  "replace")).hexdigest()[:16]
    except Exception:
        return ""


def _audited_text_for(url: str, evidence, qualification) -> str:
    """Texto efetivamente auditado: usable_text qualificado, senão bruto."""
    try:
        qual = (qualification or {}).get(url) or {}
        if isinstance(qual, dict) and qual.get("usable_text"):
            return str(qual.get("usable_text") or "")
    except Exception:
        pass
    try:
        value = (evidence or {}).get(url)
    except Exception:
        value = None
    return _doc_text(value)


def _selection_window(state: dict) -> dict:
    """Seleção efetiva quando o state a expõe (last_selection.hashes).

    O assessor expõe ``assess.last_selection = {urls, hashes, ...}`` por
    chamada; o state persiste urls em ``assessments``/``report.selection``
    mas nem sempre os hashes. Reusa os hashes quando presentes, senão
    registra a fonte fallback (texto auditado) para a divergência
    excerto vs full-text ficar explícita, nunca silenciosa.
    """
    urls: list[str] = []
    hashes: dict[str, str] = {}
    hash_source = "texto-auditado (last_selection.hashes ausente no state)"
    try:
        for key in ("last_selection", "selection"):
            cand = (state or {}).get(key)
            if isinstance(cand, dict):
                if isinstance(cand.get("hashes"), dict):
                    for k, v in cand["hashes"].items():
                        if isinstance(k, str) and isinstance(v, str):
                            hashes[k] = v
                    hash_source = f"state[{key}].hashes"
                for u in cand.get("urls") or []:
                    if isinstance(u, str) and u not in urls:
                        urls.append(u)
        for rec in (state or {}).get("assessments") or []:
            if not isinstance(rec, dict):
                continue
            for u in rec.get("selection") or []:
                if isinstance(u, str) and u not in urls:
                    urls.append(u)
        rep_sel = ((state or {}).get("report") or {}).get("selection") or {}
        for u in rep_sel.get("included_urls") or []:
            if isinstance(u, str) and u not in urls:
                urls.append(u)
    except Exception:
        pass
    return {"urls": urls, "hashes": hashes, "hash_source": hash_source}


def _norm_mention(text) -> str:
    """Accent-insensitive, separator-normalized mention form."""
    import unicodedata as _ud
    norm = "".join(c for c in _ud.normalize(
        "NFKD", str(text or "").lower()) if not _ud.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", norm).strip()


def _entity_mentioned(label, eid, doc_text: str) -> bool:
    """The cell entity is named in the cited doc (label or id, full form).

    Token overlap ("opencode" + "agents" via "sub-agents") is not a
    mention: the normalized label/id itself must occur — or the doc
    must share at least two longer content tokens with the label (a doc
    about "OpenCode Plugin" is about the "OpenCode Eclipse Plugin"
    cell; a doc sharing only "opencode" is not). Short ids ("e1") are
    skipped, the label decides.
    """
    doc = _norm_mention(doc_text)
    if not doc:
        return False
    compact_doc = doc.replace(" ", "")
    for cand in (label, eid):
        ent = _norm_mention(cand)
        if len(ent) < 4:
            continue
        if ent in doc or ent.replace(" ", "") in compact_doc:
            return True
    try:
        label_toks = {w for w in _content_tokens(label) if len(w) >= 4}
        doc_toks = {w for w in _content_tokens(doc_text) if len(w) >= 4}
        if len(label_toks & doc_toks) >= 2:
            return True
    except Exception:
        pass
    return False


_TIGHTEN_CITE_RE = re.compile(r"\[(\d+)\]")


def _plan_entity_forms(plan) -> list[tuple[object, object, set[str]]]:
    """(label, entity_id, content tokens) per plan entity (generic)."""
    out = []
    for ent in (plan or {}).get("entities", []) or []:
        if not isinstance(ent, dict):
            continue
        toks = {t for t in _content_tokens(ent.get("label") or ent.get("id"))
                if len(t) >= 4}
        if toks:
            out.append((ent.get("label"), ent.get("id"), toks))
    return out


def _tighten_citations(markdown, n_to_url, evidence, plan
                       ) -> tuple[str, list[str]]:
    """Drop loose conjunctive citations, never masking real gaps.

    In a sentence naming plan entities, every cited number must resolve
    to a document mentioning at least one named entity. Numbers whose
    document lacks all named entities are removed — but only when at
    least one sustaining citation remains; otherwise the sentence is
    left untouched so the support audit still flags it (a removed
    citation would turn a flaggable claim into an invisible one).
    Sentences naming no entity, and unresolvable numbers, are untouched.
    Returns (tightened_markdown, notes).
    """
    try:
        from scripts import citation_audit as ca
    except ImportError:  # pragma: no cover
        import citation_audit as ca  # type: ignore
    norm_docs: dict[str, str] = {}
    if isinstance(evidence, dict):
        for url, value in evidence.items():
            if not isinstance(url, str):
                continue
            norm = ca.normalize_url(url)
            if norm:
                norm_docs[norm] = _doc_text(value)
    forms = _plan_entity_forms(plan)
    if not forms:
        return str(markdown or ""), []
    notes: list[str] = []
    out_lines = []
    for line in str(markdown or "").splitlines():
        cites = _TIGHTEN_CITE_RE.findall(line)
        if len(set(cites)) < 2:
            out_lines.append(line)
            continue
        sent_tokens = set(_content_tokens(line))
        named = [(label, eid) for label, eid, toks in forms
                 if sent_tokens & toks]
        if not named:
            out_lines.append(line)
            continue
        keep, drop, unknown = [], [], []
        for n in cites:
            url = (n_to_url or {}).get(int(n)) if str(n).isdigit() else None
            doc = ""
            if url is not None:
                try:
                    from scripts import citation_audit as _ca
                except ImportError:  # pragma: no cover
                    import citation_audit as _ca  # type: ignore
                doc = norm_docs.get(_ca.normalize_url(url) or "", "")
            if not url or not doc:
                unknown.append(n)
            elif any(_entity_mentioned(label, eid, doc)
                     for label, eid in named):
                keep.append(n)
            else:
                drop.append(n)
        if drop and (keep or unknown):
            for n in set(drop):
                line = re.sub(rf"\[{n}\]", "", line)
            line = re.sub(r"\s+([.,;:!?])", r"\1", line)
            line = re.sub(r" {2,}", " ", line).strip()
            notes.append("citação ajustada por entidade: "
                         f"removido(s) {sorted(set(drop))} "
                         f"mantido(s) {sorted(set(keep + unknown))} "
                         f"em: {line[:120]}")
        out_lines.append(line)
    return "\n".join(out_lines), notes


def _n_to_url(numbers) -> dict[int, str]:
    """Accept {url: n} (renderer) or {n: url} and return n -> url."""
    out: dict[int, str] = {}
    if not isinstance(numbers, dict):
        return out
    for key, value in numbers.items():
        if isinstance(value, int) and not isinstance(value, bool) \
                and isinstance(key, str):
            out[value] = key
        elif isinstance(key, int) and not isinstance(key, bool) \
                and isinstance(value, str):
            out[key] = value
        elif isinstance(key, str) and key.isdigit() and isinstance(value, str):
            out[int(key)] = value
    return out


def _sentence_supported(sentence_tokens: set[str], doc_text: str,
                        named_entities: list,
                        sentence_raw: str = "") -> tuple[bool, str]:
    """(supported, reason) for one sentence against one cited document.

    ``named_entities`` holds (tokens, label, entity_id) per plan entity.
    A version tag claimed by the sentence but absent from the doc never
    sustains (same "sem sobreposição" reason: audit consumers compare it
    for equality). A named cell entity must occur in its full form.
    """
    doc_tokens = set(_content_tokens(doc_text))
    if not sentence_tokens:
        return False, "sem sobreposição"
    # A claimed release/generation absent from the doc is not sustained,
    # however high the remaining overlap is — unless the sentence itself
    # declares the version unknown/absent (then absence is the content).
    if sentence_raw and not _text_versions(sentence_raw) <= _text_versions(
            doc_text):
        if _mentions_version_gap(sentence_raw):
            pass
        else:
            return False, "sem sobreposição"
    common = _expand_support_tokens(set(sentence_tokens)) & doc_tokens
    ratio = len(common) / len(sentence_tokens)
    title = set()
    for line in str(doc_text or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            title = set(_content_tokens(line[:160]))
            break
    rare = {w for w in common if len(w) >= 6 and w not in title}
    if ratio < 0.35 and len(rare) < 2:
        return False, "sem sobreposição"
    # The cell entity must be named in full ("opencode" + "agents" via
    # "sub-agents" is not a mention). A sentence can share a generic
    # token with several entities: at least one named entity in full
    # form sustains (per-cell audit: the cell's own entity).
    named = [(label, eid) for tokens, label, eid in named_entities
             if sentence_tokens & tokens]
    if named and not any(_entity_mentioned(label, eid, doc_text)
                         for label, eid in named):
        return False, "entidade não mencionada no doc"
    return True, ""


# Absence declarations ("no excerpt states X") are sustained by consultation,
# not by word overlap: the cited source was checked and says nothing either
# way. Bare "lacuna" is excluded: "a lacuna foi preenchida" is a positive
# claim and must pass the overlap check.
LACUNA_DECLARATION_MARKERS = (
    "nenhum excerto", "nao ha excerto", "não há excerto",
    "não afirma", "nao afirma", "não nega", "nao nega",
    "não consta", "nao consta", "sem evidência", "sem evidencia",
    "não cobre", "nao cobre", "não menciona", "nao menciona",
    "não foi encontrado", "nao foi encontrado",
    "sem menção", "sem mencao", "sem menções", "sem mencoes",
    "não há menção", "nao ha mencao",
    "lacuna permanece", "lacuna em aberto", "lacuna na documentação",
    "lacuna documental", "há uma lacuna", "existe uma lacuna",
)


# A leading explicit mark is a declaration, not prose: the writer
# convention labels absence/inference FIRST ("LACUNA: ...",
# "INFERÊNCIA/LACUNA ..."). Bare "lacuna" mid-sentence stays excluded
# ("a lacuna foi preenchida" is a positive claim and must pass the
# overlap check) — only the leading label counts as marked.
LEADING_DECLARATION_PREFIXES = ("lacuna", "inferencia", "inferência",
                                "inference", "inferred")


def _has_leading_declaration_mark(lowered: str) -> bool:
    stripped = str(lowered or "").lstrip("-–—*#> \t`\"'")
    for prefix in LEADING_DECLARATION_PREFIXES:
        if stripped.startswith(prefix):
            rest = stripped[len(prefix):len(prefix) + 1]
            if rest not in ("", ":", "/", " ", "-", "–", "—"):
                continue
            # Lacuna-leading mark ("LACUNA:", "INFERÊNCIA/LACUNA ..."):
            # explicit absence declaration, audited on the premise.
            # Bare leading "INFERÊNCIA:" keeps the factual-anchor path
            # (pure inference without anchor must still fail).
            head = stripped[:24]
            if "lacuna" in head:
                return True
    return False


def is_lacuna_declaration(sentence: str) -> bool:
    lowered = str(sentence or "").lower()
    if any(m in lowered for m in LACUNA_DECLARATION_MARKERS):
        return True
    # Leading explicit mark (writer convention): audited on the premise,
    # never on word overlap with the marked absence/inference.
    if _has_leading_declaration_mark(lowered):
        return True
    # Template do writer para célula insufficient: "sem <dimensão>
    # demonstrad[o/a]" (ex. accept15 "sem revisão demonstrada") — afirma
    # ausência de evidência, não fato positivo; genérico na dimensão.
    return re.search(r"sem\s+\w+\s+demonstrad[oa]\b", lowered) is not None


#: Quoted evidence strings in a LACUNA sentence (accept21): even an
#: absence declaration misattributes when it quotes a flag/version the
#: cited doc does not contain — resolvability alone is not premise.
#: Short labels/ids (``cand-x``, `c1`) are references, not excerpt
#: quotes, and stay exempt (M7 writer template preserved).
_QUOTED_LITERAL_RE = re.compile(r'"([^"]{3,})"|\'([^\']{3,})\'|`([^`]{3,})`')


def _quoted_literals(sentence: str) -> list[str]:
    """Quoted/backticked spans in the sentence (generic, no plugin names)."""
    out = []
    try:
        for m in _QUOTED_LITERAL_RE.finditer(str(sentence or "")):
            lit = m.group(1) or m.group(2) or m.group(3) or ""
            lit = lit.strip().strip("\"'`")
            if len(lit) >= 3:
                out.append(lit)
    except Exception:
        pass
    return out


def _is_evidence_literal(lit: str) -> bool:
    """Substantive excerpt quote vs short label/id reference."""
    s = (lit or "").strip()
    if len(s) < 4:
        return False
    # Code-like strings always count, even when short (flags with `_`).
    if any(c in s for c in "_./:=#"):
        return True
    return len(s) >= 8


# An explicitly marked inference ("INFERÊNCIA: ...") is audited on its
# factual anchor, not on the inference itself: strip the inference clause
# (text from the marker on) before the overlap check. A sentence that is
# pure inference with no anchor falls back to the full-text audit.
INFERENCE_MARKERS = ("inferência", "inferencia", "inference", "inferido")


def _factual_anchor(sentence: str) -> str:
    lowered = str(sentence or "").lower()
    cuts = [lowered.find(m) for m in INFERENCE_MARKERS]
    cuts = [c for c in cuts if c >= 0]
    if not cuts:
        return sentence
    anchor = sentence[:min(cuts)].strip(" -–—:;,.\"'`*")
    # The anchor must carry substance on its own: markdown debris ("-",
    # "**") is not substance, and neither is a vacuous conclusion prefix
    # ("Sobreposição provável"). Substance = an acronym/version tag, a
    # token with a digit, or at least three longer words. Without it the
    # facts come after the marker — audit the full sentence.
    region = sentence[:min(cuts)]
    has_acronym = bool(re.search(r"\b[A-Z][A-Z0-9]{1,4}\b", region))
    has_digit = bool(re.search(r"[0-9]", region))
    substance = [w for w in re.split(r"[^a-zà-ú]+", lowered[:min(cuts)])
                 if len(w) >= 4]
    if not (has_acronym or has_digit or len(substance) >= 3):
        return sentence
    return anchor if len(anchor.split()) >= 3 else sentence


def check_support(synthesis_text: str, numbers, corpus, plan,
                  selection=None) -> dict:
    """Sentence-level support audit of the synthesis (audit only, no rewrite).

    Each sentence with a ``[n]`` citation is mapped back to the cited URL
    via ``numbers`` (renderer order) and checked against the real corpus:
    supported when (a) >=35% of the sentence content words occur in the doc
    or >=2 rare words (len>=6, absent from the title) are shared, and (b)
    every plan entity named by the sentence is mentioned in the doc.
    Uncited sentences are counted (informative, never a failure).

    Granularity is per bullet/line (B2): multi-bullet blobs are split by
    line first, then by sentence within each line, so the version gate
    (``_text_versions``/``_mentions_version_gap``) and the lacuna
    exemption apply per bullet, exactly as the line-based diagnose.
    A "desconhecida" bullet never exempts a neighbouring concrete
    version claim (e.g. user-context facts) from its own check.
    """
    text = str(synthesis_text or "")
    n_to_url = _n_to_url(numbers)
    docs: dict[str, str] = {}
    if isinstance(corpus, dict):
        for url, value in corpus.items():
            if isinstance(url, str):
                docs[url] = _doc_text(value)
    elif isinstance(corpus, (list, tuple, set)):
        docs = {str(u): "" for u in corpus}
    norm_docs = {}
    try:
        from scripts import citation_audit as ca
    except ImportError:  # pragma: no cover
        ca = None  # type: ignore
    if ca is not None:
        for url in docs:
            norm = ca.normalize_url(url)
            if norm:
                norm_docs[norm] = url

    def _doc_for(url: str) -> str:
        if url in docs:
            return docs[url]
        if ca is not None:
            norm = ca.normalize_url(url)
            if norm and norm in norm_docs:
                return docs[norm_docs[norm]]
        return ""

    entities: list[tuple[set[str], object, object]] = []
    for ent in (plan or {}).get("entities", []) or []:
        if not isinstance(ent, dict):
            continue
        toks = {t for t in _content_tokens(ent.get("label") or ent.get("id"))
                if len(t) >= 4}
        if toks:
            entities.append((toks, ent.get("label"), ent.get("id")))

    claims = supported = uncited = 0
    declared: list[dict] = []
    unsupported: list[dict] = []
    # B2: unidades por bullet/linha, não por blob multi-bullet. O split
    # antigo (re.split sobre o texto inteiro) juntava bullets sem
    # pontuação terminal num único "sentence", diluindo a trava de
    # versão e a isenção de lacuna. Linha primeiro, frase depois: mesma
    # regra do diagnose (que audita por linha).
    _units: list[str] = []
    for _line in str(text).splitlines():
        _stripped = _line.strip()
        if not _stripped:
            continue
        for _raw in re.split(r"(?<=[.!?])\s+", _stripped):
            _s = _raw.strip()
            if _s:
                _units.append(_s)
    if not _units and text.strip():
        _units = [text.strip()]
    for sentence in _units:
        citations = [int(n) for n in re.findall(r"\[(\d+)\]", sentence)]
        if not citations:
            uncited += 1
            continue
        claims += 1
        # Named entities of this sentence (factual anchor for inference
        # markers): computed before the lacuna branch, which needs the
        # S2 premise check on the same set.
        factual = _factual_anchor(sentence)
        sent_tokens = set(_content_tokens(factual))
        named = [entry for entry in entities if sent_tokens & entry[0]]
        # Absence declaration over consulted sources: sustained by the
        # consultation itself (the cited doc was read and says nothing),
        # never by word overlap with an empty statement — but a quoted
        # literal/version the cited doc does not contain misattributes
        # the excerpt (accept21): resolvability alone is not premise.
        if is_lacuna_declaration(sentence):
            _cited_docs: list[str] = []
            _missing_nums: list[int] = []
            for _n in citations:
                _url = n_to_url.get(_n)
                _doc = _doc_for(_url) if _url else ""
                if not _url or not _doc:
                    _missing_nums.append(_n)
                else:
                    _cited_docs.append(_doc)
            if _missing_nums:
                unsupported.append({
                    "sentence": sentence, "citations": citations,
                    "reason": "citação fora do corpus: "
                              + ", ".join(f"[{n}]"
                                           for n in _missing_nums)})
                continue
            # S2 premise: an absence claim over consulted sources is
            # sustained by the consultation itself — but the cited source
            # must be about the named entity when the sentence names one.
            # Citing a foreign doc as absence premise is a loose citation,
            # not a verified premise.
            _premise_docs = sum(
                1 for _doc in _cited_docs
                if not named or any(
                    _entity_mentioned(label, eid, _doc)
                    for _toks, label, eid in named))
            if named and not _premise_docs:
                unsupported.append({"sentence": sentence,
                                    "citations": citations,
                                    "reason": "entidade não mencionada no "
                                              "doc"})
                continue
            # LACUNA+quote gate: a literal/version quoted as excerpt
            # content must occur in the cited doc, even in an absence
            # declaration. Version-gap language ("desconhecida", "sem
            # menção") keeps the exemption: absence is the content.
            _vers = _text_versions(sentence)
            if _vers and not _mentions_version_gap(sentence):
                _union_vers: set[str] = set()
                for _doc in _cited_docs:
                    _union_vers |= _text_versions(_doc)
                if not _vers <= _union_vers:
                    unsupported.append({
                        "sentence": sentence, "citations": citations,
                        "reason": "versão ausente no doc citado"})
                    continue
            _lits = [lit for lit in _quoted_literals(sentence)
                     if _is_evidence_literal(lit)]
            if _lits:
                _absent = [lit for lit in _lits
                           if not any(lit.lower() in (_doc or "").lower()
                                      for _doc in _cited_docs)]
                if _absent:
                    unsupported.append({
                        "sentence": sentence, "citations": citations,
                        "reason": "literal ausente no doc citado: "
                                  + ", ".join(_absent)[:160]})
                    continue
            supported += 1
            declared.append({"sentence": sentence, "citations": citations,
                             "premise_docs": _premise_docs})
            continue
        # Inference-marked claim: audit the factual anchor only.
        ok = False
        reasons: list[str] = []
        for n in citations:
            url = n_to_url.get(n)
            if not url:
                reasons.append("sem sobreposição")
                continue
            good, reason = _sentence_supported(
                sent_tokens, _doc_for(url), named, factual)
            if good:
                ok = True
                break
            reasons.append(reason)
        if ok:
            supported += 1
        else:
            reason = ("entidade não mencionada no doc"
                      if "entidade não mencionada no doc" in reasons
                      else "sem sobreposição")
            unsupported.append({"sentence": sentence,
                                "citations": citations,
                                "reason": reason})
    if claims == 0:
        status = "unknown"
    elif supported == 0:
        # No cited sentence is sustained: the synthesis is unsupported.
        status = "failed"
    elif supported / claims < 0.7:
        status = "partial"
    else:
        status = "ok"
    detail = (f"{supported}/{claims} frase(s) citada(s) sustentada(s); "
              f"{uncited} sem citação")
    if declared:
        detail += f"; {len(declared)} declaração(ões) de lacuna sustentada(s)"
    # B5: registra qual janela foi auditada (texto usable integral +
    # hashes no formato last_selection, com seleção quando exposta).
    try:
        _doc_hashes = {url: _window_hash(txt) for url, txt in docs.items()}
    except Exception:
        _doc_hashes = {}
    _audit_window: dict = {
        "mode": "usable_text integral (full-text); por bullet/linha",
        "granularity": "linha+frase (trava de versão por bullet)",
        "doc_hashes": _doc_hashes,
    }
    try:
        if isinstance(selection, dict):
            _sel_hashes = selection.get("hashes")
            if isinstance(_sel_hashes, dict) and _sel_hashes:
                _audit_window["selection_hashes"] = dict(_sel_hashes)
                _audit_window["hash_source"] = "arg selection.hashes"
    except Exception:
        pass
    return {"status": status, "claims": claims, "supported": supported,
            "uncited": uncited, "unsupported": unsupported, "detail": detail,
            "declared": declared, "audit_window": _audit_window}


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _result(dimension: str, status: str, evidence: dict,
            notes: list[str] | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"[VERIFY] unknown status {status!r}")
    return {"dimension": dimension, "status": status,
            "evidence": evidence, "notes": list(notes or [])}


def _count(values) -> dict:
    out: dict[str, int] = {}
    for value in values or ():
        key = value if isinstance(value, str) and value else "unknown"
        out[key] = out.get(key, 0) + 1
    return out


def verify_execution(state: dict) -> dict:
    """Ops attempted/concluded/failed by reason and channel, budget, stop."""
    ops = [o for o in (state.get("pending_ops") or []) if isinstance(o, dict)]
    attempted = len(ops)
    done = [o for o in ops if o.get("status") == "done"]
    failed = [o for o in ops if o.get("status") == "failed"]
    unresolved = [o for o in ops
                  if o.get("status") not in ("done", "failed")]
    by_reason = _count(o.get("outcome") for o in failed)
    by_channel = _count(o.get("channel") for o in ops)
    consumption = state.get("consumption") or {}
    evidence = {
        "ops_attempted": attempted,
        "ops_completed": len(done),
        "ops_failed": len(failed),
        "failures_by_reason": by_reason,
        "ops_by_channel": by_channel,
        "ops_unresolved": len(unresolved),
        "budget_used": consumption.get("budget_used", "unknown"),
        "queries": consumption.get("queries", "unknown"),
        "fetches": consumption.get("fetches", "unknown"),
        "stop": dict(state.get("stop") or {}),
    }
    notes = []
    if attempted == 0:
        return _result("execution", "not_run", evidence,
                       ["nenhuma operação registrada"])
    unknown_reason = [o.get("op_id") for o in failed if not o.get("outcome")]
    if unknown_reason:
        notes.append("falhas sem motivo registrado: "
                     f"{unknown_reason[:5]}")
    if unresolved:
        notes.append(f"{len(unresolved)} op(s) sem desfecho concluído")
    if len(done) == 0 and failed:
        return _result("execution", "failed", evidence,
                       notes + ["nenhuma operação concluída"])
    if unresolved or unknown_reason:
        return _result("execution", "partial", evidence, notes)
    if failed:
        notes.append(f"{len(failed)} falha(s) registradas por motivo")
    return _result("execution", "ok", evidence, notes)


def verify_question(state: dict, ledger=None) -> dict:
    """Per criterion/entity coverage; a pending required pair is never ok."""
    plan = state.get("plan")
    if not isinstance(plan, dict) or not plan.get("criteria"):
        return _result("question", "not_run",
                       {"plan": None, "required_pending": []},
                       ["sem plano de cobertura: pergunta não avaliada"])
    block = None
    if ledger is not None:
        try:
            block = ledger.compute()
        except Exception as exc:  # never favourable
            return _result("question", "failed", {"error": str(exc)},
                           ["ledger.compute falhou"])
    if not isinstance(block, dict):
        block = state.get("question_coverage") or {}
    required = [c for c in plan.get("criteria", [])
                if c.get("required", True)]
    by_id = {c.get("id"): c for c in block.get("criteria", []) or []}
    pending = []
    for crit in required:
        state_of = (by_id.get(crit.get("id")) or {}).get(
            "state", "uninvestigated")
        if state_of != "covered":
            pending.append({"criterion_id": crit.get("id"),
                            "state": state_of})
    evaluated = sum(1 for crit in required
                    if (by_id.get(crit.get("id")) or {}).get("state")
                    not in (None, "uninvestigated"))
    evidence = {
        "plan_id": plan.get("plan_id"),
        "required_total": len(required),
        "required_pending": pending,
        "proportion": block.get("proportion"),
        "complete": bool(block.get("complete")),
        "criteria_evaluated": evaluated,
        "gaps": [g.get("criterion_id") for g in block.get("gaps", []) or []],
    }
    notes = []
    if pending:
        notes.append(f"{len(pending)} critério(s) obrigatório(s) pendente(s)")
    if block.get("complete") and not pending:
        return _result("question", "ok", evidence, notes)
    if evaluated == 0:
        notes.append("nenhum critério obrigatório foi avaliado")
        return _result("question", "partial", evidence, notes)
    return _result("question", "partial", evidence, notes)


def verify_review(state: dict, audit: dict | None = None) -> dict:
    """Claims extracted/reviewed, votes, failures and batches (audit only)."""
    audit = audit if isinstance(audit, dict) else (state.get("semantic") or {})
    enabled = bool(audit.get("enabled"))
    claims = audit.get("claims")
    claims = int(claims) if isinstance(claims, int) else 0
    verdicts = audit.get("verdicts") or []
    reviewed = audit.get("claims_reviewed")
    if not isinstance(reviewed, int):
        reviewed = sum(1 for v in verdicts
                       if v.get("verdict") not in ("review_incomplete",
                                                   "missing_result"))
    summary = audit.get("summary") or {}
    coverage = audit.get("coverage") or summary.get("coverage") or {}
    counts = coverage.get("counts") or {}
    failures = summary.get("technical_failures")
    if not isinstance(failures, int):
        failures = sum(1 for v in verdicts
                       if v.get("verdict") in ("review_incomplete",
                                               "missing_result"))
    unsupported = [v.get("id") for v in verdicts
                   if v.get("verdict") == "unsupported"]
    evidence = {
        "enabled": enabled,
        "claims_extracted": claims,
        "claims_reviewed": reviewed,
        "claims_unreviewed": max(0, claims - reviewed),
        "verdict_state": audit.get("verdict_state", "não revisado"),
        "accepted": bool(audit.get("accepted")),
        "votes": summary.get("votes", "unknown"),
        "technical_failures": failures,
        "technical_failure_votes": summary.get("technical_failure_votes",
                                                "unknown"),
        "unsupported_claims": unsupported,
        "batches": {"blocks_total": counts.get("blocks_total"),
                    "blocks_processed": counts.get("blocks_processed"),
                    "blocks_incomplete": counts.get("blocks_incomplete")},
    }
    if not enabled:
        return _result("review", "not_run", evidence,
                       ["revisão semântica não executada/desativada"])
    if claims == 0:
        return _result("review", "partial", evidence,
                       ["nenhuma afirmação verificável extraída; "
                        "cobertura da revisão não comprovada"])
    notes = []
    if reviewed < claims:
        notes.append(f"{claims - reviewed} afirmação(ões) não revisada(s) "
                     "(omissão explícita, nunca silenciosa)")
    if failures:
        notes.append(f"{failures} falha(s) técnica(s) contabilizada(s); "
                     "falha não conta como voto favorável")
    if audit.get("verdict_state") == "reprovado":
        return _result("review", "failed", evidence,
                       notes + ["veredito semântico reprovado"])
    if reviewed == 0:
        return _result("review", "failed", evidence,
                       notes + ["nenhuma afirmação revisada"])
    if reviewed < claims or failures or not audit.get("accepted"):
        return _result("review", "partial", evidence, notes)
    return _result("review", "ok", evidence, notes)


def _corpus(state: dict) -> dict:
    """URLs that really sustain claims: obtained text, qualification allows."""
    evidence = state.get("evidence") or {}
    qualification = state.get("qualification") or {}
    corpus = {}
    for url, text in evidence.items():
        if not isinstance(text, str) or not text.strip():
            continue
        qual = qualification.get(url) or {}
        if qual.get("excluded"):
            continue
        if not (qual.get("usable_text") or text or "").strip():
            continue
        corpus[url] = qual
    return corpus


def verify_support(state: dict, report_text: str,
                   audit: dict | None = None) -> dict:
    """Every citation must resolve to real evidence; unknown never supports."""
    try:
        from scripts import citation_audit as ca
    except ImportError:  # pragma: no cover - scripts/ on sys.path
        import citation_audit as ca  # type: ignore
    corpus = _corpus(state)
    norm_corpus = {}
    for url in corpus:
        norm = ca.normalize_url(url)
        if norm:
            norm_corpus[norm] = url
    refs = ca.extract_references(report_text or "")
    resolved, unknown = [], []
    for ref in refs:
        norm = ca.normalize_url(ref.get("url"))
        if norm and norm in norm_corpus:
            resolved.append(norm)
        elif norm:
            unknown.append(norm)
    audit = audit if isinstance(audit, dict) else (state.get("semantic") or {})
    verdicts = audit.get("verdicts") or []
    unsupported = [v.get("id") for v in verdicts
                   if v.get("verdict") == "unsupported"]
    claims = audit.get("claims") if isinstance(audit.get("claims"), int) else 0
    reviewed = audit.get("claims_reviewed")
    if not isinstance(reviewed, int):
        reviewed = sum(1 for v in verdicts
                       if v.get("verdict") not in ("review_incomplete",
                                                   "missing_result"))
    evidence = {
        "citations": len(refs),
        "citations_resolved": len(set(resolved)),
        "citations_unknown": sorted(set(unknown)),
        "claims_extracted": claims,
        "claims_reviewed": reviewed,
        "claims_without_support_evidence": max(0, claims - reviewed),
        "unsupported_claims": unsupported,
        "corpus_size": len(corpus),
    }
    # Informational (never fails): cited in claim sections but outside
    # the writer-declared synthesis base. Both are observed events; a gap
    # here means findings reference material the writer did not list as
    # base. The §7 sources table is inventory (every corpus URL is listed
    # there by design), not a claim — its rows never count as beyond.
    try:
        used = set(((state.get("counters") or {}).get("documents") or {})
                   .get("used_in_synthesis") or [])
        _table_urls: set[str] = set()
        for _line in (report_text or "").splitlines():
            if _line.strip().startswith("|") and "http" in _line:
                for _m in re.finditer(r"https?://[^\s`)\]|]+", _line):
                    _n = ca.normalize_url(_m.group(0).rstrip(".,;:"))
                    if _n:
                        _table_urls.add(_n)
        beyond = sorted((set(resolved) - {ca.normalize_url(u) for u in used
                                           if ca.normalize_url(u)}
                         ) - _table_urls)
    except Exception:
        beyond = []
    evidence["cited_beyond_synthesis"] = beyond
    # B5: registra qual janela foi auditada (converge excerto vs full-text).
    # O texto auditado aqui é o usable_text integral; os hashes seguem o
    # formato last_selection (sha256[:16]) e a seleção efetiva é reusada
    # quando o state a expõe (assessments/report.selection/last_selection).
    try:
        _ev_all = state.get("evidence") or {}
        _qual_all = state.get("qualification") or {}
        _doc_hashes = {}
        for _u in list(corpus.keys()):
            try:
                _doc_hashes[_u] = _window_hash(
                    _audited_text_for(_u, _ev_all, _qual_all))
            except Exception:
                continue
        _sel_win = _selection_window(state)
        evidence["audit_window"] = {
            "mode": "usable_text integral (full-text)",
            "doc_hashes": _doc_hashes,
            "selection_urls": _sel_win.get("urls") or [],
            "selection_hashes": _sel_win.get("hashes") or {},
            "hash_source": _sel_win.get("hash_source") or "",
        }
    except Exception:
        pass
    notes = []
    # B5: pondera sentence_support quando a citação é do doc da entidade.
    # Sem reescrever auditores: roda o audit por frase (por bullet, B2) nas
    # linhas de afirmação (fora tabela/cabeçalho) com a mesma numeração
    # persistida do relatório; versão/entidade/literal ausente no doc e
    # citação fora do corpus ponderam (overlap genérico baixo nunca força
    # falha, para preservar a verificação existente).
    _sent_weighted = None
    try:
        _plan = state.get("plan") or {}
        _has_entities = bool((_plan.get("entities") or []))
        _rep_numbers = ((state.get("report") or {}).get("numbers") or {})
        if _has_entities and refs and _rep_numbers:
            _claim_lines: list[str] = []
            for _line in (report_text or "").splitlines():
                _s = _line.strip()
                if not _s:
                    continue
                if _s.startswith(("|", "#", ">", "```")):
                    continue
                _low = re.sub(r"^[\s*_`]+", "", _s)
                if re.match(r"(refer[êe]ncias?|fontes?)\s*:",
                            _low, re.I):
                    continue
                _claim_lines.append(_line)
            _claim_text = "\n".join(_claim_lines)
            if _claim_text and re.search(r"\[\d+\]", _claim_text):
                _corpus_check: dict[str, str] = {}
                for _u in list(corpus.keys()):
                    _corpus_check[_u] = _audited_text_for(
                        _u, state.get("evidence") or {},
                        state.get("qualification") or {})
                _sent = check_support(_claim_text, _rep_numbers,
                                      _corpus_check, _plan)
                _sent_weighted = {"claims": _sent.get("claims"),
                                  "supported": _sent.get("supported"),
                                  "status": _sent.get("status")}
                evidence["sentence_weighted"] = _sent_weighted
                _weighted_misses: list[dict] = []
                for _item in _sent.get("unsupported") or []:
                    if not isinstance(_item, dict):
                        continue
                    _sraw = str(_item.get("sentence") or "")
                    if _sraw.strip().startswith(
                            ("|", "#", ">", "```")):
                        continue
                    _reason = str(_item.get("reason") or "")
                    if _reason == "entidade não mencionada no doc":
                        _weighted_misses.append(_item)
                        continue
                    # LACUNA+quote/corpus: literal citado ausente no doc e
                    # citação fora do corpus ponderam como versão/entidade.
                    if _reason.startswith(("literal ausente no doc citado",
                                           "citação fora do corpus")):
                        _weighted_misses.append(_item)
                        continue
                    # Trava de versão por bullet: versão afirmada sem
                    # isenção de lacuna nunca é overlap genérico.
                    try:
                        if (_text_versions(_sraw)
                                and not _mentions_version_gap(_sraw)):
                            _weighted_misses.append(_item)
                    except Exception:
                        continue
                if _weighted_misses:
                    evidence["sentence_misses"] = [
                        {"sentence": str(m.get("sentence") or "")[:300],
                         "citations": m.get("citations"),
                         "reason": m.get("reason")}
                        for m in _weighted_misses[:8]]
                    notes.append(
                        "sentence_support pondera: "
                        f"{len(_weighted_misses)} afirmação(ões) com "
                        "versão/entidade/literal ausente no doc ou citação "
                        "fora do corpus "
                        f"(janela: {len(_doc_hashes)} doc(s) em "
                        "usable_text integral)")
    except Exception:
        pass
    if _sent_weighted is None:
        # Sem ponderação aplicável: mantém só a janela registrada.
        pass
    if beyond:
        notes.append("citação no relatório fora da base declarada de síntese "
                     f"({len(beyond)} no total): " + ", ".join(beyond))
    if unknown:
        notes.append("citação fora do corpus (não é fonte): "
                     + ", ".join(sorted(set(unknown))))
    if unsupported:
        notes.append(f"{len(unsupported)} afirmação(ões) sem suporte")
    if not refs:
        return _result("support", "not_run", evidence,
                       notes + ["relatório sem citações verificáveis"])
    if unknown or unsupported:
        return _result("support", "failed", evidence, notes)
    # Convergência B5: a sentença (full-text por bullet) pondera quando a
    # citação é do doc da entidade. Base aqui seria ok/partial (failed já
    # retornou); adota o pior sem reescrever os auditores.
    try:
        _has_weighted = bool(evidence.get("sentence_misses"))
    except Exception:
        _has_weighted = False
    if _has_weighted:
        try:
            _sent_status = (_sent_weighted or {}).get("status") or "partial"
        except Exception:
            _sent_status = "partial"
        if _sent_status == "failed":
            return _result("support", "failed", evidence, notes)
        return _result("support", "partial", evidence, notes)
    if not audit.get("enabled") or reviewed < claims:
        notes.append("citações resolvem no corpus, mas as afirmações não "
                     "foram integralmente revisadas")
        return _result("support", "partial", evidence, notes)
    return _result("support", "ok", evidence, notes)


def aggregate(dimensions: dict) -> str:
    """Overall status from the four independent dimensions (no promotion)."""
    statuses = [d.get("status") for d in (dimensions or {}).values()]
    if not statuses or all(s == "not_run" for s in statuses):
        return "not_run"
    if "failed" in statuses:
        return "failed"
    if all(s == "ok" for s in statuses):
        return "ok"
    return "partial"


def verify_all(state: dict, *, ledger=None, audit: dict | None = None,
               report_text: str | None = None) -> dict:
    """Aggregate the four independent dimensions (no cross-promotion)."""
    if report_text is None:
        report_text = ((state.get("report") or {}).get("markdown")
                       or (state.get("report") or {}).get("text") or "")
    dims = {
        "execution": verify_execution(state),
        "question": verify_question(state, ledger),
        "review": verify_review(state, audit),
        "support": verify_support(state, report_text, audit),
    }
    return {"run_id": state.get("run_id", ""),
            "generated_at": _utcnow(),
            "overall": aggregate(dims),
            "dimensions": dims,
            "note": ("dimensões independentes: aprovação semântica não "
                     "promove cobertura da pergunta")}


def write_verification(run_dir, verification: dict) -> Path:
    """Persist verification.json in the run directory."""
    path = Path(run_dir) / "verification.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verification, ensure_ascii=False, indent=1,
                               sort_keys=True), encoding="utf-8")
    return path
