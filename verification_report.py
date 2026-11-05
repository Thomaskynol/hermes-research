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
from functools import lru_cache
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
    "revisor": ("review", "reviewer"),
    "revisa": ("review",), "planos": ("plans", "plan"),
    "codigo": ("code",), "perguntas": ("questions",),
    "interativas": ("interactive",),
    "estruturar": ("structure", "structured"),
    "revisavel": ("reviewable",),
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
    "instalador": ("install", "installer"),
    "instalar": ("install",),
    "atualizar": ("update",),
    "anotacao": ("annotation", "annotate"),
    "auditoria": ("audit", "review"),
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
    # Paráfrase de escopo PT→EN (cognatos literais): sem ponte, limite
    # "apenas revisão visual de plano" nunca casa "Review the final plan
    # visually" no overlap lexical. Só cognatos indisputáveis.
    "visual": ("visual",),
    "detalhada": ("detailed",),
    "detalhado": ("detailed",),
    "equivalente": ("equivalent",),
    "profundidade": ("depth",),
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

_EXACT_VERSION_RE = re.compile(
    r"\b\d+\.\d+(?:\.\d+)?(?:[-+][a-z0-9.]+)?\b", re.IGNORECASE)
_FAMILY_VERSION_RE = re.compile(r"\bV\d+\b", re.IGNORECASE)


def _text_versions(text: str) -> set[str]:
    """Normalized version tags in a sentence/doc (v/@ stripped, lowered)."""
    out = set()
    for raw in _VERSION_RE.findall(str(text or "")):
        norm = raw.lower().lstrip("v@")
        if norm:
            out.add(norm)
    return out


def _text_exact_versions(text: str) -> set[str]:
    """Tag exata pontilhada (2.1.4): conclusao separada da familia."""
    out = set()
    for raw in _EXACT_VERSION_RE.findall(str(text or "")):
        norm = raw.lower().lstrip("v@")
        if norm:
            out.add(norm)
    return out


def _text_family_versions(text: str) -> set[str]:
    """Familia funcional (V2): conclusao separada da tag exata."""
    out = set()
    for raw in _FAMILY_VERSION_RE.findall(str(text or "")):
        norm = raw.lower().lstrip("v@")
        if norm:
            out.add(norm)
    return out


#: Proveniencia de fato do usuario: citavel como premissa explicita sem
#: numero de corpus, nunca LACUNA automatica.
_USER_CONTEXT_MARKERS = ("user://", "contexto informado pelo usuário",
                         "contexto informado pelo usuario",
                         "informado pelo usuário", "informado pelo usuario",
                         "user-provided", "versão instalada",
                         "versao instalada", "installed_opencode_version",
                         "premissa controlada", "premissa de contexto")


#: Comparação numérica contra mínimo declarado (Missão 3, versão-premissa):
#: "requer mínimo 1.0.0, instalada 2.1.4, atende ao mínimo" compara
#: numericamente (premissa + corpus) e não afirma tag ausente; sem esses
#: marcadores, menção de versão com linguagem funcional é afirmação
#: sobre a versão (gate de tag exata aplica).
_NUMERIC_COMPARISON_MARKERS = (
    "mínimo", "minimo", "minima", "mínima", "minimum",
    "atende", ">=", "igual ou superior", "superior a", "acima de",
)

#: Afirmação funcional/integração sobre a versão (Missão 3): sem fonte
#: que mencione a tag exata, é LACUNA (versão exata ausente no doc).
_FUNCTIONAL_VERSION_MARKERS = (
    "compat", "integr", "combin", "suport", "funcion",
)


def _is_numeric_comparison(sentence: str) -> bool:
    """True quando a frase compara numericamente contra mínimo declarado."""
    try:
        low = str(sentence or "").lower()
    except Exception:
        return False
    return any(m in low for m in _NUMERIC_COMPARISON_MARKERS)


def _claims_version_functionally(sentence: str) -> bool:
    """True quando a frase afirma compat/integração sobre a versão."""
    try:
        low = str(sentence or "").lower()
    except Exception:
        return False
    return any(m in low for m in _FUNCTIONAL_VERSION_MARKERS)


def _is_user_premise(sentence: str) -> bool:
    """Only a version premise/comparison, never an entire mixed assertion.

    A marker inside an inference's caveat does not change the origin of
    its functional premises. Those must follow the ordinary evidence gate.
    """
    try:
        low = str(sentence or "").lower()
    except Exception:
        return False
    if not any(m.lower() in low for m in _USER_CONTEXT_MARKERS):
        return False
    if _has_inference_marker(sentence):
        return False
    if not _text_exact_versions(sentence):
        return False
    if _is_numeric_comparison(sentence):
        return True
    return bool(re.match(r"^\s*[-*]?\s*(?:premissa[^:]*:\s*)?vers[aã]o\s+(?:instalada|informada)", low)
                and not _claims_version_functionally(sentence))


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


