#!/usr/bin/env python3
"""Transportes nativos (search/fetch) sem gpt_researcher.

Usa os conectores já testados do projeto: ``agent_reach`` (gateway local,
página, repositório) e ``academic_search`` (OpenAlex/arXiv). Este módulo não
importa ``gpt_researcher`` — é o caminho que roda no host sem a biblioteca.

Falha é visível: canal indisponível levanta ``TransportError`` (do
coordenador, importado tardiamente) com motivo honesto; nunca devolve
chrome/erro como conteúdo utilizável. Se ``adaptive_coordinator`` não for
importável, usa ``NativeTransportError`` (mesma semântica).
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_S = 45.0
SEARCH_LIMIT = 8
GITHUB_API = "https://api.github.com/search/repositories"


class NativeTransportError(RuntimeError):
    """Fallback quando ``adaptive_coordinator.TransportError`` não resolve."""


def _error(message: str) -> Exception:
    """Import tardio: o módulo não acopla ao coordenador no import."""
    try:
        from adaptive_coordinator import TransportError  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - host pode não ter o coordenador
        return NativeTransportError(message)
    return TransportError(message)


# -- conectores reais (funções de módulo para permitir injeção nos testes) ---

def _default_academic_search(query: str, **kw):
    import academic_search  # noqa: PLC0415
    return academic_search.search_works(query, **kw)


def _default_web_search(query: str, **kw):
    import agent_reach  # noqa: PLC0415
    return agent_reach.search(query, **kw)


def _read_work(url: str, *, timeout: float):
    import academic_search  # noqa: PLC0415
    return academic_search.read_work(url, full_text=True, timeout=timeout)


def _read_repo(url: str, *, timeout: float, token: str | None = None):
    import agent_reach  # noqa: PLC0415
    return agent_reach.read_repo(url, timeout=timeout, token=token)


def _read_page(url: str, *, timeout: float, transport=None):
    import agent_reach  # noqa: PLC0415
    return agent_reach.read_page(url, timeout=timeout, transport=transport)


def _github_search(query: str, *, timeout: float, token: str | None) -> list[dict]:
    url = f"{GITHUB_API}?q={quote(query, safe='')}&per_page={SEARCH_LIMIT}"
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "hermes-native-transport"}
    request = Request(url, headers=headers)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except HTTPError as exc:
        raise _error(
            f"github search failed: HTTP {exc.code} "
            f"({'rate limited or unauthorised' if exc.code in (401, 403) else 'request rejected'})"
        ) from exc
    except (URLError, OSError) as exc:
        raise _error(f"github search unavailable: {type(exc).__name__}") from exc
    try:
        payload = json.loads(body.decode("utf-8", "replace")
                             if isinstance(body, bytes) else str(body))
    except (ValueError, AttributeError) as exc:
        raise _error("github search returned invalid JSON") from exc
    items = payload.get("items") if isinstance(payload, dict) else None
    hits: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict) or not item.get("html_url"):
            continue
        hits.append({"url": str(item["html_url"]),
                     "title": str(item.get("full_name") or ""),
                     "snippet": str(item.get("description") or "")[:500]})
    return hits


def _academic_hits(result) -> list[dict]:
    works = (getattr(result, "metadata", {}) or {}).get("works") or []
    hits: list[dict] = []
    for work in works:
        if not isinstance(work, dict):
            continue
        url = (work.get("url") or work.get("oa_url") or work.get("id") or "")
        if not str(url).startswith("http"):
            url = (f"https://doi.org/{work['doi']}"
                   if work.get("doi") else "")
        if not url:
            continue
        hits.append({"url": str(url), "title": str(work.get("title") or ""),
                     "snippet": str(work.get("abstract") or "")[:500]})
    if not hits:
        raise _error("academic search returned no usable works: "
                     f"{getattr(result, 'reason', None) or getattr(result, 'status', '')}")
    return hits


def _web_hits(result) -> list[dict]:
    status = str(getattr(result, "status", "") or "").lower()
    if status in ("unavailable", "failed") or not getattr(result, "ok", True):
        raise _error("web search unavailable: "
                     f"{getattr(result, 'reason', None) or status}")
    hits: list[dict] = []
    for item in (getattr(result, "metadata", {}) or {}).get("results") or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        hits.append({"url": str(item["url"]),
                     "title": str(item.get("title") or ""),
                     "snippet": str(item.get("snippet") or "")[:500]})
    return hits


def _payload(result) -> dict:
    """ReachResult -> dict aceito por ``_coerce_payload``.

    Contrato: failed/unavailable sem texto útil levantam TransportError
    (falha visível). Qualificação metadata_only/insufficient/none nunca vira
    texto utilizável; partial/usable carregam o texto lido.
    """
    status = str(getattr(result, "status", "") or "").lower()
    qualification = str(getattr(result, "qualification", "") or "").lower()
    text = str(getattr(result, "text", "") or "")
    reason = str(getattr(result, "reason", "") or "")
    if status in ("failed", "unavailable"):
        raise _error(f"fetch failed for {getattr(result, 'target', '?')}: "
                     f"{reason or status}")
    usable = qualification in ("usable", "partial") and bool(text.strip())
    if not usable:
        return {"text": "", "status": "empty",
                "reason": reason or f"no_usable_text:{qualification or status}",
                "usable_text": "", "excluded": True}
    return {"text": text, "status": qualification, "reason": reason,
            "usable_text": text, "excluded": False}


def build_native_transports(*, model_client=None, timeout: float = DEFAULT_TIMEOUT_S,
                            github_token: str | None = None, page_transport=None,
                            academic_search_fn=None, web_search_fn=None):
    """(search_fn, fetch_fn, model_client) sem gpt_researcher.

    ``describe()`` fica anexado a search_fn/fetch_fn com canais e limites
    efetivos (web depende do gateway local e pode estar indisponível).
    """
    academic_search_fn = academic_search_fn or _default_academic_search
    web_search_fn = web_search_fn or _default_web_search

    def search_fn(query: str, channel: str = "web") -> list[dict]:
        name = str(channel or "web").lower()
        if name == "academic":
            return _academic_hits(academic_search_fn(
                query, limit=SEARCH_LIMIT, source="both"))
        if name == "arxiv":
            # Coordinator channel for the academic family; native serves it
            # with the arXiv slice of the academic connector.
            return _academic_hits(academic_search_fn(
                query, limit=SEARCH_LIMIT, source="arxiv"))
        if name == "github":
            return _github_search(query, timeout=timeout, token=github_token)
        if name == "web":
            return _web_hits(web_search_fn(
                query, limit=SEARCH_LIMIT, channel="web"))
        if name == "youtube":
            # No search connector for YouTube in native scope: discovery of
            # videos needs web search (unavailable here); known URLs can
            # still be read via read_source/read_video. Honest, never empty.
            raise _error("youtube search unavailable in native transport: "
                         "no search connector; read known URLs directly")
        raise _error(f"channel {name!r} unavailable for native search")

    def fetch_fn(url: str) -> dict:
        target = str(url or "").strip()
        host = (urlsplit(target).hostname or "").lower()
        if host.endswith("arxiv.org"):
            result = _read_work(target, timeout=timeout)
        elif host == "github.com" or host.endswith(".github.com"):
            result = _read_repo(target, timeout=timeout, token=github_token)
        else:
            result = _read_page(target, timeout=timeout,
                                transport=page_transport)
        return _payload(result)

    def describe() -> dict:
        model_desc = None
        if hasattr(model_client, "describe"):
            try:
                model_desc = model_client.describe()
            except Exception as exc:  # noqa: BLE001 - describe nunca derruba
                model_desc = {"error": type(exc).__name__}
        return {
            "kind": "native",
            "channels": {
                "web": "agent_reach.search (gateway local; may be unavailable)",
                "academic": "academic_search.search_works (openalex+arxiv)",
                "github": "api.github.com/search/repositories"
                          + (" (token)" if github_token else " (no token: rate limited)"),
            },
            "timeout_s": timeout,
            "page_transport": "injected" if page_transport else "agent_reach.cascade",
            "limits": ["web_depends_on_local_retriever",
                       "academic_metadata_and_abstract_only",
                       "github_rate_limited_without_token"],
            "model_client": model_desc,
        }

    search_fn.describe = describe
    fetch_fn.describe = describe
    return search_fn, fetch_fn, model_client
