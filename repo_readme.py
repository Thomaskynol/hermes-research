#!/usr/bin/env python3
"""
README real de repositorio do GitHub, pelo caminho raw.

POR QUE ESTE MODULO EXISTE
-------------------------
O vast enriquecia resultado de repositorio lendo a PAGINA HTML do GitHub pelo
cascade_fetcher. Medido nesta maquina, com 3 repositorios diferentes:

    yonyu/rust_ownership_borrowing        leu 3.032 chars de menu do GitHub
    tensor-programming/Rust-ownership...   leu o mesmo menu
    FrancescoXX/rust-ownership             leu o mesmo menu

169 das 205 linhas nao vazias (82%) apareciam nos TRES repositorios, e os tres
comecavam identicos: "Skip to content / Navigation Menu / Sign in / Appearance
settings / Platform / AI CODE CREATION / GitHub Copilot...". Zero conteudo
especifico do repo. O nivel do cascade nao denuncia: os tresResolveram no
level 1, acima do minimo de 500 chars. O README de verdade, no caminho raw,
sao 9.160 chars de prosa sobre o assunto do repo.

E a agulha e o palco. Ler HTML do GitHub com extrator de artigo devolve o
chrome de navegacao, nao o repositorio. Ler `README.md` cru devolve o
repositorio, e nao tem o que extrair: ja e o conteudo.

O `HEAD` no lugar do branch: o branch default muda (main/master) e some em
renome; `HEAD` resolve para o default sem adivinhar. E se o README nao existir,
o GitHub devolve 404 honesto -- que e a resposta certa, e nao menu de navegacao
com o nome de outro repo.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger("vast.repo")

# Mesmo diretorio que o vast_local_retriever usa para achar o cascade_fetcher. O
# vast roda com cwd em qualquer lugar, entao o caminho tem que ser absoluto.
CASCADE_DIR: Final[str] = "/opt/data/scripts"
RAW_HOST: Final[str] = "raw.githubusercontent.com"

# Medido: raw.githubusercontent.com responde em ~0.3s. 8s e folga larga para o
# caso de DNS frio -- e, quando a URL nao existe, o cache ainda esta frio e a
# primeira leva o custo do handshake.
DEFAULT_TIMEOUT_S: Final[float] = 8.0

# A URL tem que ser a do REPO, nada mais. Abaixo de dois segmentos (/search,
# /login) nao e repo. Nos dois segmentos, o primeiro nao pode ser uma palavra
# reservada da interface -- /topics/rust e /features/xyz tem dois segmentos e
# nao sao repositorios, e sem esta lista eles virariam "owner=topics, repo=rust"
# e buscariam o README de um repo chamado rust/topics que nao existe.
RESERVED_OWNERS: Final[frozenset[str]] = frozenset({
    "about", "apps", "collections", "contact", "dashboard", "enterprise", "events",
    "features", "issues", "join", "login", "marketplace", "new", "notifications",
    "orgs", "premium", "pricing", "pulls", "readme", "search", "security",
    "settings", "sponsors", "stars", "topics", "trending", "users",
})
# owner/repo do GitHub: nome de usuario pode ter hifen e ponto; o repo aceita
# os mesmos. Barreira de paranoia -- o objetivo e recusar pagina, nao aceitar
# repo raro.
_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# O cascade tem MIN_CHARS=500 e por isso classifica README curto como "nao
# resolvido" e sobe para o navegador. A barra deste modulo e menor e o motivo
# esta no log: um README de 120 chars e Short e ainda e o README do repo.
MIN_CHARS: Final[int] = 40

# Cache NEGATIVO dos 404/0 bytes. Medido antes dele: 4 repos sem README =
# 8.5s na primeira consulta e 8.1s na segunda, porque o cascade NAO cacheia
# falha -- ele trata 404 como erro permanente, sobe para o Chromium antes de
# desistir, e cada nova query paga a escalada de novo. Um README que nao existe
# e imutavel (o branch default e o unico caminho testado, e um repo so ganha
# README se alguem commitar), entao guardar o "nao ha README" por 7 dias e seguro
# e e o mesmo TTL da transcricao. O que fica guardado e so o motivo -- nunca
# texto: um miss aqui e ausencia, e ausencia nao vira conteudo.
README_MISS_DB: Final[str] = os.environ.get(
    "VAST_README_MISS_DB", "/opt/data/cache/readme_misses.db"
)
README_MISS_TTL_S: Final[float] = 604800.0

REASON_LIMIT: Final[int] = 200


@dataclass(frozen=True, slots=True)
class ReadmeResult:
    """README do repo, ou o motivo honesto de nao haver um.

    `text` vazio com `reason` preenchido e um resultado completo: 404 e
    resposta certa tanto quanto 9.160 chars. O que nao pode e text inventado --
    o erro de sempre desta maquina era devolver chrome de pagina como se fosse
    conteudo do repo.
    """

    text: str
    chars: int
    http_status: int | None
    source_url: str | None
    reason: str | None


def raw_readme_url(github_url: str) -> str | None:
    """URL crua do arquivo apontado por uma URL do GitHub, ou None se nao houver.

    Despite o nome, nao e so de README: aceita tambem `.../blob/{ref}/{path}` e
    devolve o caminho raw daquele arquivo. O motivo e o mesmo dos dois casos -- o
    arquivo cru e o conteudo e nao tem o que extrair, enquanto a pagina HTML do
    GitHub devolve o chrome de navegacao. Um `plugin.yaml` lido pela pagina vira
    2.923 chars de menu; lido pelo caminho raw vira 151 chars de YAML.

    Aceita `https://github.com/owner/repo`, com barra final, com `.git`, e com
    query/fragmento -- sao as formas que o `gh search` e o dedo do usuario
    produzem da mesma pagina. Descarta o `.git` porque `owner/repo.git` e o
    mesmo repositorio.

    Recusa caminho mais fundo que `owner/repo` sem ser `blob` (ex.:
    `/owner/repo/issues/3`, `/owner/repo/tree/main`): o conteudo de uma subpagina
    nao e um arquivo do repo, e tratar a subpagina como repo devolveria de novo o
    chrome de navegacao -- exatamente o bug que este modulo existe para matar.
    Do mesmo modo, gist, outro host e `https://github.com/search` devolvem None.

    ASSIMICAO: o `{ref}` e descartado (ver o HEAD no comentario abaixo), entao um
    branch com barra -- `blob/feature/x/src/main.py` -- perde o `feature/` do
    caminho. Raro, e o pior caso e um 404 honesto, nao conteudo de outro arquivo.
    """
    if not github_url or not github_url.strip():
        return None
    parts = urlsplit(github_url.strip())
    if parts.scheme.lower() not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower()
    # gist.github.com cai aqui: e um host diferente, e um gist nao tem README.md
    # no formato que este modulo le.
    if host not in ("github.com", "www.github.com"):
        return None

    segments = [seg for seg in parts.path.split("/") if seg]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if owner.lower() in RESERVED_OWNERS:
        return None
    if not _NAME_RE.match(owner) or not _NAME_RE.match(repo):
        return None
    if repo in (".", ".."):
        return None

    if len(segments) > 2:
        # Sem `{ref}` e sem `{path}` nao ha arquivo: `blob/main` aponta para um
        # diretorio, e ai o certo e None, como para qualquer outra subpagina.
        if len(segments) < 5 or segments[2] != "blob":
            return None
        # HEAD, e nao o {ref} que veio na URL: HEAD resolve para o branch default,
        # que e o mesmo caminho que o README ja usa, entao nao ha motivo para
        # aprender main/master nem para guardar o nome do branch. Um branch
        # nomeado na URL envelhece -- renomeado ou tag movida, o caminho cru
        # vira 404 -- enquanto HEAD acompanha o repo. Custa um 404 em URL de
        # branch antigo e ganha um arquivo que continua la.
        return f"https://{RAW_HOST}/{owner}/{repo}/HEAD/{'/'.join(segments[4:])}"

    return f"https://{RAW_HOST}/{owner}/{repo}/HEAD/README.md"


def _miss(reason: str, *, http_status: int | None = None, source_url: str | None = None) -> ReadmeResult:
    """README vazio com o motivo real, no formato que o vast espera."""
    return ReadmeResult(
        text="", chars=0, http_status=http_status, source_url=source_url,
        reason=reason[:REASON_LIMIT],
    )


# --------------------------------------------------------------------------
# Cache negativo. Mesmo desenho do cascade_fetcher e do youtube_transcript:
# schema com IF NOT EXISTS em toda conexao, PRAGMA de WAL, commit no `with` e
# close no `finally`. Tabela propria e banco proprio porque a politica e
# diferente: o cache do cascade guarda PAGINA (24h) e so guarda sucesso, e o
# youtube_transcript guarda TRANSCRICAO (7 dias). Aqui o que se guarda e a prova
# de que o repo nao tem README -- o unico estado que o cascade se recusa a guardar.
# --------------------------------------------------------------------------

_MISS_SCHEMA: Final[tuple[str, ...]] = (
    """CREATE TABLE IF NOT EXISTS readme_misses (
        url_hash    TEXT PRIMARY KEY,
        url         TEXT NOT NULL,
        reason      TEXT NOT NULL,
        http_status INTEGER,
        missed_at   REAL NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_readme_misses_missed_at ON readme_misses(missed_at)",
)


