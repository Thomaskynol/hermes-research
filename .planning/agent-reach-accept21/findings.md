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

## Revisão 2026-10-31 (pós-accept22, HEAD `534c946` → novo commit docs)

- Teste `test_pool_reserve_mention_window.py:101` (`or True`) era
  tautologia — provado RED com ops fabricadas (asserção antiga retorna
  `True` mesmo sobre `read_source` inventado). GREEN: sem-pool exige
  `_pick_pool_reserve→(None,None)` + zero `read_source` + zero nota;
  teste-de-falha exige URL boa em `read_source` + nota registrada.
  Foco 20 passed, EXIT=0 (sem `cat/head/sed` no fluxo; `grep`+`read`).
- Matriz sincronizada com entrega atual: RA8 = accept22 11/54 failed
  honesto, PENDENTE; seção "Entrega atual" + "Escopo REAL vs PENDENTE"
  (5 itens sem validação: gateway vast, deep 10h, conduct_research,
  pausa mid-model, multiusuário — limitação, sem fechar aceite);
  HEADs explicitados (produto frozen `a704463`/`776af89` vs docs).
- Riscos amarelos registrados como limitação (CONTINUIDADE +
  matriz): janela legado `u>start`, ranking low, nota duplicada,
  single-hit transcrição, versão major nua, LACUNA overlap 0,
  B5 convergência. Sem refatorar — nenhum teste prova bug crítico.

## Resultado accept22 (evidência: `/home/thomaskyn/hermes-runs/accept22/`)

- **11/54 + 0 N/A (20,4%)**; diagnose: `ok 10, partial_legit 11,
  missing_dimension_evidence 16, selection_context 16,
  synthesis_unsupported 1` (c7/e5: covered avaliado, sem suporte na
  síntese). Síntese 65/9/59 (verification conta 57/17/30 — métodos
  distintos, mesma conclusão). Verification overall **failed**
  (execution ok; question/review partial; support failed). RA8 PENDENTE.
- Corpus saudável com vast DOWN: 31 descobertos em 11 hosts (github 9,
  opencode.ai 8, resto ≤3; 1 YouTube); 28/28 obtidos-usáveis, 22
  analisados, 55 avaliações com **0 assessor_error**. 5 nomes com
  identidade (lit-opencode, opencode-browser, plugin-testing/dzianisv,
  opencode-plugins/jadmadi, Context7).
- Failed por: (1) 5 URLs nuas fora do corpus (renderer auto-declarou e
  removeu das fontes — honesto mas não resolve a citação);
  (2) claims [12,13,14] = as 3 inferências de combinação do §11,
  reprovadas pelo revisor (inferência composicional ≠ evidência direta);
  (3) 17 frases LACUNA com citação in-corpus sem overlap (0,00–0,22).
- Hipóteses 1–2 (cc0f3ff/b81e8f6): 1 com sinal positivo fraco — classe de
  falha do accept20 (inferência de versão) não recorreu; sentença de
  compat declara LACUNA com contexto marcado e fica contida
  (sentence-unsupported, sem promoção). 2 sem alvo (M8 sem disparo).
  Não são provas isoladas (corpus distinto do accept20).
- Hipótese 3 (flake assessor): 0 erros em 55 avaliações — 2 runs seguidos
  limpos (accept21 teve 0 em 16).
- Hipótese 4 (variância): confirmada por contraste — vast DOWN 11/54 vs
  vast UP 0/15, mesma config (fator causal: mistura de canais; ddgs+arXiv
  cobrem, funil YouTube sem transcrição colapsa).
- Leniência LACUNA (regressão suspeita do accept21): **estreitada** —
  URL nua fora do corpus ⇒ `failed` (igual accept19); índices `[N]`
  in-corpus sem overlap ⇒ unsupported em sentença; o caso accept21
  (índices fora da base de síntese ⇒ só `partial`) segue como classe
  aberta a investigar, sem flexibilizar critério.
- Fix `a704463` monopólio-break: sem alvo neste run (diversidade veio do
  canal morto, não necessariamente do código); disparo não isolável.
  Residual novo/recorrente: `selection_context` 16 (accept20: 4);
  c11/c12 seguem insufficient (corpus sem material comparativo).

## Revisão de coerência — Missão 2 (2026-10-31, HEAD `15443a5`)

### Estado atual (evidência: `git log` + `git status` + `ss`, 2026-10-31)

