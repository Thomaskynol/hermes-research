#!/usr/bin/env python3
"""
Vast Local Retriever — 100% local, sem Exa, sem APIs pagas.
Ponte HTTP que o GPT Researcher consulta como fonte de busca: faz fan-out paralelo
para GitHub (gh), YouTube (yt-dlp), Bilibili (bili-cli) e V2EX (API publica) e
devolve no maximo MAX_RESULTS itens.

Uso:
    python3 vast_local_retriever.py  # sobe em 127.0.0.1:8001

GPT Researcher config:
    RETRIEVER=custom,searx,duckduckgo,arxiv
    RETRIEVER_ENDPOINT=http://127.0.0.1:8001/
    SEARX_URL=http://127.0.0.1:8888/

Duas regras que este arquivo existe para garantir:

1. Uma fonte que nao tem resultado devolve lista vazia, nunca inventa conteudo.
   Resultado inventado e pior que fonte ausente: o GPT Researcher nao tem como
   saber que esta lendo ruido e citaria aquilo no relatorio final.

2. Toda falha deixa rastro. Um processo que engole excecao e devolve "" transforma
   "fonte morta" em "0 resultados", que e indistinguivel de "nada encontrado".
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import threading
import time
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Protocol
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger("vast")

# Contrato com o GPT Researcher: nunca aumentar MAX_RESULTS sem mudar os dois lados.
MAX_RESULTS = 12

# Teto de raw_content por item, e o teto do que o GPT Researcher le DEPOIS: o
# context/retriever.py dele corta em MAX_CONTENT_CHARS ANTES do chunking
# (vector_store faz _split_documents(chunk_size=1000, overlap=200) e so entao
# add_documents). E um teto PRE-chunk, nao "uma chamada de embedding".
#
# 50000 = o proprio default do GPT Researcher (context/retriever.py). Nao e
# escolha nossa e nao e escolha de ninguem: e o ponto onde os dois lados ja
# concordam sem override.
#
# O teto de 2048 tokens do endpoint de embedding NAO restringe este valor: o
# chunking acontece antes, entao add_documents so ever sees ~1.000 chars
# (~250 tokens) por chamada. Medido nesta maquina, com o
# RecursiveCharacterTextSplitter de verdade, 12 itens:
#   teto   2000 ->  3 chunks/item =  36 chunks/query
#   teto   8000 -> 11 chunks/item = 132 chunks/query
#   teto  20000 -> 28 chunks/item = 336 chunks/query
#   teto  50000 -> 68 chunks/item = 816 chunks/query
# Embedding real dos 816 chunks de 1.000 chars contra o harrier local em
# 172.17.0.1:8082: 816 ok, 0 falhas, 55.1s, 68 ms/chunk. Linear e local: o custo
# de 50000 e ~33s de embedding por query, nao dinheiro.
#
# O valor anterior (20000) se justificava com "ja passa do maior conteudo real
# medido" -- medido a partir de um video de 18s. Essa medicao estava errada e a
# corte silenciosamente: no cache real, 3 de 7 transcricoes eram cortadas em
# 20.000 (45.919, 33.093 e 26.176 chars), perdendo 45.188 chars por run. O maior
# conteudo real medido e 45.919 chars, que 20000 descarta em 56%. O erro nao e
# "custo de embedding" e o teto ser grande demais, e o teto ser pequeno demais.
_DEFAULT_RAW_CONTENT_LIMIT: Final[int] = 50000
try:
    RAW_CONTENT_LIMIT: Final[int] = int(
        os.environ.get("VAST_RAW_CONTENT_LIMIT", str(_DEFAULT_RAW_CONTENT_LIMIT))
    )
except ValueError:
    # Env malformado nao derruba o servico no import: o default medido entra e o
    # log avisa o que foi ignorado.
    RAW_CONTENT_LIMIT = _DEFAULT_RAW_CONTENT_LIMIT
    logger.warning(
        "VAST_RAW_CONTENT_LIMIT=%r nao e inteiro; usando o default %d",
        os.environ.get("VAST_RAW_CONTENT_LIMIT"), _DEFAULT_RAW_CONTENT_LIMIT,
    )
# Os dois lados do corte precisam concordar: aqui e RAW_CONTENT_LIMIT, la no GPT
# Researcher e MAX_CONTENT_CHARS. setdefault e nao atribuicao -- quem define
# MAX_CONTENT_CHARS no ambiente sabe o que esta fazendo; este codigo so preenche o
# que ninguem preencheu. O aviso de divergencia esta em log_content_limits().
os.environ.setdefault("MAX_CONTENT_CHARS", str(RAW_CONTENT_LIMIT))
try:
    _EFFECTIVE_MAX_CONTENT_CHARS: Final[int] = int(
        os.environ.get("MAX_CONTENT_CHARS", str(RAW_CONTENT_LIMIT))
    )
except ValueError:
    _EFFECTIVE_MAX_CONTENT_CHARS = RAW_CONTENT_LIMIT

# Enriquecimento: ler a pagina de verdade e trocar o snippet de CLI (no maximo
# 498 chars) pelo texto real. Medido nesta maquina, o custo por URL varia ~25x
# entre as fontes: github ~2.4s/URL no level 1; bilibili ~2.4s/URL no level 2
# com ~1.3-1.5k chars; youtube 24.5s/URL e 0% de aproveitamento (HTTP 429 em
# todas as tentativas de level 1/2, depois uma pagina anti-bot de 298 chars no
# level 3 que nunca passa do minimo de 500 chars -- bloqueio no IP deste
# datacenter, ja que a primeira tentativa ja era 429). Da o round-robin por
# fonte e os dois tetos: sem teto geral o orcamento voa, so com teto por fonte
# a fonte cara fica com tudo.
# "level 1" nao quer dizer "texto bom", e vale saber antes de confiar no
# numero: de 4 repos do github lidos, 3 devolveram README de verdade (2.3-3.0k
# chars) e 1 devolveu 3.032 chars de menu do GitHub -- tambem level 1, tambem
# acima do minimo de 500. O nivel nao separa os dois casos, so o chars grosso.
# Kill-switch: VAST_ENRICH=0 volta ao comportamento antigo sem mexer no
# codigo.
ENRICH_ENABLED: bool = os.environ.get("VAST_ENRICH", "1") != "0"
# Teto geral por request. A busca custa 8.7s no caso tipico, mas o pior caso
# dela e o timeout de 30s do proprio CLI da fonte, e as 4 fontes rodam em
# paralelo: o bilibili falhou assim em 2 de 3 requests (curl (35) connection
# reset), medido. 30s aqui + 30s la seria 60s cravado no teto do
# GPT Researcher. 20.0 aqui da ~50s no pior caso e nao corta nada que preste:
# o grupo do github (3 URLs) fecha em ~7s medido.
ENRICH_MAX_PAGES: Final[int] = 6
ENRICH_MAX_PER_SOURCE: Final[int] = 3
ENRICH_TOTAL_BUDGET_S: Final[float] = 20.0
# Teto por pagina. Um level 3 bem-sucedido mediu 5.1s (um 404 do github que
# caiu no browser), entao 8.0s deixa a leitura rapida terminar e corta a URL
# condenada que mediu 24.5s. Incerteza: o custo do level 3 depende da maquina;
# se o browser aqui ficar mais lento, este e o primeiro numero a subir.
ENRICH_PAGE_TIMEOUT_S: Final[float] = 8.0
# YouTube: a transcricao substitui a descricao (que e a isca) quando existe. Tres
# videos por request e 25s de orcamento: o yt-dlp gasta ~4-8s no video curto e
# ~25s no longo, entao tres com 3 slots e o maximo que cabe sem o endpoint virar
# uma busca de legenda. Concorrencia 3 e nao 5 porque o yt-dlp gasta CPU de node
# no desafio de JS, e o 2s de --sleep-subtitles existe pelo mesmo motivo.
# Kill-switch: VAST_YT_ENRICH=0 volta a descricao como esta no codigo.
YT_ENRICH_ENABLED: Final[bool] = os.environ.get("VAST_YT_ENRICH", "1") != "0"
YT_ENRICH_MAX: Final[int] = 3
YT_ENRICH_BUDGET_S: Final[float] = 25.0
YT_ENRICH_CONCURRENCY: Final[int] = 3
# Teto por transcricao. O default do modulo e 45s (video longo leva isso); aqui o
# que manda e o orcamento da request, e o wait_for corta no min(remaining, isto).
YT_FETCH_TIMEOUT_S: Final[float] = 45.0
# Quanto o grupo do YouTube espera o veredito da transcricao antes de ler a pagina
# (ver _read_page). O orcamento total da request e YT_ENRICH_BUDGET_S e a leitura
# de pagina custa ate ENRICH_PAGE_TIMEOUT_S; esperar mais que a diferenca
# guarantee que sempre sobra tempo para a pagina, e o fallback de descricao
# continua vivo nos videos que nao ganharam transcricao.
YT_PAGE_WAIT_S: Final[float] = YT_ENRICH_BUDGET_S - ENRICH_PAGE_TIMEOUT_S
# GitHub: README cru em vez da pagina HTML. Medido com 3 repos diferentes, a
# pagina HTML devolvia o mesmo menu de navegacao nos tres -- 169 das 205 linhas
# nao vazias (82%) iguais -- e o README cru sao 9.160 chars do repo certo. O
# README e barato de pedir e honesto no 404, entao ele NAO passa pelo plano de
# paginas (ENRICH_MAX_PAGES) e nao e sequencial por host: no maximo 5 por
# request, 2 em voo, cada uma com o seu teto.
README_MAX: Final[int] = 5
README_CONCURRENCY: Final[int] = 2
README_TIMEOUT_S: Final[float] = 8.0
# Gate de chrome. Sao rotulos POSITIVOS de interface, medidos no texto que o
# cascade devolve quando cai para o level 2 (pagina inteira, menu incluido), e
# nao uma heuristica de densidade ou entropia: palavra de menu nao aparece em
# prosa, entao "o texto tem '会员购'" e prova de que o texto e a pagina, nao o
# video. Medido: no bilibili os 7 rotulos ocupam ~60 chars seguidos logo depois
# do titulo; no GitHub o level 1 devolvia 3.032 chars comecando em "Skip to
# content / Navigation Menu / Appearance settings / AI CODE CREATION".
# A chave e o HOSTNAME (sem www), porque e o que urlsplit devolve.
CHROME_LABELS: Final[dict[str, tuple[str, ...]]] = {
    "bilibili.com": ("游戏中心", "会员购", "漫画", "赛事", "首页", "番剧", "直播"),
    "github.com": ("Skip to content", "Navigation Menu", "Appearance settings", "AI CODE CREATION"),
}
# Janela de inspecao: os rotulos de menu ficam nos primeiros centos de chars, e
# vasculhar a pagina inteira custaria CPU para achar prova de que ela e chrome.
CHROME_WINDOW: Final[int] = 800
# Depois de cortar a corrida de menu, o que sobra tem que valer mais que o
# snippet que a busca ja deu -- e ter pelo menos isso de conteudo. Abaixo disso
# o item volta a ser o snippet da busca: snippet de CLI e real, e um pedaco de
# menu com o titulo grudado nao e.
MIN_CLEAN_CHARS: Final[int] = 120
# O vast roda com cwd em qualquer lugar e os dois modulos novos moram do lado
# deste arquivo: sem isto, `uvicorn vast_local_retriever:app` de outro cwd nao
# acha nenhum dos dois e o enriquecimento degrada sozinho.
_THIS_DIR: Final[str] = str(Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
# O vast roda com cwd em qualquer lugar e o cascade vive num caminho absoluto.
CASCADE_DIR: Final[str] = "/opt/data/scripts"

# Timeouts sao por fonte porque cada uma tem um perfil de latencia proprio:
# gh responde em ~1s, yt-dlp e bili batem em rede china e demoram 5-15s.
DEFAULT_TIMEOUT = 20.0
GITHUB_TIMEOUT = 15.0
YOUTUBE_TIMEOUT = 30.0
BILIBILI_TIMEOUT = 30.0
V2EX_TIMEOUT = 10.0

# /health e chamado com frequencia; sondar 4 fontes a cada chamada (3 delas com
# subprocess) deixaria o endpoint lento e o usuario esperando. 60s de cache da
# tempo de ver a falha sem virar peso.
HEALTH_CACHE_TTL = 60.0
# Query de sondagem: precisa ser generica o bastante para retornar resultado em
# qualquer fonte saudavel, senao "0 resultados" e normal e nao quer dizer "morta".
HEALTH_PROBE_QUERY = "rust"

# Limites por fonte. A soma e maior que MAX_RESULTS de proposito: o corte final
# acontece no /, depois de remover duplicatas, para nao gastar vaga com repetido.
PER_SOURCE_LIMIT = {"github": 5, "youtube": 5, "bilibili": 5, "v2ex": 3}
# As queries do usuario vao inteiras como argumento do subprocess (sem shell).
# O corte existe porque as CLIs engasgam com termos enormes e o resultado util
# esta no comeco da query de qualquer forma.
YOUTUBE_QUERY_LIMIT = 80
BILIBILI_QUERY_LIMIT = 60

V2EX_HOT_URL = "https://www.v2ex.com/api/topics/hot.json"
V2EX_USER_AGENT = "agent-reach/1.0"

ENV_FILE = Path("/opt/data/.env")

STATE_WORKING = "working"
STATE_DEGRADED = "degraded"
STATE_BROKEN = "broken"
STATE_BLOCKED = "blocked"

STDERR_SNIPPET = 200

logging.basicConfig(
    level=os.environ.get("VAST_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)

app = FastAPI(title="Vast Local Retriever", version="2.0")

# Import opcional dos dois modulos de enriquecimento, no escopo do modulo para
# que a funcao seja resolvida uma vez. Se algum falhar, quem chama degrada: sem
# youtube_transcript o video volta a ser a descricao (o comportamento antigo, que
# e ruim mas honesto) e sem repo_readme o repo volta a ser a pagina HTML (pior: e
# o menu de navegacao, medido). ImportError e o caso comum; Exception cobre tambem
# um modulo que carrega e quebra na metade. Recurso opcional nao derruba o vast.
try:
    from repo_readme import fetch_repo_readme as _fetch_repo_readme
    from repo_readme import raw_readme_url as _raw_readme_url
except Exception as exc:  # noqa: BLE001 - ver acima
    _fetch_repo_readme = None
    _raw_readme_url = None
    logger.warning(
        "repo_readme indisponivel (%s: %s); repo do github volta a ser lido como pagina",
        type(exc).__name__, exc,
    )

try:
    from youtube_transcript import METHOD_CACHE as _YT_METHOD_CACHE
    from youtube_transcript import fetch_transcript as _fetch_transcript
    from youtube_transcript import peek_transcript as _peek_transcript
except Exception as exc:  # noqa: BLE001 - ver acima
    _fetch_transcript = None
    _peek_transcript = None
    _YT_METHOD_CACHE = "cache"
    logger.warning(
        "youtube_transcript indisponivel (%s: %s); video volta a ser so descricao",
        type(exc).__name__, exc,
    )


class SourceError(RuntimeError):
    """A fonte nao respondeu de jeito nenhum: binario ausente, timeout, rc != 0.

    Existe como excecao (e nao como "") porque /health precisa distinguir
    "respondeu e nao achou nada" de "esta morta", e uma string vazia nao diz qual
    dos dois aconteceu.
    """


class SourceBlocked(SourceError):
    """A fonte respondeu recusando o acesso (HTTP 401/403), tipicamente IP bloqueado."""


@dataclass(slots=True)
class Hit:
    """Um resultado ja no formato do contrato, antes do truncamento final.

    Os campos transcript_* nascem defaultados (descricao como fallback) e o
    enriquecimento os preenche sem mexer em titulo, descricao-base ou URL: a
    transcricao e ADICAO rotulada, nunca substituicao. Sao eles -- e nao o
    tamanho do raw_content -- que dizem no trace se o video chegou a geracao
    com fala transcrita ou so com a isca.
    """

    url: str
    title: str
    raw_content: str
    source: str
    # Origem da transcricao ("cache"/"live") ou "" quando nao ha nenhuma.
    transcript_origin: str = ""
    # Idioma da legenda ("en", ...) ou "" quando nao ha nenhuma.
    transcript_lang: str = ""
    # True/False quando a origem e conhecida, None (unknown) em caso contrario.
    transcript_automatic: bool | None = None
    # Chars de transcricao aproveitados, ou 0 quando nao ha nenhuma.
    transcript_chars: int = 0
    # Status da transcricao neste hit. Sempre preenchido em video do YouTube:
    # um dos transcript_* abaixo (ok/cache), ou transcript_absent/
    # transcript_error quando ficou so a descricao.
    transcript_status: str = ""

    def as_contract_item(self) -> dict[str, str]:
        """Reduz ao que o GPT Researcher le, na ordem e nos nomes que ele espera."""
        return {
            "url": self.url,
            "title": self.title,
            "raw_content": self.raw_content[:RAW_CONTENT_LIMIT],
            "source": self.source,
        }


@dataclass(slots=True)
class CommandResult:
    """Saida completa de um subprocess, com o custo e o motivo da falha.

    O codigo original descartava stderr e returncode, e com eles a unica
    informacao util quando uma fonte morre.
    """

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass(slots=True)
class SourceHealth:
    """Estado de UMA fonte,reevalado no maximo a cada HEALTH_CACHE_TTL segundos."""

    name: str
    state: str
    detail: str
    latency_ms: int | None
    checked_at: str

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at,
        }


SourceProbe = Callable[[str], Awaitable[list[Hit]]]


@dataclass(slots=True)
class _YtGate:
    """Decisao compartilhada entre o pool de transcricao e o pool de paginas.

    A pergunta "este video ja tem transcricao?" so tem resposta DEPOIS que o pool
    de transcricao terminou, e os dois pools rodam em paralelo. Sem esta ponte as
    rotas se atropelam: ou o grupo do YouTube espera um yt-dlp de 25s dentro de um
    orcamento de pagina de 20s, ou busca a pagina HTML sabendo que ela da 429.
    Com ela, o grupo do YouTube espera a conta fechar (dentro do prazo que ele ja
    tinha) e so entao decide se le a pagina.

    Medido do lado que ela resolve: a pagina HTML do YouTube e morta nesta maquina
    (HTTP 429 em todas as tentativas, pagina anti-bot de 298 chars no level 3), e
    o unico resultado medido dela em `/` era `timeout=2` -- dois videos x 8s de
    espera pura por consulta, com a transcricao do mesmo video ja na mao.
    """

    done: asyncio.Event
    urls: set[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clip_query(query: str, limit: int) -> str:
    return " ".join(query.split())[:limit]


def _one_line(text: str) -> str:
    """Achata em uma linha o que vai para log e para o `detail` do /health.

    O stderr do gh traz a mensagem de login em duas linhas; sem achatar, o detail
    do health sairia com quebra de linha no meio do JSON.
    """
    return " ".join(text.split())


def load_github_token() -> None:
    """Deixa o gh autenticado, uma unica vez, no startup do processo.

    O gh exige token ate para `gh search repos`: sem ele sai com rc=4 e a mensagem
    de "gh auth login" no stderr, ou seja, a fonte morre. Ler o .env aqui (import do
    modulo, antes de qualquer request) e seguro; ler dentro de um handler e perigoso,
    porque qualquer traceback passa a ter chance de vazar o token no log.
    """
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        logger.info("github: token ja veio do ambiente, .env nao sera lido")
        return
    try:
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.startswith("GITHUB_TOKEN="):
                continue
            token = line.partition("=")[2].strip().strip("'\"")
            if token:
                os.environ["GH_TOKEN"] = token
                logger.info("github: GITHUB_TOKEN carregado de %s (valor nao logado)", ENV_FILE)
                return
        logger.warning("github: %s existe mas nao tem GITHUB_TOKEN; gh vai rodar sem auth", ENV_FILE)
    except OSError as exc:
        logger.warning("github: nao consegui ler %s (%s); gh vai rodar sem auth", ENV_FILE, exc)


async def run_command(
    argv: Sequence[str],
    *,
    source: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> CommandResult:
    """Executa um binario SEM shell, recebendo os argumentos ja separados.

    O original usava create_subprocess_shell com a query interpolada na string do
    comando. Isso e injecao de comando (query "rust; rm -rf ~" virava dois comandos)
    e quebra com qualquer query que contenha aspas, & ou | — "rust & golang" virava
    um comando invalido e a fonte morria em silencio.

    Levanta SourceError quando o processo nem chegou a produzir saida (binario
    ausente, timeout, spawn falhou) e devolve o CommandResult mesmo com rc != 0,
    para o chamador decidir se ainda ha algo aproveitavel no stdout.
    """
    args = [str(part) for part in argv]
    command_line = " ".join(args)
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.error("fonte=%s comando ausente no PATH: %s", source, args[0])
        raise SourceError(f"{args[0]} nao encontrado no PATH") from None
    except OSError as exc:
        logger.error("fonte=%s nao consegui executar %s: %s", source, args[0], exc)
        raise SourceError(f"falha ao executar {args[0]}: {exc}") from None

    started = time.monotonic()
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.error(
            "fonte=%s timeout de %.0fs: %s", source, timeout, command_line,
        )
        raise SourceError(f"timeout de {timeout:.0f}s em {args[0]}") from None

    result = CommandResult(
        argv=args,
        returncode=proc.returncode or 0,
        stdout=stdout.decode("utf-8", errors="ignore"),
        stderr=stderr.decode("utf-8", errors="ignore"),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    if result.returncode != 0:
        logger.warning(
            "fonte=%s comando falhou rc=%d em %dms: %s | stderr: %s",
            source,
            result.returncode,
            result.duration_ms,
            command_line,
            _one_line(result.stderr.strip())[:STDERR_SNIPPET] or "(vazio)",
        )
    return result


def _failed(result: CommandResult) -> str:
    """Motivo curto de um comando que saiu com erro, para a excecao e para o /health."""
    detail = _one_line(result.stderr.strip() or result.stdout.strip())
    return f"{result.argv[0]} rc={result.returncode}: {detail[:STDERR_SNIPPET] or 'sem saida'}"


def _parse_ytdlp_lines(stdout: str, limit: int) -> list[Hit]:
    """yt-dlp --dump-json emite um JSON por linha; linhas de log sao ignoradas."""
    hits: list[Hit] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            video = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = video.get("id") or ""
        title = video.get("title") or ""
        description = (video.get("description") or "")[:400]
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else video.get("webpage_url", "")
        if not url:
            continue
        hits.append(
            Hit(
                url=url,
                title=title,
                raw_content=f"YouTube: {title}\n{description}",
                source="youtube",
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _parse_bili_yaml(text: str, limit: int) -> list[Hit]:
    """Le a saida YAML do bili-cli (ok:, data:, - bvid:, title:, author:).

    Feito linha a linha de proposito: o formato e fixo e o PyYAML nao vem
    garantido no venv que roda o vast, e um ImportError aqui derrubaria o servico
    inteiro por causa de uma fonte opcional. Se o CLI um dia devolver `ok: false`,
    isso e erro da fonte e nao "nada encontrado".
    """
    if re.search(r"^ok:\s*false", text, re.MULTILINE):
        message = next(
            (line.split(":", 1)[1].strip() for line in text.splitlines() if line.strip().startswith("message:")),
            text.strip().splitlines()[-1] if text.strip() else "",
        )
        raise SourceError(f"bili falhou: {message[:STDERR_SNIPPET]}")

    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("- "):
            if current:
                records.append(current)
            current = {}
            line = line[2:]
        key, separator, value = line.partition(":")
        if separator:
            current[key.strip()] = value.strip().strip("'\"")
    if current:
        records.append(current)

    hits: list[Hit] = []
    for record in records:
        bvid = record.get("bvid") or record.get("id") or ""
        if not bvid:
            continue
        title = record.get("title", "")
        author = record.get("author", "")
        hits.append(
            Hit(
                url=f"https://www.bilibili.com/video/{bvid}",
                title=title,
                raw_content=(
                    f"Bilibili: {title}\n"
                    f"autor: {author} | duracao: {record.get('duration', '?')} | "
                    f"plays: {record.get('play', '?')}"
                ),
                source="bilibili",
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


async def github_search(query: str) -> list[Hit]:
    """Busca repositorios no GitHub e, se nao achar, cai para busca de codigo.

    O fallback e legitimo: sao dois modos de pesquisa real da mesma fonte, com
    resultados que passam no filtro da query. (O fallback do V2EX era outra coisa:
    devolvia topico quente sem relacao nenhuma com a query.)
    """
    limit = PER_SOURCE_LIMIT["github"]
    repos = await run_command(
        ["gh", "search", "repos", query, "--limit", str(limit), "--json", "fullName,description,url"],
        source="github",
        timeout=GITHUB_TIMEOUT,
    )
    hits = _parse_gh_repos(repos.stdout, limit)
    if hits:
        return hits

    code = await run_command(
        ["gh", "search", "code", query, "--limit", str(limit), "--json", "repository,path,url"],
        source="github",
        timeout=GITHUB_TIMEOUT,
    )
    if code.returncode != 0 and not code.stdout.strip():
        # Sem resultado em repos E erro em code: a fonte esta morta, nao vazia.
        # O que vier antes (vazio) e o que o /health precisa reportar como broken.
        raise SourceError(_failed(code))
    return _parse_gh_code(code.stdout, limit)


def _parse_gh_repos(stdout: str, limit: int) -> list[Hit]:
    hits: list[Hit] = []
    if not stdout.strip().startswith("["):
        return hits
    try:
        repos = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("fonte=github json de repos invalido: %s", exc)
        raise SourceError("gh search repos devolveu json invalido") from exc
    for repo in repos[:limit]:
        full_name = repo.get("fullName") or ""
        hits.append(
            Hit(
                url=repo.get("url") or (f"https://github.com/{full_name}" if full_name else ""),
                title=full_name,
                raw_content=f"GitHub repo: {full_name} — {repo.get('description') or ''}",
                source="github",
            )
        )
    return [hit for hit in hits if hit.url]


def _parse_gh_code(stdout: str, limit: int) -> list[Hit]:
    hits: list[Hit] = []
    if not stdout.strip().startswith("["):
        return hits
    try:
        matches = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("fonte=github json de code search invalido: %s", exc)
        raise SourceError("gh search code devolveu json invalido") from exc
    for match in matches[:limit]:
        repository = (match.get("repository") or {}).get("nameWithOwner") or ""
        path = match.get("path") or ""
        hits.append(
            Hit(
                url=match.get("url") or "",
                title=path,
                raw_content=f"GitHub code: {repository}/{path}",
                source="github-code",
            )
        )
    return [hit for hit in hits if hit.url]


async def youtube_search(query: str) -> list[Hit]:
    """YouTube via yt-dlp em modo busca (ytsearch), sem API e sem download."""
    limit = PER_SOURCE_LIMIT["youtube"]
    result = await run_command(
        ["yt-dlp", "--dump-json", f"ytsearch{limit}:{_clip_query(query, YOUTUBE_QUERY_LIMIT)}"],
        source="youtube",
        timeout=YOUTUBE_TIMEOUT,
    )
    hits = _parse_ytdlp_lines(result.stdout, limit)
    if not hits and result.returncode != 0:
        raise SourceError(_failed(result))
    return hits


async def bilibili_search(query: str) -> list[Hit]:
    """Bilibili via bili-cli local."""
    limit = PER_SOURCE_LIMIT["bilibili"]
    result = await run_command(
        ["bili", "search", _clip_query(query, BILIBILI_QUERY_LIMIT), "--type", "video", "-n", str(limit)],
        source="bilibili",
        timeout=BILIBILI_TIMEOUT,
    )
    hits = _parse_bili_yaml(result.stdout, limit)
    if not hits and result.returncode != 0:
        raise SourceError(_failed(result))
    return hits


async def v2ex_search(query: str) -> list[Hit]:
    """V2EX: topicos quentes filtrados localmente pela query.

    Devolve [] quando nada casa. O codigo antigo devolvia 2 topicos quentes
    quaisquer nesse caso, so com o titulo: o GPT Researcher nao tem como saber
    que aquilo nao tem relacao com a pergunta e citaria como se fosse. Fonte
    vazia e honesta; fonte inventada e pior que fonte ausente.
    """
    limit = PER_SOURCE_LIMIT["v2ex"]
    async with httpx.AsyncClient(timeout=V2EX_TIMEOUT) as client:
        response = await client.get(V2EX_HOT_URL, headers={"User-Agent": V2EX_USER_AGENT})

    if response.status_code in (401, 403):
        logger.error("fonte=v2ex acesso recusado com HTTP %s (IP bloqueado?)", response.status_code)
        raise SourceBlocked(f"HTTP {response.status_code}: IP provavelmente bloqueado")
    if response.status_code != 200:
        raise SourceError(f"HTTP {response.status_code} em {V2EX_HOT_URL}")

    topics = response.json()
    terms = [term for term in query.lower().split() if len(term) > 2]
    hits: list[Hit] = []
    for topic in topics:
        title = topic.get("title") or ""
        body = topic.get("content") or _strip_html(topic.get("content_rendered") or "")
        if terms and not any(term in f"{title} {body}".lower() for term in terms):
            continue
        url = topic.get("url") or f"https://www.v2ex.com/t/{topic.get('id', '')}"
        hits.append(
            Hit(
                url=url,
                title=title,
                raw_content=f"V2EX: {title}\n{body[:400]}",
                source="v2ex",
            )
        )
        if len(hits) >= limit:
            break

    if not hits:
        logger.warning(
            "fonte=v2ex nenhum topico quente casa com a query %r; devolvendo [] de proposito", query,
        )
    return hits


SOURCE_PROBES: dict[str, SourceProbe] = {
    "github": github_search,
    "youtube": youtube_search,
    "bilibili": bilibili_search,
    "v2ex": v2ex_search,
}


class _Ledger:
    """Contador agregado por run_id, compartilhado entre requisicoes concorrentes.

    Os caps por request (max_results, yt_live) limitam UMA chamada. Uma run deep
    faz dezenas de chamadas em rodadas e branches paralelos, entao sem um teto
    agregado nada impede uma run de rodar por horas (medido: ~10,5h). Este
    ledger e o teto agregado: guardado por run_id no processo do servico, com
    lock para que branches concorrentes nao gastem em dobro.

    Os limites chegam pela query (o cliente manda o que resolveu do perfil);
    o servico so impoe. Nunca inventa limite: sem run_id ou sem limites, o
    comportamento e o de antes.
    """

    def __init__(self, limits: dict[str, int]):
        self.limits = {k: int(v or 0) for k, v in limits.items()}
        self.used = {k: 0 for k in self.limits}
        self.started = time.monotonic()
        self.stop_reason: str | None = None
        # RLock, not Lock: snapshot() holds the lock and calls exhausted(),
        # which locks again. With a plain Lock that is a self-deadlock (it hung
        # /budget for real before this was fixed).
        self.lock = threading.RLock()

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def exhausted(self) -> str | None:
        with self.lock:
            if self.stop_reason:
                return self.stop_reason
            for k, used in self.used.items():
                limit = self.limits.get(k, 0)
                if limit and used >= limit:
                    return f"budget:{k}"
            tlimit = self.limits.get("time_s", 0)
            if tlimit and self.elapsed() >= tlimit:
                return "budget:time_s"
        return None

    def spend(self, counter: str, n: int = 1) -> bool:
        with self.lock:
            if counter not in self.used:
                return True
            limit = self.limits.get(counter, 0)
            if limit and self.used[counter] + n > limit:
                if self.stop_reason is None:
                    self.stop_reason = f"budget:{counter}"
                return False
            self.used[counter] += n
            return True

    def remaining(self, counter: str) -> int:
        """Unidades restantes do contador (sentinela grande se ilimitado)."""
        with self.lock:
            limit = self.limits.get(counter, 0)
            if not limit:
                return 10**9
            return max(0, limit - self.used.get(counter, 0))

    def snapshot(self) -> dict:
        with self.lock:
            return {"limits": dict(self.limits), "used": dict(self.used),
                    "elapsed_s": round(self.elapsed(), 1),
                    "stop_reason": self.exhausted()}


_LEDGERS: dict[str, _Ledger] = {}
_LEDGERS_LOCK = threading.Lock()
# Teto duro de ledgers vivos: sem isto, run_ids distintos (um por run) acumulam
# para sempre no processo de longa duracao do servico.
_LEDGERS_MAX = 64


def _ledger(run_id: str, limits: dict) -> _Ledger:
    """Recupera/cria o ledger do run, com teto de entradas (FIFO)."""
    with _LEDGERS_LOCK:
        led = _LEDGERS.get(run_id)
        if led is None:
            if len(_LEDGERS) >= _LEDGERS_MAX:
                oldest = next(iter(_LEDGERS))
                _LEDGERS.pop(oldest, None)
            led = _Ledger({k: v for k, v in limits.items() if v is not None})
            _LEDGERS[run_id] = led
        return led


async def search_all(query: str) -> list[Hit]:
    """Dispara as 4 fontes em paralelo e recolhe o que respondeu.

    O gather engole excecao, entao cada erro e registrado aqui com nome da fonte e
    query: e o unico lugar onde se ve que uma fonte morreu durante uma pesquisa.
    """
    names = list(SOURCE_PROBES)
    outcomes = await asyncio.gather(
        *(SOURCE_PROBES[name](query) for name in names),
        return_exceptions=True,
    )
    hits: list[Hit] = []
    for name, outcome in zip(names, outcomes, strict=True):
        if isinstance(outcome, SourceBlocked):
            logger.warning("fonte=%s query=%r bloqueada: %s", name, query, outcome)
        elif isinstance(outcome, BaseException):
            logger.warning(
                "fonte=%s query=%r falhou: %s: %s", name, query, type(outcome).__name__, outcome,
            )
        else:
            logger.info("fonte=%s query=%r -> %d resultados", name, query, len(outcome))
            hits.extend(outcome)
    return hits


def _select_hits(hits: list[Hit], cap: int | None = None) -> list[Hit]:
    """Dedup por url e corta em MAX_RESULTS, antes de qualquer leitura de pagina.

    O corte vem antes do enriquecimento de proposito: 12 e o contrato, e gastar
    leitura numa pagina de um item que depois seria descartado e orcamento jogado
    fora. Devolve os proprios objetos Hit, que o enriquecimento mexe in place.

    `cap` (opcional, via query param `max_results`): reduz o corte para perfis
    leves, sempre clampado a [1, MAX_RESULTS] -- nunca amplia o contrato.
    """
    limit = MAX_RESULTS if cap is None else max(1, min(MAX_RESULTS, int(cap)))
    selected: list[Hit] = []
    seen: set[str] = set()
    for hit in hits:
        if not hit.url or hit.url in seen:
            continue
        seen.add(hit.url)
        selected.append(hit)
        if len(selected) >= limit:
            break
    return selected


class _FetchedPage(Protocol):
    """O que este arquivo usa do FetchResult do cascade_fetcher, campo a campo.

    Protocol em vez do dataclass importado porque o import do cascade e opcional:
    se ele falhar, o retriever continua de pe e so perde o enriquecimento. O
    acoplamento fica explicito aqui, e nao escondido num import que pode nao
    existir. Se o cascade mudar um destes nomes, a troca para aqui e visivel.
    """

    text: str
    level: int
    from_cache: bool
    chars: int
    reason: str | None


# O callable do cascade, resolvido uma vez no import do modulo. None significa
# "enriquecimento indisponivel" e o chamador degrada para o snippet.
_cascade_fetch: Callable[[str], Awaitable[_FetchedPage]] | None = None


def load_cascade() -> None:
    """Importa o cascade_fetcher do diretorio fixo, uma vez, no startup.

    Import opcional e defensivo porque o vast roda com cwd em qualquer lugar e em
    mais de um interpretador: medido aqui, so
    /opt/data/home/.agent-reach-venv/bin/python tem trafilatura, bs4, playwright e
    curl_cffi; o python3 do sistema nao tem nenhum dos quatro. Se o import
    falhar isso e logado e o retriever sobe sem enriquecimento -- nunca derruba o
    servico inteiro por causa de um recurso opcional.
    """
    global _cascade_fetch
    if not ENRICH_ENABLED:
        logger.info("enriquecimento desligado por VAST_ENRICH=0; cascade nao importado")
        return
    try:
        sys.path.insert(0, CASCADE_DIR)
        from cascade_fetcher import fetch
    except Exception as exc:
        # ImportError e o caso comum; Exception cobre tambem um SyntaxError ou
        # um modulo que carrega e quebra na metade. Nada disso pode derrubar o
        # vast.
        logger.error(
            "cascade indisponivel em %s (%s: %s); busca segue sem enriquecimento",
            CASCADE_DIR, type(exc).__name__, exc,
        )
        return
    _cascade_fetch = fetch
    logger.info("cascade carregado de %s; enriquecimento ativo", CASCADE_DIR)


def _enrich_plan(hits: list[Hit]) -> list[Hit]:
    """Escolhe quem vai ser lido: round-robin entre as fontes, nao "os N primeiros".

    O custo por URL varia ~25x entre as fontes (github ~2.4s devolvendo texto
    real; youtube 24.5s com 0% de aproveitamento, por HTTP 429 e pagina
    anti-bot). Pegar os primeiros N do contrato entregaria o orcamento por sorte
    de ordenacao: a fonte cara, que nao devolve nada, comeria metade da verba e
    ainda assimeria a outra. O round-robin gasta o mesmo numero de slots em cada
    fonte e o teto por fonte impede uma delas de dominar.

    A ordem de insercao do dict preserva a ordem de primeira aparicao, entao o
    plano e deterministico: a mesma busca gera sempre o mesmo plano.
    """
    by_source: dict[str, list[Hit]] = {}
    for hit in hits:
        by_source.setdefault(hit.source, []).append(hit)

    plan: list[Hit] = []
    for round_index in range(ENRICH_MAX_PER_SOURCE):
        for group in by_source.values():
            if len(plan) >= ENRICH_MAX_PAGES:
                return plan
            if round_index < len(group):
                plan.append(group[round_index])
    return plan


def _is_repo_page(url: str) -> bool:
    """Diz se a URL e a pagina de um repositorio (e nao uma subpagina dele).

    A decisao de rota mora aqui e nao dentro do repo_readme porque quem chama
    precisa saber ANTES de gastar o orcamento: repo vai por README cru, o resto
    vai por pagina. `raw_readme_url` sozinho ja responde a isso, mas a funcao
    pode ter falhado no import -- e nesse caso nenhum hit e repo, que e o
    comportamento antigo.
    """
    if _raw_readme_url is None:
        return False
    try:
        return _raw_readme_url(url) is not None
    except Exception as exc:  # noqa: BLE001 - URL malformada nao pode derrubar o enrich
        logger.debug("raw_readme_url falhou em %r: %s: %s", url, type(exc).__name__, exc)
        return False


def strip_nav_run(text: str, host: str) -> tuple[str, list[str]]:
    """Corta a corrida de menu do comeco e devolve (texto, rotulos vistos).

    Medido: no bilibili os 7 rotulos ficam em ~60 chars seguidos logo depois do
    titulo -- `..._游戏热门视频 首页 番剧 直播 游戏中心 会员购 漫画 赛事 投稿` -- e o
    que vem DEPOIS deles e conteudo de verdade: a descricao (`简介`) e a lista de
    capitulos (`课程总结`), ~2.000 chars num video medido. Cortar no fim do ultimo
    rotulo da janela preserva esses 2.000 chars; rejeitar o resultado inteiro
    jogaria fora a unica descricao que o bilibili tem.

    Devolve o texto intacto e lista vazia quando o host nao tem rotulos
    conhecidos, ou quando nenhum rotulo aparece na janela. Quem chama decide o
    que fazer com o que sobrou -- e o gate so e doador de prova, nao de veredito.

    O `www.` e comido antes da consulta porque URL de video e sempre `www.` e o
    primeiro teste desta funcao (rodando pelo `_read_page` de verdade) nao
    disparou gate nenhum: comparava "www.bilibili.com" com a chave "bilibili" e
    devolvia o texto intacto. Falha silenciosa, do tipo que so aparece quando o
    codigo roda no caminho de verdade e nao no teste da unidade.
    """
    labels = CHROME_LABELS.get(host.lower().removeprefix("www."))
    if not labels:
        return text, []
    head = text[:CHROME_WINDOW]
    seen: list[str] = []
    cut = -1
    for label in labels:
        pos = head.find(label)
        if pos >= 0:
            seen.append(label)
            cut = max(cut, pos + len(label))
    if cut < 0:
        return text, []
    return text[cut:].lstrip(), seen


async def _try_read(
    hit: Hit,
    deadline: float,
    stats: Counter[str],
    *,
    call: Callable[[str], Awaitable[Any]],
    timeout: float,
    miss: str,
    label: str,
) -> Any | None:
    """Roda um leitor de URL dentro do prazo e devolve o resultado, ou None ja contado.

    Concentra o que as duas rotas novas (README, transcricao) fazem igual: respeitar
    o orcamento, distinguir timeout de erro, contar a falha na chave `miss` que o
    chamador passou e manter o conteudo que ja estava no item. A diferenca entre
    elas -- o que fazer com o texto que voltou -- fica nas poucas linhas de cada
    chamador.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0.0:
        stats[miss] += 1
        logger.warning("%s: orcamento estourado em %s; conteudo original mantido", label, hit.url)
        return None
    try:
        return await asyncio.wait_for(call(hit.url), timeout=min(remaining, timeout))
    except asyncio.TimeoutError:
        stats[miss] += 1
        logger.warning("%s: timeout em %s; conteudo original mantido", label, hit.url)
        return None
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        stats[miss] += 1
        logger.warning(
            "%s: falhou %s: %s: %s; conteudo original mantido", label, hit.url, type(exc).__name__, exc,
        )
        return None


