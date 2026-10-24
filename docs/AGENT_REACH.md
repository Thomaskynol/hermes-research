# Agent Reach — operações individuais

**Implementação:** `agent_reach.py` + `academic_search.py` (branch `feat/reach-agent-reach`)
**Referência:** `docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` §2, §4, §5, §11, §16;
`docs/REQUIREMENTS_MATRIX.md` R2.1–R2.8, R4.1–R4.5, R5.1–R5.7, R11.6.

O Agent Reach resolve **uma operação por pedido** ("leia esta página", "resuma este
vídeo", "examine este repositório") e devolve conteúdo, origem, limitações e estado
de obtenção. Ele **não** importa `adaptive_coordinator`, `adaptive_planner` nem
`coverage_ledger`, e não inicia pesquisa coordenada. O Deep Researcher consome o
mesmo contrato (`ReachResult`) e os mesmos conectores.

## Contrato — `ReachResult`

| Campo | Tipo | Significado |
|---|---|---|
| `ok` | bool | `True` para `obtained`/`partial`; `False` para `unavailable`/`failed`. |
| `operation` | str | `search`, `read_page`, `read_repo`, `read_video`, `academic_search`, `read_work`. |
| `target` | str | Consulta, URL ou identificador pedido. |
| `title` | str | Título observado (vazio quando não houve). |
| `text` | str | **Somente conteúdo lido de verdade**; metadados/abstract ficam em `metadata`. |
| `chars` | int | `len(text)` (sempre coerente com `text`). |
| `channel` | str | `web`, `github`, `youtube`, `academic`, `openalex`, `arxiv`. |
| `obtained_at` | str | Instante UTC ISO-8601 (`...Z`). |
| `status` | str | `obtained`, `partial`, `unavailable`, `failed`. |
| `qualification` | str | `usable`, `partial`, `insufficient`, `metadata_only`, `none`. |
| `reason` | str\|null | Motivo legível; nunca esconde falha esperada atrás de exceção. |
| `http_status` | int\|null | **Só quando observado**; `null` = não observado, nunca 200 presumido. |
| `metadata` | dict | Idioma/origem/timestamps/DOI/autores/ano/venue/resultados/etc. |
| `limits` | list[str] | Limitações efetivas daquela operação. |
| `evidence` | dict | `url`/`urls`, `sha256`, `chars`, `excerpt`, `read_scope`. |

`to_dict()` devolve exatamente esses 15 campos. Falha esperada **não levanta**:
retorna `ok=False` com `status` e `reason` corretos.

### Status × qualificação (regra aplicada)

| Situação | status | qualification | ok |
|---|---|---|---|
| Texto útil (≥ 500 chars) | `obtained` | `usable` | True |
| Captura curta (1–499 chars) | `partial` | `partial` | True |
| HTML sem conteúdo / anti-bot / nada lido | `unavailable` | `insufficient` | False |
| Resultado só de metadados (busca, repo sem README) | `obtained`/`partial` | `metadata_only` | True/True |
| Abstract disponível, sem texto completo | `partial` | `partial` | True |
| Serviço/rede fora, payload inválido | `failed` | `none` | False |

O piso de 500 chars é o mesmo `MIN_CHARS` da cascata existente
(`cascade_fetcher.py`), e não um número novo.

## Operações e reaproveitamento

| Operação | Conector reusado | O que devolve |
|---|---|---|
| `search(query, limit=10, channel="web", timeout=20)` | gateway local do `vast_local_retriever` em `RETRIEVER_ENDPOINT` (default `http://127.0.0.1:8001/`), que executa `search_all` + `_select_hits` + `enrich_results` | `metadata["results"]`: `url`, `title`, `snippet`, `engine` (quando observado), `content_chars`. Não lê página. |
| `read_page(url, timeout=20)` | `cascade_fetcher.fetch` (a mesma cascata do vast: trafilatura → bs4 → navegador) | texto extraído, nível da cascata, cache, qualificação. |
| `read_repo(url, timeout=20)` | `repo_readme.fetch_repo_readme` (README/blob raw) + API pública do GitHub (`/repos`, `/releases`, `/contents`) | README ou metadados: `stars`, `license`, `default_branch`, `latest_release`, `files`. |
| `read_video(url, lang="en", timeout=30)` | `youtube_transcript.fetch_transcript` (legenda do autor ou automática, cache em disco) | transcrição com `lang`, `automatic`, `source`, `segments`; nunca ASR. |
| `search_works(query, limit=10, source="openalex"\|"arxiv"\|"both")` | OpenAlex JSON + arXiv Atom (`xml.etree`) | `metadata["works"]`: id, DOI, título, ano, autores, venue, citações, OA, abstract. |
| `read_work(identifier, full_text=False)` | OpenAlex (DOI/ID) ou arXiv (ID) | metadados + abstract; `read_level` ∈ `metadata`/`abstract`/`full_text`. |

### Detalhes de honestidade

- **Busca:** gateway fora → `failed` + `retriever_unavailable` + `results: []`.
  Nenhum resultado é inventado. Resultado vazio → `unavailable` + `no_results`.
- **Página:** HTML vazio/erro/anti-bot → `insufficient`; captura curta → `partial`.
  `http_status` só aparece se o transporte o observou (a cascata não observa).
- **Repositório:** README 404 com metadados da API → `partial`/`metadata_only`,
  `http_status=404`, motivo preservado. Repo inexistente → `unavailable` +
  `repo_not_found`. Sem `GITHUB_TOKEN` no ambiente, registra
  `github_api_unauthenticated_60_requests_per_hour`; o valor do token nunca é
  lido de arquivo, logado ou copiado.
- **Vídeo:** `absent` (legendas ausentes) ≠ `blocked` (falha/bloqueio) ≠
  `disabled`. Título/descrição nunca viram `text`; sem transcrição,
  `qualification="metadata_only"` e nenhuma afirmação sobre a fala.
  Timestamps não são inventados: `first_timestamp`/`last_timestamp` ficam
  `null` com a limitação declarada quando a fonte não os fornece.
- **Acadêmico:** `metadata` ≠ `abstract` ≠ `full_text`; texto completo só em
  local gratuito (arXiv HTML/PDF ou OA do OpenAlex). Nunca há acesso pago,
  proxy ou chave. PDF depende de `pypdf` já instalado; sem ele, a limitação é
  registrada e o resultado permanece no nível `abstract`.
- **Página — import seguro:** `agent_reach` importa `cascade_fetcher` direto
  (mesmo diretório do vast) em vez de `import vast_local_retriever`, porque o
  import do vast executa `load_github_token()` e lê `/opt/data/.env`. Uma
  leitura de página não deve carregar credencial de produção como efeito
  colateral. A lógica de extração é a mesma (`fetch`).

## CLI

```bash
python agent_reach.py search "consulta" --limit 5 --json
python agent_reach.py read-page https://docs.gptr.dev/docs/gpt-researcher/gptr/config --json
python agent_reach.py read-repo https://github.com/assafelovic/gpt-researcher --json
python agent_reach.py read-video https://www.youtube.com/watch?v=... --lang en --json
python agent_reach.py academic-search "retrieval augmented generation" --source both --json
python agent_reach.py read-work 10.1038/nature12373 --full-text --json
```

Flags comuns: `--json`, `--output-dir DIR` (grava `<operation>-<UTC>-<hash>.json`),
`--timeout S`. Exit: `0` quando `ok` é True (`obtained`/`partial`), `1` quando não
foi possível obter (`unavailable`/`failed`), `2` para uso inválido (argparse).

## Testes

```bash
python3 -m unittest tests.test_agent_reach tests.test_academic_search -v
python3 -m unittest discover -s tests -p "test_*.py"
```

- Offline por padrão: transporte injetado e rede bloqueada por
  `sys.addaudithook` (`socket.connect`/`getaddrinfo`/`sendto`).
- Rede real opt-in: `HERMES_REAL_NETWORK=1` (testes `skipUnless`).
- Cobertura: contrato nos seis caminhos; página vazia/erro/anti-bot/curta/útil;
  vídeo autor vs automático vs ausente vs bloqueado vs desabilitado; repo
  README raw, 404 honesto e releases simuladas; parsing OpenAlex/arXiv,
  DOI/arXiv ID, `read_level`; ausência de import do coordenador (AST +
  `sys.modules` em processo novo); busca indisponível sem resultados fabricados.

Resultados medidos (24/10/2026):

| Ambiente | Comando | Resultado |
|---|---|---|
| host (Python 3.14.6) | `python3 -m unittest tests.test_agent_reach tests.test_academic_search -v` | **59 testes, OK (5 skipped), exit 0** |
| host (Python 3.14.6) | `python3 -m unittest discover -s tests -p "test_*.py"` | **129 testes, 1 erro pré-existente** (`test_yt_enrich_fix`: `ModuleNotFoundError: httpx` no host), 9 skipped, exit 1. Baseline antes da mudança: 70 testes, o mesmo erro, 4 skipped. |
| container `hermes-gateway`, venv `/opt/data/home/.agent-reach-venv` (3.13.5), snapshot `/tmp/reach_snap` | `python -m unittest discover -s tests -p "test_*.py"` | **128 testes, OK (5 skipped), exit 0** |

O erro do host não é causado por esta mudança: o módulo `test_yt_enrich_fix`
importa `vast_local_retriever`, que exige `httpx`; o host não tem `httpx`. No
container (ambiente real do projeto) a suíte fecha verde.

## Validação real (snapshot isolado, rede real)

Snapshot do worktree copiado para `/tmp/reach_snap` **dentro do container**
(nunca produção), executado com o venv do Agent Reach. Caches redirecionados
para `/tmp/reach_real` (`CASCADE_CACHE_DB`, `VAST_README_MISS_DB`,
`VAST_YT_TRANSCRIPT_DB`), então nada foi escrito em `/opt/data` nem em
`/home/thomaskyn/.hermes`. Saídas JSON em `/tmp/reach_real/*.json` (container).

| # | Operação | Comando (resumo) | Início UTC | Exit | Resultado real |
|---|---|---|---|---|---|
| 1 | `search` | `agent_reach.py search "gpt researcher" --limit 5 --json` | 2026-10-24T23:01:08Z | 1 | **Bloqueado**: `failed`/`retriever_unavailable`, `URLError [Errno 111] Connection refused`, `results: []`. O gateway `127.0.0.1:8001` não estava no ar. Nada foi fabricado. |
| 2 | `read-page` | `... read-page https://docs.gptr.dev/docs/gpt-researcher/gptr/config --json` | 2026-10-24T23:01:15Z | 0 | `obtained`/`usable`, **11.655 chars**, cascata nível 1, sem cache, `http_status: null` (não observado). Trecho: "Configuration The config.py enables you to customize GPT Researcher...". |
| 3 | `read-repo` | `... read-repo https://github.com/assafelovic/gpt-researcher --json` | 2026-10-24T23:01:20Z | 0 | `obtained`/`usable`, **3.090 chars** de README; `stars=30284`, `license=Apache-2.0`, `default_branch=main`, `latest_release=v3.7.0` (2026-09-26), `files` com 8 nomes; `api_authenticated=false` + limite 60 req/h. |
| 4 | `academic-search` OpenAlex | `... academic-search "retrieval augmented generation" --limit 5 --source openalex --json` | 2026-10-24T23:01:28Z | 0 | `obtained`/`metadata_only`, `http_status=200`, **5 works**. Ex.: "Corrective Retrieval Augmented Generation" (2025, DOI 10.2139/ssrn.5267341, 177 citações, OA). |
| 5 | `academic-search` arXiv | `... academic-search "retrieval augmented generation" --limit 5 --source arxiv --json` | 2026-10-24T23:01:34Z | 0 | `obtained`/`metadata_only`, `http_status=200`, **5 works**. Ex.: "AR-RAG: Autoregressive Retrieval Augmentation..." (2506.06962v3, 4 autores). |
| 6 | `read-work` DOI | `... read-work 10.1038/nature12373 --json` | 2026-10-24T23:01:41Z | 0 | `partial`/`metadata_only`, `http_status=200`, `read_level=metadata`. "Nanometre-scale thermometry in a living cell", Nature, 2013, 1.957 citações; **abstract ausente no OpenAlex** (não inventado). |
| 7 | `read-work` texto completo (HTML) | `... read-work 1706.03762 --full-text --json` | 2026-10-24T23:02:19Z | 0 | `obtained`/`usable`, **33.902 chars**, `read_level=full_text`, arXiv `1706.03762v7` ("Attention Is All You Need"), abstract de 1.136 chars preservado. Extração HTML via trafilatura (já instalada no venv). |
| 8 | `read-work` texto completo (PDF) | `... read-work cs/0112017 --full-text --json` | 2026-10-24T23:06:19Z | 0 | `obtained`/`usable`, **67.193 chars**, `read_level=full_text`. O HTML do arXiv não existia; o PDF foi baixado e extraído (pypdf/PyMuPDF já instalados). O gate `_plausible_text` rejeitou a primeira extração (201k chars de sintaxe `%PDF`/`obj`) e só aceitou prosa real. |

Observações da validação:

- O único bloqueio foi o **retriever local fora do ar** (item 1). Ele aparece no
  retorno como `ok=false`, `status=failed`, `reason=retriever_unavailable`,
  `results=[]` e `limits`, e no CLI como exit 1 — nunca como "0 resultados".
- `http_status` ficou `null` em página/repo porque a cascata e o caminho raw não
  expõem o status; quando a API do GitHub respondeu, o status foi registrado
  (404/200). O contrato proíbe preencher por suposição.
- O README veio pelo caminho raw (não pela página HTML do GitHub), como o
  `repo_readme` já faz; a API foi usada para metadados/releases/arquivos.
- Nenhum token foi lido de arquivo: `read-repo` rodou sem `GITHUB_TOKEN` no
  ambiente e registrou a franquia não autenticada. `read-page` importa
  `cascade_fetcher` direto justamente para não disparar a leitura de
  `/opt/data/.env` que o import do vast faz.

## Limitações conhecidas

- **Retriever local:** a busca depende do gateway `127.0.0.1:8001`; fora do ar,
  a operação falha nomeada (não há busca web alternativa silenciosa).
- **GitHub:** sem token, 60 requisições/hora e sem dados privados. O token só é
  usado se já estiver em `GITHUB_TOKEN` no ambiente.
- **YouTube:** depende de `yt-dlp` + cookies já configurados no ambiente; sem
  transcrição, o vídeo fica fora das evidências de fala. Não há ASR local nem
  análise visual.
- **Timestamps de vídeo:** `fetch_transcript` não devolve primeiro/último
  timestamp; o campo fica `null` com limitação explícita (não é inventado).
- **Texto completo acadêmico:** só em local gratuito; PDF exige `pypdf` ou
  PyMuPDF já instalados. Sem extrator, permanece em `abstract` com a limitação
  registrada. Texto extraído de PDF passa por `_plausible_text`; sintaxe de PDF
  decodificada como texto é rejeitada em vez de virar "texto completo".
- **`search`:** devolve snippets identificados, não o `raw_content` completo do
  gateway; para conteúdo, o chamador usa `read_page`.
