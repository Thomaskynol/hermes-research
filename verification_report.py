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
import time
from pathlib import Path

DIMENSIONS = ("execution", "question", "review", "support")
STATUSES = ("ok", "partial", "failed", "not_run")


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
    notes = []
    if unknown:
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