async def _read_repo_readme(
    hit: Hit,
    deadline: float,
    stats: Counter[str],
) -> None:
    """Troca o snippet do gh pelo README cru do repo. Nunca levanta excecao.

    E o inverso do fallback que existia antes: se o README nao veio, NAO se cai na
    pagina HTML do GitHub. Aquele caminho devolveu 3.032 chars de menu de
    navegacao -- 82% das linhas iguais entre tres repositorios diferentes -- e um
    "repo sem README" dito com honestidade vale mais que esse menu. O snippet
    curto do `gh search` (owner/nome + descricao) continua de pe, e o contador
    diz readme_miss: isso e um resultado, nao uma falha.
    """
    if _fetch_repo_readme is None:
        return
    result = await _try_read(
        hit, deadline, stats, call=_fetch_repo_readme, timeout=README_TIMEOUT_S,
        miss="readme_miss", label="README",
    )
    if result is None:
        return
    if result.chars > 0:
        hit.raw_content = result.text
        stats["readme_ok"] += 1
        stats["chars"] += result.chars
        return
    stats["readme_miss"] += 1
    logger.info("README ausente em %s: %s; snippet do gh mantido", hit.url, result.reason)


async def _read_pool(
    hits: list[Hit],
    deadline: float,
    stats: Counter[str],
    reader: Callable[[Hit, float, Counter[str]], Awaitable[None]],
    concurrency: int,
    gate: _YtGate | None = None,
) -> None:
    """Roda um reader em varios hits, `concurrency` em voo, ate o prazo. Nunca levanta.

    O semaphore nasce por chamada e nao e constante global: o limite e por
    request, e um global sobrevive entre requests e deixaria duas requisicoes
    simultaneas virarem o dobro de yt-dlp ao mesmo tempo.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def one(hit: Hit) -> None:
        async with semaphore:
            if gate is None:
                await reader(hit, deadline, stats)
            else:
                await reader(hit, deadline, stats, gate)  # type: ignore[call-arg]

    await asyncio.gather(*(one(hit) for hit in hits), return_exceptions=True)


async def _read_yt_pool(
    hits: list[Hit],
    deadline: float,
    stats: Counter[str],
    gate: _YtGate,
) -> None:
    """Pool de transcricao que fecha a porta para o pool de paginas.

    O `finally` e o ponto: mesmo cancelado pelo orcamento da request, o pool avisa
    quem estava esperando, senao o grupo do YouTube ficaria esperando uma conta que
    nunca fecha e perderia o orcamento de pagina inteiro.
    """
    try:
        await _read_pool(hits, deadline, stats, _read_transcript, YT_ENRICH_CONCURRENCY, gate)
    finally:
        gate.done.set()


# Rótulos explicitos de status de transcricao no Hit. transcript_ok e
# transcript_cache sao separados pelo mesmo motivo de yt_ok/yt_cache: um "ok"
# que nao saiu na rede e a mesma mentira de um relatorio que contou cache como
# enriquecimento. transcript_absent (sem legenda, motivo honesto) e
# transcript_error (timeout/orcamento/erro) dizem por que ficou so a descricao.
TRANSCRIPT_OK: Final[str] = "transcript_ok"
TRANSCRIPT_CACHE: Final[str] = "transcript_cache"
TRANSCRIPT_ABSENT: Final[str] = "transcript_absent"
TRANSCRIPT_ERROR: Final[str] = "transcript_error"


def _auto_label(value: bool | None) -> str:
    """Rotula automatic para o trace: True/False/unknown, nunca vazio."""
    if value is True:
        return "True"
    if value is False:
        return "False"
    return "unknown"


def _segment_spoken(text: str, width: int = 900) -> list[str]:
    """Corta o texto falado em segmentos de ate `width` chars sem partir palavra.

    Cada segmento sobrevivente carrega o proprio rotulo de tipo: o chunking
    downstream (RecursiveCharacterTextSplitter 1000/100, site-packages) parte
    o texto em janelas arbitrarias e so o 1o chunk herda o cabecalho
    `[transcript ...]`. Com segmentos de ~900 chars, qualquer janela de 1000
    chars contem ao menos um rotulo `[spoken i/M]` -- o tipo viaja no texto,
    nao depende de metadado que o pretty_print descarta (so source/title
    chegam as mensagens, verificado no installed prompts.py:557-561).
    """
    words = text.split()
    segs, cur = [], ""
    for w in words:
        add = (w if not cur else " " + w)
        if len(cur) + len(add) > width and cur:
            segs.append(cur)
            cur = w
        else:
            cur += add
    if cur:
        segs.append(cur)
    return segs


def _format_transcript_section(result: Any, limit: int) -> tuple[str, str]:
    """Monta a secao rotulada de transcricao e diz se ela foi cortada.

    Devolve (secao, status_extra): a secao e o bloco "[transcript ...]..." pronto
    para colar depois da descricao, e o status_extra e "" ou
    `transcript_truncated_at_N` quando o texto estourou o `limit`. O corte aqui e
    PRE-truncamento: garante que a secao caiba no RAW_CONTENT_LIMIT sem comer a
    descricao nem a URL, antes do corte final do as_contract_item().
    O texto falado sai em segmentos rotulados `[spoken i/M]`: cada chunk
    sobrevivente ao chunking downstream carrega o tipo no proprio texto.
    """
    text = result.text
    truncated_at: int | None = None
    if len(text) > limit:
        text = text[:limit]
        truncated_at = limit
    segs = _segment_spoken(text)
    n = len(segs)
    labeled = "\n".join(f"[spoken {i}/{n}]\n{s}" for i, s in enumerate(segs, 1))
    section = (
        f"\n\n[transcript origin={result.method} lang={result.lang} "
        f"automatic={_auto_label(result.automatic)} chars={result.chars} "
        f"segments={n}]\n{labeled}"
    )
    extra = f"transcript_truncated_at_{truncated_at}" if truncated_at is not None else ""
    return section, extra


def _apply_transcript(hit: Hit, result: Any) -> None:
    """Cola a transcricao no hit como secao rotulada, sem tocar no resto.

    Titulo, descricao-base e URL ficam intactos: a transcricao e ADICAO com o
    cabecalho [transcript ...], de modo que e evidente onde a descricao termina
    e onde comeca o conteudo falado. Os campos transcript_* do hit registram
    origem/idioma/automatic/chars/status para o trace e para a geracao.
    """
    section, extra = _format_transcript_section(result, RAW_CONTENT_LIMIT)
    hit.raw_content = f"[description]\n{hit.raw_content}{section}"
    hit.transcript_origin = result.method
    hit.transcript_lang = result.lang
    hit.transcript_automatic = result.automatic
    hit.transcript_chars = result.chars
    status = TRANSCRIPT_CACHE if result.method == _YT_METHOD_CACHE else TRANSCRIPT_OK
    hit.transcript_status = f"{status}+{extra}" if extra else status


async def _read_transcript(
    hit: Hit,
    deadline: float,
    stats: Counter[str],
    gate: _YtGate | None = None,
) -> None:
    """Enriquece o video com a transcricao como secao ADICIONADA. Nunca levanta.

    A descricao-base (`YouTube: {titulo}\\n{descricao[:400]}`) e a isca: no video
    medido ela tinha 128 chars contra 18.527 da transcricao, 145x mais. A
    transcricao entra como secao rotulada DEPOIS dela (_apply_transcript), nunca
    no lugar -- o caminho antigo trocava e apagava a fronteira entre descricao
    e fala. Quando a transcricao nao vem, a descricao fica como estava, e o hit
    ganha o transcript_status explicito (absent/error) em vez de silencio.
    """
    if _fetch_transcript is None:
        return
    if hit.transcript_chars > 0:
        # Fase A (cache-first em enrich_results) ja resolveu este video: refetch
        # seria um yt-dlp inteiro por um texto que ja esta no hit.
        return
    result = await _try_read(
        hit, deadline, stats, call=_fetch_transcript, timeout=YT_FETCH_TIMEOUT_S,
        miss="yt_miss", label="transcricao",
    )
    if result is None:
        # _try_read ja contou yt_miss (timeout/orcamento/erro): o status diz o
        # mesmo no hit, para o trace nao depender de juntar dois contadores.
        hit.transcript_status = TRANSCRIPT_ERROR
        logger.info("transcricao erro em %s; descricao mantida", hit.url)
        return
    if result.chars <= 0:
        stats["yt_miss"] += 1
        hit.transcript_status = TRANSCRIPT_ABSENT
        logger.info("transcricao ausente em %s: %s; descricao mantida", hit.url, result.reason)
        return

    # yt_ok e so rede de verdade; yt_cache e acerto de cache. Sao separados
    # porque um "ok" que nao saiu na rede e a mesma mentira de um relatorio que
    # contou cache como enriquecimento.
    if result.method == _YT_METHOD_CACHE:
        stats["yt_cache"] += 1
    else:
        stats["yt_ok"] += 1
    _apply_transcript(hit, result)
    stats["chars"] += result.chars
    if gate is not None:
        # Avisa o pool de paginas: este video ja tem conteudo de verdade, e a
        # pagina HTML dele nao precisa ser lida.
        gate.urls.add(hit.url)
    logger.info(
        "transcricao %s %s: %d chars, %d segmentos lang=%s automatic=%s status=%s",
        result.method, hit.url, result.chars, result.segments,
        result.lang, _auto_label(result.automatic), hit.transcript_status,
    )


async def _read_page(
    hit: Hit,
    deadline: float,
    stats: Counter[str],
    gate: _YtGate | None = None,
) -> None:
    """Le uma pagina e troca o snippet pelo texto real. Nunca levanta excecao.

    Toda falha mantem o raw_content original e conta no stats: um item sem
    enrichment e melhor que um item perdido, e quem consome nao tem como
    distinguir "a fonte nao respondeu" do "resultado sumiu".

    Dois desvios, ambos medidos:
    - hit de repo do GitHub vai por README cru (ver _read_repo_readme);
    - hit de video que ganhou transcricao nao le a pagina HTML: o caminho de
      pagina/browser do YouTube esta morto nesta maquina (HTTP 429 em todas as
      tentativas, pagina anti-bot de 298 chars no level 3) e so produzia espera --
      era o que o `timeout=2` de cada consulta media. A espera pelo veredito da
      transcricao e limitada por YT_PAGE_WAIT_S para sobrar tempo da leitura de
      pagina no video que NAO ganhou transcricao, que e o unico caso em que ela
      ainda serve.
    """
    if _is_repo_page(hit.url) and _fetch_repo_readme is not None:
        await _read_repo_readme(hit, deadline, stats)
        return

    # A transcricao ganha da pagina, sempre e sem depender do gate: o gate so
    # existe quando ha transcricao live em voo (fase B), mas a fase A (cache)
    # resolve antes dele nascer -- sem este guarda, a pagina HTML Sobrescreveria
    # o transcript que o cache ja colocou no hit. Video com fala transcrita
    # nunca volta a ser pagina.
    if hit.source == "youtube" and hit.transcript_chars > 0:
        stats["skipped"] += 1
        logger.info("pagina nao lida em %s: a transcricao ja cobre este video", hit.url)
        return
    if gate is not None and hit.source == "youtube":
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(
                gate.done.wait(),
                # Nao espera ate acabar o prazo: espera no maximo o que sobra depois
                # de uma leitura de pagina. Sem esse teto, uma transcricao lenta
                # consome o orcamento inteiro e o fallback de descricao some por
                # indireto -- e ele existe como fallback justamente nos videos sem
                # transcricao.
                timeout=max(0.0, min(deadline - time.monotonic(), YT_PAGE_WAIT_S)),
            )
        if hit.url in gate.urls:
            stats["skipped"] += 1
            logger.info("pagina nao lida em %s: a transcricao ja cobre este video", hit.url)
            return

    fetch = _cascade_fetch
    if not ENRICH_ENABLED or fetch is None:
        stats["skipped"] += 1
        return

    remaining = deadline - time.monotonic()
    if remaining <= 0.0:
        stats["skipped"] += 1
        return

    try:
        result = await asyncio.wait_for(
            fetch(hit.url), timeout=min(remaining, ENRICH_PAGE_TIMEOUT_S),
        )
    except asyncio.TimeoutError:
        stats["timeout"] += 1
        logger.warning("enriquecimento: timeout em %s; snippet mantido", hit.url)
        return
    except Exception as exc:
        stats["failed"] += 1
        logger.warning(
            "enriquecimento: falhou %s: %s: %s", hit.url, type(exc).__name__, exc,
        )
        return

    if result.level == 0:
        # level 0 e o caso "nao li nada e nao inventei nada": text vem vazio e
        # o motivo vem no reason. O snippet do CLI e melhor que texto vazio.
        stats["failed"] += 1
        logger.warning("enriquecimento: nada lido em %s: %s", hit.url, result.reason)
        return

    # Gate de chrome. O level 2 e a PAGINA INTEIRA, menu de navegacao incluso, e
    # subir o teto de raw_content de 2.000 para 20.000 passou a embutir esse
    # menu inteiro no relatorio: medido, um video do bilibili ia de 803 chars
    # reais para 2.221 chars comecando em "首页 番剧 直播 游戏中心 会员购 漫画
    # 赛事". O chrome nao era novo -- ele ja existia e o corte antigo o escondera
    # por acidente. A regra e a do GitHub: conteudo generico de pagina nunca
    # substitui conteudo real. Corta-se a corrida de menu, e o que sobrar so entra
    # se valer mais que o snippet que a busca ja deu.
    is_bili = hit.source == "bilibili"
    cleaned, chrome = strip_nav_run(result.text, (urlsplit(hit.url).hostname or "").lower())
    text, chars = result.text, result.chars
    if chrome:
        if len(cleaned) < max(MIN_CLEAN_CHARS, len(hit.raw_content)):
            stats["skipped"] += 1
            if is_bili:
                stats["bili_chrome"] += 1
            logger.warning(
                "cascata devolveu menu de navegacao em %s (nivel=%d, %d rotulos, %d chars uteis "
                "depois do corte); snippet mantido", hit.url, result.level, len(chrome), len(cleaned),
            )
            return
        text, chars = cleaned, len(cleaned)
        if is_bili:
            stats["bili_chrome"] += 1
        logger.warning(
            "cascata devolveu menu de navegacao em %s (nivel=%d, %d rotulos: %s); corrida de "
            "menu cortada, %d chars mantidos", hit.url, result.level, len(chrome), ",".join(chrome), chars,
        )
    elif is_bili:
        # Gate passou: e assim que bili_ok/bili_cache se separam, com o mesmo
        # cuidado de ok=/cache= -- rede de um lado, acerto de cache do outro.
        stats["bili_cache" if result.from_cache else "bili_ok"] += 1

    if result.from_cache:
        stats["cache"] += 1
    else:
        stats["ok"] += 1
    stats["chars"] += chars
    # Guarda o texto inteiro, sem cortar: o truncamento pertence a
    # as_contract_item(), que ja corta em RAW_CONTENT_LIMIT, e dois donos do
    # mesmo limite e uma regra que se contradiz. Um timeout pode abandonar uma
    # tentativa do cascade no meio (uma thread de extracao via to_thread
    # termina e e descartada): isso e uma leitura parcial aceita, nao
    # corrupcao, porque quem nao termina volta com o snippet e nao com texto
    # pela metade.
    #
    # Transcricao nunca e sobrescrita pela pagina: o guarda no topo desta
    # funcao ja pula video com transcript_chars > 0, e esta segunda checagem
    # cobre qualquer caminho futuro que chegue aqui sem passar por ele. Pagina
    # HTML do YouTube e 429/antibot medidos contra fala transcrita -- nao ha
    # empate a desempatar.
    if hit.source != "youtube" or hit.transcript_chars <= 0:
        hit.raw_content = text


async def _read_group(
    hits: list[Hit],
    deadline: float,
    stats: Counter[str],
    gate: _YtGate | None = None,
) -> None:
    """Le as paginas de um mesmo dominio em sequencia, uma por vez.

    O throttle do cascade e um asyncio.sleep apoiado num dicionario global de
    "ultimo acesso por dominio", nao um lock: duas corrotinas do mesmo host
    saem juntas e furam o intervalo minimo. Sequencial dentro do dominio e o que
    mediu a cadencia de ~2.4s no grupo do github; grupos de dominios diferentes
    correm em paralelo, que ai nao ha limite a respeitar.
    """
    for hit in hits:
        await _read_page(hit, deadline, stats, gate)


async def enrich_results(hits: list[Hit], query: str,
                         yt_live: int | None = None,
                         ledger: "_Ledger | None" = None) -> None:
    """Le as paginas do plano em paralelo por dominio, dentro de um orcamento.

    Tres rotas, cada uma com o seu orcamento e o seu teto, todas em paralelo:
    pagina (o que ja existia, sequencial dentro do dominio), README cru de repo
    (barato, e o unico caminho de repo do GitHub) e transcricao de video (a mais
    cara, 3 por request).

    O stats e um Counter compartilhado entre as tarefas, mexido sem await entre
    ler e escrever. E de proposito: e assim que a contagem continua correta para
    uma tarefa cancelada no meio do orcamento, coisa que coletar valor de
    retorno nao faria (tarefa cancelada nao devolve nada). Um log por request e
    a observabilidade do bonus inteiro -- sem ele nao ha como saber se o
    enriquecimento esta lendo, falhando ou so custando tempo.
    """
    plan = _enrich_plan(hits)
    stats: Counter[str] = Counter()

    # Repo do GitHub sai do plano de paginas: ele vai por README cru, e o plano
    # so existe para paginas. Um hit de repo que sobrou fora do plano (o plano
    # corta em ENRICH_MAX_PAGES) entra assim mesmo no README, porque o README e
    # barato e o miss dele e honesto -- e sao eles que somam em readme_miss.
    repo_hits = [hit for hit in hits if _is_repo_page(hit.url) and _fetch_repo_readme is not None]
    if len(repo_hits) > README_MAX:
        for hit in repo_hits[README_MAX:]:
            stats["readme_miss"] += 1
            logger.info("README acima do teto de %d por request: %s", README_MAX, hit.url)
        repo_hits = repo_hits[:README_MAX]
    page_plan = [hit for hit in plan if not _is_repo_page(hit.url)]

    # Transcricao em DUAS fases, sobre o `selected` (pos-selecao), e nao sobre o
    # corpus inteiro:
    #
    # Fase A (cache-first, SEM limite): todo video do YouTube no selected passa
    # pelo peek_transcript, que e so leitura de SQLite -- sem rede, sem yt-dlp,
    # sem orcamento. E isto que corrige a causa (c): antes, o slice
    # [:YT_ENRICH_MAX] aplicado no corpus pre-selecao deixava a maioria dos
    # videos fora do yt_hits, e os que a selecao mantinha chegavam a geracao
    # com titulo+descricao apenas. Agora, o que ja esta em disco entra em todo
    # video selecionado, independente da posicao.
    #
    # Fase B (live, teto YT_ENRICH_MAX inalterado): so os videos que o cache nao
    # resolveu disputam os 3 slots de rede, na ordem do selected. O teto, o
    # orcamento e a concorrencia nao mudam -- continua cabendo no endpoint sem
    # virar uma busca de legenda.
    #
    # VAST_YT_ENRICH=0 desliga as duas fases (a pagina continua).
    yt_hits: list[Hit] = []
    if YT_ENRICH_ENABLED and _fetch_transcript is not None:
        yt_all = [hit for hit in hits if hit.source == "youtube"]
        if _peek_transcript is not None:
            for hit in yt_all:
                try:
                    cached = _peek_transcript(hit.url)
                except Exception as exc:  # noqa: BLE001 - peek nunca derruba o enrich
                    logger.debug("peek de transcricao falhou em %s: %s: %s",
                                 hit.url, type(exc).__name__, exc)
                    cached = None
                if cached is not None and cached.chars > 0:
                    _apply_transcript(hit, cached)
                    stats["yt_cache"] += 1
                    stats["chars"] += cached.chars
                    logger.info(
                        "transcricao %s %s: %d chars lang=%s automatic=%s status=%s (fase A)",
                        cached.method, hit.url, cached.chars,
                        cached.lang, _auto_label(cached.automatic), hit.transcript_status,
                    )
        unresolved = [hit for hit in yt_all if hit.transcript_chars <= 0]
        live_cap = YT_ENRICH_MAX if yt_live is None else max(
            0, min(YT_ENRICH_MAX, int(yt_live)))
        if ledger is not None:
            # Teto agregado do run manda: nunca mais que o que resta do orcamento
            # global, mesmo que o cap por request seja maior.
            live_cap = min(live_cap, ledger.remaining("yt_live_fetches"))
        yt_hits = unresolved[:live_cap]
        if ledger is not None and yt_hits:
            ledger.spend("yt_live_fetches", len(yt_hits))
        for hit in unresolved[live_cap:]:
            # Fora do teto live E sem cache: ficou a descricao, dito em voz
            # alta no hit. Nao conta yt_miss (nada foi tentado); o status no
            # hit e a evidencia.
            hit.transcript_status = TRANSCRIPT_ABSENT
            logger.info(
                "transcricao acima do teto live de %d por request: %s; descricao mantida",
                live_cap, hit.url,
            )

    tasks: list[asyncio.Task[None]] = []
    gate: _YtGate | None = None
    yt_deadline = time.monotonic() + YT_ENRICH_BUDGET_S
    if YT_ENRICH_ENABLED and yt_hits:
        # A porta so existe quando ha transcricao para ganhar. Com
        # VAST_YT_ENRICH=0 (ou sem o modulo) o video vai direto para a pagina
        # HTML como antes, sem esperar nada.
        gate = _YtGate(done=asyncio.Event(), urls=set())

    if page_plan and ENRICH_ENABLED and _cascade_fetch is not None:
        # Aggregate budget FIRST: extractions are the expensive unit (one live
        # fetch per page). When the run's allowance runs out, drop the tail of
        # the plan before any task is created, so the run finishes with what it
        # already has instead of starting work it cannot afford.
        if ledger is not None:
            allowed = ledger.remaining("extractions")
            if allowed < len(page_plan):
                dropped = page_plan[allowed:]
                page_plan = page_plan[:allowed]
                stats["skipped"] += len(dropped)
                logger.info(
                    "query=%r orcamento do run: %d extracoes restantes, %d "
                    "paginas puladas por teto agregado",
                    query, allowed, len(dropped))
            if page_plan:
                ledger.spend("extractions", len(page_plan))
        groups: dict[str, list[Hit]] = {}
        for hit in page_plan:
            host = (urlsplit(hit.url).hostname or "").lower() or "sem-host"
            groups.setdefault(host, []).append(hit)

        deadline = time.monotonic() + ENRICH_TOTAL_BUDGET_S
        # O grupo do YouTube pode passar tempo esperando a conta da transcricao (que
        # dura ate 25s), entao ele ganha o prazo MAIOR como deadline proprio. Sem
        # isso, um video sem transcricao perderia a leitura da pagina por ter
        # esperado um veredito que so o yt-dlp da, e o orcamento de 20s ja estaria
        # gasto quando a pagina fosse lida. Medido, esse caminho de pagina e 0% de
        # aproveitamento -- mas "medido como 0%" nao e "nao existe", e nenhum
        # caminho de leitura e apagado aqui por indireto.
        group_deadline = max(deadline, yt_deadline) if gate is not None else deadline
        tasks = [
            asyncio.create_task(_read_group(group, group_deadline, stats, gate))
            for group in groups.values()
        ]
    else:
        stats["skipped"] += len(page_plan)

    if repo_hits:
        # Duas em voo, e nao um por host como a pagina fazia: cada README e um
        # arquivo de 4-9k num host estatico do GitHub, sem o rate limit de 2s do
        # cascade. Medido: 0.3s com o cache quente, ~4.5s quando o repo nao tem
        # README (o cascade sobe para o navegador antes de desistir, e sobe
        # mesmo em 404) -- por isso o teto e os 2 em voo. Desde o cache negativo
        # do repo_readme, so a primeira query de cada repo paga esse preco.
        tasks.append(asyncio.create_task(_read_pool(
            repo_hits, time.monotonic() + ENRICH_TOTAL_BUDGET_S, stats,
            _read_repo_readme, README_CONCURRENCY,
        )))
    if yt_hits:
        assert gate is not None
        tasks.append(asyncio.create_task(_read_yt_pool(yt_hits, yt_deadline, stats, gate)))

    if tasks:
        # O teto da espera e o maior dos dois orcamentos: quem acaba primeiro se
        # cancela sozinho pelo deadline interno dele, e o cancelamento final
        # abaixo cobre o resto.
        budget = max(ENRICH_TOTAL_BUDGET_S, YT_ENRICH_BUDGET_S if yt_hits else 0.0)
        await asyncio.wait(tasks, timeout=max(0.0, budget))
        # Cancelar o que sobrou e obrigatorio, nao hygiene: uma tarefa
        # pendente continuaria rodando depois da resposta, segurando o lock do
        # browser do cascade e as conexoes HTTP que a proxima requisicao
        # precisa.
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # plano= conta as DUAS rotas que saem do plano de paginas (as de sempre, mais
    # o README cru), e por isso que a soma fecha: ok + cache + falhas + timeout +
    # pulados + readme_ok + readme_miss da o plano inteiro; yt_ok + yt_cache +
    # yt_miss da o que saiu fora dele (transcricao tem teto proprio). chars= e o
    # texto que trocou snippet, de qualquer rota. ok= so fetch ao vivo, cache= so
    # acerto de cache: um relatorio que contou cache como "enriquecido" e o
    # numero que ja mentiu uma vez nesta maquina (plano=6 ok=0 cache=4 vira "8 de
    # 12 enriquecidos" se voce somar errado). Os tres bili_* sao uma VISADA do
    # gate sobre os itens de bilibili, mutually exclusive e fora da soma do plano:
    # bili_ok/bili_cache e so o que passou limpo (rede e cache separados, como
    # ok=/cache=), e bili_chrome e o que o cascade entregou como menu -- nesse
    # caso ou o menu foi cortado ou o snippet da busca foi mantido, e as duas
    # coisas ja aparecem em ok=/cache= ou pulados=.
    logger.info(
        "query=%r enriquecimento: plano=%d ok=%d cache=%d falhas=%d timeout=%d "
        "pulados=%d chars=%d yt_ok=%d yt_cache=%d yt_miss=%d readme_ok=%d readme_miss=%d "
        "bili_ok=%d bili_cache=%d bili_chrome=%d",
        query, len(page_plan) + len(repo_hits), stats["ok"], stats["cache"], stats["failed"],
        stats["timeout"], stats["skipped"], stats["chars"],
        stats["yt_ok"], stats["yt_cache"], stats["yt_miss"],
        stats["readme_ok"], stats["readme_miss"],
        stats["bili_ok"], stats["bili_cache"], stats["bili_chrome"],
    )


@app.get("/")
async def search(query: str = Query(..., description="Search query"),
                 max_results: int | None = Query(
                     default=None,
                     description="Reduz o corte de selecao para perfis leves; "
                                 "clampado a [1, 12], nunca amplia o contrato."),
                 yt_live: int | None = Query(
                     default=None,
                     description="Reduz o teto live de transcricoes; "
                                 "clampado a [0, 3]. Cache-first (fase A) "
                                 "nao tem limite e nao e afetado."),
                 run_id: str | None = Query(
                     default=None,
                     description="Orcamento agregado por run: com run_id, o "
                                 "servico conta queries/extractions/yt_live "
                                 "DESTE run entre todas as requisicoes "
                                 "concorrentes e recusa quando estoura."),
                 budget_queries: int | None = Query(
                     default=None, description="Teto de queries do run (0=ilimitado)."),
                 budget_extractions: int | None = Query(
                     default=None, description="Teto de extracoes do run."),
                 budget_yt_live: int | None = Query(
                     default=None, description="Teto de fetches live de transcricao do run."),
                 budget_time_s: int | None = Query(
                     default=None, description="Teto de tempo do run em segundos."),
                 checkpoint_dir: str | None = Query(
                     default=None,
                     description="Diretorio da run: quando dado, o servico grava "
                                 "os hits no checkpoint.jsonl DURANTE a coleta "
                                 "(o vast e processo separado, entao o wrapper "
                                 "in-process do cliente nunca ve os hits)."),
                 ) -> JSONResponse:
    """Endpoint do GPT Researcher CustomRetriever: GET /?query=... -> lista de ate 12.

    O contrato (url, title, raw_content, source; no maximo MAX_RESULTS) e o que
    o GPT Researcher consome, entao a forma da resposta nao muda aqui: o que muda
    e nunca encher a lista com resultado que nao veio da query.
    """
    if not query or not query.strip():
        return JSONResponse([])

    ledger = None
    if run_id:
        ledger = _ledger(run_id, {
            "queries": budget_queries, "extractions": budget_extractions,
            "yt_live_fetches": budget_yt_live, "time_s": budget_time_s,
        })
        stop = ledger.exhausted()
        if stop:
            logger.warning("run=%s orcamento esgotado (%s): recusando query", run_id, stop)
            return JSONResponse([])
        ledger.spend("queries", 1)

    hits = await search_all(query)
    selected = _select_hits(hits, cap=max_results)
    # Sem try/except em volta do enriquecimento, de proposito: cada pagina
    # engole o proprio erro e mantem o snippet, entao nao ha caminho em que
    # isto levante para dentro do endpoint. Um guard aqui seria ruido
    # escondendo bug.
    await enrich_results(selected, query, yt_live=yt_live, ledger=ledger)

    items = [hit.as_contract_item() for hit in selected]

    if checkpoint_dir:
        # The vast runs as its own process: the client's in-process probe
        # wrapper never sees these hits, so the service writes the checkpoint
        # itself. Best-effort — a checkpoint failure must never break a search.
        try:
            import run_checkpoint as _rc
            _ck = _rc.Checkpoint(checkpoint_dir)
            for hit in selected:
                _ck.note_source(
                    hit.url, source=hit.source, title=hit.title,
                    content=hit.raw_content or "",
                    evidence_type=("transcript" if hit.transcript_chars else ""),
                    chars=hit.transcript_chars or None)
            _ck.note_query_done(query, n_sources=len(selected))
        except Exception as exc:  # noqa: BLE001 - checkpoint is best-effort
            logger.warning("checkpoint_dir=%r falhou: %s: %s",
                           checkpoint_dir, type(exc).__name__, exc)

    logger.info("query=%r devolveu %d itens de %d resultados brutos", query, len(items), len(hits))
    return JSONResponse(items)


_health_cache: dict[str, tuple[float, SourceHealth]] = {}
_health_lock = asyncio.Lock()


async def probe_source(name: str, probe: SourceProbe) -> SourceHealth:
    """Sonda uma fonte chamando a MESMA funcao de busca que o / usa.

    Verificar so se o binario existe nao prova nada: o gh sem token esta no PATH e
    mesmo assim nao responde. Sonda com a funcao real, o resultado real e o erro
    real sao a unica evidencia confiavel de que a fonte esta viva.
    """
    started = time.monotonic()
    try:
        hits = await probe(HEALTH_PROBE_QUERY)
    except SourceBlocked as exc:
        return SourceHealth(name, STATE_BLOCKED, _one_line(str(exc))[:STDERR_SNIPPET], None, _utc_now())
    except SourceError as exc:
        return SourceHealth(name, STATE_BROKEN, _one_line(str(exc))[:STDERR_SNIPPET], None, _utc_now())
    except Exception as exc:
        logger.exception("fonte=%s erro inesperado na sondagem", name)
        return SourceHealth(name, STATE_BROKEN, f"{type(exc).__name__}: {exc}"[:STDERR_SNIPPET], None, _utc_now())

    latency_ms = int((time.monotonic() - started) * 1000)
    if hits:
        return SourceHealth(
            name, STATE_WORKING, f"{len(hits)} resultados em {latency_ms / 1000:.1f}s", latency_ms, _utc_now(),
        )
    return SourceHealth(
        name, STATE_DEGRADED, f"0 resultados em {latency_ms / 1000:.1f}s (normal para esta query)",
        latency_ms, _utc_now(),
    )


def _overall_status(sources: list[SourceHealth]) -> str:
    """'ok' so quando todas responderam; 'degraded' com alguma morta; 'broken' se todas."""
    dead = [source for source in sources if source.state in (STATE_BROKEN, STATE_BLOCKED)]
    if len(dead) == len(sources):
        return STATE_BROKEN
    if dead:
        return STATE_DEGRADED
    return STATE_WORKING


@app.get("/budget")
async def budget_status(run_id: str = Query(..., description="Run id")) -> JSONResponse:
    """Consumo AGREGADO do run, do lado de quem de fato gasta.

    O cliente nao ve o gasto: quem faz fetch/transcricao e este processo. Sem
    este endpoint o cliente registraria `used: 0` para tudo e o artefato
    mentiria por omissao. Aqui o numero e o real, com o mesmo lock do ledger.
    """
    with _LEDGERS_LOCK:
        led = _LEDGERS.get(run_id)
    if led is None:
        return JSONResponse({"run_id": run_id, "known": False,
                             "limits": {}, "used": {}, "elapsed_s": 0.0,
                             "stop_reason": None})
    snap = led.snapshot()
    snap.update({"run_id": run_id, "known": True})
    return JSONResponse(snap)


@app.get("/health")
async def health() -> dict[str, object]:
    """Estado real de cada fonte, com cache de HEALTH_CACHE_TTL.

    A versao anterior devolvia uma lista fixa de nomes e um "ok" permanente: ela
    respondia "4 fontes ok" com 3 mortas, que e a unica coisa que um health check
    nao pode fazer. O status global e derivado das sondagens, nao escolhido a mao.
    """
    now = time.monotonic()
    fresh = {name: entry for name, (_, entry) in _health_cache.items() if now - _health_cache[name][0] < HEALTH_CACHE_TTL}
    pending = [name for name in SOURCE_PROBES if name not in fresh]

    if pending:
        async with _health_lock:
            # Re-checar dentro do lock evita a estampida: varias chamadas
            # simultaneas de /health nao devem disparar as mesmas 4 sondagens.
            now = time.monotonic()
            fresh = {
                name: entry
                for name, (_, entry) in _health_cache.items()
                if now - _health_cache[name][0] < HEALTH_CACHE_TTL
            }
            pending = [name for name in SOURCE_PROBES if name not in fresh]
            if pending:
                probed = await asyncio.gather(
                    *(probe_source(name, SOURCE_PROBES[name]) for name in pending),
                    return_exceptions=True,
                )
                for name, outcome in zip(pending, probed, strict=True):
                    if isinstance(outcome, BaseException):
                        logger.exception("fonte=%s falhou ao sondar", name, exc_info=outcome)
                        entry = SourceHealth(name, STATE_BROKEN, "sondagem quebrou", None, _utc_now())
                    else:
                        entry = outcome
                    fresh[name] = entry
                    _health_cache[name] = (time.monotonic(), entry)

    ordered = [fresh[name] for name in SOURCE_PROBES]
    return {
        "status": _overall_status(ordered),
        "checked_at": _utc_now(),
        "sources": [source.as_json() for source in ordered],
    }


def log_content_limits() -> None:
    """Loga o teto daqui e o teto la do GPT Researcher, e reclama se divergirem.

    Fica no fim do arquivo, e nao junto da constante, por causa do
    logging.basicConfig: um logger.info antes dele seria descartado pelo
    lastResort, que so mostra WARNING. MAX_CONTENT_CHARS MENOR que
    RAW_CONTENT_LIMIT nao quebra nada -- o GPT Researcher corta antes do chunking,
    entao o texto maior nunca chega a ser lido, e nao da para ver. E o unico jeito
    de um teto parecer funcionando sem funcionar.
    """
    logger.info(
        "raw_content: RAW_CONTENT_LIMIT=%d MAX_CONTENT_CHARS=%d (teto efetivo do GPT Researcher)",
        RAW_CONTENT_LIMIT, _EFFECTIVE_MAX_CONTENT_CHARS,
    )
    if _EFFECTIVE_MAX_CONTENT_CHARS < RAW_CONTENT_LIMIT:
        logger.warning(
            "MAX_CONTENT_CHARS=%d e MENOR que RAW_CONTENT_LIMIT=%d: o GPT Researcher trunca em "
            "silencio ANTES do chunking e %d chars por item nunca serao lidos",
            _EFFECTIVE_MAX_CONTENT_CHARS, RAW_CONTENT_LIMIT,
            RAW_CONTENT_LIMIT - _EFFECTIVE_MAX_CONTENT_CHARS,
        )


load_github_token()
load_cascade()
log_content_limits()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
