#!/usr/bin/env python3
"""
Transcricao de video do YouTube (yt-dlp --write-subs) com cache em disco.

POR QUE ESTE MODULO EXISTE
-------------------------
O vast buscava video pelo yt-dlp e devolvia, como raw_content, so a descricao
(`YouTube: {titulo}\\n{descricao[:400]}`). Medido nesta maquina: 128 chars de
descricao contra 18.527 chars de transcricao de um video de 18min -- 145x mais
conteudo. A descricao e a isca ("Neural networks" como titulo), nao o assunto
do video. Quem resumia o video citava a isca como se fosse conteudo.

O caminho antigo de leitura de pagina do YouTube nao resolvia: 24.5s por URL,
HTTP 429 em todas as tentativas de level 1/2 e uma pagina anti-bot de 298 chars
no level 3 (-- bloqueio no IP do datacenter, ja que a primeira tentativa ja era
429). A legenda nao passa por pagina nenhuma: o yt-dlp pede direto ao player, e
aqui passou de primeira.

DUAS REGRAS, IGUAIS AS DO vast_local_retriever
---------------------------------------------
1. NUNCA levanta e NUNCA inventa. Video sem legenda (bloqueado, removido, sem
   faixa em ingles) devolve texto vazio com o motivo real. Transcricao
   inventada e o pior resultado possivel aqui: o GPT Researcher a cita como
   fala do autor do video.

2. `--sub-langs en`, e nao `en.*`. Medido: `en.*` dispara HTTP 429 no player do
   YouTube; `en` passa. Comment esta aqui porque e a unica parte do comando que
   parece "melhoria" e e na verdade a diferenca entre 18k chars e zero.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import time
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import parse_qs, urlsplit

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger("vast.yt")

# Binario resolvido por LISTA, e nao pelo PATH de quem chama. Medido: o vast roda
# com PATH="/opt/data/.local/bin:/usr/local/bin:/usr/bin:/bin" e funciona por
# causa disso, mas um chamador que nao exporte esse PATH exato quebra com rc=-1 --
# medido de novo aqui, e o modulo nao e auto-suficiente enquanto isso durar.
# /usr/bin e /usr/local/bin sao somente-leitura nesta maquina, entao a correcao e
# uma lista de candidatos, e NAO mexer em os.environ["PATH"]: isso vaza para os
# subprocessos do proprio vast. Mesmo desenho do CHROME_PATH do cascade_fetcher
# (variavel de ambiente primeiro, caminho absoluto depois, e ausencia = erro
# honesto e nomeado); o shutil.which fica como segundo candidato para nao perder
# quem tem o yt-dlp em outro lugar do PATH. O ultimo argumento do next() e o
# caminho conhecido: se nada existir, YTDLP ainda nomeia o que foi tentado, e o
# FileNotFoundError do create_subprocess_exec continua sendo a falha honesta.
YTDLP: Final[str] = os.environ.get("VAST_YTDLP") or next(
    (
        candidate
        for candidate in ("/opt/data/.local/bin/yt-dlp", shutil.which("yt-dlp"))
        if candidate and os.path.exists(candidate)
    ),
    "/opt/data/.local/bin/yt-dlp",
)
logger.debug("yt-dlp resolvido para %s", YTDLP)

# Achar o yt-dlp nao basta: o proprio yt-dlp e quem roda `node` para resolver o
# desafio de JS, e sem o node a legenda nao vem. Medido com o yt-dlp chamado na
# mao (nada deste modulo envolvido) sob PATH=/usr/bin:/bin:
#   WARNING: n challenge solving failed: ... supported JavaScript runtime ...
#   ERROR: The page needs to be reloaded.
# Mesma dependencias de PATH, um nivel abaixo. O node esta em /usr/local/bin, que
# nao esta no PATH de teste -- entao o filho ganha o PATH do vast. `env=` e
# child-scoped: os.environ do processo fica intacto, que era o requisito.
YTDLP_CHILD_PATH: Final[str] = os.pathsep.join(
    dict.fromkeys(  # dict.fromkeys: a ordem do vast e preservada e nao duplica
        ("/opt/data/.local/bin", "/usr/local/bin", *os.environ.get("PATH", "").split(os.pathsep))
    )
)

# O arquivo de cookie e Netscape (curl) e o yt-dlp so aceita esse formato; sem
# ele a legenda e a propria origem do bloqueio, entao a ausencia do arquivo e
# tratada como "sem legenda", nunca como erro fatal.
YT_COOKIE_FILE: Final[str] = os.environ.get(
    "VAST_YT_COOKIES", "/opt/data/secrets/youtube_cookies.txt"
)

# Legenda de video nao envelhece como pagina de forum, mas 7 dias nao custam
# nada (o video e o mesmo) e seguram o yt-dlp -- que e lento, com desafio de JS
# resolvido por node -- de sair em toda consulta repetida sobre o mesmo video.
TRANSCRIPT_TTL_S: Final[float] = 604800.0

# Banco proprio, e nao o do cascade_fetcher: sao politicas diferentes (TTL de
# 24h e "mesma pagina" la, 7 dias e "mesmo video" aqui) e um cache de 20k chars
# por video dentro do banco de paginas pesaria no cache que o cascade varre.
TRANSCRIPT_DB: Final[str] = os.environ.get(
    "VAST_YT_TRANSCRIPT_DB", "/opt/data/cache/yt_transcripts.db"
)

# Medido: o yt-dlp gasta ~4-8s no video curto (desafio de JS via node) e ~25s
# em video longo. 45s cabe o caso comum com folga e corta o video que travou.
DEFAULT_TIMEOUT_S: Final[float] = 45.0

# Motivo curto de uma falha, para o `reason` e para o log. Mesmo corte do
# STDERR_SNIPPET do retriever: um motivo de 3 linhas nao cabe em log de request.
REASON_LIMIT: Final[int] = 200

# method do TranscriptResult: como o texto foi obtido. "cache" e "live" ficam
# separados porque o log do vast precisa dizer quanta transcricao veio da rede de
# verdade -- ver YT_ENRICH_MAX em vast_local_retriever.
METHOD_CACHE: Final[str] = "cache"
METHOD_LIVE: Final[str] = "live"
METHOD_NONE: Final[str] = "none"

# Regexes portadas de /opt/data/scripts/prove_transcript.py, que e a
# implementacao provada: 171.557 chars de VTT real -> 18.527 chars de texto,
# 984 linhas duplicadas removidas, 3.366 palavras, 999 segmentos. Alterar
# qualquer uma delas aqui muda o resultado medido; se precisar mudar, meca de
# novo com prove_transcript.py ao lado.
_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")
_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3} -->")
# Marcadores de som sao ruido de legenda automatica. So entram entre colchetes e
# isolados na linha, para nao cortar "[music] de Bach" no meio de uma frase.
_SOUND_RE: Final[re.Pattern[str]] = re.compile(
    r"^\[(?:Music|Applause|Blaughtering laughs|laughter)\]$"
)
_VTT_SKIP_PREFIXES: Final[tuple[str, ...]] = ("Kind:", "Language:")

# Um id de video do YouTube tem exatamente 11 caracteres de [A-Za-z0-9_-].
# Medido: sem isto, `fetch_transcript("aircAruvnKk")` e
# `fetch_transcript("https://www.youtube.com/watch?v=aircAruvnKk")` caem em
# chaves de cache diferentes -- apagando a entrada do videoApareceu sumiram 2
# linhas no banco, nao 1. O vast sempre passa URL, entao producao nao sente;
# quem chama com id cru pagava um yt-dlp inteiro de graca (7.9s e ~170KB
# medidos) por um video que ja estava em disco.
_VIDEO_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass(frozen=True, slots=True)
class TranscriptResult:
    """Transcricao de um video, ou o motivo honesto de nao haver uma.

    Congelada e com slots porque e um valor que atravessa varias corrotinas e
    nao tem estado proprio: mutar no meio do caminho seria o tipo de bug que
    so aparece com 3 transcritos em paralelo.

    `method` distingue "veio do cache" de "veio da rede" e `reason` preenchido
    significa que `text` esta vazio -- nunca os dois ao mesmo tempo com texto.

    `automatic` diz se a legenda e gerada por maquina: True/False quando da para
    saber, None quando nao da (unknown). Hoje e sempre None, e isso e honesto e
    nao provisório: o argv pede manual E automatica juntas (`--write-subs` +
    `--write-auto-subs`) e o VTT que o yt-dlp grava nao carrega marcador de
    origem -- `yt.en.vtt` e o mesmo nome nos dois casos. Descobrir de verdade
    custaria uma segunda chamada (`--list-subs`) por video, ou seja, dobrar o
    orcamento de rede da transcricao para rotular o que o prompt trata do mesmo
    jeito (spoken-content-only, ver o EVIDENCE_PROMPT nos runners). Se um dia
    existir sinal barato, e aqui que ele entra.
    """

    text: str
    lang: str
    chars: int
    segments: int
    dupes_removed: int
    method: str
    reason: str | None
    automatic: bool | None = None


def clean_vtt(raw: str) -> tuple[str, int, int]:
    """Limpa um VTT e devolve (texto, duplicadas_removidas, segmentos).

    Portado linha a linha de prove_transcript.py, que mediu 171.557 -> 18.527
    chars no VTT real de /tmp/yt_subs.en.vtt. As tres coisas que fazem o
    trabalho:

    1. Timestamps, `WEBVTT`, `Kind:`, `Language:` e linha vazia saem fora. O
       VTT traz a legenda repetida em rolling caption, com a linha anterior
       repetida no fim da atual: 171k de arquivo viram 18k de texto.

    2. Tags `<...>`, `&nbsp;`, `&amp;`, `&#39;` e marcadores [Music] sao
       removidos. O `&nbsp;` vira espaco e nao string vazia: juntar sem
       separador cola "palavra"+"palavra" numa coisa so.

    3. Duplicadas consecutivas saem (984 de 999 linhas na medicao). A lista
       intermediaria mantem a string vazia de um marcador removido, e isso e
    proposital: e assim que a contagem de duplicadas bate com a medicao.

    Devolve os numeros junto porque eles sao a unica prova de que o texto
    aproveitou: um "ok" sem chars nao diz nada.
    """
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or "-->" in stripped
            or stripped == "WEBVTT"
            or stripped.startswith(_VTT_SKIP_PREFIXES)
        ):
            continue
        cleaned = _TAG_RE.sub("", stripped)
        cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
        cleaned = _SOUND_RE.sub("", cleaned)
        lines.append(cleaned)

    deduped: list[str] = []
    for text in lines:
        if not deduped or text != deduped[-1]:
            deduped.append(text)

    segments = len(_SEGMENT_RE.findall(raw))
    return " ".join(part for part in deduped if part), len(lines) - len(deduped), segments


# --------------------------------------------------------------------------
# Identidade do video. Mesma ideia do _cache_key do cascade_fetcher: a chave do
# cache e o sha256 da URL, e a URL e normalizada antes para que duas formas do
# mesmo video compartilhem entrada.
# --------------------------------------------------------------------------


def _normalize_url(url: str) -> str:
    """Reduz o video a `https://www.youtube.com/watch?v=<id>` quando da para.

    `youtu.be/ID`, `/shorts/ID`, `/embed/ID` e o mesmo video que `/watch?v=ID`.
    Sem isso sao quatro entradas de cache e quatro yt-dlp para o mesmo audio.
    O id cru (`aircAruvnKk`, sem esquema e sem host) tambem vira a URL canonica
    pelo mesmo motivo -- ver _VIDEO_ID_RE. Quando nao da para extrair o id (url
    exotica), a propria URL limpa vira a chave: melhor uma entrada duplicada que
    um id adivinhado errado.
    """
    candidate = url.strip()
    # Id cru: nenhum host para olhar, e o yt-dlp aceita o id como URL, entao o
    # caminho feliz aqui e so normalizar a chave -- o argv continua idêntico.
    if _VIDEO_ID_RE.match(candidate):
        return f"https://www.youtube.com/watch?v={candidate}"

    parts = urlsplit(candidate)
    host = (parts.hostname or "").lower()
    if host.endswith("youtube.com") or host.endswith("youtu.be"):
        video_id = parse_qs(parts.query).get("v", [""])[0]
        if not video_id:
            segments = [seg for seg in parts.path.split("/") if seg]
            if host.endswith("youtu.be") and segments:
                video_id = segments[0]
            elif len(segments) >= 2 and segments[0] in ("shorts", "embed", "live", "v"):
                video_id = segments[1]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    return url.strip().split("#", 1)[0]


def _cache_key(url: str) -> str:
    """sha256 da URL normalizada -- identico ao esquema do cascade_fetcher."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Cache (SQLite). Mesmo estilo do cascade_fetcher: schema com IF NOT EXISTS em
