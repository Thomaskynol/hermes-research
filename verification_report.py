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


def _norm_mention(text) -> str:
    """Accent-insensitive, separator-normalized mention form."""
    import unicodedata as _ud
    norm = "".join(c for c in _ud.normalize(
        "NFKD", str(text or "").lower()) if not _ud.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", norm).strip()


def _entity_mentioned(label, eid, doc_text: str) -> bool:
    """The cell entity is named in the cited doc (label or id, full form).

    Token overlap ("opencode" + "agents" via "sub-agents") is not a
    mention: the normalized label/id itself must occur. Short ids
    ("e1") are skipped, the label decides.
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
    # however high the remaining overlap is.
    if sentence_raw and not _text_versions(sentence_raw) <= _text_versions(
            doc_text):
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


def is_lacuna_declaration(sentence: str) -> bool:
    lowered = str(sentence or "").lower()
    if any(m in lowered for m in LACUNA_DECLARATION_MARKERS):
        return True
    # Template do writer para célula insufficient: "sem <dimensão>
    # demonstrad[o/a]" (ex. accept15 "sem revisão demonstrada") — afirma
    # ausência de evidência, não fato positivo; genérico na dimensão.
    return re.search(r"sem\s+\w+\s+demonstrad[oa]\b", lowered) is not None


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


def check_support(synthesis_text: str, numbers, corpus, plan) -> dict:
    """Sentence-level support audit of the synthesis (audit only, no rewrite).

    Each sentence with a ``[n]`` citation is mapped back to the cited URL
    via ``numbers`` (renderer order) and checked against the real corpus:
    supported when (a) >=35% of the sentence content words occur in the doc
    or >=2 rare words (len>=6, absent from the title) are shared, and (b)
    every plan entity named by the sentence is mentioned in the doc.
    Uncited sentences are counted (informative, never a failure).
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
    for raw in re.split(r"(?<=[.!?])\s+", text):
        sentence = raw.strip()
        if not sentence:
            continue
        citations = [int(n) for n in re.findall(r"\[(\d+)\]", sentence)]
        if not citations:
            uncited += 1
            continue
        claims += 1
        # Absence declaration over consulted sources: sustained by the
        # consultation itself (the cited doc was read and says nothing),
        # never by word overlap with an empty statement.
        if is_lacuna_declaration(sentence) and all(
                n_to_url.get(n) and _doc_for(n_to_url[n])
                for n in citations):
            supported += 1
            declared.append({"sentence": sentence, "citations": citations})
            continue
        # Inference-marked claim: audit the factual anchor only.
        factual = _factual_anchor(sentence)
        sent_tokens = set(_content_tokens(factual))
        named = [entry for entry in entities if sent_tokens & entry[0]]
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
    return {"status": status, "claims": claims, "supported": supported,
            "uncited": uncited, "unsupported": unsupported, "detail": detail,
            "declared": declared}


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
    # Informational (never fails): cited in the report but outside the
    # writer-declared synthesis base. Both are observed events; a gap here
    # means findings reference material the writer did not list as base.
    try:
        used = set(((state.get("counters") or {}).get("documents") or {})
                   .get("used_in_synthesis") or [])
        beyond = sorted(set(resolved) - {ca.normalize_url(u) for u in used
                                         if ca.normalize_url(u)})
    except Exception:
        beyond = []
    evidence["cited_beyond_synthesis"] = beyond
    notes = []
    if beyond:
        notes.append("citação no relatório fora da base declarada de síntese: "
                     + ", ".join(beyond[:5]))
        notes.append("citação fora do corpus (não é fonte): "
                     + ", ".join(sorted(set(unknown))[:5]))
    if unsupported:
        notes.append(f"{len(unsupported)} afirmação(ões) sem suporte")
    if not refs:
        return _result("support", "not_run", evidence,
                       notes + ["relatório sem citações verificáveis"])
    if unknown or unsupported:
        return _result("support", "failed", evidence, notes)
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