@lru_cache(maxsize=256)
def _norm_mention(text) -> str:
    """Accent-insensitive, separator-normalized mention form."""
    import unicodedata as _ud
    norm = "".join(c for c in _ud.normalize(
        "NFKD", str(text or "").lower()) if not _ud.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", norm).strip()


def _is_derived_eid(eid) -> bool:
    """IDs gerados pelo coordenador (e-*, e1, e_*) não são identidade.

    São chaves de célula (e-planner, e-pwf, e0), não nomes citáveis: só a
    forma cheia do label sustenta menção. Genérico, sem nomes.
    """
    try:
        s = str(eid or "").strip().lower()
    except Exception:
        return True
    if not s:
        return True
    import re as _re
    return bool(_re.match(r"^e([-_].*)?$", s) or _re.match(r"^e\d+$", s))


def _raw_glued(raw: str, idx: int, direction: int) -> bool:
    """True when raw[idx] glues a match to extra alphanumerics.

    Generic, no product literals: an adjacent alnum always glues; a
    compound joiner (``-``, ``_``, ``.``, ``/``) glues only when an
    alnum sits beyond it (``alpha-beta``, ``name.host``) — trailing
    punctuation (``BetaGadget.``) or spaced dashes stay boundaries.
    """
    try:
        if idx < 0 or idx >= len(raw):
            return False
        c = raw[idx]
    except Exception:
        return False
    try:
        if c.isalnum():
            return True
        if c in "-_./":
            try:
                return bool(raw[idx + direction].isalnum())
            except IndexError:
                return False
    except Exception:
        return False
    return False


def _raw_compound_ok(label, doc_text: str) -> bool:
    """True when the label occurs with compound-aware boundaries.

    Generic, no product literals: accent/case-insensitive, tokens joined
    by any separator, but the occurrence must not be glued to extra
    alphanumerics in the raw text — so a short label inside a longer
    hyphenated compound is not a mention of the short entity, while the
    full hyphen form still matches either separator variant and trailing
    punctuation keeps counting as a boundary.
    """
    import re as _re
    import unicodedata as _ud
    try:
        raw = "".join(c for c in _ud.normalize(
            "NFKD", str(doc_text or "").lower()) if not _ud.combining(c))
        lab = "".join(c for c in _ud.normalize(
            "NFKD", str(label or "").lower()) if not _ud.combining(c))
    except Exception:
        return True
    toks = [t for t in _re.split(r"[^a-z0-9]+", lab) if t]
    if not toks:
        return False
    try:
        core = r"[^a-z0-9]+".join(_re.escape(t) for t in toks)
        for _m in _re.finditer(core, raw):
            _s, _e = _m.start(), _m.end()
            if _raw_glued(raw, _s - 1, -1):
                continue
            if _raw_glued(raw, _e, 1):
                continue
            return True
        return False
    except Exception:
        return True


def _entity_mentioned(label, eid, doc_text: str) -> bool:
    """The cell entity is named in the cited doc (label or id, full form).

    Token overlap ("opencode" + "agents" via "sub-agents") is not a
    mention: the normalized label/id itself must occur with fronteira
    (forma cheia, não prefixo de palavra maior) — or the doc
    must share at least two longer content tokens with the label (a doc
    about "OpenCode Plugin" is about the "OpenCode Eclipse Plugin"
    cell; a doc sharing only "opencode" is not). Short ids ("e1") e
    derivados ("e-*") são ignorados, o label decide. A fronteira é
    hifen-consciente: o rótulo curto dentro de um composto hifenado
    ("alpha" em "alpha-beta") não é menção da entidade curta, mas a
    forma cheia casa insensível a separador ("alpha-beta" casa
    "alpha beta").
    """
    doc = _norm_mention(doc_text)
    if not doc:
        return False
    padded = f" {doc} "
    cands: list[tuple[str, bool]] = [(label, False)]
    try:
        if not _is_derived_eid(eid):
            cands.append((eid, True))
    except Exception:
        pass
    for cand, _is_eid in cands:
        ent = _norm_mention(cand)
        if len(ent) < 4:
            continue
        # fronteira: forma cheia com separador, não prefixo ("widget alpha"
        # não casa "widget alphabeta").
        try:
            import re as _re2
            if _re2.search(r"(^| )" + _re2.escape(ent) + r"($| )", doc):
                if _raw_compound_ok(cand, doc_text):
                    return True
                continue
        except Exception:
            if f" {ent} " in padded:
                try:
                    if _raw_compound_ok(cand, doc_text):
                        return True
                except Exception:
                    pass
                continue
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


#: Gate de polaridade do scope (accept42 item 1): marcadores PT de
#: negação/limite e de modalidade não-factual. Formas normalizadas
#: (minúsculas, sem acento, via _norm_mention); lista revisável.
#: Frase interop (≥2 entidades) com qualquer marcador tem teto
#: "partial declarada/LACUNA", nunca "integração testada". Afirmação
#: positiva legítima que cita teste ("integração testada documentada
#: em [7]") não contém marcador e segue integração testada.
_POLARITY_NEGATION_MARKERS = (
    "sem prova",
    "ausencia de",
    "nao ha",
    "permanece lacuna",
    "sem teste",
    "nao demonstra",
    "nao testada",
    "nao testado",
    "desconhecida",
)

_POLARITY_MODALITY_MARKERS = (
    "pode",
    "poderia",
    "inferida",
    "prudente",
    "plausivel",
)


def _has_polarity_ceiling(sentence: str) -> bool:
    """True quando a frase carrega negação/limite ou modalidade não-factual.

    Multi-palavra casa por substring normalizada; palavra isolada
    ("pode") exige fronteira para não vetar substring ("podemos" segue
    livre — só a forma isolada limita).
    """
    try:
        norm = _norm_mention(sentence)
    except Exception:
        return False
    if not norm:
        return False
    padded = f" {norm} "
    try:
        for marker in _POLARITY_NEGATION_MARKERS:
            if marker in norm:
                return True
        for marker in _POLARITY_MODALITY_MARKERS:
            if f" {marker} " in padded:
                return True
    except Exception:
        return False
    return False


#: Verbos de integração/teste (accept42 item 2): formas normalizadas
#: (minúsculas, sem acento, via _norm_mention); lista revisável.
#: A família do verbo integrar casa por igualdade de token (fronteira de
#: palavra): "integralmente"/"integridade"/"integral" NÃO casam.
_INTEROP_VERB_FAMILY = frozenset({
    "integra", "integrar", "integram", "integrou",
    "integrado", "integrada", "integracao",
})
_INTEROP_VERB_MARKERS = (
    "interoperabilidade testada",
    "teste de uso conjunto",
    "funciona com",
    "compativel testado",
)
#: Frase interop (≥2 entidades) sem verbo da família/lista e sem evidência
#: de execução no doc recebe "documentado (sem teste executado)", nunca
#: "integração testada" — mera menção ao host + plugin não fecha interop.

#: Evidência de execução no doc (accept42 item 2, endurecido accept43):
#: só formas frasais contam. Tokens isolados ("funciona", "tested",
#: "working") casavam boilerplate do doc (chrome Discourse, texto sobre
#: outro plugin) e forjavam "execução" para a integração citada — por isso
#: saíram da lista. Formas normalizadas; lista revisável.
_INTEROP_EXECUTION_MARKERS = (
    "teste executado",
    "test executed",
    "test passed",
)


def _has_interop_verb(sentence: str) -> bool:
    """True quando a frase alega integração/teste com verbo da lista.

    Família exata por igualdade de token; frases por substring
    normalizada. "integralmente" nunca é verbo de integração.
    """
    try:
        norm = _norm_mention(sentence)
    except Exception:
        return False
    if not norm:
        return False
    try:
        toks = set(norm.split())
        if toks & _INTEROP_VERB_FAMILY:
            return True
        for marker in _INTEROP_VERB_MARKERS:
            if " " in marker and marker in norm:
                return True
    except Exception:
        return False
    return False


def _has_execution_evidence(doc_text: str) -> bool:
    """True quando o doc mostra execução (forma frasal explícita).

    Só frases ("teste executado", ...) — token isolado em doc de 50KB é
    boilerplate, não evidência da integração citada.
    """
    try:
        norm = _norm_mention(doc_text)
    except Exception:
        return False
    if not norm:
        return False
    try:
        for marker in _INTEROP_EXECUTION_MARKERS:
            if marker in norm:
                return True
    except Exception:
        return False
    return False


def _meets_test_standard(sentence: str, cited_docs) -> bool:
    """Verbo de integração/teste na frase OU execução em doc citado."""
    try:
        if _has_interop_verb(sentence):
            return True
        for doc in cited_docs or ():
            if doc and _has_execution_evidence(doc):
                return True
    except Exception:
        return False
    return False


def _is_plan_enumeration(sentence: str, strict_named) -> bool:
    """Enumeração de candidatos do plano: ≥3 entidades em forma estrita,
    sem verbo de integração/teste e sem marcador de inferência.

    Listagem, nunca canal declared_inference (genérico, sem literais de
    produto). Pares (2 entidades) sem verbo caem em "documentado
    (sem teste executado)"; só a enumeração sai do canal.
    """
    try:
        if len(strict_named or ()) < 3:
            return False
        if _has_inference_marker(sentence):
            return False
        return not _has_interop_verb(sentence)
    except Exception:
        return False


@lru_cache(maxsize=128)
def _support_doc_tokens(doc_text: str):
    # Repeated claims consult the same frozen full text. Immutable cached
    # tokens preserve content identity without re-normalizing megabytes.
    return frozenset(_content_tokens(doc_text))


def _sentence_supported(sentence_tokens: set[str], doc_text: str,
                        named_entities: list,
                        sentence_raw: str = "", identity_fn=None) -> tuple[bool, str]:
    """(supported, reason) for one sentence against one cited document.

    ``named_entities`` holds (tokens, label, entity_id) per plan entity.
    Gate separado: tag exata (2.1.4) vs familia funcional (V2), conclusoes
    separadas (razoes distintas, nunca o mesmo "sem sobreposição").
    A named cell entity must occur in its full form.
    """
    mention = identity_fn or _entity_mentioned
    if sentence_raw:
        clean = re.sub(r"\([^)]*(?:vers[aã]o instalada|installed.version)[^)]*\)",
                       lambda m: "" if any(k in m[0].lower() for k in _USER_CONTEXT_MARKERS) else m[0],
                       sentence_raw, flags=re.I)
        if clean != sentence_raw:
            sentence_raw = clean
            sentence_tokens = set(_content_tokens(clean))
    doc_tokens = _support_doc_tokens(doc_text)
    if not sentence_tokens:
        return False, "sem sobreposição"
    # Gate separado tag exata vs familia funcional: ausencia de cada uma
    # tem conclusao propria — a mesma frase nao decide no overlap generico.
    # Isencao de lacuna ("desconhecida") vale para ambas.
    if sentence_raw:
        _exact_sent = _text_exact_versions(sentence_raw)
        _family_sent = _text_family_versions(sentence_raw)
        if _exact_sent or _family_sent:
            if _mentions_version_gap(sentence_raw):
                pass
            else:
                _exact_doc = _text_exact_versions(doc_text)
                _family_doc = _text_family_versions(doc_text)
                if _exact_sent and not _exact_sent <= _exact_doc:
                    return False, "versão exata ausente no doc"
                if _family_sent and not _family_sent <= _family_doc:
                    return False, "família funcional ausente no doc"
    common = _expand_support_tokens(set(sentence_tokens)) & doc_tokens
    ratio = len(common) / len(sentence_tokens)
    title = set()
    for line in str(doc_text or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            title = set(_content_tokens(line[:160]))
            break
    rare = {w for w in common if len(w) >= 6 and w not in title}
    # A entidade citada deve ocorrer na forma cheia: atribuição errada
    # (doc sobre outra entidade) é "entidade não mencionada", nunca
    # "sem sobreposição" genérico — identidade antes de overlap.
    named = [(label, eid) for tokens, label, eid in named_entities
             if sentence_tokens & tokens]
    try:
        if sentence_raw:
            _strict_named = [(label, eid)
                             for tokens, label, eid in named_entities
                             if _entity_mentioned(label, eid, sentence_raw)]
            if _strict_named:
                named = _strict_named
    except Exception:
        pass
    # Gate de polaridade (accept42 item 1): frase interop (nomeia >=2)
    # com negação/limite ou modalidade não-factual nunca sustenta
    # "integração testada" — o emissor dá teto partial/LACUNA.
    try:
        if (sentence_raw and len(named) >= 2
                and _has_polarity_ceiling(sentence_raw)):
            return False, ("teto polaridade: afirmação com negação/limite "
                           "ou modalidade não-factual (partial "
                           "declarada/LACUNA, nunca integração testada)")
    except Exception:
        pass
    if named and not any(mention(label, eid, doc_text)
                         for label, eid in named):
        return False, "entidade não mencionada no doc"
    if ratio < 0.35 and len(rare) < 2:
        return False, "sem sobreposição"
    # The cell entity must be named in full ("opencode" + "agents" via
    # "sub-agents" is not a mention). A sentence can share a generic
    # token with several entities: at least one named entity in full
    # form sustains (per-cell audit: the cell's own entity).
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
    # Molde "LACUNA nos excertos ... não estabelece/sem trecho/sem fonte":
    # ausência sobre fontes consultadas, auditada na premissa (S2), nunca
    # no overlap com a declaração vazia. Exige "lacuna" junto de
    # "excertos" para não sequestrar inferência que só delimita janela.
    "lacuna nos excertos", "lacuna no excerto",
)


#: Moldes nus de janela ("sem fonte/trecho", "não estabelece"): sozinhos
#: desviam prosa positiva p/ declared — só valem com coocorrência de
#: "lacuna"/"excertos" ou marca líder (condição do gate reviewer).
_LACUNA_BARE_WINDOW = (
    "sem fonte", "sem trecho",
    "não estabelece", "nao estabelece",
)


#: Divisor de orações p/ escopo de molde (itens 2 e 5): molde e alcance
#: precisam da mesma oração; versão isenta precisa da oração de
#: comparação numérica junto ao marcador. Sem quebrar "2.1.4" (ponto
#: nunca separa).
_CLAUSE_SPLIT_RE = re.compile(
    r"[;!?\n]+|,\s*(?:e|ou|mas|porém|contudo|todavia|entretanto|porque|pois|"
    r"enquanto|ao passo que)\s+", re.IGNORECASE)


def _clauses_of(lowered: str) -> list[str]:
    """Orações do texto já em minúsculas (spans preservados p/ versões)."""
    try:
        return [c.strip() for c in _CLAUSE_SPLIT_RE.split(str(lowered or ""))
                if c.strip()]
    except Exception:
        return [str(lowered or "")]


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
    # Moldes nus só com coocorrência na MESMA oração (lacuna/excertos):
    # sem ela, "X declara Y sem fonte" é prosa positiva e segue o caminho
    # normal — alcance em frase inteira desviava incidental.
    for _c in _clauses_of(lowered):
        if any(m in _c for m in _LACUNA_BARE_WINDOW) \
                and ("lacuna" in _c or "excerto" in _c or "excerpt" in _c):
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
_QUOTED_LITERAL_RE = re.compile(
    r'"([^"]{3,})"|\'([^\']{3,})\'|`([^`]{3,})`|'
    r'“([^”]{3,})”|‘([^’]{3,})’')


def _quoted_literals(sentence: str) -> list[str]:
    """Quoted/backticked spans in the sentence (generic, no plugin names)."""
    out = []
    try:
        for m in _QUOTED_LITERAL_RE.finditer(str(sentence or "")):
            lit = next((g for g in m.groups() if g), "") or ""
            lit = lit.strip().strip("\"'`“”‘’")
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


# Inferencia por premissas: ancora E relacao auditadas separadamente.
# INFERENCIA vira declared-inference (nunca supported por ancora); exige
# citacao de interoperabilidade para supported, senao LACUNA explicita.
# Complementaridade plausivel (ancora ok, relacao sem prova) != integracao
# testada (relacao com citacao de interoperabilidade).
INFERENCE_MARKERS = ("inferência", "inferencia", "inference", "inferido")


def _has_inference_marker(sentence: str) -> bool:
    try:
        low = str(sentence or "").lower()
    except Exception:
        return False
    return any(m in low for m in INFERENCE_MARKERS)


def _split_inference(sentence: str) -> tuple[str, str]:
    """(ancora, relacao) split no marcador de inferencia."""
    try:
        low = str(sentence or "").lower()
    except Exception:
        return str(sentence or ""), ""
    cuts = [low.find(m) for m in INFERENCE_MARKERS]
    cuts = [c for c in cuts if c >= 0]
    if not cuts:
        return str(sentence or ""), ""
    idx = min(cuts)
    anchor = str(sentence or "")[:idx].strip(" -–—:;,.\"'`*“”‘’")
    relation = str(sentence or "")[idx:].strip(" -–—:;,.\"'`*“”‘’")
    return anchor or str(sentence or ""), relation or ""


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


def _window_scope_for(sentence: str) -> str:
    """Escopo da lacuna: janela (excertos avaliados) vs global (corpus)."""
    try:
        low = str(sentence or "").lower()
    except Exception:
        return "janela (excertos avaliados)"
    if "excerto" in low or "excerpt" in low:
        return "janela (excertos avaliados)"
    if "corpus" in low:
        return "global (corpus integral)"
    # padrao: auditoria por bullet e na janela do writer
    return "janela (excertos avaliados)"


def _audit_inference(anchor: str, relation: str, doc_text: str,
                     named_anchor: list, named_relation: list, identity_fn=None) -> tuple[bool, bool, str, str]:
    """Audita ancora E relacao separadamente contra um doc.

    Retorna (anchor_ok, relation_ok, anchor_reason, relation_reason).
    Interoperabilidade: quando a frase nomeia >=2 entidades, a relacao
    so e sustentada pelo doc que menciona >=2 delas (integracao testada);
    doc de entidade unica e complementaridade plausivel, nunca prova.
    """
    # Sem âncora de entidade (nem ancora nem relação nomeiam plano algum):
    # paráfrase sem forma cheia nunca sustenta relação — LACUNA explícita,
    # nunca supported/integração testada, em qualquer espelho que use este
    # auditor.
    mention = identity_fn or _entity_mentioned
    try:
        _capped = bool(_has_polarity_ceiling(relation)
                       or _has_polarity_ceiling(anchor))
    except Exception:
        _capped = False
    if not named_anchor and not named_relation:
        return False, False, "sem âncora de entidade", \
            ("inferência sem âncora de entidade (sem citação de "
             "interoperabilidade: LACUNA, nunca integração testada)")
    anchor_tokens = set(_content_tokens(anchor)) if anchor else set()
    relation_tokens = set(_content_tokens(relation)) if relation else set()
    if not anchor_tokens:
        anchor_ok, anchor_reason = False, "sem sobreposição"
    else:
        anchor_ok, anchor_reason = _sentence_supported(
            anchor_tokens, doc_text, named_anchor, anchor, identity_fn=identity_fn)
    if not relation_tokens:
        relation_ok, relation_reason = False, "sem sobreposição"
    else:
        # exige mencao das entidades da relacao no mesmo doc
        if named_relation:
            _mentioned = sum(
                1 for _toks, label, eid in named_relation
                if mention(label, eid, doc_text))
            if len(named_relation) >= 2 and _mentioned < 2:
                return anchor_ok, False, anchor_reason, \
                    "inferência sem citação de interoperabilidade " \
                    "(complementaridade plausível, não integração testada)"
        relation_ok, relation_reason = _sentence_supported(
            relation_tokens, doc_text, named_relation, relation, identity_fn=identity_fn)
        if not relation_ok and "não mencionada" in relation_reason:
            relation_reason = (
                "inferência sem citação de interoperabilidade "
                "(complementaridade plausível, não integração testada)")
        elif not relation_ok:
            # ancora pode passar no overlap, mas a relacao (combinacao)
            # exige prova de integracao, nao so plausibilidade
            relation_reason = (
                "inferência sem citação de interoperabilidade "
                "(complementaridade plausível, não integração testada)")
    # Gate de polaridade (accept42 item 1): negação/limite ou modalidade
    # não-factual na âncora/relação nunca vira integração testada.
    if _capped and relation_ok:
        relation_ok = False
        relation_reason = ("teto polaridade: afirmação com negação/limite "
                           "ou modalidade não-factual (partial "
                           "declarada/LACUNA, nunca integração testada)")
    return anchor_ok, relation_ok, anchor_reason, relation_reason


def strict_named_in_sentence(sentence, entities):
    """Entities named by full label or unambiguous base (comparison scan).

    Generic, no product literals: a candidate counts as named only by its
    full form in the sentence, or by its base (label without parenthesis)
    when that base is unique in the given entity set. Loose token overlap
    ('opencode'/'code review' as common words) never names anyone. Same
    rule family as the check_support comparison scan; `entities` is a
    plan entity list (dicts with label/id). Returns [(label, id)].
    """
    labs: list[tuple] = []
    for e in (entities or []):
        if not isinstance(e, dict):
            continue
        lb = str(e.get("label") or e.get("id") or "")
        if lb:
            labs.append((lb, e.get("id")))
    alias_counts: dict[str, int] = {}
    for lb, _ in labs:
        base = _norm_mention(re.sub(r"\([^)]*\)", "", lb))
        if base:
            alias_counts[base] = alias_counts.get(base, 0) + 1
    comp = _norm_mention(sentence)
    out: list[tuple] = []
    for lb, eid in labs:
        full = _norm_mention(lb)
        base = _norm_mention(re.sub(r"\([^)]*\)", "", lb))
        forms = [full] + ([base] if alias_counts.get(base) == 1 else [])
        if any(f and re.search(r"(?:^| )" + re.escape(f) + r"(?:$| )", comp)
               for f in forms):
            out.append((lb, eid))
    return out


# Rótulo único das inferências (complementaridade/sobreposição inferida):
# relação sem prova nunca "documentada" nem "integração testada"; âncoras
# sustentadas contam partial declarada com limites explícitos.
PARTIAL_DECLARED_SCOPE = ("partial declarada (complementaridade/sobreposição "
                          "inferida a partir de premissas em fontes distintas; "
                          "LACUNA explícita sem prova de integração; limites: "
                          "janela auditada; nunca integração testada)")


def doc_covers_entity(label, eid, url, evidence, plan):
    """A cited doc is a premise for the named entity (generic).

    Same link rule as the verifier's missing-entity check: the doc whose
    own repository/identity matches covers its entity; a foreign
    repository doc never borrows another entity's premise; otherwise the
    entity must be named in the body. Used by renderer lists and by the
    excerpt rescope so every surface maps each entity to the source
    that sustains it.
    """
    try:
        from entity_identity import source_identity as _sid
    except Exception:
        _sid = None
    try:
        body = (evidence or {}).get(url) or ""
        if not body:
            return False
        ent = next((e for e in ((plan or {}).get("entities") or [])
                    if isinstance(e, dict) and e.get("id") == eid), {})
        if _sid is not None:
            try:
                proven = _sid(ent, body, url)
            except Exception:
                proven = None
            if proven is True:
                return True
            if proven is False:
                return False
        return bool(_entity_mentioned(label, eid, body))
    except Exception:
        return False


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
    class SourcedText(str):
        def __new__(cls, body, url):
            obj = super().__new__(cls, body)
            obj.source_url = url
            return obj
    if isinstance(corpus, dict):
        for url, value in corpus.items():
            if isinstance(url, str):
                docs[url] = SourcedText(_doc_text(value), url)
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
    from entity_identity import context_entity_ids, repo_key
    contexts = context_entity_ids(plan)
    entity_map = {e.get("id"): e for e in (plan or {}).get("entities", []) if isinstance(e, dict)}
    original_mention = globals()["_entity_mentioned"]
    doc_urls = {body: url for url, body in docs.items() if body}

    def _entity_mentioned(label, eid, body):
        from entity_identity import source_identity
        url = getattr(body, "source_url", None) or doc_urls.get(body)
        if url and eid in entity_map:
            proven = source_identity(entity_map[eid], body, url)
            if proven is not None:
                return proven
        if not url and eid in entity_map and repo_key(entity_map[eid].get("source_url")):
            base = re.sub(r"\([^)]*\)", "", str(label or "")).strip()
            if base != label and original_mention(base, eid, body):
                return True
        return original_mention(label, eid, body)

    for ent in (plan or {}).get("entities", []) or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("id") in contexts:
            continue
        toks = {t for t in _content_tokens(ent.get("label") or ent.get("id"))
                if len(t) >= 4}
        if toks:
            entities.append((toks, ent.get("label"), ent.get("id")))

    alias_counts = {}
    for _, label, eid in entities:
        alias = _norm_mention(re.sub(r"\([^)]*\)", "", str(label or "")))
        if alias:
            alias_counts[alias] = alias_counts.get(alias, 0) + 1

    def _strict_doc(label, eid, doc):
        """Premissa estrita: mesma regra do lado da frase (forma cheia ou
        base inequívoca com fronteira) ou link de identidade própria.
        Doc identifiavelmente de outro dono no plano nunca é premissa,
        mesmo partilhando 2 tokens. Posse indecidida mantém o contrato S2
        (menção frouxa vale quando nada contradiz a titularidade); repo
        próprio compartilhado (monorepo) vale menção frouxa do próprio doc.
        """
        try:
            url = getattr(doc, "source_url", None) or doc_urls.get(doc)
            cur = repo_key(url) if url else None
            _own = None
            if eid in entity_map and isinstance(entity_map[eid], dict):
                _own = repo_key(entity_map[eid].get("canonical_source_url")
                                or entity_map[eid].get("source_url"))
            _mono = bool(cur and _own and cur == _own)
            _mentioned = bool(_entity_mentioned(label, eid, doc))
            if not _mentioned and not _mono:
                return False
            if _mono and not _mentioned:
                return bool(original_mention(label, eid, doc))
            _dn = _norm_mention(doc)
            _full = _norm_mention(label)
            _base = _norm_mention(re.sub(r"\([^)]*\)", "", str(label or "")))
            _forms = [_full] + ([_base] if _base and alias_counts.get(_base) == 1 else [])
            for _f in _forms:
                if _f and re.search(r"(?:^| )" + re.escape(_f) + r"(?:$| )", _dn) \
                        and _raw_compound_ok(_f, doc):
                    return True
            if eid in entity_map:
                from entity_identity import source_identity
                if url and source_identity(entity_map[eid], doc, url) is True:
                    return True
                # Dono estrangeiro decidível: repo do doc é de outra
                # entidade do plano — nunca premissa desta. Irmãos de
                # monorepo (cur == repo do requerente) pulam o veto.
                if cur and cur != _own:
                    for _oid, _oent in entity_map.items():
                        if _oid == eid or not isinstance(_oent, dict):
                            continue
                        _okey = repo_key((_oent or {}).get("canonical_source_url")
                                         or (_oent or {}).get("source_url"))
                        if _okey and _okey == cur:
                            return False
            return True
        except Exception:
            pass
        return False

    def _vetoed_mention(label, eid, doc):
        """Porta positiva: menção verificada menos doc de outro dono.

        Cognatos/overlap decidem conteúdo; titularidade decide atribuição:
        doc cujo repo é de outra entidade do plano nunca sustenta afirmação
        sobre esta (vale p/ o ramo positivo; inferência tem canal próprio).
        Repo próprio compartilhado (monorepo) vale menção frouxa.
        """
        try:
            url = getattr(doc, "source_url", None) or doc_urls.get(doc)
            cur = repo_key(url) if url else None
            _own = None
            if eid in entity_map and isinstance(entity_map[eid], dict):
                _own = repo_key(entity_map[eid].get("canonical_source_url")
                                or entity_map[eid].get("source_url"))
            _mono = bool(cur and _own and cur == _own)
            _mentioned = bool(_entity_mentioned(label, eid, doc))
            if not _mentioned and not _mono:
                return False
            if _mono and not _mentioned:
                return bool(original_mention(label, eid, doc))
            if cur and cur != _own:
                for _oid, _oent in entity_map.items():
                    if _oid == eid or not isinstance(_oent, dict):
                        continue
                    _okey = repo_key((_oent or {}).get("canonical_source_url")
                                     or (_oent or {}).get("source_url"))
                    if _okey and _okey == cur:
                        return False
        except Exception:
            pass
        return True

    claims = supported = uncited = 0
    declared: list[dict] = []
    declared_inference: list[dict] = []
    partial_declared: list[dict] = []
    user_premises: list[dict] = []
    unsupported: list[dict] = []
    missing_entity_sources: list[dict] = []
    inferred_comparisons: list[dict] = []
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
        # Atribuição estrita (v2-3): token compartilhado ("widget") nomeia
        # ambas no overlap frouxo; a entidade nomeada de fato é a de forma
        # cheia na frase. Quando há menção estrita, ela decide quem a frase
        # atribui (evita Beta espúrio via "widget" mascarando erro de
        # atribuição para Alpha).
        try:
            _factual_norm = _norm_mention(factual)
            _strict = []
            for entry in entities:
                _toks, _label, _eid = entry
                _full = _norm_mention(_label)
                _base = _norm_mention(re.sub(r"\([^)]*\)", "", str(_label or "")))
                _forms = [_full] + ([_base] if _base and alias_counts.get(_base) == 1 else [])
                _hit = next((_form for _form in _forms
                             if _form and re.search(r"(?:^| )" + re.escape(_form) + r"(?:$| )",
                                                    _factual_norm)), None)
                # Fronteira composta vale para a forma que casou (cheia ou
                # base inequívoca): decoração ausente na prosa não veta a
                # base, mas "Widget Alpha" em "Widget Alphabeta" segue fora.
                if _hit and _raw_compound_ok(_hit, factual):
                    _strict.append(entry)
            if _strict:
                named = _strict
        except Exception:
            pass
        named_selected = []
        missing_named = []
        comparison = _norm_mention(sentence)
        if _has_inference_marker(sentence) or any(w in comparison for w in
                ("sobrepos", "overlap", "combin", "complement", "integra")):
            for entry in entities:
                _, label, eid = entry
                if not (entity_map.get(eid) or {}).get("required", True):
                    continue
                full = _norm_mention(label)
                base = _norm_mention(re.sub(r"\([^)]*\)", "", str(label or "")))
                forms = [full] + ([base] if alias_counts.get(base) == 1 else [])
                if any(form and re.search(r"(?:^| )" + re.escape(form) + r"(?:$| )", comparison)
                       for form in forms):
                    named_selected.append(entry)
            if len(named_selected) >= 2:
                for entry in named_selected:
                    if not any((url := n_to_url.get(n)) and (doc := _doc_for(url))
                               and _entity_mentioned(entry[1], entry[2], doc) for n in citations):
                        missing_named.append(str(entry[1]))
            if missing_named:
                missing_entity_sources.append({"sentence": sentence, "citations": citations,
                                               "missing_entities": missing_named})
            if (len(named_selected) >= 2 and not _has_inference_marker(sentence)
                    and any(w in comparison for w in ("sobrepos", "overlap", "combin", "complement"))
                    and not any((url := n_to_url.get(n)) and (doc := _doc_for(url))
                                and all(_entity_mentioned(e[1], e[2], doc) for e in named_selected)
                                for n in citations)):
                inferred_comparisons.append({"sentence": sentence, "citations": citations})
            if _has_inference_marker(sentence) and len(named_selected) == 2:
                _strict = named_selected
        # Fato do usuario como premissa explicita (sem numero de corpus,
        # nunca LACUNA automatica): isenta o gate de versao da versao
        # vinda do contexto e audita a premissa da entidade.
        if _is_user_premise(sentence) and not is_lacuna_declaration(sentence):
            _cited_docs_u: list[str] = []
            _missing_u: list[int] = []
            for _n in citations:
                _url = n_to_url.get(_n)
                _doc = _doc_for(_url) if _url else ""
                if not _url or not _doc:
                    _missing_u.append(_n)
                else:
                    _cited_docs_u.append(_doc)
            if _missing_u:
                unsupported.append({
                    "sentence": sentence, "citations": citations,
                    "reason": "citação fora do corpus: "
                              + ", ".join(f"[{n}]" for n in _missing_u)})
                continue
            _prem_u = sum(
                1 for _doc in _cited_docs_u
                if not named or any(
                    _entity_mentioned(label, eid, _doc)
                    for _toks, label, eid in named))
            if named and not _prem_u:
                unsupported.append({"sentence": sentence,
                                    "citations": citations,
                                    "reason": "entidade não mencionada no "
                                              "doc"})
                continue
            # premissa explicita do usuario + doc da entidade: sustentada
            # sem exigir a tag exata do contexto no doc, exceto na
            # regra estreita versão-premissa (Missão 3): comparação
            # numérica contra mínimo declarado = sustentada
            # (premissa + corpus); compat funcional/integração sem fonte
            # que mencione a tag exata = LACUNA. Só claim numérico
            # exige a tag exata do contexto no doc.
            _exact_s = _text_exact_versions(sentence)
            if (_exact_s and not _is_numeric_comparison(sentence)
                    and _claims_version_functionally(sentence)):
                _exact_u: set[str] = set()
                for _doc in _cited_docs_u:
                    _exact_u |= _text_exact_versions(_doc)
                if not _exact_s <= _exact_u:
                    unsupported.append({
                        "sentence": sentence, "citations": citations,
                        "reason": "versão exata ausente no doc"})
                    continue
            supported += 1
            user_premises.append({"sentence": sentence,
                                  "citations": citations,
                                  "premise_docs": _prem_u,
                                  "scope": "premissa explícita do usuário "
                                           "(sem número de corpus)"})
            declared.append({"sentence": sentence, "citations": citations,
                             "premise_docs": _prem_u,
                             "scope": "premissa explícita do usuário "
                                      "(sem número de corpus)"})
            continue
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
                    _strict_doc(label, eid, _doc)
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
            # Gate separado tag exata vs familia funcional.
            _exact_s = _text_exact_versions(sentence)
            _fam_s = _text_family_versions(sentence)
            if (_exact_s or _fam_s) and not _mentions_version_gap(sentence):
                _exact_u: set[str] = set()
                _fam_u: set[str] = set()
                for _doc in _cited_docs:
                    _exact_u |= _text_exact_versions(_doc)
                    _fam_u |= _text_family_versions(_doc)
                if _exact_s and not _exact_s <= _exact_u:
                    # Premissa numérica isenta só a tag adjacente ao marcador
                    # (≤40 chars, mesma oração/cláusula): versão exata com
                    # ocorrência a ≤40 chars do marcador de premissa
                    # controlada/informada, em oração com comparação numérica,
                    # não é exigida no doc; demais tags precisam estar
                    # corroboradas no citado. Sem isenções por
                    # INFERÊNCIA/LACUNA/negação (só _USER_CONTEXT_MARKERS).
                    _premise_ok = False
                    if _is_numeric_comparison(sentence):
                        try:
                            _low = str(sentence or "").lower()
                            _bounds = [0] + [m.end() for m in
                                             _CLAUSE_SPLIT_RE.finditer(_low)] \
                                + [len(_low)]
                            # posições dos marcadores de premissa no texto
                            _mark_pos = []
                            for _k in _USER_CONTEXT_MARKERS:
                                _kl = _k.lower()
                                _from = 0
                                while True:
                                    _fi = _low.find(_kl, _from)
                                    if _fi < 0:
                                        break
                                    _mark_pos.append((_fi, _fi + len(_kl)))
                                    _from = _fi + 1
                            _marked = set()
                            for _m in _EXACT_VERSION_RE.finditer(str(sentence or "")):
                                _v = _m.group(0).lower().lstrip("v@")
                                _cs = _m.start()
                                _ce = _m.end()
                                _ci = next((_i for _i in range(len(_bounds) - 1)
                                            if _bounds[_i] <= _cs < _bounds[_i + 1]),
                                           len(_bounds) - 2)
                                _span = _low[_bounds[_ci]:_bounds[_ci + 1]]
                                if not (any(k.lower() in _span for k in _USER_CONTEXT_MARKERS)
                                        and _is_numeric_comparison(_span)):
                                    continue
                                # shortcut: adjacência ao marcador ≤40 chars
                                # na mesma oração; qualquer ocorrência vale
                                # para o tipo (T2a multi-versão preservado).
                                _near = False
                                for (_ms, _me) in _mark_pos:
                                    if not (_bounds[_ci] <= _ms < _bounds[_ci + 1]):
                                        continue
                                    _d = 0 if (_cs < _me and _ms < _ce) \
                                        else ((_cs - _me) if _cs >= _me else (_ms - _ce))
                                    if _d <= 40:
                                        _near = True
                                        break
                                if _near:
                                    _marked.add(_v)
                            _premise_ok = bool(_marked) and (_exact_s - _marked) <= _exact_u
                        except Exception:
                            _premise_ok = False
                    if not _premise_ok:
                        unsupported.append({
                            "sentence": sentence, "citations": citations,
                            "reason": "versão exata ausente no doc citado"})
                        continue
                if _fam_s and not _fam_s <= _fam_u:
                    unsupported.append({
                        "sentence": sentence, "citations": citations,
                        "reason": "família funcional ausente no doc citado"})
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
                             "premise_docs": _premise_docs,
                             "scope": _window_scope_for(sentence)})
            continue
        # Inferencia marcada: audita ancora E relacao separadamente.
        # INFERENCIA vira declared-inference (nunca supported por ancora);
        # exige citacao de interoperabilidade para supported, senao
        # LACUNA explicita (complementaridade plausivel != integracao).
        if _has_inference_marker(sentence):
            _anchor, _relation = _split_inference(sentence)
            _anchor_toks = set(_content_tokens(_anchor))
            _rel_toks = set(_content_tokens(_relation))
            _named_anchor = [e for e in entities if _anchor_toks & e[0]]
            _named_rel = [e for e in entities if _rel_toks & e[0]]
            # sem marcador util: usa a frase cheia como relacao
            if not _relation:
                _relation, _rel_toks, _named_rel = (
                    sentence, set(_content_tokens(sentence)),
                    [e for e in entities
                     if set(_content_tokens(sentence)) & e[0]])
            _interop_ok = False
            _anchor_any_ok = False
            _rel_reasons: list[str] = []
            _std_docs: list[str] = []
            for n in citations:
                url = n_to_url.get(n)
                if not url:
                    _rel_reasons.append("citação fora do corpus")
                    continue
                _doc = _doc_for(url)
                if not _doc:
                    _rel_reasons.append("citação fora do corpus")
                    continue
                _std_docs.append(_doc)
                a_ok, r_ok, _a_r, r_r = _audit_inference(
                    _anchor, _relation, _doc, _named_anchor, _named_rel,
                    identity_fn=_entity_mentioned)
                if a_ok:
                    _anchor_any_ok = True
                if a_ok and r_ok:
                    _interop_ok = True
                    break
                _rel_reasons.append(r_r or _a_r)
            # A relation can be grounded by one independently cited premise
            # for each named entity; neither source needs to mention both.
            # Require every substantive word in each explicit premise to
            # match its own entity's document. No compatibility/test claim
            # follows from this check.
            grounded_pair = False
            pair = re.search(r"\b(?:pois|porque)\s+um\s+(.+?)\s+e\s+(?:o|a)\s+outr[oa]\s+(.+?)(?:[,;.]|$)", sentence, re.I)
            if pair and len(_strict) == 2 and len(_std_docs) >= 2 and _has_polarity_ceiling(sentence):
                ordered = sorted(_strict, key=lambda e: _norm_mention(sentence).find(_norm_mention(e[1])))
                matched_urls = []
                for entry, clause in zip(ordered, pair.groups()):
                    terms = {w for w in _content_tokens(clause) if len(w) >= 4}
                    found = None
                    for n in citations:
                        url = n_to_url.get(n); doc = _doc_for(url) if url else ""
                        doc_terms = _support_doc_tokens(doc) if doc else frozenset()
                        if (terms and doc and _entity_mentioned(entry[1], entry[2], doc)
                                and all(_expand_support_tokens({w}) & doc_terms for w in terms)):
                            found = url
                            break
                    matched_urls.append(found)
                grounded_pair = len(set(matched_urls)) == 2 and all(matched_urls)
                if grounded_pair:
                    _anchor_any_ok = True
            # The same contract also applies when each named entity has its
            # own explicit clause, without the "um ... outro" construction.
            # Require every substantive term in each positive clause to match
            # that entity's independently identified source.
            if (not grounded_pair and len(_strict) == 2 and len(_std_docs) >= 2
                    and _has_polarity_ceiling(sentence)
                    and re.search(r"(?i)complement|combin", sentence)):
                spans = []
                for entry in _strict:
                    full = str(entry[1] or "")
                    base = re.sub(r"\([^)]*\)", "", full).strip()
                    match = re.search(re.escape(full), sentence, re.I)
                    if not match and alias_counts.get(_norm_mention(base)) == 1:
                        match = re.search(re.escape(base), sentence, re.I)
                    spans.append((match, entry))
                if all(m for m, _ in spans):
                    spans.sort(key=lambda item: item[0].start())
                    (first, e1), (second, e2) = spans
                    clauses = [sentence[first.end():second.start()],
                               re.split(r"[,;.:]", sentence[second.end():], maxsplit=1)[0]]
                    found_urls = []
                    glue = {"ajuda", "helps", "help", "contribui", "contributes", "permite", "allows",
                            "estruturar", "structure", "organizar", "organize",
                            "visibilidade", "elicitação", "elicitacao", "posterior"}
                    for entry, clause in zip((e1, e2), clauses):
                        if re.search(r"(?i)\b(?:não|nao|sem|not|never)\b", clause):
                            found_urls.append(None)
                            continue
                        terms = {w for w in _content_tokens(clause) if len(w) >= 4 and w not in glue}
                        found = None
                        for n in citations:
                            url = n_to_url.get(n); doc = _doc_for(url) if url else ""
                            doc_terms = _support_doc_tokens(doc) if doc else frozenset()
                            if (terms and doc and _entity_mentioned(entry[1], entry[2], doc)
                                    and all(_expand_support_tokens({w}) & doc_terms for w in terms)):
                                found = url
                                break
                        found_urls.append(found)
                    grounded_pair = len(set(found_urls)) == 2 and all(found_urls)
                    if grounded_pair:
                        _anchor_any_ok = True
            if missing_named:
                _anchor_any_ok = False
                _interop_ok = False
                grounded_pair = False
            # Gate de polaridade (accept42 item 1): negação/limite ou
            # modalidade não-factual nunca emite "integração testada".
            try:
                _capped = bool(_has_polarity_ceiling(sentence))
            except Exception:
                _capped = False
            if _interop_ok and not _capped:
                if _meets_test_standard(sentence, _std_docs):
                    supported += 1
                    declared_inference.append(
                        {"sentence": sentence, "citations": citations,
                         "anchor_ok": True, "relation_ok": True,
                         "scope": "integração testada (interoperabilidade "
                                  "citada)"})
                    continue
                # Co-mencção ≠ teste (accept42 item 2): premissas
                # sustentadas, mas sem verbo de teste nem execução no doc —
                # inferência parcial declarada, nunca integração testada.
                supported += 1
                _decl_i = {"sentence": sentence, "citations": citations,
                           "anchor_ok": True, "relation_ok": False,
                           "scope": PARTIAL_DECLARED_SCOPE}
                declared_inference.append(dict(_decl_i))
                partial_declared.append(dict(_decl_i))
                continue
            if _capped and _interop_ok:
                # Teto: âncora+relação ok no overlap, mas a frase nega ou
                # limita — cai no ramo partial/LACUNA abaixo.
                _interop_ok = False
                _rel_reasons = ["teto polaridade: afirmação com "
                                "negação/limite ou modalidade não-factual "
                                "(partial declarada/LACUNA, nunca "
                                "integração testada)"]
            # ancora ok mas relacao sem prova = complementaridade plausivel
            reason = _rel_reasons[0] if _rel_reasons else \
                ("inferência sem citação de interoperabilidade "
                 "(complementaridade plausível, não integração testada)")
            if "interoperabilidade" not in reason and "integra" not in reason:
                reason = ("inferência sem citação de interoperabilidade "
                          "(complementaridade plausível, não integração "
                          "testada)")
            if not grounded_pair:
                unsupported.append({"sentence": sentence,
                                    "citations": citations,
                                    "reason": reason})
            _decl = {"sentence": sentence, "citations": citations,
                     "anchor_ok": bool(_anchor_any_ok), "relation_ok": False,
                     "scope": PARTIAL_DECLARED_SCOPE}
            declared_inference.append(dict(_decl))
            if _anchor_any_ok:
                # Premissas sustentadas em fontes distintas contam partial
                # declarada com limites explícitos; só alegação de
                # integração testada exige doc-interop (≥2 entidades).
                partial_declared.append(dict(_decl))
            continue
        # Trava de interoperabilidade (Missão 3): claim com >=2
        # entidades exige um doc que mencione >=2 delas (integração
        # testada); âncoras ok em docs separados = complementaridade
        # plausível (declared/LACUNA explícita, não unsupported
        # genérico); resto unsupported. Unificada com o ramo marcado.
        _cited: list[tuple[int, str]] = []
        for n in citations:
            _url = n_to_url.get(n)
            _doc = _doc_for(_url) if _url else ""
            if not _url or not _doc:
                _cited.append((n, ""))
            else:
                _cited.append((n, _doc))
        _needs_interop = len(named) >= 2
        if _needs_interop:
            # Nomeação frouxa (token compartilhado como "widget") não
            # arma a trava: exige menção estrita de >=2 entidades na
            # frase (mesmo critério _entity_mentioned usado nos docs).
            _interop_named = [entry for entry in named if entry in _strict] if _strict else [
                entry for entry in named if _entity_mentioned(entry[1], entry[2], sentence)]
            _needs_interop = len(_interop_named) >= 2
        else:
            _interop_named = []
        _has_interop_doc = _needs_interop and any(
            sum(1 for _toks, _lb, _eid in _interop_named
                if _entity_mentioned(_lb, _eid, _doc)) >= 2
            for _, _doc in _cited if _doc)
        ok = False
        reasons: list[str] = []
        for n, _doc in _cited:
            if not _doc:
                reasons.append("citação fora do corpus")
                continue
            good, reason = _sentence_supported(
                sent_tokens, _doc, named, factual, identity_fn=_vetoed_mention)
            if good:
                ok = True
                break
            reasons.append(reason)
        if ok and _needs_interop and not _has_interop_doc:
            # overlap/entidade ok em doc(s) só, mas nenhum doc citado
            # menciona >=2 entidades: não é integração testada
            ok = False
        # Gate de polaridade (accept42 item 1): frase interop com
        # negação/limite ou modalidade não-factual nunca vira
        # "integração testada" — cai em unsupported com teto explícito.
        try:
            _cap2 = bool(_needs_interop and _has_polarity_ceiling(sentence))
        except Exception:
            _cap2 = False
        # Enumeração do plano (accept42 item 3): lista de ≥3 candidatos
        # sem verbo de teste nunca entra no canal declared_inference.
        try:
            _enum = bool(_needs_interop and _has_interop_doc
                         and _is_plan_enumeration(sentence, _interop_named))
        except Exception:
            _enum = False
        if _cap2 and ok:
            ok = False
            reasons.append("teto polaridade: afirmação com negação/limite "
                           "ou modalidade não-factual (partial "
                           "declarada/LACUNA, nunca integração testada)")
        if not ok and _needs_interop and not _has_interop_doc and not _enum:
            _covered = [entry for entry in _interop_named
                        if any(_entity_mentioned(entry[1], entry[2], _doc)
                               for _, _doc in _cited if _doc)]
            if _cited and any(_doc for _, _doc in _cited) \
                    and len(_covered) == len(named):
                unsupported.append({
                    "sentence": sentence, "citations": citations,
                    "reason": "inferência sem citação de "
                              "interoperabilidade (complementaridade "
                              "plausível, não integração testada)"})
                _decl2 = {"sentence": sentence, "citations": citations,
                          "anchor_ok": True, "relation_ok": False,
                          "scope": PARTIAL_DECLARED_SCOPE}
                declared_inference.append(dict(_decl2))
                partial_declared.append(dict(_decl2))
                continue
            if "entidade não mencionada no doc" not in reasons:
                reasons.append("entidade não mencionada no doc")
        if ok:
            supported += 1
            # v2-1 positiva: integração testada vai para o canal declared
            # com premissas+limites (não só contagem): qual doc sustenta
            # quais entidades, na janela auditada.
            if _needs_interop and _has_interop_doc and not _cap2 and not _enum:
                if not _meets_test_standard(
                        sentence, [d for _, d in _cited if d]):
                    # Co-mencção ≠ teste (accept42 item 2): sustentada,
                    # mas sem verbo de teste nem execução no doc —
                    # inferência parcial declarada, nunca integração testada.
                    _decl_i2 = {"sentence": sentence, "citations": citations,
                                "anchor_ok": True, "relation_ok": False,
                                "scope": PARTIAL_DECLARED_SCOPE}
                    declared_inference.append(dict(_decl_i2))
                    partial_declared.append(dict(_decl_i2))
                else:
                    try:
                        _which = []
                        for _, _doc in _cited:
                            if not _doc:
                                continue
                            _hit = [str(_lb)
                                    for _toks, _lb, _eid in _interop_named
                                    if _entity_mentioned(_lb, _eid, _doc)]
                            if len(_hit) >= 2:
                                _which.append("; ".join(_hit[:4]))
                                break
                    except Exception:
                        _which = []
                    declared_inference.append(
                        {"sentence": sentence, "citations": citations,
                         "anchor_ok": True, "relation_ok": True,
                         "scope": "integração testada (interoperabilidade "
                                  "citada)" + (f": {_which[0][:160]}"
                                                if _which else "") +
                                  "; limites: janela auditada (usable_text "
                                  "integral), sem extrapolar além do doc "
                                  "citado"})
        else:
            # conclusoes separadas: preserva a razao do gate (exata vs
            # familia vs entidade vs corpus) em vez de colapsar em
            # "sem sobreposição". Teto de polaridade tem prioridade: é a
            # causa do rebaixamento, não a entidade.
            _cap_reasons = [r for r in reasons
                            if r.startswith("teto polaridade")]
            _prio = [r for r in reasons
                     if r in ("versão exata ausente no doc",
                              "família funcional ausente no doc",
                              "entidade não mencionada no doc",
                              "citação fora do corpus")]
            reason = _cap_reasons[0] if _cap_reasons else (
                _prio[0] if _prio else (
                "entidade não mencionada no doc"
                if "entidade não mencionada no doc" in reasons
                else (reasons[0] if reasons else "sem sobreposição")))
            unsupported.append({"sentence": sentence,
                                "citations": citations,
                                "reason": reason})
    if claims == 0:
        status = "unknown"
    elif supported == 0:
        # Semântica: inferência declarada com limites explícitos
        # (premissas em fontes distintas, sem alegar integração testada)
        # é partial — nunca ok (relação sem prova) nem failed total
        # (âncoras sustentadas). Só failed puro quando nada é nem
        # sustentado nem partial declarado.
        status = "partial" if partial_declared else "failed"
    elif supported / claims < 0.7:
        status = "partial"
    else:
        status = "ok"
    if (missing_entity_sources and status == "failed" and unsupported
            and all(str(item.get("reason") or "").startswith("inferência")
                    or item.get("reason") == "entidade não mencionada no doc" for item in unsupported)):
        status = "partial"  # incomplete attribution is not factual disproof
    elif missing_entity_sources and status == "ok":
        status = "partial"
    detail = (f"{supported}/{claims} frase(s) citada(s) sustentada(s); "
              f"{uncited} sem citação")
    if declared:
        detail += f"; {len(declared)} declaração(ões) de lacuna sustentada(s)"
    if declared_inference:
        detail += (f"; {len(declared_inference)} inferência(s) declarada(s) "
                   f"(nunca supported por âncora)")
    if partial_declared:
        detail += (f"; {len(partial_declared)} partial(is) declarada(s) "
                   f"(premissas em fontes distintas, limites explícitos)")
    if missing_entity_sources:
        detail += f"; {len(missing_entity_sources)} inferência(s) sem fonte para todas as entidades"
    # B5+janela: registra qual janela foi auditada (texto usable integral +
    # hashes no formato last_selection, com seleção quando exposta).
    # Audita na mesma janela do writer ou diff excerto×full-text antes de
    # concluir "só links": o modo carrega o escopo (janela vs global).
    try:
        _doc_hashes = {url: _window_hash(txt) for url, txt in docs.items()}
    except Exception:
        _doc_hashes = {}
    _audit_window: dict = {
        "mode": "usable_text integral (full-text); por bullet/linha",
        "granularity": "linha+frase (trava de versão por bullet)",
        "doc_hashes": _doc_hashes,
        "window": "janela (excertos avaliados) vs global (corpus integral): "
                  "ver declared[].scope",
        "excerpt_vs_fulltext": "auditado em usable_text integral; "
                               "writer usa excertos (2000 chars/doc, teto "
                               "12000): LACUNA 'só links' é da janela, "
                               "não global sem diff",
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
            "declared": declared, "declared_inference": declared_inference,
            "partial_declared": partial_declared,
            "missing_entity_sources": missing_entity_sources,
            "inferred_comparisons": inferred_comparisons,
            "user_premises": user_premises, "audit_window": _audit_window}


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