# toda conexao, PRAGMA de WAL, commit no `with` e close no `finally`. O
# acesso passa por asyncio.to_thread: sqlite3 bloqueia a thread, e a thread do
# loop nao pode ficar esperando I/O de disco.
# --------------------------------------------------------------------------

_SCHEMA: Final[tuple[str, ...]] = (
    """CREATE TABLE IF NOT EXISTS transcripts (
        url_hash     TEXT PRIMARY KEY,
        url          TEXT NOT NULL,
        text         TEXT NOT NULL,
        lang         TEXT NOT NULL,
        char_count   INTEGER NOT NULL,
        segments     INTEGER NOT NULL,
        fetched_at   REAL NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_transcripts_fetched_at ON transcripts(fetched_at)",
)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Abre o banco garantindo o schema, e fecha de verdade ao sair.

    Fecha E commita: o `with` do proprio sqlite3 so faz commit/rollback, e um
    retriever de processo longo vazaria um handle do WAL por transcricao ate o
    banco travar. `IF NOT EXISTS` dispensa estado global de "ja inicializei".
    """
    os.makedirs(os.path.dirname(TRANSCRIPT_DB) or ".", exist_ok=True)
    conn = sqlite3.connect(TRANSCRIPT_DB, timeout=5.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        for stmt in _SCHEMA:
            conn.execute(stmt)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _cache_get_sync(url: str) -> tuple[str, str, int, int, int] | None:
    """Le do cache, ou None se nao houver entrada vigente."""
    row = None
    with _connect() as conn:
        row = conn.execute(
            "SELECT text, lang, char_count, segments, fetched_at FROM transcripts"
            " WHERE url_hash = ?",
            (_cache_key(url),),
        ).fetchone()
    if row is None:
        return None
    text, lang, char_count, segments, fetched_at = row
    if time.time() - fetched_at > TRANSCRIPT_TTL_S:
        logger.debug("cache expirado (ttl=%ss) %s", int(TRANSCRIPT_TTL_S), url)
        return None
    return text, lang, int(char_count), int(segments), time.time() - fetched_at


def _cache_put_sync(url: str, text: str, lang: str, segments: int, dupes: int) -> None:
    """Guarda a transcricao. So quem leu de verdade grava -- nunca uma falha."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO transcripts"
            " (url_hash, url, text, lang, char_count, segments, fetched_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_cache_key(url), url, text, lang, len(text), segments, time.time()),
        )
    logger.info("transcricao guardada: %s chars=%d segmentos=%d dupes=%d",
                url, len(text), segments, dupes)


def cache_stats() -> dict[str, object]:
    """Fotografia do cache de transcricoes: entradas, chars, frescor, TTL."""
    if not os.path.exists(TRANSCRIPT_DB):
        return {"db": TRANSCRIPT_DB, "exists": False, "entries": 0, "ttl_seconds": TRANSCRIPT_TTL_S}
    now = time.time()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(char_count), 0),"
            " COALESCE(MIN(fetched_at), 0), COALESCE(MAX(fetched_at), 0),"
            " COALESCE(SUM(CASE WHEN ? - fetched_at > ? THEN 1 ELSE 0 END), 0)"
            " FROM transcripts",
            (now, TRANSCRIPT_TTL_S),
        ).fetchone()
    entries, chars, oldest, newest, stale = row
    return {
        "db": TRANSCRIPT_DB,
        "exists": True,
        "size_bytes": os.path.getsize(TRANSCRIPT_DB),
        "entries": entries,
        "chars_total": chars,
        "fresh": entries - stale,
        "stale": stale,
        "ttl_seconds": TRANSCRIPT_TTL_S,
        "oldest_age_seconds": round(now - oldest) if oldest else None,
        "newest_age_seconds": round(now - newest) if newest else None,
    }


def clear_cache() -> None:
    """Esvazia o cache de transcricoes. Idempotente."""
    if not os.path.exists(TRANSCRIPT_DB):
        logger.info("clear_cache: nada a fazer, %s nao existe", TRANSCRIPT_DB)
        return
    with _connect() as conn:
        removed = conn.execute("DELETE FROM transcripts").rowcount
    logger.info("clear_cache: %d transcricoes removidas de %s", removed, TRANSCRIPT_DB)


# --------------------------------------------------------------------------
# Subprocess
# --------------------------------------------------------------------------


def _one_line(text: str) -> str:
    """Achata em uma linha o que vai para o `reason` e para o log."""
    return " ".join(text.split())


def _sub_langs(lang: str) -> str:
    """Nunca deixa passar um curinga para o --sub-langs.

    `en.*` foi medido dando HTTP 429; `en` passa. Se alguem pedir `en.*` de novo,
    o modulo nao repete o erro em silencio: avisa e corta o curinga.
    """
    if "*" in lang:
        base = lang.split(".", 1)[0]
        logger.warning("sub-langs %r vira %r: '*' no YouTube devolve HTTP 429 (medido)", lang, base)
        return base
    return lang


def _ytdlp_argv(url: str, lang: str, outdir: Path) -> list[str]:
    """Comando do yt-dlp, na ordem em que o yt-dlp le.

    Cada flag esta aqui por uma razao:
      --sub-langs en        unico idioma pedido; `en.*` = 429 (medido)
      --write-auto-subs     legenda automatica, que e o que existe em 95% dos videos
      --write-subs          legenda humana, quando existir
      --sub-format vtt      VTT e o unico formato de onde sai texto recuperavel
      --skip-download      o vast quer o texto, nao os 40MB de video
      --no-playlist         uma URL de video nunca vira uma lista de videos
      --no-warnings         o stderr e usado como motivo; aviso nao e motivo
      --cookies             sem sessao o player nega a legenda (429)
      --sleep-subtitles 2   o yt-dlp cobra 2s entre downloads de legenda; sem
                            isso ele nem faz a pausa e leva 429 na segunda
    Sem shell: a URL vai como argumento, nunca interpolada numa string.
    """
    return [
        YTDLP,
        "--sub-langs", lang,
        "--write-auto-subs",
        "--write-subs",
        "--sub-format", "vtt",
        "--skip-download",
        "--no-playlist",
        "--no-warnings",
        "--cookies", YT_COOKIE_FILE,
        "--sleep-subtitles", "2",
        "-o", str(outdir / "yt.%(ext)s"),
        url,
    ]


async def _kill(proc: asyncio.subprocess.Process) -> None:
    """Mata o processo e espera ele morrer, sem deixar exception escaping.

    Chamar depois de um cancelamento e seguro: o CancelledError ja foi entregue
    uma vez, e o await seguinte so volta a ser interrompido se o cancelamento
    vier de novo -- o wait_for do chamador cancela uma vez e espera.
    """
    proc.kill()
    with suppress(Exception):
        await proc.wait()


async def _run_ytdlp(argv: list[str], timeout: float) -> tuple[int, str]:
    """Roda o yt-dlp e devolve (returncode, motivo_curto). Nunca levanta.

    `asyncio.create_subprocess_exec` em vez do run_command do vast_local_retriever
    de proposito: aquele modulo importa este, e importar de la para ca aqui
    fecharia um ciclo no import. O codigo e pequeno e a duplicacao e de 15 linhas.

    Mata o processo no timeout E no cancelamento. O cancelamento e o caso que
    importa: quando o vast estoura o orcamento da request ele cancela esta
    corrotina, e um yt-dlp que sobrevive a isso continuaria baixando legenda em
    segundo plano depois da resposta -- gastando CPU, rede e o rate limit do
    YouTube com ninguem esperando o resultado.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PATH": YTDLP_CHILD_PATH},
        )
    except FileNotFoundError:
        return -1, f"{YTDLP} nao encontrado"
    except OSError as exc:
        return -1, f"nao consegui executar {YTDLP}: {exc}"

    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.CancelledError:
        await _kill(proc)
        raise
    except asyncio.TimeoutError:
        await _kill(proc)
        return -1, f"timeout de {timeout:.0f}s em {YTDLP}"
    except Exception as exc:  # noqa: BLE001 - communicate so falha por erro de plumbing
        await _kill(proc)
        return -1, f"{type(exc).__name__}: {_one_line(str(exc))}"

    return proc.returncode or 0, _one_line(stderr.decode("utf-8", errors="ignore"))


def _pick_vtt(outdir: Path, lang: str) -> Path | None:
    """Acha o VTT produzido. Preferencia pelo nome exato, senao o primeiro.

    O yt-dlp nomeia pelo prefixo do `-o` mais o idioma (`yt.en.vtt`); com mais de
    um idioma em disco o primeiro em ordem alfabetica seria arbitrario, e o
    criterio tem que ser o idioma pedido.
    """
    exact = outdir / f"yt.{lang}.vtt"
    if exact.exists():
        return exact
    found = sorted(outdir.glob("*.vtt"))
    return found[0] if found else None


def _miss(lang: str, reason: str) -> TranscriptResult:
    """Transcricao vazia com o motivo real, no formato que o vast espera."""
    return TranscriptResult(
        text="", lang=lang, chars=0, segments=0, dupes_removed=0,
        method=METHOD_NONE, reason=reason[:REASON_LIMIT],
    )


def _detect_automatic(vtt_raw: str) -> bool | None:
    """Diz se o VTT e legenda automatica. Hoje: sempre unknown (None).

    Nao ha sinal barato e confiavel: o argv pede manual E automatica juntas
    (`--write-subs` + `--write-auto-subs`, com a manual vencendo quando existe)
    e o arquivo que o yt-dlp grava (`yt.en.vtt`) tem o mesmo nome e o mesmo
    formato nos dois casos -- o stderr diz so "Downloading subtitles: en".
    Saber de verdade custaria uma segunda chamada (`--list-subs`) por video,
    dobrando o orcamento de rede da transcricao para rotular o que o prompt de
    evidencia trata do mesmo jeito (spoken-content-only). Chutar pela presenca
    de cabecalho `Kind:` seria adivinhar, e a regra 1 do modulo proibe isso.
    A deteccao foi feita (sobre o VTT ja em memoria, custo zero) e o resultado
    honesto e unknown. Se um dia existir marcador barato, e aqui que ele entra.
    """
    _ = vtt_raw
    return None


def peek_transcript(url: str) -> TranscriptResult | None:
    """Somente-cache: devolve a transcricao se vigente, None se miss/expirada.

    Existe para a fase A do vast (`enrich_results`): todos os videos do
    `selected` passam por aqui sem gastar rede nem orcamento live. Nunca toca
    em rede nem em cookie -- disco cheio ou cache corrompido viram None, e quem
    chama segue para a rede como se fosse um miss comum.
    """
    if not url or not url.strip():
        return None
    try:
        cached = _cache_get_sync(_normalize_url(url))
    except Exception as exc:  # noqa: BLE001 - ver fetch_transcript: cache nao derruba busca
        logger.debug("peek de cache indisponivel (%s: %s)", type(exc).__name__, exc)
        return None
    if cached is None:
        return None
    text, stored_lang, chars, segments, age = cached
    logger.debug("peek acertou %s: %d chars (idade %ds)", url, chars, int(age))
    return TranscriptResult(
        text=text, lang=stored_lang, chars=chars, segments=segments, dupes_removed=0,
        method=METHOD_CACHE, reason=None, automatic=None,
    )


async def _fetch_live(url: str, key_url: str, lang: str, timeout: float) -> TranscriptResult:
    """Caminho do yt-dlp, sem cache. Devolve texto ou motivo, nunca raise."""
    with tempfile.TemporaryDirectory(prefix="vast-yt-") as tmpdir:
        outdir = Path(tmpdir)
        started = time.monotonic()
        returncode, stderr = await _run_ytdlp(_ytdlp_argv(url, lang, outdir), timeout)
        elapsed = time.monotonic() - started

        if returncode != 0:
            reason = stderr or "yt-dlp nao disse nada"
            logger.warning("transcricao falhou %s rc=%d em %.1fs: %s", url, returncode, elapsed, reason)
            return _miss(lang, f"yt-dlp rc={returncode}: {reason}")

        vtt_path = _pick_vtt(outdir, lang)
        if vtt_path is None:
            logger.warning("transcricao ausente %s em %.1fs: yt-dlp nao produziu VTT", url, elapsed)
            return _miss(lang, f"yt-dlp nao produziu legenda em {lang} (rc=0)")

        try:
            raw = vtt_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return _miss(lang, f"nao consegui ler {vtt_path.name}: {exc}")

    text, dupes, segments = clean_vtt(raw)
    if not text.strip():
        # rc=0 e arquivo produzido, mas sem fala: legenda so de musica, ou
        # faixa em outro idioma. Honesto e vazio, com o motivo.
        return _miss(lang, f"legenda em {lang} sem texto ({len(raw)} chars de VTT)")

    await asyncio.to_thread(_cache_put_sync, key_url, text, lang, segments, dupes)
    logger.info(
        "transcricao ok %s: %d chars, %d segmentos, %d duplicadas, %.1fs",
        url, len(text), segments, dupes, elapsed,
    )
    return TranscriptResult(
        text=text, lang=lang, chars=len(text), segments=segments, dupes_removed=dupes,
        method=METHOD_LIVE, reason=None, automatic=_detect_automatic(raw),
    )


async def fetch_transcript(url: str, *, lang: str = "en", timeout: float = DEFAULT_TIMEOUT_S) -> TranscriptResult:
    """Transcricao de um video do YouTube. Nunca levanta e nunca inventa texto.

    A ordem e deliberada: cache primeiro (acerto de cache nao custa yt-dlp nem
    45s de timeout, e nao precisa de cookie), depois conferida do arquivo de
    cookies, so entao a rede. Qualquer falha -- binario ausente, cookie
    ausente, rc != 0, timeout, VTT nao produzido, legenda sem fala -- vira
    `text=""` com o motivo no `reason`. Um video sem legenda e um resultado
    legitimo e unhelpful; uma transcricao inventada e mentira com confianca.
    """
    if not url or not url.strip():
        return _miss(lang, "url vazia")
    key_url = _normalize_url(url)
    lang = _sub_langs(lang)

    try:
        cached = await asyncio.to_thread(_cache_get_sync, key_url)
    except Exception as exc:  # noqa: BLE001 - disco cheio e cache corrompido nao podem derrubar a busca
        logger.warning("cache de transcricao indisponivel (%s: %s); sigo para a rede", type(exc).__name__, exc)
        cached = None

    if cached is not None:
        text, stored_lang, chars, segments, age = cached
        logger.info("transcricao do cache %s: %d chars (idade %ds)", key_url, chars, int(age))
        return TranscriptResult(
            text=text, lang=stored_lang, chars=chars, segments=segments, dupes_removed=0,
            method=METHOD_CACHE, reason=None, automatic=None,
        )

    if not os.path.exists(YT_COOKIE_FILE):
        # Sem cookie o player nega a legenda. Isso e configuracao, nao erro do
        # video: aviso unico e segue, para nao encher o log de 12 linhas iguais.
        logger.warning("transcricao indisponivel: cookies ausentes em %s", YT_COOKIE_FILE)
        return _miss(lang, f"cookies ausentes em {YT_COOKIE_FILE}")

    try:
        return await _fetch_live(url, key_url, lang, timeout)
    except Exception as exc:  # noqa: BLE001 - contrato: esta funcao nao levanta
        logger.warning("transcricao erro inesperado %s: %s: %s", url, type(exc).__name__, exc)
        return _miss(lang, f"{type(exc).__name__}: {_one_line(str(exc))}")
