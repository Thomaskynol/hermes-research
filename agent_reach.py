#!/usr/bin/env python3
"""Agent Reach — operações individuais de acesso, sem iniciar pesquisa coordenada.

Uma pergunta como "leia esta página", "resuma este vídeo" ou "examine este
repositório" é resolvida aqui, com conteúdo, origem, limitações e estado de
obtenção. O Deep Researcher consome este mesmo contrato (`ReachResult`), então
uma correção de leitura/transcrição beneficia as duas ferramentas.

REAPROVEITAMENTO (não duplicar extração)
----------------------------------------
- busca: gateway local do `vast_local_retriever` (RETRIEVER_ENDPOINT, default
  http://127.0.0.1:8001/), o mesmo contrato que o Deep Researcher já consome;
- página: o mesmo `cascade_fetcher.fetch` que o `vast_local_retriever` usa
  (trafilatura, bs4, navegador — a cascata real, sem cópia); importado direto
  para não disparar o `load_github_token()` que o import do vast executa;
- repositório: `repo_readme.fetch_repo_readme` (README/blob pelo caminho raw) +
  API pública do GitHub para metadados/releases/arquivos;
- vídeo: `youtube_transcript.fetch_transcript` (legenda do autor ou automática,
  com cache); nunca ASR local;
- acadêmico: `academic_search.py` (OpenAlex + arXiv, sem chave).

HONESTIDADE
-----------
Nada aqui inventa resultado. Serviço fora → `ok=False`, `status="failed"`,
`reason="retriever_unavailable"` e `limits`; página sem conteúdo → `insufficient`;
transcrição ausente ≠ falha de acesso (`absent` vs `blocked`); `http_status` só é
preenchido quando o status foi realmente observado.

Uso:
    python agent_reach.py search "consulta" --limit 5 --json
    python agent_reach.py read-page https://exemplo.org/doc --json
    python agent_reach.py read-repo https://github.com/owner/repo --json
    python agent_reach.py read-video https://www.youtube.com/watch?v=... --lang en
    python agent_reach.py academic-search "retrieval augmented generation" --source both
    python agent_reach.py read-work 10.1038/nature12373 --full-text

Exit: 0 quando `ok` é True (obtained/partial), 1 quando não foi possível obter,
2 para uso inválido (argparse).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html as _html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Final
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

# Raiz do worktree: imports dos conectores reais resolvem daqui.
ROOT: Final[Path] = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

USER_AGENT: Final[str] = "agent-reach/1.0"
DEFAULT_ENDPOINT: Final[str] = "http://127.0.0.1:8001/"
# Mesmo diretório que o vast_local_retriever usa para achar o cascade_fetcher.
CASCADE_DIR: Final[Path] = Path("/opt/data/scripts")
DEFAULT_TIMEOUT_S: Final[float] = 20.0
MAX_BODY_BYTES: Final[int] = 30 * 1024 * 1024
SEARCH_SNIPPET_CHARS: Final[int] = 500

# Mesmo piso da cascata (cascade_fetcher.MIN_CHARS=500): abaixo disso o texto
# não é uma leitura utilizável, é captura curta/parcial.
USABLE_MIN_CHARS: Final[int] = 500
# Marcadores de anti-bot só valem em páginas curtas: um artigo que discute
# captcha não é uma página de bloqueio.
ANTIBOT_WINDOW: Final[int] = 2000

STATUS_OBTAINED: Final[str] = "obtained"
STATUS_PARTIAL: Final[str] = "partial"
STATUS_UNAVAILABLE: Final[str] = "unavailable"
STATUS_FAILED: Final[str] = "failed"
STATUSES: Final[frozenset[str]] = frozenset(
    {STATUS_OBTAINED, STATUS_PARTIAL, STATUS_UNAVAILABLE, STATUS_FAILED}
)

QUAL_USABLE: Final[str] = "usable"
QUAL_PARTIAL: Final[str] = "partial"
QUAL_INSUFFICIENT: Final[str] = "insufficient"
QUAL_METADATA: Final[str] = "metadata_only"
QUAL_NONE: Final[str] = "none"
QUALIFICATIONS: Final[frozenset[str]] = frozenset(
    {QUAL_USABLE, QUAL_PARTIAL, QUAL_INSUFFICIENT, QUAL_METADATA, QUAL_NONE}
)

SEARCH_CHANNELS: Final[dict[str, frozenset[str]]] = {
    "web": frozenset({"github", "github-code", "youtube", "bilibili", "v2ex", "arxiv"}),
    "github": frozenset({"github", "github-code"}),
    "youtube": frozenset({"youtube"}),
}

# (url, timeout) -> {"status": int|None, "text": str, "error": str|None, ...}
Transport = Callable[[str, float], dict[str, Any]]
# (url, lang, timeout) -> payload de transcrição (ver read_video).
VideoTransport = Callable[[str, str, float], dict[str, Any]]

_ANTIBOT_RE: Final[re.Pattern[str]] = re.compile(
    r"(enable javascript|javascript is disabled|access denied|are you a robot|"
    r"captcha|cloudflare|checking your browser|too many requests|403 forbidden|"
    r"attention required|request blocked|unusual traffic)"
)
_HTML_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<(?:html|body|div|p|main|article)\b", re.I)
_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")


def _utc_now() -> str:
    """Instante UTC em ISO-8601 com Z (o mesmo formato do resto da stack)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(slots=True)
