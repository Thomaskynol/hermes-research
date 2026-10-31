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
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_S = 45.0
SEARCH_LIMIT = 8
GITHUB_API = "https://api.github.com/search/repositories"
# Instância SearXNG autohospedada (nossa infraestrutura). O host alcança o
# container pelo IP da bridge; o default tenta o loop local (caso da pesquisa
# rodando dentro do container) e o operador fixa SEARXNG_URL no ambiente.
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://127.0.0.1:8888").rstrip("/")


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


def _searxng_search(query: str, *, limit: int = SEARCH_LIMIT,
                   base_url: str | None = None) -> list[dict]:
    """Busca web via SearXNG autohospedado (nossa infraestrutura).

    Rota intermediária do canal web: o gateway local continua primário; se
    ele falhar, tenta o SearXNG antes do ddgs. Hits carregam ``via`` e o
    ``engine`` que o SearXNG identifica — origem e motor sempre visíveis.
    Zero resultados conta como falha (recua para o ddgs); rede/instância
    fora levantam erro honesto com a base usada.
    """
    base = (base_url or SEARXNG_URL).rstrip("/")
    url = f"{base}/search?q={quote(query, safe='')}&format=json&language=all"
    request = Request(url, headers={"User-Agent": "hermes-native-transport",
                                    "Accept": "application/json"})
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_S) as response:
            body = response.read()
    except Exception as exc:  # noqa: BLE001 - qualquer falha vira erro honesto
        raise _error(f"searxng search unavailable at {base}: "
                     f"{type(exc).__name__}") from exc
    try:
        payload = json.loads(body.decode("utf-8", "replace")
                             if isinstance(body, bytes) else str(body))
    except (ValueError, AttributeError) as exc:
        raise _error("searxng search returned invalid JSON") from exc
    rows = (payload.get("results") if isinstance(payload, dict) else None) or []
    hits: list[dict] = []
    for row in rows[:max(1, int(limit or SEARCH_LIMIT))]:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        hit = {"url": str(row["url"]),
               "title": str(row.get("title") or ""),
               "snippet": str(row.get("content") or "")[:500],
               "via": "searxng"}
        if row.get("engine"):
            hit["engine"] = str(row["engine"])
        hits.append(hit)
    if not hits:
        raise _error(f"searxng search at {base} returned no usable results")
    return hits


def _ddgs_fallback_search(query: str, *, limit: int = SEARCH_LIMIT) -> list[dict]:
    """Busca web via ddgs (DuckDuckGo, sem chave, sem API comercial).

    Fallback honesto quando o gateway local está indisponível: levanta
    erro visível se o pacote não estiver instalado ou a rede falhar.
    """
    try:
        from ddgs import DDGS  # noqa: PLC0415
    except Exception as exc:
        raise _error(f"web fallback unavailable: ddgs not installed ({exc})") from exc
    try:
        rows = DDGS().text(query, max_results=max(1, int(limit or SEARCH_LIMIT)))
    except Exception as exc:  # noqa: BLE001 - rede/bloqueio viram erro honesto
        raise _error(f"web fallback failed: {type(exc).__name__}") from exc
    hits: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("href"):
            continue
        hits.append({"url": str(row["href"]),
                     "title": str(row.get("title") or ""),
                     "snippet": str(row.get("body") or "")[:500],
                     "via": "ddgs-fallback"})
    return hits


def _read_work(url: str, *, timeout: float):
    import academic_search  # noqa: PLC0415
    return academic_search.read_work(url, full_text=True, timeout=timeout)


def _read_repo(url: str, *, timeout: float, token: str | None = None):
    import agent_reach  # noqa: PLC0415
    # read_repo não aceita token (usa GITHUB_TOKEN do env); token ignorado.
    return agent_reach.read_repo(url, timeout=timeout)


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