@contextmanager
def _miss_connect() -> Iterator[sqlite3.Connection]:
    """Abre o banco do cache negativo garantindo o schema, e fecha ao sair."""
    os.makedirs(os.path.dirname(README_MISS_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(README_MISS_DB, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        for stmt in _MISS_SCHEMA:
            conn.execute(stmt)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _miss_get_sync(url: str) -> tuple[str, int | None] | None:
    """(reason, http_status) de um miss vigente, ou None se nao ha miss vigente."""
    with _miss_connect() as conn:
        row = conn.execute(
            "SELECT reason, http_status, missed_at FROM readme_misses WHERE url_hash = ?",
            (_cache_key(url),),
        ).fetchone()
    if row is None:
        return None
    reason, http_status, missed_at = row
    if time.time() - missed_at > README_MISS_TTL_S:
        logger.debug("miss de README expirado (ttl=%ss) %s", int(README_MISS_TTL_S), url)
        return None
    return reason, http_status


def _miss_put_sync(url: str, reason: str, http_status: int | None) -> None:
    """Guarda a prova de que o repo nao tem README. So miss permanente entra.

    Chamar so com 404/410 ou 200 com 0 bytes (ver _is_permanent_miss). Timeout e
    erro de rede NAO sao miss: sao uma pergunta que nao foi respondida, e guarda-los
    transformaria uma falha de rede em "este repo nao tem README" -- que e
    justamente o tipo de mentira que este arquivo existe para nao contar.
    """
    with _miss_connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO readme_misses (url_hash, url, reason, http_status, missed_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (_cache_key(url), url, reason[:REASON_LIMIT], http_status, time.time()),
        )
    logger.info("miss de README guardado: %s (%s)", url, reason)


def _cache_key(url: str) -> str:
    """sha256 da URL, igual ao esquema do cascade_fetcher e do youtube_transcript."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _is_permanent_miss(result: ReadmeResult) -> bool:
    """Diz se este miss vale a pena guardar (imutavel) ou se e so uma falha.

    404/410 e "200 com 0 bytes" sao resposta definitiva do GitHub. Timeout, DNS e
    rede sao a pergunta de novo na proxima vez -- por isso a distincao.
    """
    if result.http_status in (404, 410):
        return True
    return result.http_status == 200 and not result.text


def _load_cascade_fetch():
    """Import tardio e defensivo do `fetch` do cascade_fetcher.

    Dentro da funcao, e nao no topo: o import do cascade precisa de trafilatura e
    bs4, que so existem no interpretador do agent-reach. Se faltar, este modulo
    cai no fetch direto de httpx em vez de derrubar o vast inteiro por causa de
    um recurso opcional.
    """
    if CASCADE_DIR not in sys.path:
        sys.path.insert(0, CASCADE_DIR)
    from cascade_fetcher import fetch

    return fetch


async def _via_cascade(raw_url: str, timeout: float) -> ReadmeResult | None:
    """Le o README pelo cascade. Devolve None se ele nao deu texto utilizavel.

    None significa "tente o proximo caminho", nao "o repo nao tem README": o
    trafilatura come markdown puro com voracidade (e o README e markdown puro),
    e nesse caso quem distingue 404 de "200 com 0 bytes" e o fetch direto.

    O `timeout` e aplicado aqui com wait_for mesmo o vast ja aplicando um por
    fora: `fetch_repo_readme(timeout=...)` precisa valer sozinho para quem
    chamar este modulo direto, sem o vast no meio.
    """
    try:
        fetch = _load_cascade_fetch()
    except Exception as exc:  # noqa: BLE001 - ImportError e SyntaxError e o que importa
        logger.warning("cascade indisponivel para README (%s: %s); vou direto no httpx", type(exc).__name__, exc)
        return None

    try:
        result = await asyncio.wait_for(fetch(raw_url), timeout=timeout)
    except (TimeoutError, asyncio.TimeoutError):
        logger.warning("cascade passou de %.0fs no README %s; vou direto no httpx", timeout, raw_url)
        return None
    except Exception as exc:  # noqa: BLE001 - enrichecedor nunca propaga excecao
        logger.warning("cascade falhou no README %s: %s: %s", raw_url, type(exc).__name__, exc)
        return None

    text = (result.text or "").strip()
    if len(text) < MIN_CHARS:
        logger.info(
            "cascade devolveu %d chars para %s (%s); vou direto no httpx",
            len(text), raw_url, result.reason or "sem motivo",
        )
        return None
    logger.info("README via cascade: %s chars=%d nivel=%d cache=%s",
                raw_url, len(text), result.level, result.from_cache)
    return ReadmeResult(
        text=text, chars=len(text), http_status=None,
        source_url=getattr(result, "url", raw_url), reason=None,
    )


async def _direct(raw_url: str, timeout: float) -> ReadmeResult:
    """Uma ida so de httpx no corpo cru, e o corpo e a resposta.

    O motivo de existir alem do cascade: o GitHub responde 404 de um jeito e 200
    com 0 bytes de outro (medido: WowVeryLogin/rust_ownership_workshop tem
    README.md vazio, HTTP 200, 0 bytes, em HEAD/main/master), e o cascade trata
    os dois como "nada lido" sem contar qual dos dois foi. Aqui os dois casos
    ficam nomeados, porque "o repo nao tem README" e "o README esta vazio" sao
    diagnosticos diferentes para quem esta escrevendo sobre isso.
    """
    import httpx  # local: se o httpx faltar, so este caminho perde, nao o modulo

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(raw_url, headers={"User-Agent": "agent-reach/1.0"})
    except httpx.TimeoutException as exc:
        return _miss(f"timeout de {timeout:.0f}s no raw", source_url=raw_url)
    except Exception as exc:  # noqa: BLE001 - erro de rede vira motivo, nao traceback
        return _miss(f"rede: {type(exc).__name__}: {exc}", source_url=raw_url)

    status = response.status_code
    if status in (404, 410):
        return _miss(f"ausente no raw (HTTP {status})", http_status=status, source_url=raw_url)
    if status != 200:
        return _miss(f"HTTP {status} no raw", http_status=status, source_url=raw_url)

    # Verbatim: o arquivo cru ja e o conteudo, e por isso que este caminho e o
    # que ele. Nao normaliza, nao resume, nao corta -- cortou quem chama
    # (as_contract_item).
    text = response.text
    if not text.strip():
        return _miss("arquivo esta vazio (0 bytes)", http_status=status, source_url=raw_url)

    logger.info("README direto: %s chars=%d", raw_url, len(text))
    return ReadmeResult(
        text=text, chars=len(text), http_status=status, source_url=raw_url, reason=None,
    )


async def fetch_repo_readme(github_url: str, *, timeout: float = DEFAULT_TIMEOUT_S) -> ReadmeResult:
    """README real do repo, ou o motivo honesto de nao existir. Nunca levanta.

    Ordem: cache negativo, depois cascade (ele tem cache de 24h, throttle por
    dominio e fingerprint TLS de browser, e ja esta quente nesta maquina -- 0.3s
    medido para o README do yonyu) e, se ele nao entregar texto, UMA ida direta
    de httpx, que e quem consegue dizer 404 de "200 com 0 bytes".

    O cache negativo vem primeiro porque e a unica etapa que encurta a consulta
    seguinte: o cascade trata 404 como erro permanente e ainda assim sobe para o
    Chromium antes de desistir, sem guardar a falha. Medido: 4 repos sem README
    custavam 8.5s e 8.1s em duas consultas identicas; com o cache negativo a
    segunda vira ~0s. O miss continua sendo miss -- a resposta devolvida e a
    mesma `ReadmeResult(text="", reason=...)`, entao quem chama continua contando
    readme_miss, e nenhum texto aparece onde nao ha README.

    Nao ha terceiro caminho de proposito: cair para a pagina HTML do GitHub e
    voltar a devolver o menu de navegacao de 3.032 chars, que e o defeito que
    este modulo corrige. Sem README a resposta honesta e "nao ha README", e o
    snippet curto que o `gh search` devolveu continua valendo.
    """
    raw_url = raw_readme_url(github_url)
    if raw_url is None:
        return _miss("nao aponta para um repositorio nem para um arquivo do github")

    try:
        cached_miss = await asyncio.to_thread(_miss_get_sync, raw_url)
    except Exception as exc:  # noqa: BLE001 - disco cheio nao pode derrubar a busca
        logger.warning("cache negativo de README indisponivel (%s: %s); sigo para a rede", type(exc).__name__, exc)
        cached_miss = None
    if cached_miss is not None:
        reason, status = cached_miss
        logger.info("README ausente (cache negativo, ttl=%ss): %s", int(README_MISS_TTL_S), raw_url)
        return _miss(reason, http_status=status, source_url=raw_url)

    result = await _via_cascade(raw_url, timeout)
    if result is None:
        result = await _direct(raw_url, timeout)

    if _is_permanent_miss(result):
        try:
            await asyncio.to_thread(_miss_put_sync, raw_url, result.reason or "sem motivo", result.http_status)
        except Exception as exc:  # noqa: BLE001 - guardar o miss e otimo, obrigatorio nao e
            logger.warning("nao consegui guardar o miss de README (%s: %s)", type(exc).__name__, exc)
    return result
