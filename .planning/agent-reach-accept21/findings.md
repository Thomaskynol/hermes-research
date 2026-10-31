# Findings — agent-reach-accept21

## Estado do branch (evidência: `git log`, 2026-10-31)

- Branch `feat/product-v1`, HEAD `b1cf76c`
  ("docs(aceite): rodada accept19/accept20, correções de identidade, RA8 pendente").
- `cc0f3ff` — `fix(writer,diagnose)`: contexto do usuário não é evidência;
  bucket `na_scoped` no diagnose. Arquivos: `adaptive_coordinator.py`,
  `tools/diagnose_run.py`, `tests/test_accept19_corrections.py`.
- `b81e8f6` — `fix(m8)`: entidade fraca sem troca registra pool não explorado.
  Arquivos: `adaptive_coordinator.py`, `tests/test_accept19_corrections.py`.
- Ambas validadas só em unit test (476 passed / 15 skipped / 1 falha
  pré-existente de ambiente: `requests` ausente, ocorre na árvore limpa).
  **Não validadas em run real** — é o que o accept21 precisa provar.

## Lições do accept20 (evidência: §16 de `docs/ACEITE_V1_RESULTADO.md`)

- 5/52 + 4 N/A; 5 candidatos com identidade real; buckets
  `ok 5, partial_legit 10, na_scoped 4, assessor_error 17 (classe correta:
  proximidade-em-listagem), missing 16`; síntese 37/1/76.
- `accept19` falhou por race com o commit (código antigo) + assessor flakou
  no round 0 (não-lista 2×). **Não repetir run sobre código desatualizado:
  conferir `git rev-parse HEAD` antes de cada run.**
- `verification` overall **failed** por 1 inferência com versão vinda do
  contexto do usuário → motivou `cc0f3ff`. RA8 segue PENDENTE.

## Configuração efetiva (evidência: código + portas, 2026-10-31)

- `vast_local_retriever.py` docstring: `RETRIEVER=custom,searx,duckduckgo,arxiv`,
  `RETRIEVER_ENDPOINT=http://127.0.0.1:8001/`, `SEARX_URL=http://127.0.0.1:8888/`.
- Observado: `hermes-gateway` UP (portas 9119/8081); **sem listener em
  :8001 (vast) nem :8888 (searxng)** → STOPPED on-demand, conforme esperado.
  Embeddings: STOPPED (estado informado pelo orquestrador, sem checagem própria).
- `opencode v2.2.5` (evidência: `opencode --version`).
- `SEARXNG_URL` do ACEITE_V1.md usa IP de bridge (`http://172.18.0.2:8888`) —
  **frágil, pode mudar**; revalidar com `/healthz` → 200 antes do run.

## Hipóteses em aberto

1. `cc0f3ff` elimina a classe de falha do `verification` do accept20
   (versão vinda de contexto do usuário) sem derrubar `ok` legítimos.
2. `b81e8f6` (pool não-explorado declarado) reduz `missing` silencioso no M8.
3. Maior risco de flake no accept21: assessor não-lista no round 0
   (ocorreu 2× no accept19) e SearXNG morto/IP mudado.
4. Variância de retrieval single-run (~±0,1 de cobertura entre configs
   idênticas) pode mascarar ganho das correções — comparar antes/depois
   controlado no estado congelado, como no accept18→20.

## Resultado accept21 (evidência: `/home/thomaskyn/hermes-runs/accept21/`)

- **0/15 + 0 N/A** (diagnose buckets: 15× missing, total 15; ok/partial/na/
  assessor_error 0); síntese 7/15/79; verification overall **partial**
  (execution ok; question/review/support partial). RA8 PENDENTE.
- Corpus colapsou: 38/40 descobertos = YouTube (vast UP mudou a mistura de
  canais vs accept20 ddgs-only); `yt_live_fetches=0` (teto 2 não usado) →
  15 MB de boilerplate Innertube, 2 v2ex usáveis, 0 entidades
  (`entity_id null` nas 16 avaliações: 14 insufficient + 2 partial).
- Suporte: 7/22 frases sustentadas + 7 LACUNA sustentadas; **15 frases
  LACUNA citam `[1]`–`[6]` fora do corpus** (auto-marcadas no texto) + 18
  sem citação; 9 URLs YouTube fora da base de síntese.
- Hipóteses 1–2: **não testadas** — sem afirmação de versão no run
  (cc0f3ff sem alvo) e M8 sem disparo por vacuidade (b81e8f6 sem alvo).
- Hipótese 3: flake do assessor NÃO ocorreu (16 avaliações limpas);
  SearXNG morto confirmado nas duas portas.
- Hipótese 4: **confirmada e ampliada** — variância 5/52→0/15 entre runs
  idênticos (muito além de ±0,1); causa identificada: funil single-channel
  sem transcrição. Comparar correções exige run com corpus não-colapsado.
- **Suspeita de regressão (registrada, sem corrigir):** moldura LACUNA
  blinda citação não-resolvida no caminho de frases (claims 12/12 ok,
  frases 15 unsupported ⇒ só `partial`; accept19 falhava 1 caso assim).
  Investigar sem flexibilizar critério.