def _academic_hits(result, via: str | None = None) -> list[dict]:
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
        hit = {"url": str(url), "title": str(work.get("title") or ""),
               "snippet": str(work.get("abstract") or "")[:500]}
        if via:
            hit["via"] = via
        hits.append(hit)
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
    payload = {"text": text, "status": qualification, "reason": reason,
               "usable_text": text, "excluded": False}
    # Rastreabilidade R11.6/R10.5: nível de leitura e URL usada viajam com o
    # payload até a qualificação (nunca inventados: só quando presentes).
    for key in ("read_level", "used_url", "title"):
        value = getattr(result, key, None)
        if value:
            payload[key] = value
    metadata = getattr(result, "metadata", {}) or {}
    if isinstance(metadata, dict) and metadata.get("read_level"):
        payload["read_level"] = metadata["read_level"]
    return payload


# Sinais genericos de conteudo (capability, nunca nome de origem): a secao
# de transcricao que o enriquecimento adiciona viaja no snippet (os
# primeiros 500 chars cobrem o cabecalho, que comeca apos ~400 de
# descricao). Dominancia so se julga com pagina cheia o bastante para nao
# ser ruido de amostra pequena; acima da metade, um unico host decide o
# corpus da op sozinho (medido: pagina cheia sem transcricao virava
# boilerplate no fetch e o fallback nunca tentava).
_TRANSCRIPT_MARKERS: tuple[str, ...] = ("[transcript", "[spoken")
_DIVERSITY_MIN_HITS: int = 4
_DIVERSITY_MAX_SHARE: float = 0.5


def _hit_host(url: str) -> str:
    """Host canonico generico (sem www) para agrupar; vazio se irreconhecivel."""
    try:
        host = (urlsplit(str(url or "")).hostname or "").lower()
    except Exception:  # noqa: BLE001 - URL malformada nunca derruba a busca
        return ""
    return host[4:] if host.startswith("www.") else host


def _hit_has_transcript_signal(hit: dict) -> bool:
    """True quando o snippet carrega secao de transcricao (conteudo real)."""
    if not isinstance(hit, dict):
        return False
    text = f"{hit.get('title') or ''}\n{hit.get('snippet') or ''}".lower()
    return any(marker in text for marker in _TRANSCRIPT_MARKERS)


def _needs_diversity(primary: list[dict]) -> bool:
    """Pagina cheia dominada por um host e sem nenhum sinal de transcricao.

    Monopolio sem enriquecimento: o fetch vira boilerplate e o short-circuit
    desperdica a op. Com transcricao (conteudo real) ou corpus ja diverso, o
    primario vence sozinho como antes.
    """
    if len(primary) < _DIVERSITY_MIN_HITS:
        return False
    hosts = [_hit_host(h.get("url")) for h in primary if isinstance(h, dict)]
    hosts = [h for h in hosts if h]
    if not hosts:
        return False
    top = max(hosts.count(h) for h in set(hosts))
    if top / len(hosts) <= _DIVERSITY_MAX_SHARE:
        return False
    return not any(_hit_has_transcript_signal(h) for h in primary
                   if isinstance(h, dict))


def _merge_diverse(primary: list[dict], extras: list[dict],
                   limit: int) -> list[dict]:
    """Mistura priorizando conteudo comprovado e diversidade, sem perder dado.

    Ordem: primario COM transcricao (bom, mantem primeiro), extras diversos,
    primario SEM transcricao de hosts nao-dominantes (usaveis isolados),
    resto dominante por ultimo. Trunca no limite anterior (nunca amplia).
    """
    counts: dict[str, int] = {}
    for h in primary:
        if isinstance(h, dict):
            host = _hit_host(h.get("url"))
            if host:
                counts[host] = counts.get(host, 0) + 1
    dominant = max(counts, key=lambda k: counts[k]) if counts else ""
    seen: set[str] = set()
    out: list[dict] = []

    def push(hit: dict) -> None:
        url = hit.get("url") if isinstance(hit, dict) else None
        if not isinstance(url, str) or not url or url in seen:
            return
        seen.add(url)
        out.append(hit)

    for hit in primary:
        if isinstance(hit, dict) and _hit_has_transcript_signal(hit):
            push(hit)
    for hit in extras:
        if isinstance(hit, dict):
            push(hit)
    for hit in primary:
        if (isinstance(hit, dict) and not _hit_has_transcript_signal(hit)
                and _hit_host(hit.get("url")) != dominant):
            push(hit)
    for hit in primary:
        if (isinstance(hit, dict) and not _hit_has_transcript_signal(hit)
                and _hit_host(hit.get("url")) == dominant):
            push(hit)
    return out[:max(1, int(limit or SEARCH_LIMIT))]