def _judged_quorum(audit: dict | None, reviewed: int) -> int:
    """Afirmações com veredito final com quórum.

    Exclui review_incomplete/missing_result (tentativa sem quórum).
    Sem detalhe de vereditos, equivale a reviewed (comportamento
    preservado); campo novo, leitores antigos intactos.
    """
    try:
        audit = audit if isinstance(audit, dict) else {}
        explicit = audit.get("claims_judged_quorum")
        if isinstance(explicit, int) and not isinstance(explicit, bool):
            return max(0, explicit)
        verdicts = audit.get("verdicts") or []
        if any(isinstance(v, dict) for v in verdicts):
            return sum(1 for v in verdicts
                       if isinstance(v, dict)
                       and v.get("verdict") not in ("review_incomplete",
                                                   "missing_result"))
    except Exception:
        pass
    return reviewed


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
    judged = _judged_quorum(audit, reviewed)
    evidence = {
        "enabled": enabled,
        "claims_extracted": claims,
        "claims_reviewed": reviewed,
        "claims_judged_quorum": judged,
        "claims_unreviewed": max(0, claims - reviewed),
        "verdict_state": audit.get("verdict_state", "não revisado"),
        "accepted": bool(audit.get("accepted")),
        "audited_sha": audit.get("audited_sha"),
        "audited_scope": audit.get("audited_scope", "síntese; suporte ao Markdown final verificado separadamente"),
        "votes": summary.get("votes", "unknown"),
        "technical_failures": failures,
        "technical_failure_votes": summary.get("technical_failure_votes",
                                                "unknown"),
        "unsupported_claims": unsupported,
        "judgment_counts": {k: sum(v.get("verdict") == k for v in verdicts)
                            for k in ("sustained", "partial", "gap", "unsupported", "disputed_tie", "review_incomplete")},
        "extraction_complete": coverage.get("coverage_complete", "unknown"),
        "incomplete_extractions": counts.get("claims_incomplete", "unknown"),
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
    # Denominadores de quórum (accept42 item 4): votos por afirmação vs
    # total de slots — tentativa (reviewed) sem quórum nunca se passa por
    # julgamento (judged).
    try:
        _votes = summary.get("votes")
        _tfv = summary.get("technical_failure_votes")
        if (isinstance(_votes, int) and not isinstance(_votes, bool)
                and isinstance(_tfv, int) and not isinstance(_tfv, bool)
                and claims > 0 and _votes > 0):
            _slots = claims * _votes
            notes.append(
                f"quórum: {_votes} voto(s) por afirmação com veredito; "
                f"{_tfv} voto(s) de falha técnica em {_slots} slot(s) "
                f"de voto ({claims} afirmações × {_votes} votos); "
                f"julgadas com quórum: {judged}/{claims} "
                f"(tentadas: {reviewed}/{claims})")
    except Exception:
        pass
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
    """URLs that really sustain claims: obtained text, qualification allows.

    user://context/* nunca e corpus (premissa explicita do usuario, sem
    numero; nunca LACUNA automatica).
    """
    evidence = state.get("evidence") or {}
    qualification = state.get("qualification") or {}
    corpus = {}
    for url, text in evidence.items():
        if isinstance(url, str) and url.startswith("user://"):
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        qual = qualification.get(url) or {}
        if qual.get("excluded"):
            continue
        if not (qual.get("usable_text") or text or "").strip():
            continue
        corpus[url] = qual
    return corpus


def _is_own_note_line(line: str) -> bool:
    """Linha de nota propria do renderer/verificacao, nao afirmacao."""
    try:
        s = str(line or "").strip()
    except Exception:
        return False
    if not s:
        return False
    if s.startswith("|"):
        return True
    low = s.lower()
    # notas que listam outside/beyond + tabela de fontes
    if "fora do corpus" in low or "fora da base" in low:
        return True
    if low.startswith("- render:") or low.startswith("- support:"):
        return True
    return False


def verify_support(state: dict, report_text: str,
                   audit: dict | None = None) -> dict:
    """Every citation must resolve to real evidence; unknown never supports.

    Consultado vs mencionado: exclui linhas de nota propria e aplica
    classify_reference (so evidence pondera unknown); utility/in_command
    mencionado sem citacao como fonte nunca falha.
    """
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
    _all_refs = ca.extract_references(report_text or "")
    # exclui linhas de nota propria (tabela §7, notas render/support)
    refs = [r for r in _all_refs
            if not _is_own_note_line(r.get("snippet") or "")]
    # so evidence pondera unknown (consultado); mencionado (utility/
    # in_command) nunca vira unknown
    resolved, unknown = [], []
    _evidence_refs = []
    for ref in refs:
        try:
            kind = ca.classify_reference(ref)
        except Exception:
            kind = "utility"
        if kind != "evidence":
            continue
        _evidence_refs.append(ref)
        norm = ca.normalize_url(ref.get("url"))
        if norm and norm in norm_corpus:
            resolved.append(norm)
        elif norm:
            unknown.append(norm)
    # [N] resolve (Missão 3): o corpo cita ([N]) e o extrator só enxerga
    # URLs nuas — resolve in-text [N] via state[report][numbers] (mesmo
    # _n_to_url de check_support) antes de extract_references. unknown =
    # [N] sem URL + URL fora do corpus. Linhas de tabela/nota propria
    # excluídas (inventário, não afirmação).
    _rep_numbers_raw = ((state.get("report") or {}).get("numbers") or {})
    _bracket_n_to_url = _n_to_url(_rep_numbers_raw)
    if not _bracket_n_to_url:
        # fallback: tabela de fontes do próprio relatório (mesma
        # convenção de diagnose._number_map; estados sem numbers)
        try:
            _table_map: dict[int, str] = {}
            for _m in re.finditer(r"\| \[(\d+)\] \| (\S+)",
                                  report_text or ""):
                _table_map[int(_m.group(1))] = _m.group(2)
            _bracket_n_to_url = _table_map
        except Exception:
            _bracket_n_to_url = {}
    _bracket_total = 0
    _bracket_unknown: list[str] = []
    try:
        for _line in (report_text or "").splitlines():
            _s = _line.strip()
            if not _s or _s.startswith(("|", "#", ">", "```")):
                continue
            if _is_own_note_line(_s):
                continue
            _low = re.sub(r"^[\s*_`]+", "", _s)
            if re.match(r"(refer[êe]ncias?|fontes?)\s*:", _low, re.I):
                continue
            for _m in re.finditer(r"\[(\d+)\]", _s):
                _bracket_total += 1
                try:
                    _bn = int(_m.group(1))
                except ValueError:
                    continue
                _burl = _bracket_n_to_url.get(_bn)
                if not _burl:
                    _bracket_unknown.append(f"[{_bn}]")
                    continue
                _norm = ca.normalize_url(_burl)
                if _norm and _norm in norm_corpus:
                    resolved.append(_norm)
                elif _norm:
                    unknown.append(_norm)
                else:
                    _bracket_unknown.append(f"[{_bn}]")
    except Exception:
        pass
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
    judged = _judged_quorum(audit, reviewed)
    evidence = {
        "citations": len(_all_refs) + _bracket_total,
        "citations_evidence": len(_evidence_refs) + _bracket_total,
        "citations_all_mentions": len(_all_refs) + _bracket_total,
        "citations_resolved": len(set(resolved)),
        "citations_unknown": sorted(
            set(unknown) | set(_bracket_unknown)),
        "claims_extracted": claims,
        "claims_reviewed": reviewed,
        "claims_judged_quorum": judged,
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
                    _n = ca.normalize_url(_m.group(0).rstrip('.,;:\"\'”“’'))
                    if _n:
                        _table_urls.add(_n)
        _resolved_all: set[str] = set()
        for _r in _all_refs:
            if _is_own_note_line(_r.get("snippet") or ""):
                continue
            _nn = ca.normalize_url(_r.get("url"))
            if _nn and _nn in norm_corpus:
                _resolved_all.add(_nn)
        beyond = sorted((_resolved_all - {ca.normalize_url(u) for u in used
                                           if ca.normalize_url(u)}
                         ) - _table_urls)
    except Exception:
        beyond = []
    evidence["cited_beyond_synthesis"] = beyond
    # Janela Context7: sintese cita a janela (selection_hashes); LACUNA
    # com escopo de janela vs global; audita na mesma janela do writer ou
    # diff excerto×full-text antes de "só links".
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
        _rep_sel = ((state.get("report") or {}).get("selection") or {})
        _writer_urls = list(_rep_sel.get("included_urls") or [])
        evidence["audit_window"] = {
            "mode": "usable_text integral (full-text)",
            "doc_hashes": _doc_hashes,
            "selection_urls": _sel_win.get("urls") or [],
            "selection_hashes": _sel_win.get("hashes") or {},
            "hash_source": _sel_win.get("hash_source") or "",
            # sintese cita a janela do writer (teto 12000/2000/doc)
            "writer_included_urls": _writer_urls,
            "writer_chars": _rep_sel.get("chars"),
            "writer_cuts": str(_rep_sel.get("cuts") or "")[:600],
            "excerpt_vs_fulltext": "auditado em full-text; writer em "
                                   "excertos: 'só links' e LACUNA sem diff "
                                   "sao da janela, nao global",
        }
    except Exception:
        pass
    notes = []
    # B5: pondera sentence_support quando a citação é do doc da entidade.
    # Sem reescrever auditores: roda o audit por frase (por bullet, B2) nas
    # linhas de afirmação (fora tabela/cabeçalho/nota propria) com a mesma
    # numeração persistida do relatório; versão/entidade/literal/interop
    # ausente no doc e citação fora do corpus ponderam (overlap genérico
    # baixo nunca força falha, para preservar a verificação existente).
    _sent_weighted = None
    _rep_numbers: dict = {}
    try:
        _plan = state.get("plan") or {}
        _has_entities = bool((_plan.get("entities") or []))
        _rep_numbers = ((state.get("report") or {}).get("numbers") or {})
        if _has_entities and _rep_numbers:
            _claim_lines: list[str] = []
            for _line in (report_text or "").splitlines():
                _s = _line.strip()
                if not _s:
                    continue
                if _s.startswith(("|", "#", ">", "```")):
                    continue
                if _is_own_note_line(_s):
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
                    if _is_own_note_line(_sraw):
                        continue
                    _reason = str(_item.get("reason") or "")
                    if _reason == "entidade não mencionada no doc":
                        _weighted_misses.append(_item)
                        continue
                    # LACUNA+quote/corpus/interop: literal/interop ausente
                    # e citação fora do corpus ponderam como versão/entidade.
                    if _reason.startswith(("literal ausente no doc citado",
                                           "citação fora do corpus",
                                           "inferência sem citação de "
                                           "interoperabilidade",
                                           "inferencia sem citacao")):
                        _weighted_misses.append(_item)
                        continue
                    if _reason.startswith(("versão exata ausente",
                                           "versao exata ausente",
                                           "família funcional ausente",
                                           "familia funcional ausente",
                                           "versão ausente")):
                        _weighted_misses.append(_item)
                        continue
                    # Trava de versão por bullet: versão afirmada sem
                    # isenção de lacuna nunca é overlap genérico.
                    # Gate separado tag exata vs familia funcional.
                    # Regra estreita Div3 (mesma do check_support):
                    # premissa numérica sustenta (isenção mantida);
                    # funcional sem fonte reprova (pondera como miss).
                    try:
                        if ((_text_exact_versions(_sraw)
                             or _text_family_versions(_sraw))
                                and not _mentions_version_gap(_sraw)
                                and not (_is_user_premise(_sraw)
                                         and _is_numeric_comparison(_sraw))):
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
                        "versão/entidade/literal/interop ausente no doc ou "
                        "citação fora do corpus "
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
                     + ", ".join(sorted(set(unknown)
                                        | set(_bracket_unknown))))
    if unsupported:
        notes.append(f"{len(unsupported)} afirmação(ões) sem suporte")
    # Gate vazio (Missão 3): claims==0 com refs válidas ([N] resolvidos
    # contam) não pode dizer "Sem citações verificáveis" — só vazio
    # real (sem URL e sem [N]) é not_run.
    if not _all_refs and not _bracket_total and not _rep_numbers:
        return _result("support", "not_run", evidence,
                       notes + ["relatório sem citações verificáveis"])
    if unknown or _bracket_unknown or unsupported:
        return _result("support", "failed", evidence, notes)
    try:
        _contra = _contradictory_absence(report_text or "", state)
    except Exception:
        _contra = ""
    if _contra:
        notes.append(_contra)
        return _result("support", "failed", evidence, notes)
    try:
        _fa_flags = _false_absence_flags(report_text or "", state=state)
    except Exception:
        _fa_flags = []
    if _fa_flags:
        evidence["false_absence_flags"] = [
            {"entity": str(f.get("label") or f.get("entity_id")),
             "sentence": str(f.get("sentence") or "")[:300],
             "evaluations": f.get("evaluations")}
            for f in _fa_flags[:8]]
        evidence["sentence_unsupported"] = list(
            evidence.get("sentence_unsupported") or []) + [
            {"sentence": str(f.get("sentence") or "")[:300],
             "citations": [int(n) for n in
                           re.findall(r"\[(\d+)\]",
                                      str(f.get("sentence") or ""))],
             "reason": "ausência contradiz evaluations com refs"}
            for f in _fa_flags[:8]]
        notes.append(
            "ausência contradiz evaluations com refs: "
            f"{len(_fa_flags)} afirmação(ões) de 'sem funcionalidade/"
            "documentação atribuível' com evaluations partial/covered "
            "e refs resolvidas")
        return _result("support", "failed", evidence, notes)
    # Oráculo externo (diagnose pós-hoc, quando fornecido em
    # state["diagnose_audit"]): misses que este auditor não ponderou
    # impedem ok SOMENTE com pergunta parcial (gaps abertos) — sem
    # pendência, viram nota informativa sem mudar o veredito.
    # Ausente = sem efeito (comportamento in-product inalterado).
    try:
        _oracle = state.get("diagnose_audit") or {}
        _o_uns = int(_oracle.get("unsupported", 0) or 0)
        _o_items = [i for i in (_oracle.get("unsupported_items") or [])
                    if isinstance(i, dict)]
    except Exception:
        _o_uns, _o_items = 0, []
    if _o_uns or _o_items:
        evidence["oracle_misses"] = [
            {"sentence": str(i.get("sentence") or "")[:300],
             "reason": str(i.get("reason") or "")[:300]}
            for i in _o_items[:8]]
        try:
            _qc = state.get("question_coverage") or {}
            _q_open = bool(_qc.get("gaps")) or (
                bool(_qc) and not _qc.get("complete"))
        except Exception:
            _q_open = False
        notes.append(
            f"oráculo diagnose: {_o_uns or len(_o_items)} afirmação(ões) "
            "sem suporte fora da janela deste auditor")
        if _q_open:
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
    # "integralmente revisadas" só com quórum (accept42 item 4): a
    # tentativa (reviewed) sem veredito final não conta como julgamento.
    if not audit.get("enabled") or judged < claims:
        notes.append("citações resolvem no corpus, mas as afirmações não "
                     "foram integralmente revisadas")
        return _result("support", "partial", evidence, notes)
    return _result("support", "ok", evidence, notes)


#: Ausência global de funcionalidade atribuível (genérico, sem literais):
#: formas normalizadas (sem acento, minúsculas, via _norm_mention) de 'sem
#: funcionalidade/documentação atribuível' + 'sem funcionalidade
#: documentada (atribuível)'. Só o claim global casa; LACUNA window-scoped
#: ('nenhum excerto afirma X') e 'sem X demonstrado' ficam de fora.
_FALSE_ABSENCE_PATTERNS = (
    "sem funcionalidade atribu",
    "sem funcionalidades atribu",
    "sem documentacao atribu",
    "sem documentacoes atribu",
    "sem funcionalidade documentada",
    "sem funcionalidades documentadas",
)


def _false_absence_ref_usable(url, evidence, qualification) -> bool:
    """Uma ref sustenta presença só resolvendo p/ usable_text não-excluído.

    Mesmos gates do Ledger._resolves (url no corpus + qualificação
    presente, não-excluída, sem status de erro, com usable_text): refs
    fora do corpus/excluídas/vazias e partial_declared fraco (anchor_ok
    sem refs resolvidas) nunca sustentam presença — falsa-presença
    inversa proibida.
    """
    try:
        if not isinstance(url, str) or not url:
            return False
        if url not in (evidence or {}):
            return False
        qual = (qualification or {}).get(url)
        if not isinstance(qual, dict):
            return False
        if qual.get("excluded"):
            return False
        status = str(qual.get("status") or "").strip().lower()
        if status in ("error", "failed", "fetch_error", "timeout",
                      "access_failure", "access-failure"):
            return False
        if not str(qual.get("usable_text") or "").strip():
            return False
        return True
    except Exception:
        return False


def _false_absence_flags(synthesis_text, evaluations=None, *, plan=None,
                         evidence=None, qualification=None,
                         state=None) -> list[dict]:
    """Flags de ausência-falsa: 'sem funcionalidade atribuível' × evals.

    Detecta frases que afirmam ausência GLOBAL de funcionalidade/
    documentação atribuível a entidade rotulada (padrões acima + menção
    estrita via _entity_mentioned, nunca substring) e verifica contra
    evaluations partial/covered dessa entidade com refs resolvidas.
    Retorna [{entity_id, label, sentence, evaluations}]. NUNCA força
    covered: sem evaluations que sustentem, retorna [] (LACUNA genuína
    passa). Mira o claim, não a seção: dispara em qualquer linha de
    afirmação fora de tabela/nota própria.
    """
    try:
        if isinstance(state, dict):
            if plan is None:
                plan = state.get("plan") or {}
            if evaluations is None:
                evaluations = state.get("evaluations")
            if evidence is None:
                evidence = state.get("evidence") or {}
            if qualification is None:
                qualification = state.get("qualification") or {}
        plan = plan if isinstance(plan, dict) else {}
        evidence = evidence if isinstance(evidence, dict) else {}
        qualification = (qualification if isinstance(qualification, dict)
                         else {})
        entities = [e for e in plan.get("entities") or []
                    if isinstance(e, dict)
                    and str(e.get("label") or "").strip()]
        if not entities:
            return []
        # evaluations: lista do ledger OU bloco question_coverage (dict).
        items: list[dict] = []
        if isinstance(evaluations, dict):
            for crit in evaluations.get("criteria") or []:
                if not isinstance(crit, dict):
                    continue
                refs = crit.get("references") or []
                by_ent: dict = {}
                if isinstance(crit.get("entity_states"), dict):
                    by_ent.update(crit["entity_states"])
                if crit.get("entity_id") is not None:
                    by_ent.setdefault(crit.get("entity_id"),
                                      crit.get("state"))
                for eid, stt in by_ent.items():
                    items.append({"criterion_id": crit.get("id"),
                                  "entity_id": eid, "state": stt,
                                  "references": refs})
        elif isinstance(evaluations, (list, tuple)):
            items = [e for e in evaluations if isinstance(e, dict)]
        if not items:
            return []
        sustaining: dict[str, list] = {}
        for ev in items:
            try:
                if ev.get("state") not in ("partial", "covered"):
                    continue
                eid = ev.get("entity_id")
                if eid is None:
                    continue
                refs = ev.get("references") or []
                ok = False
                for ref in refs:
                    url = ""
                    if isinstance(ref, dict):
                        url = ref.get("url", ref.get("doc_id", ""))
                    if _false_absence_ref_usable(url, evidence,
                                                 qualification):
                        ok = True
                        break
                if ok:
                    sustaining.setdefault(str(eid), []).append(ev)
            except Exception:
                continue
        if not sustaining:
            return []
        flags: list[dict] = []
        for line in str(synthesis_text or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith(("|", "#", ">", "```")):
                continue
            if _is_own_note_line(s):
                continue
            for sent in re.split(r"(?<=[.!?])\s+", s):
                sent = sent.strip()
                if not sent:
                    continue
                try:
                    norm = _norm_mention(sent)
                except Exception:
                    continue
                if not any(p in norm for p in _FALSE_ABSENCE_PATTERNS):
                    continue
                for ent in entities:
                    try:
                        named = bool(_entity_mentioned(
                            str(ent.get("label") or ""), ent.get("id"),
                            sent))
                    except Exception:
                        named = False
                    if not named:
                        continue
                    sup = sustaining.get(str(ent.get("id")))
                    if not sup:
                        continue
                    flags.append({
                        "entity_id": ent.get("id"),
                        "label": ent.get("label"),
                        "sentence": sent,
                        "evaluations": [
                            {"criterion_id": e.get("criterion_id"),
                             "state": e.get("state")} for e in sup],
                    })
        return flags
    except Exception:
        return []


def _contradictory_absence(report_text: str, state: dict) -> str:
    """Detecta §0-ausência × §7-usable contraditórios (genérico).

    Retorna nota quando uma linha de afirmação (fora tabela/nota própria)
    diz 'fora do corpus' sobre entidade que tem documento utilizável no
    corpus que a nomeia no corpo.
    """
    try:
        plan = state.get("plan") or {}
        evidence = state.get("evidence") or {}
        qualification = state.get("qualification") or {}
        entities = [e for e in plan.get("entities") or []
                    if isinstance(e, dict) and str(e.get("label") or "").strip()]
        if not entities:
            return ""
        # Docs utilizáveis por entidade (identidade estrita no corpo
        # qualificado: forma cheia com fronteira, nunca substring de label
        # — mesmo conceito de _identity_matches/status).
        docs_by_ent: dict[str, str] = {}
        for ent in entities:
            for url, text in evidence.items():
                if not isinstance(url, str) or url.startswith("user://"):
                    continue
                try:
                    qual = qualification.get(url) or {}
                    if qual.get("excluded"):
                        continue
                    body = str(qual.get("usable_text") or text or "")
                except Exception:
                    body = str(text or "")
                if not body.strip():
                    continue
                try:
                    _hit = bool(_entity_mentioned(
                        str(ent.get("label") or ""), ent.get("id"), body))
                except Exception:
                    _hit = False
                if _hit:
                    docs_by_ent[str(ent.get("id"))] = url
                    break
        if not docs_by_ent:
            return ""
        for line in str(report_text or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith(("|", "#", ">", "```")):
                continue
            _low0 = s.lower()
            if _low0.startswith(("- render:", "- support:")):
                continue
            low = s.lower()
            if "fora do corpus" not in low:
                continue
            for ent in entities:
                try:
                    _named = bool(_entity_mentioned(
                        str(ent.get("label") or ""), ent.get("id"), s))
                except Exception:
                    _named = False
                if not _named:
                    continue
                url = docs_by_ent.get(str(ent.get("id")))
                if url:
                    return (f"contradição §0-ausência × §7-usable: "
                            f"{ent.get('label') or ent.get('id')} tem "
                            f"documento utilizável no corpus ({url[:80]}), "
                            f"mas o relatório afirma 'fora do corpus'")
        return ""
    except Exception:
        return ""


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