- Branch `feat/product-v1`, HEAD `15443a5`
  ("docs+test(revisao): tautologia or True vira assercao estrita …").
- `git status`: só untracked pré-existente `.planning/.active_plan`
  (conteúdo `agent-reach-accept21`); árvore rastreada limpa.
- Serviços: `hermes-gateway` UP (9119/8081); **:8001 (vast), :8888
  (searxng), :8082 (embeddings) sem listener** — baseline DOWN restaurada.
- CLI: `opencode v2.2.5`.

### Configuração efetiva (evidência: código, sem presumir)

- `vast_local_retriever.py:11-14`: `RETRIEVER=custom,searx,duckduckgo,arxiv`,
  `RETRIEVER_ENDPOINT=http://127.0.0.1:8001/`,
  `SEARX_URL=http://127.0.0.1:8888/`.
- `SEARXNG_URL` do ACEITE_V1.md usa IP de bridge (`http://172.18.0.2:8888`) —
  **frágil, pode mudar**; revalidar com `/healthz` → 200 antes de cada run.
- Runs accept21/22 usaram medium/max-rounds-3, contexto
  `installed_opencode_version=2.1.4`, modelo
  `opencode-go/muse-spark-1.3-contributor`. `max-rounds 3` era **config
  desses runs, não requisito fixo** (rodadas: controle independente,
  R6.4 / modelagem §6).

### Conferência de obrigatoriedade dos "cinco bloqueadores"

Fonte: `docs/ACEITE_V1.md` § Limites ("Sem validação: …") ×
`docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` ×
`docs/REQUIREMENTS_MATRIX.md`. Regra: **item listado como não validado
não vira requisito adicional automaticamente**.

| # | Item "Sem validação" | Base normativa | Classe |
|---|---|---|---|
| 1 | Gateway vast local no ar em run real | Modelagem §3.1 (busca por infra própria); matriz R3.1 = BLOQUEADO | **PENDENTE legítimo** (obrigatório, sem validação; accept21 subiu on-demand e desligou) |
| 2 | Perfil deep 10h | Modelagem §6: tempos são "referências iniciais, não cotas obrigatórias"; matriz sem R exigindo run deep | **Fora de escopo como quota** (só medium exercitado; deep-10h não é critério de aceite) |
| 3 | `conduct_research` ponta a ponta da biblioteca | Modelagem §15: sem função nominal obrigatória; matriz R15.2 (biblioteca encapsulada) = IMPL; ponta a ponta já coberta via CLI (RA5 = REAL) | **Fora de escopo como requisito adicional** (segunda interface, sem R distinto) |
| 4 | Pausa no meio de chamada ao modelo | ACEITE_V1.md declara "Limite conhecido: pausa só entre rounds"; modelagem §14 exige pausa/retomada da pesquisa (R14.3 = REAL via hermdemo6, entre rounds) | **Limite documentado, não ação** (contradiz o próprio roteiro pedir mid-call) |
| 5 | Multiusuário | Sem requisito na modelagem (§14: run_id por pesquisa) nem R na matriz | **Fora de escopo** (nunca foi critério; não bloqueia o aceite) |

Conclusão: só o item 1 é pendência legítima (e mesmo ele é BLOQUEADO por
ambiente, não falha de produto). RA8 continua sendo o único critério
aberto do aceite; os demais itens não viram condição de fechamento.

### 4 inconsistências corrigidas nesta missão

1. **Run-com-vast-UP como instrução ativa** (`task_plan` Phase 2 + Next
   Step): superada — accept21 já rodou vast UP (colapsou 0/15) e accept22
   vast DOWN (11/54); baseline atual é DOWN. Subir serviço só sob nova
   hipótese explícita.
2. **"3 rounds" como fixo** (Phase 3): 3 era config accept21/22, não
   requisito — removido o caráter fixo (R6.4 / modelagem §6).
3. **5 itens "Sem validação" tratados como requisitos de fechamento**
   (Phase 4): reclassificados — são skips/limites do próprio ACEITE_V1.md;
   tabela acima separa PENDENTE legítimo (só item 1) vs fora de escopo.
4. **Pausa mid-model como pendência acionável** (Phase 4 item 4):
   contradiz o limite conhecido do roteiro + R14.3 REAL — registrada como
   limite documentado, sem ação associada.