def build_native_transports(*, model_client=None, timeout: float = DEFAULT_TIMEOUT_S,
                            github_token: str | None = None, page_transport=None,
                            academic_search_fn=None, web_search_fn=None,
                            searxng_search_fn=None, web_fallback_fn=None):
    """(search_fn, fetch_fn, model_client) sem gpt_researcher.

    ``describe()`` fica anexado a search_fn/fetch_fn com canais e limites
    efetivos. O canal web usa o gateway local (``agent_reach.search``); se
    ele falhar, tenta o SearXNG autohospedado (``searxng_search_fn``) e por
    fim o fallback ``web_fallback_fn`` (padrão: ddgs, sem chave). Cada etapa
    rotula os hits com ``via`` — origem sempre identificável.
    """
    academic_search_fn = academic_search_fn or _default_academic_search
    web_search_fn = web_search_fn or _default_web_search
    searxng_search_fn = searxng_search_fn or _searxng_search
    web_fallback_fn = web_fallback_fn or _ddgs_fallback_search

    def search_fn(query: str, channel: str = "web") -> list[dict]:
        name = str(channel or "web").lower()
        if name == "academic":
            return _academic_hits(academic_search_fn(
                query, limit=SEARCH_LIMIT, source="both"))
        if name == "arxiv":
            # Coordinator channel for the academic family; native serves it
            # with the arXiv slice of the academic connector. arXiv
            # rate-limits (HTTP 429) while OpenAlex serves the same family,
            # so on arXiv failure we fall back to OpenAlex and label the
            # hits with their real origin (never relabelled as arXiv).
            try:
                return _academic_hits(academic_search_fn(
                    query, limit=SEARCH_LIMIT, source="arxiv"), via="arxiv")
            except Exception as arxiv_exc:
                try:
                    return _academic_hits(academic_search_fn(
                        query, limit=SEARCH_LIMIT, source="openalex"),
                        via="openalex-fallback")
                except Exception as oa_exc:
                    raise _error(
                        "academic search unavailable: arxiv failed "
                        f"({arxiv_exc}); openalex fallback failed ({oa_exc})"
                    ) from oa_exc
        if name == "github":
            return _github_search(query, timeout=timeout, token=github_token)
        if name == "web":
            try:
                primary = _web_hits(web_search_fn(
                    query, limit=SEARCH_LIMIT, channel="web"))
            except Exception as primary_exc:
                try:
                    return searxng_search_fn(query, limit=SEARCH_LIMIT)
                except Exception as searxng_exc:
                    try:
                        return web_fallback_fn(query, limit=SEARCH_LIMIT)
                    except Exception as fallback_exc:
                        raise _error(
                            "web search unavailable: gateway failed "
                            f"({primary_exc}); searxng failed ({searxng_exc}); "
                            f"fallback failed ({fallback_exc})"
                        ) from fallback_exc
            if not _needs_diversity(primary):
                return primary
            # Monopolio de um host sem transcricao: tenta as rotas seguintes
            # na mesma op e mistura por diversidade. Falha nas extras nao
            # perde o primario (devolve o que ja tinha).
            extras: list[dict] = []
            for attempt in (searxng_search_fn, web_fallback_fn):
                try:
                    got = attempt(query, limit=SEARCH_LIMIT) or []
                except Exception:  # noqa: BLE001 - rota honesta que falhou
                    continue
                for hit in got:
                    if isinstance(hit, dict) and hit.get("url"):
                        extras.append(hit)
            if not extras:
                return primary
            return _merge_diverse(primary, extras, SEARCH_LIMIT)
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
            result = _read_repo(target, timeout=timeout)
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
                "web": ("agent_reach.search (gateway local) "
                        "-> searxng autohospedado (SEARXNG_URL, hits com "
                        "via/engine) -> fallback ddgs sem chave"),
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