class ReachResult:
    """Resultado de UMA operação do Agent Reach.

    `ok` é True para obtained/partial (houve material verificável) e False para
    unavailable/failed. `http_status` só existe quando o status foi observado;
    None é "não observado", nunca "200 assumido". `text` contém apenas conteúdo
    lido de verdade: metadados/abstract ficam em `metadata`, e nunca preenchem
    `text` no lugar de uma leitura que não aconteceu.
    """

    ok: bool
    operation: str
    target: str
    title: str = ""
    text: str = ""
    chars: int = 0
    channel: str = ""
    obtained_at: str = field(default_factory=_utc_now)
    status: str = STATUS_FAILED
    qualification: str = QUAL_NONE
    reason: str | None = None
    http_status: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    limits: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Contrato serializável (JSON) consumido pelo Deep Researcher."""
        return {
            "ok": self.ok,
            "operation": self.operation,
            "target": self.target,
            "title": self.title,
            "text": self.text,
            "chars": self.chars,
            "channel": self.channel,
            "obtained_at": self.obtained_at,
            "status": self.status,
            "qualification": self.qualification,
            "reason": self.reason,
            "http_status": self.http_status,
            "metadata": self.metadata,
            "limits": list(self.limits),
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Construção do contrato
# ---------------------------------------------------------------------------


def _hash(text: str) -> str | None:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None


def _excerpt(text: str, limit: int = 280) -> str:
    return " ".join(text.split())[:limit]


def _evidence(
    url: str,
    text: str,
    *,
    urls: list[str] | None = None,
    read_scope: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Procedência mínima: URL(s), hash, trecho e alcance efetivamente lido."""
    evidence: dict[str, Any] = {
        "url": url,
        "urls": list(dict.fromkeys([u for u in (urls or [url]) if u])),
        "sha256": _hash(text),
        "chars": len(text),
        "excerpt": _excerpt(text),
    }
    if read_scope:
        evidence["read_scope"] = read_scope
    if extra:
        evidence.update(extra)
    return evidence


def _make(
    operation: str,
    target: str,
    *,
    channel: str,
    status: str,
    qualification: str,
    text: str = "",
    title: str = "",
    reason: str | None = None,
    http_status: int | None = None,
    metadata: dict[str, Any] | None = None,
    limits: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> ReachResult:
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status!r}")
    if qualification not in QUALIFICATIONS:
        raise ValueError(f"qualification inválida: {qualification!r}")
    return ReachResult(
        ok=status in (STATUS_OBTAINED, STATUS_PARTIAL),
        operation=operation,
        target=target,
        title=title,
        text=text,
        chars=len(text),
        channel=channel,
        status=status,
        qualification=qualification,
        reason=reason,
        http_status=http_status if isinstance(http_status, int) else None,
        metadata=metadata or {},
        limits=list(limits or []),
        evidence=evidence or {},
    )


def _fail(
    operation: str,
    target: str,
    *,
    channel: str,
    reason: str,
    status: str = STATUS_FAILED,
    qualification: str = QUAL_NONE,
    metadata: dict[str, Any] | None = None,
    limits: list[str] | None = None,
    http_status: int | None = None,
) -> ReachResult:
    return _make(
        operation, target, channel=channel, status=status,
        qualification=qualification, reason=reason, http_status=http_status,
        metadata=metadata, limits=limits,
    )


# ---------------------------------------------------------------------------
# HTTP (stdlib): nenhuma dependência nova, token só do ambiente
# ---------------------------------------------------------------------------


