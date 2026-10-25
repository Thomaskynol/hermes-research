#!/usr/bin/env python3
"""Busca e leitura acadêmica sem chave: OpenAlex e arXiv.

Cliente próprio, sem dependência nova e sem credencial. OpenAlex responde JSON
(`https://api.openalex.org/works?search=...`); arXiv responde Atom XML
(`https://export.arxiv.org/api/query?...`), parseado com `xml.etree`.

Regras:
- metadados, resumo (abstract) e texto completo são níveis distintos
  (`read_level` ∈ {metadata, abstract, full_text}); nunca se apresenta um como
  o outro;
- texto completo só é tentado em local gratuito e acessível (arXiv HTML/PDF ou
  localização OA do OpenAlex); nunca há acesso pago, proxy ou chave;
- falha de uma fonte em `source="both"` não apaga a outra: o resultado fica
  `partial` com a fonte que falhou registrada em `metadata["sources_failed"]`.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Final
from urllib.parse import quote, urlencode

from agent_reach import (
    DEFAULT_TIMEOUT_S,
    QUAL_METADATA,
    QUAL_NONE,
    QUAL_PARTIAL,
    QUAL_USABLE,
    STATUS_FAILED,
    STATUS_OBTAINED,
    STATUS_PARTIAL,
    STATUS_UNAVAILABLE,
    ReachResult,
    Transport,
    _evidence,
    _fail,
    _http_get,
    _json_or_none,
    _make,
    _utc_now,
)

OPENALEX_API: Final[str] = "https://api.openalex.org/works"
ARXIV_API: Final[str] = "https://export.arxiv.org/api/query"
ARXIV_HTML: Final[str] = "https://arxiv.org/html"
ARXIV_PDF: Final[str] = "https://arxiv.org/pdf"
SOURCES: Final[tuple[str, ...]] = ("openalex", "arxiv", "both")
READ_LEVELS: Final[tuple[str, ...]] = ("metadata", "abstract", "full_text")
# Mesmo piso da leitura de página: abaixo disso o "texto completo" é captura
# curta/parcial, não documento.
FULLTEXT_MIN_CHARS: Final[int] = 500

_DOI_RE: Final[re.Pattern[str]] = re.compile(r"^10\.\d{4,9}/\S+$")
_OPENALEX_RE: Final[re.Pattern[str]] = re.compile(r"^[Ww]\d+$")
_ARXIV_NEW_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$")
_ARXIV_OLD_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z-]*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?$")
# Página de erro do arXiv ("No HTML for ...") tem mais de 500 chars e passaria
# como texto completo se não fosse nomeada. Só vale em página curta.
_ERROR_PAGE_RE: Final[re.Pattern[str]] = re.compile(
    r"(no html for|html is not available|page not found|404 not found|error 404)",
    re.I)

_ATOM: Final[str] = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS: Final[str] = "{http://arxiv.org/schemas/atom}"


# ---------------------------------------------------------------------------
# Identificadores
# ---------------------------------------------------------------------------


def classify_identifier(identifier: str) -> tuple[str, str] | None:
    """Classifica DOI / OpenAlex ID / arXiv ID, aceitando as formas com URL."""
    value = " ".join(str(identifier or "").split())
    if not value:
        return None
    lowered = value.lower()
    if lowered.startswith("doi:"):
        value = value[4:].strip()
        return ("doi", value) if _DOI_RE.match(value) else None
    if lowered.startswith(("arxiv:", "arxiv ")):
        value = value.split(":", 1)[1].strip()
        return ("arxiv", value) if _is_arxiv_id(value) else None
    if lowered.startswith(("http://", "https://")):
        from urllib.parse import urlsplit

        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
        path = parts.path.strip("/")
        if host.endswith("doi.org") and path:
            return ("doi", path) if _DOI_RE.match(path) else None
        if host.endswith("arxiv.org") and path:
            for prefix in ("abs/", "pdf/", "html/"):
                if path.startswith(prefix):
                    candidate = path[len(prefix):].removesuffix(".pdf")
                    return ("arxiv", candidate) if _is_arxiv_id(candidate) else None
            return None
        if host.endswith("openalex.org") and path:
            candidate = path.rsplit("/", 1)[-1]
            return ("openalex", candidate) if _OPENALEX_RE.match(candidate) else None
        return None
    if _DOI_RE.match(value):
        return "doi", value
    if _OPENALEX_RE.match(value):
        return "openalex", value.upper()
    if _is_arxiv_id(value):
        return "arxiv", value
    return None


def _is_arxiv_id(value: str) -> bool:
    return bool(_ARXIV_NEW_RE.match(value) or _ARXIV_OLD_RE.match(value))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _abstract_from_inverted_index(index: Any) -> str | None:
    """Reconstrói o abstract do OpenAlex (índice invertido palavra→posições)."""
    if not isinstance(index, dict) or not index:
        return None
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        if not isinstance(offsets, list):
            continue
        for offset in offsets:
            if isinstance(offset, int):
                positions.append((offset, str(word)))
    if not positions:
        return None
    positions.sort()
    return " ".join(word for _, word in positions)


def _first_source(item: dict[str, Any]) -> str | None:
    for location_key in ("primary_location", "best_oa_location"):
        location = item.get(location_key) or {}
        if not isinstance(location, dict):
            continue
        source = location.get("source") or {}
        if isinstance(source, dict) and source.get("display_name"):
            return str(source["display_name"])
    return None


def _pdf_url(item: dict[str, Any]) -> str | None:
    for location_key in ("best_oa_location", "primary_location"):
        location = item.get(location_key) or {}
        if isinstance(location, dict) and location.get("pdf_url"):
            return str(location["pdf_url"])
    return None


def work_from_openalex(item: dict[str, Any]) -> dict[str, Any]:
    """Normaliza um `work` do OpenAlex para o contrato de `metadata["works"]`."""
    doi = item.get("doi")
    if isinstance(doi, str):
        doi = doi.removeprefix("https://doi.org/") or None
    authors = []
    for authorship in item.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        if isinstance(author, dict) and author.get("display_name"):
            authors.append(str(author["display_name"]))
    open_access = item.get("open_access") or {}
    return {
        "id": item.get("id"),
        "doi": doi,
        "title": item.get("title") or item.get("display_name"),
        "year": item.get("publication_year"),
        "authors": authors,
        "venue": _first_source(item),
        "cited_by_count": item.get("cited_by_count"),
        "is_oa": open_access.get("is_oa") if isinstance(open_access, dict) else None,
        "abstract": _abstract_from_inverted_index(item.get("abstract_inverted_index")),
        "type": item.get("type"),
        "pdf_url": _pdf_url(item),
        "oa_url": open_access.get("oa_url") if isinstance(open_access, dict) else None,
    }


def parse_openalex(text: str) -> list[dict[str, Any]]:
    data = _json_or_none(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAlex não devolveu JSON de objeto")
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("OpenAlex sem lista 'results'")
    return [work_from_openalex(item) for item in results if isinstance(item, dict)]


def _text(node: ET.Element, path: str) -> str:
    found = node.find(path)
    return " ".join((found.text or "").split()) if found is not None else ""


def work_from_arxiv(entry: ET.Element) -> dict[str, Any]:
    """Normaliza uma entrada Atom do arXiv para o mesmo contrato do OpenAlex."""
    id_url = _text(entry, f"{_ATOM}id")
    arxiv_id = id_url.rsplit("/abs/", 1)[-1] if "/abs/" in id_url else id_url
    authors = [
        _text(author, f"{_ATOM}name")
        for author in entry.findall(f"{_ATOM}author")
        if _text(author, f"{_ATOM}name")
    ]
    doi = _text(entry, f"{_ARXIV_NS}doi") or None
    journal = _text(entry, f"{_ARXIV_NS}journal_ref") or "arXiv"
    published = _text(entry, f"{_ATOM}published")
    return {
        "id": id_url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None),
        "arxiv_id": arxiv_id or None,
        "doi": doi,
        "title": _text(entry, f"{_ATOM}title"),
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "authors": authors,
        "venue": journal,
        "cited_by_count": None,
        "is_oa": True,
        "abstract": _text(entry, f"{_ATOM}summary") or None,
        "type": "preprint",
        "pdf_url": f"{ARXIV_PDF}/{arxiv_id}" if arxiv_id else None,
        "oa_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
    }


def parse_arxiv(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Atom inválido: {exc}") from exc
    if root.tag != f"{_ATOM}feed":
        raise ValueError("arXiv não devolveu um feed Atom")
    entries = root.findall(f"{_ATOM}entry")
    works: list[dict[str, Any]] = []
    for entry in entries:
        title = _text(entry, f"{_ATOM}title")
        if title.lower() == "error":
            detail = _text(entry, f"{_ATOM}summary")
            raise ValueError(f"arXiv error: {detail}")
        if title:
            works.append(work_from_arxiv(entry))
    return works


def _dedupe(works: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for work in works:
        key = (
            (work.get("doi") or "").lower()
            or (work.get("arxiv_id") or "")
            or " ".join((work.get("title") or "").lower().split())
        )
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(work)
    return unique


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------


def _is_pdf_url(url: str) -> bool:
    """PDF por sufixo ou pelo caminho `/pdf/` do arXiv (que não termina em .pdf)."""
    from urllib.parse import urlsplit

    path = urlsplit(url).path.lower()
    return path.endswith(".pdf") or "/pdf/" in path


def _academic_fetch(url: str, timeout: float) -> dict[str, Any]:
    """Transporte padrão: PDF vem em bytes; o resto vem como texto."""
    return _http_get(url, timeout, binary=_is_pdf_url(url))


def _openalex_url(query: str, limit: int) -> str:
    return f"{OPENALEX_API}?{urlencode({'search': query, 'per-page': limit})}"


def _arxiv_url(query: str, limit: int) -> str:
    return f"{ARXIV_API}?{urlencode({'search_query': f'all:{query}', 'start': 0, 'max_results': limit})}"


def _fetch_source(
    source: str, query: str, limit: int, timeout: float, transport: Transport
) -> tuple[list[dict[str, Any]], str | None, int | None, str]:
    url = _openalex_url(query, limit) if source == "openalex" else _arxiv_url(query, limit)
    payload = transport(url, timeout)
    status = payload.get("status") if isinstance(payload.get("status"), int) else None
    if payload.get("error") and not payload.get("text"):
        return [], f"{source}: {payload['error']}", status, url
    try:
        works = (parse_openalex if source == "openalex" else parse_arxiv)(payload.get("text") or "")
    except ValueError as exc:
        return [], f"{source}: {exc}", status, url
    return works[:limit], None, status, url


def search_works(
    query: str,
    *,
    limit: int = 10,
    source: str = "openalex",
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: Transport | None = None,
) -> ReachResult:
    """Descobre trabalhos acadêmicos (metadados + abstract quando disponível)."""
    query = " ".join(str(query or "").split())
    if not query:
        return _fail("academic_search", query, channel="academic", reason="empty_query")
    if source not in SOURCES:
        return _fail("academic_search", query, channel="academic",
                     reason="unsupported_source",
                     metadata={"supported_sources": list(SOURCES)})
    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        return _fail("academic_search", query, channel="academic", reason="invalid_limit")

    fetch = transport or _academic_fetch
    requested = ("openalex", "arxiv") if source == "both" else (source,)
    works: list[dict[str, Any]] = []
    failures: list[str] = []
    urls: list[str] = []
    observed: list[int] = []
    for name in requested:
        try:
            found, error, status, url = _fetch_source(name, query, limit, timeout, fetch)
        except Exception as exc:  # noqa: BLE001 - transporte injetado nunca derruba
            found, error, status = [], f"{name}: {type(exc).__name__}: {exc}", None
            url = _openalex_url(query, limit) if name == "openalex" else _arxiv_url(query, limit)
        urls.append(url)
        if status is not None:
            observed.append(status)
        works.extend(found)
        if error:
            failures.append(error)

    works = _dedupe(works)[:limit]
    channel = "academic" if source == "both" else source
    metadata: dict[str, Any] = {
        "query": query,
        "source": source,
        "sources_ok": [name for name in requested if name not in
                       {failure.split(":", 1)[0] for failure in failures}],
        "sources_failed": failures,
        "count": len(works),
        "works": works,
    }
    http_status = observed[0] if len(observed) == 1 else None
    limits = [f"limit={limit}", "metadata_and_abstract_only_no_full_text",
              "free_api_no_key"]
    if not works:
        status = STATUS_FAILED if failures else STATUS_UNAVAILABLE
        return _fail(
            "academic_search", query, channel=channel,
            reason="academic_unavailable" if failures else "no_results",
            status=status, qualification=QUAL_NONE, http_status=http_status,
            metadata=metadata, limits=limits,
        )
    return _make(
        "academic_search", query, channel=channel,
        status=STATUS_PARTIAL if failures else STATUS_OBTAINED,
        qualification=QUAL_METADATA,
        reason=f"partial_source_failure: {'; '.join(failures)}" if failures else None,
        http_status=http_status, metadata=metadata, limits=limits,
        evidence=_evidence(
            urls[0] if urls else query, "", urls=urls, read_scope="search_results_only",
            extra={"count": len(works),
                   "work_ids": [work.get("id") for work in works]},
        ),
    )


# ---------------------------------------------------------------------------
# Leitura de um trabalho
# ---------------------------------------------------------------------------


def _strip_html(raw: str) -> str:
    """Texto de um HTML; usa trafilatura quando ele já existe no interpretador.

    trafilatura é o extrator que a cascata do projeto já usa; aqui ele é
    opcional (host sem ele cai no removedor de tags). Não é dependência nova:
    se faltar, o fallback stdlib mantém a operação funcionando.
    """
    import html as _html

    try:
        import trafilatura  # type: ignore[import-not-found]

        extracted = trafilatura.extract(raw)
        if extracted and len(extracted) >= FULLTEXT_MIN_CHARS:
            return " ".join(extracted.split())
    except Exception:  # noqa: BLE001 - extrator opcional nunca derruba a leitura
        pass
    without_scripts = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.I | re.S)
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", without_scripts)).split())


def _plausible_text(text: str) -> bool:
    """Distingue prosa extraída de sintaxe de PDF vazando no texto.

    Medido: um PDF antigo do arXiv devolveu 201k chars começando em `%PDF-1.3`
    com `obj`/`xref` — pypdf não decodificou os streams e o "texto completo"
    seria lixo. Melhor declarar a limitação do que entregar isso como leitura.
    """
    if len(text) < FULLTEXT_MIN_CHARS:
        return False
    head = text[:2000].lstrip()
    if head.startswith("%PDF") or text.count("endobj") > 5 or text.count("xref") > 5:
        return False
    printable = sum(1 for char in text if char.isprintable() or char in "\n\t")
    letters = sum(1 for char in text if char.isalpha() or char.isspace())
    return printable / len(text) > 0.85 and letters / len(text) > 0.40


def _pdf_text(body: bytes) -> tuple[str | None, str | None]:
    """Extrai texto de PDF com pypdf ou PyMuPDF, se já instalados.

    Nenhuma dependência é instalada: sem extrator, o resultado é
    `(None, limitação)`. O texto extraído passa por um gate de plausibilidade,
    porque bytes de PDF decodificados como texto não são leitura.
    """
    import io

    limitation: str | None = None
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(io.BytesIO(body))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if _plausible_text(text):
            return text, None
        limitation = "pdf_text_extraction_garbage (pypdf)"
    except Exception as exc:  # noqa: BLE001 - PDF quebrado vira limitação
        limitation = f"pdf_text_extraction_failed: {type(exc).__name__}: {exc}"

    try:
        import fitz  # type: ignore[import-not-found]  # PyMuPDF, já instalado no venv

        document = fitz.open(stream=body, filetype="pdf")
        try:
            text = "\n".join(page.get_text() for page in document).strip()
        finally:
            document.close()
        if _plausible_text(text):
            return text, None
        limitation = "pdf_text_extraction_garbage (pymupdf)"
    except Exception as exc:  # noqa: BLE001
        limitation = limitation or f"pdf_text_extraction_unavailable: {type(exc).__name__}: {exc}"
    return None, limitation


def _fetch_full_text(
    candidates: list[str], timeout: float, transport: Transport
) -> tuple[str | None, str | None, str | None]:
    """Tenta as URLs gratuitas na ordem; devolve (texto, url usada, limitação)."""
    limitation: str | None = None
    for url in candidates:
        if not url:
            continue
        binary = _is_pdf_url(url)
        try:
            payload = transport(url, timeout)
        except Exception as exc:  # noqa: BLE001
            limitation = f"full_text_fetch_failed: {type(exc).__name__}: {exc}"
            continue
        if payload.get("error") and not payload.get("body") and not payload.get("text"):
            limitation = f"full_text_fetch_failed: {payload['error']}"
            continue
        if binary:
            body = payload.get("body")
            if not isinstance(body, (bytes, bytearray)):
                limitation = "pdf_bytes_not_observed"
                continue
            text, pdf_limitation = _pdf_text(bytes(body))
            if text:
                return text, url, None
            limitation = pdf_limitation or limitation
            continue
        text = _strip_html(payload.get("text") or "")
        if len(text) < 2000 and _ERROR_PAGE_RE.search(text):
            limitation = f"error_page_not_full_text: {url}"
            continue
        if len(text) >= FULLTEXT_MIN_CHARS:
            return text, url, None
        limitation = f"full_text_below_{FULLTEXT_MIN_CHARS}_chars"
    return None, None, limitation


def _channel_for(kind: str) -> str:
    """Canal observado: DOI e OpenAlex ID são consultados no OpenAlex."""
    return "openalex" if kind in ("doi", "openalex") else "arxiv"


def _work_request(identifier: str) -> tuple[str, str, str] | None:
    """(kind, value, metadata_url) para DOI/OpenAlex ID/arXiv ID."""
    classified = classify_identifier(identifier)
    if classified is None:
        return None
    kind, value = classified
    if kind == "doi":
        doi_url = quote(f"https://doi.org/{value}", safe=":/")
        return kind, value, f"{OPENALEX_API}/{doi_url}"
    if kind == "openalex":
        return kind, value, f"{OPENALEX_API}/{value}"
    return kind, value, f"{ARXIV_API}?{urlencode({'id_list': value, 'max_results': 1})}"


def read_work(
    identifier: str,
    *,
    full_text: bool = False,
    timeout: float = DEFAULT_TIMEOUT_S,
    transport: Transport | None = None,
) -> ReachResult:
    """Metadados + abstract de um trabalho; texto completo só se gratuito."""
    identifier = " ".join(str(identifier or "").split())
    request = _work_request(identifier)
    if request is None:
        return _fail("read_work", identifier, channel="academic",
                     reason="unsupported_identifier")
    kind, value, metadata_url = request
    fetch = transport or _academic_fetch
    try:
        payload = fetch(metadata_url, timeout)
    except Exception as exc:  # noqa: BLE001
        return _fail("read_work", identifier, channel=_channel_for(kind),
                     reason=f"academic_error: {type(exc).__name__}: {exc}")
    status_code = payload.get("status") if isinstance(payload.get("status"), int) else None
    if status_code == 404:
        return _fail("read_work", identifier, channel=_channel_for(kind), reason="work_not_found",
                     status=STATUS_UNAVAILABLE, qualification=QUAL_NONE,
                     http_status=404, metadata={"api_url": metadata_url})
    if payload.get("error") and not payload.get("text"):
        return _fail("read_work", identifier, channel=_channel_for(kind),
                     reason="academic_unavailable", http_status=status_code,
                     metadata={"api_url": metadata_url, "error": str(payload["error"])})

    try:
        if kind == "arxiv":
            entries = parse_arxiv(payload.get("text") or "")
            if not entries:
                raise ValueError("arXiv sem entrada para o identificador")
            work = entries[0]
        else:
            data = _json_or_none(payload.get("text") or "")
            if not isinstance(data, dict):
                raise ValueError("OpenAlex não devolveu JSON de objeto")
            work = work_from_openalex(data)
    except ValueError as exc:
        return _fail("read_work", identifier, channel=_channel_for(kind),
                     reason=f"academic_parse_error: {exc}", http_status=status_code,
                     metadata={"api_url": metadata_url})

    abstract = work.get("abstract")
    read_level = "abstract" if abstract else "metadata"
    limits = ["no_paid_access_used", "free_api_no_key"]
    text = ""
    used_url: str | None = None
    limitation: str | None = None

    if full_text:
        candidates: list[str] = []
        if kind == "arxiv":
            arxiv_id = work.get("arxiv_id") or value
            candidates = [f"{ARXIV_HTML}/{arxiv_id}", f"{ARXIV_PDF}/{arxiv_id}"]
        else:
            candidates = [work.get("pdf_url") or "", work.get("oa_url") or ""]
        text, used_url, limitation = _fetch_full_text(
            [candidate for candidate in candidates if candidate], timeout, fetch)
        if text:
            read_level = "full_text"
        else:
            limits.append(limitation or "no_free_full_text_location")
    else:
        limits.append("full_text_not_requested")

    metadata: dict[str, Any] = {
        "api_url": metadata_url,
        "identifier_kind": kind,
        "identifier": value,
        "read_level": read_level,
        "abstract": abstract,
        **{key: work.get(key) for key in
           ("id", "doi", "year", "authors", "venue", "cited_by_count",
            "is_oa", "type", "pdf_url", "oa_url", "arxiv_id")},
        "obtained_at": _utc_now(),
    }
    urls = [metadata_url] + ([used_url] if used_url else [])
    if read_level == "full_text":
        return _make(
            "read_work", identifier, channel=_channel_for(kind), status=STATUS_OBTAINED,
            qualification=QUAL_USABLE, text=text, title=str(work.get("title") or ""),
            http_status=status_code, metadata=metadata, limits=limits,
            evidence=_evidence(used_url or metadata_url, text, urls=urls,
                               read_scope="full_text",
                               extra={"read_level": read_level}),
        )
    reason = None
    qualification = QUAL_PARTIAL if abstract else QUAL_METADATA
    if full_text:
        reason = f"full_text_unavailable: {limitation or 'no_free_location'}"
    return _make(
        "read_work", identifier, channel=_channel_for(kind), status=STATUS_PARTIAL,
        qualification=qualification, title=str(work.get("title") or ""),
        reason=reason, http_status=status_code, metadata=metadata, limits=limits,
        evidence=_evidence(metadata_url, "", urls=urls, read_scope=read_level,
                           extra={"read_level": read_level}),
    )
