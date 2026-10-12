#!/usr/bin/env python3
"""Final-transport instrumentation for LLM calls (opt-in, no site-packages edits).

Records, for every outbound chat completion: the component that issued it, PID,
run_id, timestamp, model, the output-token parameter, reasoning/stream flags,
the HTTP status, a SANITIZED error body and any generation_id the provider
returns. Covers both plain HTTP errors and failures raised while streaming.

Why: a 400 from the provider was investigated with nothing but the provider's
own dashboard, because the client swallowed the body into a one-line message.
This wraps the client so the next occurrence is diagnosable from our side.

Never logs the API key, the Authorization header, or message content.
"""
from __future__ import annotations

import functools
import json
import os
import time
import traceback

RECORDS: list[dict] = []
_MAX = 500
_installed = False

# Fields we keep from an error body. Everything else is dropped: a raw provider
# body can echo the request, and the request contains the key header in some
# providers' error dumps.
_KEEP = ("message", "code", "param", "type", "status", "generation_id",
         "request_id", "provider_name")


def _sanitize(obj) -> dict:
    """Keep only diagnostic fields; never the key, headers or prompt text.

    Handles the provider's real shape, which nests the useful fields one level
    down: ``{"error": {"message": ..., "code": ..., "param": ...}}``. A flat
    scan would drop the only sentence that explains the failure.
    """
    out: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ("api_key", "authorization", "key", "headers"):
                continue
            if k == "error" and isinstance(v, dict):
                out["error"] = _sanitize(v)
            elif k in _KEEP:
                out[k] = _sanitize(v) if isinstance(v, (dict, list)) else str(v)[:400]
            elif k == "metadata":
                out[k] = _sanitize(v) if isinstance(v, (dict, list)) else str(v)[:400]
            elif isinstance(v, dict):
                # unknown nesting: recurse, the message may live there
                inner = _sanitize(v)
                if inner:
                    out[k] = inner
    elif isinstance(obj, list):
        return {"items": [_sanitize(x) for x in obj[:3]]}
    else:
        out = {"value": str(obj)[:400]}
    return out


def _caller() -> str:
    """The first frame outside this module and outside the library's utils."""
    for fr in reversed(traceback.extract_stack()[:-2]):
        fn = fr.filename
        if "call_trace" in fn or "/gpt_researcher/utils/llm.py" in fn:
            continue
        return f"{fn.split('/')[-1]}:{fr.lineno}:{fr.name}"
    return "?"


def record(**fields) -> None:
    if len(RECORDS) >= _MAX:
        return
    rec = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": os.getpid(),
        "run_id": os.environ.get("RUN_ID", ""),
        "component": _caller(),
    }
    rec.update(fields)
    RECORDS.append(rec)


def install() -> bool:
    """Wrap the transport so both success and failure carry evidence."""
    global _installed
    if _installed:
        return True
    try:
        from gpt_researcher.utils import llm as llm_utils
    except ImportError:
        return False
    orig = llm_utils.create_chat_completion

    @functools.wraps(orig)
    async def observed(*args, **kwargs):
        import inspect
        try:
            bound = inspect.signature(orig).bind_partial(*args, **kwargs).arguments
        except Exception:
            bound = {}
        base = {
            "model": bound.get("model"),
            "max_tokens": bound.get("max_tokens"),
            "reasoning_effort": bound.get("reasoning_effort"),
            "stream": bound.get("stream"),
        }
        t0 = time.monotonic()
        try:
            result = await orig(*args, **kwargs)
        except Exception as exc:
            body = getattr(exc, "body", None) or getattr(exc, "response", None)
            status = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None)
            detail = {}
            if body is not None:
                try:
                    detail = _sanitize(
                        body if isinstance(body, dict) else json.loads(str(body)))
                except Exception:
                    detail = {"value": str(body)[:400]}
            record(**base, ok=False, status=status,
                   error_type=type(exc).__name__,
                   error_detail=detail,
                   elapsed_s=round(time.monotonic() - t0, 2))
            raise
        record(**base, ok=True, elapsed_s=round(time.monotonic() - t0, 2))
        return result

    llm_utils.create_chat_completion = observed
    # Call sites that hold their OWN reference at import time keep calling the
    # unwrapped function unless rebound. agent_creator (agent_selection) and
    # tool_selector were exactly that: they imported the symbol before this
    # wrapper existed, which is why a run showed 3 billed steps but only 2
    # traced calls. Rebind every known holder.
    for mod_path, attr in (
        ("gpt_researcher.actions.query_processing", "create_chat_completion"),
        ("gpt_researcher.actions.report_generation", "create_chat_completion"),
        ("gpt_researcher.actions.agent_creator", "create_chat_completion"),
        ("gpt_researcher.utils.tools", "create_chat_completion"),
        ("gpt_researcher.skills.deep_research", "create_chat_completion"),
        ("gpt_researcher.skills.curator", "create_chat_completion"),
        ("gpt_researcher.mcp.tool_selector", "create_chat_completion"),
    ):
        try:
            import importlib
            m = importlib.import_module(mod_path)
            if hasattr(m, attr):
                setattr(m, attr, observed)
        except Exception:
            pass
    _installed = True
    return True


def dump(path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(RECORDS, fh, ensure_ascii=False, indent=1)


def violations() -> list[dict]:
    """Calls whose output-token parameter is below the provider minimum (16)."""
    bad = []
    for r in RECORDS:
        mt = r.get("max_tokens")
        if isinstance(mt, int) and 0 < mt < 16:
            bad.append(r)
    return bad