def _http_get(
    url: str,
    timeout: float,
    *,
    headers: dict[str, str] | None = None,
    binary: bool = False,
) -> dict[str, Any]:
    """GET com resultado sempre em dict; erro esperado vira `error`, não exceção."""
    request = Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_BODY_BYTES)
            payload: dict[str, Any] = {
                "status": response.status,
                "url": response.geturl(),
                "error": None,
            }
            if binary:
                payload["body"] = body
                payload["text"] = ""
            else:
                charset = response.headers.get_content_charset() or "utf-8"
                payload["text"] = body.decode(charset, "replace")
            return payload
    except HTTPError as exc:
        try:
            body = exc.read(MAX_BODY_BYTES)
            charset = exc.headers.get_content_charset() if exc.headers else None
            text = body.decode(charset or "utf-8", "replace")
        except Exception:  # noqa: BLE001 - corpo de erro é opcional
            text = ""
        return {"status": exc.code, "url": url, "text": text,
                "error": f"HTTP {exc.code}"}
    except Exception as exc:  # noqa: BLE001 - rede/DNS/timeout nunca derrubam a operação
        return {"status": None, "url": url, "text": "",
                "error": f"{type(exc).__name__}: {exc}"}


def _endpoint() -> str:
    return (os.environ.get("RETRIEVER_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/") + "/"


def _json_or_none(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _github_token() -> str:
    """Token somente do ambiente já exportado; nunca lê .env nem loga o valor."""
    return os.environ.get("GITHUB_TOKEN", "")


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ---------------------------------------------------------------------------
# 1. Busca — gateway local do vast (mesmo contrato do Deep Researcher)
# ---------------------------------------------------------------------------


def search(
    query: str,
    *,
    limit: int = 10,
    channel: str = "web",
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: Transport | None = None,
) -> ReachResult:
    """Busca identificada, sem leitura de página.

    Reusa o gateway local do `vast_local_retriever`: o endpoint é o mesmo que o
    GPT Researcher/Deep Researcher consultam, e é ele quem executa
    `search_all` + `_select_hits` + `enrich_results`. Aqui só se devolve o que o
    gateway respondeu — nada é fabricado quando ele está fora.
    """
    query = " ".join(str(query or "").split())
    if not query:
        return _fail("search", query, channel=channel, reason="empty_query")
    if channel not in SEARCH_CHANNELS:
        return _fail(
            "search", query, channel=channel, reason="unsupported_channel",
            metadata={"supported_channels": sorted(SEARCH_CHANNELS)},
        )
    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        return _fail("search", query, channel=channel, reason="invalid_limit")

    endpoint = _endpoint()
    url = f"{endpoint}?{urlencode({'query': query, 'max_results': limit})}"
    fetch = transport or _http_get
    try:
        payload = fetch(url, timeout)
    except Exception as exc:  # noqa: BLE001 - transporte injetado não derruba a operação
        payload = {"status": None, "text": "", "error": f"{type(exc).__name__}: {exc}"}

    status_code = payload.get("status") if isinstance(payload.get("status"), int) else None
    text = payload.get("text") or ""
    if payload.get("error") and not text:
        return _fail(
            "search", query, channel=channel, reason="retriever_unavailable",
            metadata={"endpoint": endpoint, "error": str(payload.get("error")),
                      "results": []},
            limits=[f"limit={limit}", "no_page_read", "gateway_local_only"],
        )
    if status_code is not None and status_code >= 400:
        return _fail(
            "search", query, channel=channel,
            reason=f"retriever_http_{status_code}", http_status=status_code,
            metadata={"endpoint": endpoint},
            limits=[f"limit={limit}", "no_page_read", "gateway_local_only"],
        )

    data = _json_or_none(text)
    if data is None:
        return _fail(
            "search", query, channel=channel, reason="retriever_invalid_json",
            http_status=status_code, metadata={"endpoint": endpoint},
            limits=[f"limit={limit}", "no_page_read", "gateway_local_only"],
        )
    items = data.get("results", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return _fail(
            "search", query, channel=channel, reason="retriever_invalid_payload",
            http_status=status_code, metadata={"endpoint": endpoint},
        )

    allowed = SEARCH_CHANNELS[channel]
    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        source = item.get("source") or ""
        if channel != "web" and source not in allowed:
            continue
        content = item.get("raw_content") or item.get("content") or ""
        entry: dict[str, Any] = {
            "url": str(item["url"]),
            "title": str(item.get("title") or ""),
            "snippet": str(content)[:SEARCH_SNIPPET_CHARS],
        }
        if source:
            entry["engine"] = str(source)
        if content:
            entry["content_chars"] = len(str(content))
        results.append(entry)

    metadata = {
        "endpoint": endpoint,
        "query": query,
        "requested_limit": limit,
        "returned_count": len(results),
        "results": results,
    }
    limits = [f"limit={limit}", "snippet_only_no_page_read", "gateway_local_only"]
    if not results:
        return _fail(
            "search", query, channel=channel, reason="no_results",
            status=STATUS_UNAVAILABLE, qualification=QUAL_NONE,
            http_status=status_code, metadata=metadata, limits=limits,
        )
    return _make(
        "search", query, channel=channel, status=STATUS_OBTAINED,
        qualification=QUAL_METADATA, http_status=status_code, metadata=metadata,
        limits=limits,
        evidence=_evidence(
            url, "", urls=[entry["url"] for entry in results],
            read_scope="search_results_only",
            extra={"count": len(results)},
        ),
    )


# ---------------------------------------------------------------------------
# 2. Página — cascata real do vast_local_retriever
# ---------------------------------------------------------------------------


def _cascade_read(url: str, timeout: float) -> dict[str, Any]:
    """Transporte padrão: o mesmo `cascade_fetcher.fetch` que o vast usa.

    Importado direto do diretório da cascata, e não via
    `vast_local_retriever.load_cascade()`: o import do vast executa
    `load_github_token()` no topo do módulo, que lê `/opt/data/.env`. Uma
    operação de leitura de página não deve carregar credencial de produção como
    efeito colateral. A lógica de extração é exatamente a mesma (`fetch`), sem
    cópia.
    """
    try:
        if str(CASCADE_DIR) not in sys.path:
            sys.path.insert(0, str(CASCADE_DIR))
        from cascade_fetcher import fetch
    except Exception as exc:  # noqa: BLE001 - dependência opcional ausente
        return _direct_read(url, timeout,
                            f"cascade_unavailable: {type(exc).__name__}: {exc}")

    async def _run() -> Any:
        return await asyncio.wait_for(fetch(url), timeout=timeout)

    try:
        result = asyncio.run(_run())
    except (TimeoutError, asyncio.TimeoutError):
        return {"status": None, "text": "", "level": 0, "from_cache": False,
                "error": f"timeout_{timeout:g}s"}
    except Exception as exc:  # noqa: BLE001 - contrato: nunca propagar falha esperada
        return {"status": None, "text": "", "level": 0, "from_cache": False,
                "error": f"{type(exc).__name__}: {exc}"}
    return {
        "status": None,  # a cascata não observa o status HTTP
        "text": getattr(result, "text", "") or "",
        "level": getattr(result, "level", 0),
        "from_cache": bool(getattr(result, "from_cache", False)),
        "reason": getattr(result, "reason", None),
        "url": getattr(result, "url", url),
        "error": None,
    }


def _direct_read(url: str, timeout: float, why: str) -> dict[str, Any]:
    """Fallback stdlib (urllib) quando a cascata local está indisponível.

    Sem dependências novas e sem serviço pago: requisição direta com
    User-Agent, limite de 300 KB, charset do cabeçalho ou utf-8. O status
    HTTP é observado de verdade (respeita R10: só registra o observado).
    Falha preserva o motivo da cascata + o motivo direto.
    """
    try:
        req = Request(url, headers={"User-Agent": "hermes-research/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None)
            raw = resp.read(300 * 1024)
            ctype = (resp.headers.get_content_charset()
                     if hasattr(resp.headers, "get_content_charset") else None)
            text = raw.decode(ctype or "utf-8", errors="replace")
        if not text.strip():
            return {"status": None, "text": "", "level": 0, "from_cache": False,
                    "error": f"{why}; direct_empty (http {status})",
                    "http_status": status}
        return {"status": None, "text": text, "level": 1, "from_cache": False,
                "reason": f"direct_read ({why})", "url": url, "error": None,
                "http_status": status}
    except Exception as exc:  # noqa: BLE001
        return {"status": None, "text": "", "level": 0, "from_cache": False,
                "error": f"{why}; direct_failed: {type(exc).__name__}: {exc}"}


def _visible_text(raw: str) -> str:
    """Texto visível de um HTML, sem script/style; HTML já extraído passa igual."""
    without_scripts = _SCRIPT_RE.sub(" ", raw)
    return _html.unescape(_TAG_RE.sub(" ", without_scripts))


def _classify_page(text: str) -> tuple[str, str, str | None]:
    """(status, qualification, reason) de uma captura de página."""
    stripped = text.strip()
    if not stripped:
        return STATUS_UNAVAILABLE, QUAL_INSUFFICIENT, "empty_content"
    visible = _visible_text(stripped) if _HTML_TAG_RE.search(stripped) else stripped
    visible = " ".join(visible.split())
    if _HTML_TAG_RE.search(stripped) and len(visible) < 200:
        return STATUS_UNAVAILABLE, QUAL_INSUFFICIENT, "html_without_content"
    if len(stripped) < ANTIBOT_WINDOW and _ANTIBOT_RE.search(visible.lower()):
        return STATUS_UNAVAILABLE, QUAL_INSUFFICIENT, "anti_bot_page"
    if len(stripped) < USABLE_MIN_CHARS:
        return STATUS_PARTIAL, QUAL_PARTIAL, "short_capture"
    return STATUS_OBTAINED, QUAL_USABLE, None


def read_page(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: Transport | None = None,
) -> ReachResult:
    """Lê uma página/documento pela cascata local e qualifica o que foi obtido."""
    url = str(url or "").strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return _fail("read_page", url, channel="web", reason="invalid_url")

    fetch = transport or _cascade_read
    try:
        payload = fetch(url, timeout)
    except Exception as exc:  # noqa: BLE001
        payload = {"status": None, "text": "", "error": f"{type(exc).__name__}: {exc}"}

    http_status = payload.get("http_status")
    if payload.get("error") and not (payload.get("text") or "").strip():
        return _fail("read_page", url, channel="web", reason=str(payload["error"]),
                     http_status=http_status,
                     metadata={"final_url": payload.get("url", url)},
                     limits=["cascade_local_only"])

    text = payload.get("text") or ""
    level = payload.get("level")
    if level == 0 and not text.strip():
        return _fail(
            "read_page", url, channel="web",
            reason=str(payload.get("reason") or "nothing_read"),
            status=STATUS_UNAVAILABLE, qualification=QUAL_INSUFFICIENT,
            http_status=http_status,
            metadata={"extraction_level": level, "final_url": payload.get("url", url)},
            limits=["cascade_local_only"],
        )

    status, qualification, reason = _classify_page(text)
    if payload.get("reason") and reason is None:
        reason = str(payload["reason"])

    metadata: dict[str, Any] = {"final_url": payload.get("url", url)}
    if isinstance(level, int):
        metadata["extraction_level"] = level
    if "from_cache" in payload:
        metadata["from_cache"] = bool(payload["from_cache"])
    limits = ["cascade_local_only"]
    if isinstance(level, int) and level == 3:
        limits.append("browser_level_text_may_include_navigation_chrome")
    if status == STATUS_PARTIAL:
        limits.append(f"capture_below_{USABLE_MIN_CHARS}_chars")
    if payload.get("from_cache"):
        limits.append("served_from_local_cache")

    return _make(
        "read_page", url, channel="web", status=status, qualification=qualification,
        text=text if status != STATUS_UNAVAILABLE else "",
        reason=reason, http_status=http_status, metadata=metadata, limits=limits,
        evidence=_evidence(
            url, text, urls=[str(payload.get("url") or url)],
            read_scope=f"cascade_level_{level}" if isinstance(level, int) else "cascade",
            extra={"extraction_level": level} if isinstance(level, int) else None,
        ),
    )


# ---------------------------------------------------------------------------
# 3. Repositório — README raw + API pública do GitHub
# ---------------------------------------------------------------------------

_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _github_parts(url: str) -> tuple[str, str] | None:
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1].removesuffix(".git")
    if not _NAME_RE.match(owner) or not _NAME_RE.match(repo):
        return None
    return owner, repo


def _github_bundle(url: str, timeout: float) -> dict[str, Any]:
    """Transporte padrão: README (repo_readme) + repo/releases/contents (API)."""
    bundle: dict[str, Any] = {"readme": None, "repo": None,
                              "releases": None, "files": None}
    try:
        import repo_readme
        readme = asyncio.run(repo_readme.fetch_repo_readme(url, timeout=timeout))
        bundle["readme"] = {
            "text": readme.text, "chars": readme.chars,
            "http_status": readme.http_status, "source_url": readme.source_url,
            "reason": readme.reason,
        }
    except Exception as exc:  # noqa: BLE001 - README é um caminho, não a operação toda
        bundle["readme"] = {"text": "", "chars": 0, "http_status": None,
                            "source_url": None,
                            "reason": f"readme_error: {type(exc).__name__}: {exc}"}

    parts = _github_parts(url)
    if parts is None:
        return bundle
    owner, repo = parts
    api = f"https://api.github.com/repos/{owner}/{repo}"
    bundle["repo"] = _http_get(api, timeout, headers=_github_headers())
    bundle["releases"] = _http_get(
        f"{api}/releases?per_page=1", timeout, headers=_github_headers())
    bundle["files"] = _http_get(
        f"{api}/contents/", timeout, headers=_github_headers())
    return bundle


def _release_metadata(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    data = _json_or_none((payload or {}).get("text") or "")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return None
    release = data[0]
    return {
        "tag": release.get("tag_name"),
        "name": release.get("name"),
        "published_at": release.get("published_at"),
        "url": release.get("html_url"),
    }


def read_repo(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: Transport | None = None,
) -> ReachResult:
    """README/blob do repositório + metadados, releases e arquivos observados."""
    url = str(url or "").strip()
    parts = _github_parts(url)
    if parts is None:
        return _fail("read_repo", url, channel="github", reason="not_a_github_repo")
    # A mesma barreira do repo_readme: recusa subpágina que não é repo nem blob
    # (ex.: /owner/repo/issues/3) em vez de tratar a página como repositório.
    try:
        import repo_readme
        if repo_readme.raw_readme_url(url) is None:
            return _fail("read_repo", url, channel="github",
                         reason="not_a_github_repo")
    except Exception:  # noqa: BLE001 - sem o módulo, a checagem de nome acima basta
        pass
    owner, repo = parts

    fetch = transport or _github_bundle
    try:
        bundle = fetch(url, timeout)
    except Exception as exc:  # noqa: BLE001
        return _fail("read_repo", url, channel="github",
                     reason=f"github_error: {type(exc).__name__}: {exc}")

    readme = bundle.get("readme") or {}
    repo_payload = bundle.get("repo") or {}
    repo_json = _json_or_none(repo_payload.get("text") or "")
    repo_json = repo_json if isinstance(repo_json, dict) else None
    repo_status = repo_payload.get("status") if isinstance(repo_payload.get("status"), int) else None

    metadata: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "api_authenticated": bool(_github_token()),
    }
    if readme.get("source_url"):
        metadata["readme_source_url"] = readme["source_url"]
    if isinstance(readme.get("http_status"), int):
        metadata["readme_http_status"] = readme["http_status"]
    if repo_json:
        metadata["full_name"] = repo_json.get("full_name")
        metadata["description"] = repo_json.get("description")
        metadata["default_branch"] = repo_json.get("default_branch")
        metadata["stars"] = repo_json.get("stargazers_count")
        metadata["language"] = repo_json.get("language")
        license_info = repo_json.get("license") or {}
        metadata["license"] = (
            license_info.get("spdx_id") or license_info.get("name")
            if isinstance(license_info, dict) else None
        )
        metadata["pushed_at"] = repo_json.get("pushed_at")
    release = _release_metadata(bundle.get("releases"))
    if release:
        metadata["latest_release"] = release
    files_payload = bundle.get("files") or {}
    files_json = _json_or_none(files_payload.get("text") or "")
    if isinstance(files_json, list):
        metadata["files"] = [entry.get("name") for entry in files_json
                             if isinstance(entry, dict) and entry.get("name")]

    limits: list[str] = []
    if not _github_token():
        limits.append("github_api_unauthenticated_60_requests_per_hour")
    title = str(metadata.get("full_name") or f"{owner}/{repo}")
    readme_text = readme.get("text") or ""

    if readme_text.strip():
        return _make(
            "read_repo", url, channel="github", status=STATUS_OBTAINED,
            qualification=QUAL_USABLE, text=readme_text, title=title,
            http_status=readme.get("http_status"), metadata=metadata,
            limits=limits,
            evidence=_evidence(
                url, readme_text,
                urls=[readme.get("source_url") or url],
                read_scope="readme_raw",
                extra={"repo": f"{owner}/{repo}"},
            ),
        )

    readme_reason = str(readme.get("reason") or "readme_absent")
    readme_http = readme.get("http_status") if isinstance(readme.get("http_status"), int) else None
    if readme_http is not None:
        limits.append(f"readme_{readme_reason[:120]}")
    if repo_json:
        return _make(
            "read_repo", url, channel="github", status=STATUS_PARTIAL,
            qualification=QUAL_METADATA, title=title, reason=readme_reason,
            http_status=readme_http, metadata=metadata, limits=limits,
            evidence=_evidence(
                url, "", urls=[url], read_scope="metadata_only",
                extra={"repo": f"{owner}/{repo}"},
            ),
        )
    if repo_status == 404 or readme_http == 404:
        return _fail(
            "read_repo", url, channel="github", reason="repo_not_found",
            status=STATUS_UNAVAILABLE, qualification=QUAL_INSUFFICIENT,
            http_status=404, metadata=metadata, limits=limits,
        )
    return _fail(
        "read_repo", url, channel="github",
        reason=str(repo_payload.get("error") or readme_reason),
        http_status=repo_status, metadata=metadata, limits=limits,
    )


# ---------------------------------------------------------------------------
# 4. Vídeo — youtube_transcript (legenda do autor/automática; nunca ASR)
# ---------------------------------------------------------------------------


def _transcript_read(url: str, lang: str, timeout: float) -> dict[str, Any]:
    """Transporte padrão: `youtube_transcript.fetch_transcript`."""
    try:
        import youtube_transcript as yt
    except Exception as exc:  # noqa: BLE001
        return {"text": "", "lang": lang, "chars": 0, "segments": 0,
                "method": "none", "automatic": None,
                "reason": f"transcript_unavailable: {type(exc).__name__}: {exc}"}
    try:
        result = asyncio.run(yt.fetch_transcript(url, lang=lang, timeout=timeout))
    except Exception as exc:  # noqa: BLE001
        return {"text": "", "lang": lang, "chars": 0, "segments": 0,
                "method": "none", "automatic": None,
                "reason": f"{type(exc).__name__}: {exc}"}
    return {
        "text": result.text, "lang": result.lang, "chars": result.chars,
        "segments": result.segments, "method": result.method,
        "automatic": result.automatic, "reason": result.reason,
    }


def _video_reason(reason: str) -> str:
    """Traduz o motivo do transcript para {absent, blocked, disabled}."""
    low = reason.lower()
    if "disabled" in low or "desativad" in low:
        return "disabled"
    if (
        "nao produziu legenda" in low
        or "não produziu legenda" in low
        or "sem texto" in low
        or "no subtitle" in low
        or "subtitles are not available" in low
    ):
        return "absent"
    return "blocked"


def read_video(
    url: str,
    *,
    lang: str = "en",
    timeout: float = 30.0,
    transport: VideoTransport | None = None,
) -> ReachResult:
    """Transcrição disponível do vídeo; título/descrição nunca viram fala."""
    url = str(url or "").strip()
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return _fail("read_video", url, channel="youtube", reason="invalid_url")

    fetch = transport or _transcript_read
    try:
        payload = fetch(url, lang, timeout)
    except Exception as exc:  # noqa: BLE001
        payload = {"text": "", "reason": f"{type(exc).__name__}: {exc}"}

    text = str(payload.get("text") or "")
    automatic = payload.get("automatic")
    metadata: dict[str, Any] = {
        "lang": payload.get("lang") or lang,
        "automatic": automatic if isinstance(automatic, bool) else None,
        "source": ("author" if automatic is False
                   else "auto" if automatic is True else "unknown"),
        "segments": payload.get("segments"),
        "method": payload.get("method"),
        "obtained_at": _utc_now(),
        "first_timestamp": payload.get("first_timestamp"),
        "last_timestamp": payload.get("last_timestamp"),
    }
    if payload.get("title"):
        metadata["title"] = payload["title"]
    if payload.get("description"):
        metadata["description"] = payload["description"]
    limits = ["no_asr_or_visual_analysis"]
    if metadata["first_timestamp"] is None or metadata["last_timestamp"] is None:
        limits.append("timestamps_unavailable_from_transcript_source")

    if text.strip():
        return _make(
            "read_video", url, channel="youtube", status=STATUS_OBTAINED,
            qualification=QUAL_USABLE, text=text,
            title=str(payload.get("title") or ""), metadata=metadata,
            limits=limits,
            evidence=_evidence(
                url, text, read_scope="transcript",
                extra={"segments": payload.get("segments"),
                       "lang": metadata["lang"],
                       "source": metadata["source"]},
            ),
        )

    raw_reason = str(payload.get("reason") or "transcript_absent")
    reason = _video_reason(raw_reason)
    metadata["detail_reason"] = raw_reason
    qualification = QUAL_METADATA if payload.get("title") else QUAL_NONE
    return _make(
        "read_video", url, channel="youtube", status=STATUS_UNAVAILABLE,
        qualification=qualification, title=str(payload.get("title") or ""),
        reason=reason, metadata=metadata, limits=limits,
        evidence=_evidence(url, "", read_scope="no_transcript",
                           extra={"reason_detail": raw_reason}),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_output(result: ReachResult, output_dir: str) -> str:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(result.target.encode("utf-8")).hexdigest()[:8]
    path = directory / f"{result.operation}-{stamp}-{digest}.json"
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return str(path)


def _print_human(result: ReachResult) -> None:
    print(f"{result.operation}  {result.status}/{result.qualification}  "
          f"{result.chars} chars  {result.channel}")
    print(f"target: {result.target}")
    if result.title:
        print(f"title: {result.title}")
    if result.reason:
        print(f"reason: {result.reason}")
    for limit in result.limits:
        print(f"limit: {limit}")
    for index, item in enumerate(result.metadata.get("results") or [], 1):
        print(f"{index}. {item.get('title', '')}  {item.get('url', '')}")
    for index, work in enumerate(result.metadata.get("works") or [], 1):
        print(f"{index}. {work.get('title', '')}  ({work.get('year')})  {work.get('id', '')}")
    if result.text:
        print()
        print(result.text)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="saída JSON do contrato")
    parser.add_argument("--output-dir", default=None,
                        help="diretório onde o JSON do resultado é gravado")
    parser.add_argument("--timeout", type=float, default=None,
                        help="timeout da operação em segundos")


def _timeout(args: argparse.Namespace, default: float) -> float:
    return default if args.timeout is None else max(1.0, float(args.timeout))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agent Reach: operações individuais de acesso (sem iniciar pesquisa).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="busca identificada (gateway local)")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--channel", default="web", choices=sorted(SEARCH_CHANNELS))
    _add_common(p_search)

    p_page = sub.add_parser("read-page", help="lê uma página/documento")
    p_page.add_argument("url")
    _add_common(p_page)

    p_repo = sub.add_parser("read-repo", help="README/metadados de um repositório")
    p_repo.add_argument("url")
    _add_common(p_repo)

    p_video = sub.add_parser("read-video", help="transcrição disponível de um vídeo")
    p_video.add_argument("url")
    p_video.add_argument("--lang", default="en")
    _add_common(p_video)

    p_academic = sub.add_parser("academic-search", help="busca acadêmica (OpenAlex/arXiv)")
    p_academic.add_argument("query")
    p_academic.add_argument("--limit", type=int, default=10)
    p_academic.add_argument("--source", default="openalex",
                            choices=["openalex", "arxiv", "both"])
    _add_common(p_academic)

    p_work = sub.add_parser("read-work", help="metadados/resumo/texto de um trabalho")
    p_work.add_argument("identifier", help="DOI, OpenAlex ID (W...) ou arXiv ID")
    p_work.add_argument("--full-text", action="store_true")
    _add_common(p_work)
    return parser


def _run(args: argparse.Namespace) -> ReachResult:
    if args.command == "search":
        return search(args.query, limit=args.limit, channel=args.channel,
                      timeout=_timeout(args, DEFAULT_TIMEOUT_S))
    if args.command == "read-page":
        return read_page(args.url, timeout=_timeout(args, DEFAULT_TIMEOUT_S))
    if args.command == "read-repo":
        return read_repo(args.url, timeout=_timeout(args, DEFAULT_TIMEOUT_S))
    if args.command == "read-video":
        return read_video(args.url, lang=args.lang, timeout=_timeout(args, 30.0))
    if args.command == "academic-search":
        import academic_search
        return academic_search.search_works(
            args.query, limit=args.limit, source=args.source,
            timeout=_timeout(args, DEFAULT_TIMEOUT_S))
    if args.command == "read-work":
        import academic_search
        return academic_search.read_work(
            args.identifier, full_text=args.full_text,
            timeout=_timeout(args, DEFAULT_TIMEOUT_S))
    raise SystemExit(f"comando desconhecido: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit precisa ser >= 1")
    result = _run(args)
    if args.output_dir:
        path = _write_output(result, args.output_dir)
        print(f"json: {path}", file=sys.stderr)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
