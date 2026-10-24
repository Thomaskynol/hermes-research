#!/usr/bin/env python3
"""Transportes de modelo explícitos, sem acoplamento no import.

Dois caminhos reais, ambos expostos como callable(prompt)->str:

- ``litellm_client``: biblioteca instalada no container; import preguiçoso.
- ``opencode_client``: CLI do host (``opencode run --standalone --format
  json``); funciona onde a biblioteca não existe.

O modelo é resolvido uma única vez, na construção: argumento explícito >
``researcher.cfg.smart_llm`` > ``SMART_LLM`` do ambiente. Nada aqui lê .env,
rede ou configuração de produção no import.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Callable

DEFAULT_OPENCODE_MODEL = "opencode/nemotron-3.5-lightning-free"
MAX_PROMPT_CHARS = 100_000
_PROVIDER_PREFIXES = frozenset({"openrouter", "openai", "anthropic", "google_genai"})
_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{4,}|Bearer\s+[A-Za-z0-9._\-]+)")


class ModelTransportError(RuntimeError):
    """Falha explícita do transporte de modelo (nunca silenciosa)."""


def _safe(prefix: str, exc: BaseException, limit: int = 240) -> str:
    """Mensagem curta, sem chave: erros de provedor vão para stdout/log."""
    text = f"{type(exc).__name__}: {exc}"
    text = _KEY_RE.sub("[redacted]", text)
    return f"{prefix}: {text[:limit]}"


def _researcher_model(researcher) -> str:
    cfg = getattr(researcher, "cfg", None)
    return str(getattr(cfg, "smart_llm", "") or "") if cfg is not None else ""


def _normalise_model(raw) -> str:
    """``openrouter:modelo`` -> ``openrouter/modelo`` (idem demais provedores)."""
    model = str(raw or "").strip()
    if not model:
        raise ModelTransportError("model_not_configured")
    if ":" in model:
        prefix, rest = model.split(":", 1)
        if prefix in _PROVIDER_PREFIXES:
            rest = rest.strip()
            if not rest:
                raise ModelTransportError("model_not_configured")
            return f"{prefix}/{rest}"
        if "/" not in model:
            raise ModelTransportError(f"unknown_provider:{prefix}")
    return model


def _resolve_model(model, researcher) -> str:
    return _normalise_model(
        model or _researcher_model(researcher) or os.environ.get("SMART_LLM", ""))


def litellm_client(*, model=None, timeout: float = 120.0,
                   researcher=None) -> Callable[[str], str]:
    """Callable(prompt)->str via litellm; import preguiçoso e erros curtos."""
    model_id = _resolve_model(model, researcher)

    def client(prompt: str) -> str:
        try:
            import litellm  # noqa: PLC0415 - preguiçoso: host não tem a lib
        except ImportError as exc:
            raise ModelTransportError("litellm_unavailable") from exc
        client.calls += 1
        try:
            response = litellm.completion(
                model=model_id,
                messages=[{"role": "user", "content": str(prompt)}],
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - provedor nunca derruba cru
            raise ModelTransportError(_safe("litellm_call_failed", exc)) from exc
        try:
            content = response.choices[0].message.content
        except Exception:  # noqa: BLE001 - resposta fora do contrato
            content = ""
        return content or ""

    client.model_id = model_id
    client.calls = 0
    client.describe = lambda: {"kind": "litellm", "model_id": model_id,
                               "calls": client.calls, "timeout": timeout}
    return client


def _jsonl_text(stdout: str) -> str:
    """Concatena ``part.text`` dos eventos ``type=="text"`` do CLI."""
    parts: list[str] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "text":
            continue
        part = event.get("part")
        text = part.get("text") if isinstance(part, dict) else None
        if isinstance(text, str) and text:
            parts.append(text)
    return "".join(parts)


def opencode_client(*, model: str = DEFAULT_OPENCODE_MODEL, binary: str = "opencode",
                    timeout: float = 180.0,
                    max_calls: int | None = None,
                    retries: int = 2,
                    retry_delays: tuple = (15.0, 45.0)) -> Callable[[str], str]:
    """Callable(prompt)->str via CLI do host; nada de chamada oculta.

    Resposta vazia (rate limit do free tier, 429 transitório) é repetida
    até ``retries`` vezes com espera crescente — cada tentativa conta em
    ``calls`` e no teto ``max_calls``. Falha persistente vira
    ModelTransportError explícito, nunca texto inventado.
    """
    model_id = str(model or "").strip()
    if not model_id:
        raise ModelTransportError("model_not_configured")

    def client(prompt: str) -> str:
        text = str(prompt or "")
        if len(text) > MAX_PROMPT_CHARS:
            raise ModelTransportError(
                f"prompt_too_large: {len(text)} chars > {MAX_PROMPT_CHARS}")
        if max_calls is not None and client.calls >= max_calls:
            raise ModelTransportError(f"max_calls_exceeded: {max_calls}")
        if shutil.which(binary) is None:
            raise ModelTransportError("opencode_cli_unavailable")
        last_error: Exception | None = None
        for attempt in range(max(0, retries) + 1):
            if max_calls is not None and client.calls >= max_calls:
                raise ModelTransportError(f"max_calls_exceeded: {max_calls}")
            client.calls += 1
            argv = [binary, "run", "--standalone", "--format", "json",
                    "-m", model_id, text]
            try:
                proc = subprocess.run(argv, capture_output=True, text=True,
                                      timeout=timeout, shell=False)
            except subprocess.TimeoutExpired as exc:
                raise ModelTransportError(
                    f"opencode_timeout: {timeout}s") from exc
            except FileNotFoundError as exc:
                raise ModelTransportError("opencode_cli_unavailable") from exc
            except OSError as exc:
                raise ModelTransportError(
                    _safe("opencode_spawn_failed", exc)) from exc
            answer = _jsonl_text(proc.stdout or "")
            if answer:
                return answer
            tail = _KEY_RE.sub("[redacted]", (proc.stderr or "")[-300:])
            last_error = ModelTransportError(
                f"opencode_no_text: rc={proc.returncode} "
                f"stderr_tail={tail!r} attempt={attempt + 1}")
            if attempt < max(0, retries):
                delay = retry_delays[attempt] \
                    if attempt < len(retry_delays) else retry_delays[-1]
                try:
                    import time as _time
                    _time.sleep(float(delay))
                except Exception:
                    pass
        raise last_error  # type: ignore[misc]

    client.model_id = model_id
    client.calls = 0
    client.describe = lambda: {"kind": "opencode", "model_id": model_id,
                               "calls": client.calls, "timeout": timeout,
                               "binary": binary, "max_calls": max_calls,
                               "retries": max(0, retries)}
    return client


def from_env(*, kind: str = "litellm", researcher=None, model=None,
             **kw) -> Callable[[str], str]:
    """Fábrica explícita do transporte escolhido (sem autodetecção)."""
    if kind == "litellm":
        return litellm_client(model=model, researcher=researcher, **kw)
    if kind == "opencode":
        if model:
            kw["model"] = model
        return opencode_client(**kw)
    raise ModelTransportError(f"unknown_transport:{kind}")


if __name__ == "__main__":  # pragma: no cover - inspeção manual
    import sys
    _kind = sys.argv[1] if len(sys.argv) > 1 else "litellm"
    _c = from_env(kind=_kind)
    print(json.dumps(_c.describe(), ensure_ascii=False, sort_keys=True))
