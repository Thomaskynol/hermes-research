# Findings — agent-reach-accept21

## Estado do branch (evidência: `git log`, 2026-10-31)

- Branch `feat/product-v1`, HEAD `b1cf76c`
  ("docs(aceite): rodada accept19/accept20, correções de identidade, RA8 pendente").
- `cc0f3ff` — `fix(writer,diagnose)`: contexto do usuário não é evidência
  (regra estreita Missão 3: comparação numérica contra mínimo declarado =
  sustentada (premissa+corpus); compat funcional/integração sem fonte que
  mencione a versão = LACUNA, nunca a conclusão genérica antiga);
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

## Resultado accept23 (evidência: `/home/thomaskyn/hermes-runs/accept23/`)

- **0/55 + 0 N/A (0,0%)**; diagnose: `ok 0, partial_legit 24,
  missing_dimension_evidence 14, assessor_error 17`
  (sem `selection_context`, sem `synthesis_unsupported`, sem `na`).
  Síntese diagnose 49/1/66; verification-sentença 48/50 ok, 60 sem
  citação, 15 LACUNA sustentadas, 1 inferência declarada (nunca supported
  por âncora). Verification overall **failed**
  (execution ok; question/review partial; support failed). RA8 PENDENTE.
- Corpus de listagem com vast DOWN: 47 descobertos em 12+ hosts
  (github 15, opencode.ai 10, resto ≤3; 1 YouTube, `yt_live_fetches=0`);
  18/18 obtidos-usáveis, 18 analisados, 6 na síntese, 4 citados
  (counters). 5 nomes com identidade (lit-opencode, opencode-planner,
  Plannotator, opencode-handoff, opencode-local-memory).
- Failed por: **4 claims LACUNA [27,3,14,17] sobre handoff/local-memory
  ancoradas em páginas de listagem** — revisor reprova porque o doc
  menciona o nome (proximidade-em-listagem); assessor diz `insufficient`
  citando o mesmo tipo de doc (diagnose: `assessor_error` 17).
  Mesma classe do accept20 (17 lá, 17 aqui), agora nos dois níveis.
  1 frase `[8]` (Plannotator) sem suporte (overlap 0,14<0,35).
- Sem URLs nuas (`outside_corpus_citations: []`): classe accept19/22 não
  recorreu. Cobertura caiu 11/54→0/55 por corpus de listagem, não por
  regressão isolável (produto E corpus distintos entre os runs).
- Fixes `49508fe` exercitados: inferência-por-premissas segurou
  (INFERÊNCIA declarada 2×, combinação recusada, c12 insufficient);
  fato-usuário contido 2º run (2.1.4 só `[informado pelo usuário]`,
  compat = LACUNA, `user://` fora do corpus); janela auditada sem
  divergência; monopólio-break e b81e8f6 sem alvo.
- **Resíduo de medição registrado (sem corrigir):** corpo cita `([N])`
  (índices 1,7,8,9), extrator só enxerga URLs nuas da tabela-fonte ⇒
  `citations_evidence=0/resolved=0` (18/18 utility). Camada de contagem
  cega ao formato `[N]`; sentença (48/50 ok) é a camada que vale.
  Família do residual accept21 de índices `[N]`, invertido.

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

## Missão 3 — 3 contratos (2026-10-31, HEAD `cc1bf1c`)

Estado (evidência: `git log` + `git status` + `ss`/`docker`, 2026-10-31):
branch `feat/product-v1`, HEAD `cc1bf1c` (só docs do accept23; produto ==
`49508fe`); árvore rastreada limpa (só untracked pré-existente
`.planning/.active_plan`); `hermes-gateway` UP (9119/8081), :8001/:8888/:8082
sem listener (vast/searxng/embeddings DOWN, baseline restaurada).

Instruções superadas — varredura 2026-10-31: nenhuma restante como
pendência ativa. Phase 2/3 seguem SUPERADAS, Phase 4 RECLASSIFICADA
(Missão 2); único residual pendente era `selection_context` 16 (Phase 5),
que zerou no accept23 — marcado feito nesta missão, sem re-investigar.
`max-rounds 3` segue config de run, não requisito; run-vast-UP,
5-itens-como-requisito e pausa-mid-model seguem removidos.

Contratos (objetivo da Missão 3; implementação fora de escopo desta sessão):

1. `[N]` resolve — corpo cita `([N])` (accept23: índices 1,7,8,9), extrator
   só enxerga URLs nuas da tabela-fonte ⇒ `citations_evidence=0/resolved=0`
   (18/18 utility) enquanto a sentença vale 48/50 ok. Contrato: camada de
   contagem/extrator resolve citação in-text `[N]` → tabela-fonte.
2. versão-premissa — versão vinda de premissa explícita (usuário/contexto,
   `user://` fora do corpus, 2º run contido no accept23) não reprova como
   inferência; gate separado tag exata vs família funcional, conclusões
   separadas (semântica `49508fe`, Sessão 8).
3. inferência-complementaridade — frase que nomeia ≥2 entidades exige
   citação de interoperabilidade (doc com ≥2 entidades); sem ela, LACUNA
   explícita — complementaridade plausível vs integração testada
   (semântica `49508fe`, Sessão 8; accept23: combinação recusada,
   c12 insufficient).

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

## Resultado accept24 (evidência: `/home/thomaskyn/hermes-runs/accept24/`, HEAD `a70d837`)

Run real sob `a70d837` (hashes 8/8 OK pré/pós, sem edição no run), mesma
pergunta/config/infra DOWN (curl 000 pré/pós; vast NÃO subido por decisão —
colapso YouTube provado no accept21; SearxNG/embeddings impossíveis neste
lane, condições registradas no RELATORIO_ACCEPT24.md). 715s, EXIT=0.

- Cobertura oficial 9/56 + 0 N/A; diagnose ok 8/partial 14/missing 15/
  assessor_error 11/selection_context 7/synth_unsup 1; síntese 49/2/66.
- `support ok` (primeira vez) com `unsupported_claims []`; overall `partial`
  (question + review) — gargalo é cobertura/corpus, não veracidade.
- 3 contratos provados em run real: citations 68, evidence 51 (era 0),
  resolved 5 (era 0); versão numérica sustentada + funcional = LACUNA;
  combinação recusada por escrito. 5 nomes (local-memory com LACUNA de
  identidade declarada). **RA8 segue PENDENTE.**

## 3 divergências pós-accept24 — unificadas via TDD (2026-10-31)

Base: produto `a70d837` (Missão 3 provada); semântica `49508fe` + 3
contratos. Mesma entrada nos 3 auditores (`check_support` /
`verify_support` / `diagnose.synthesis_audit`), positivo+negativo,
genérico sem nomes (Widget Alpha/Beta).

1. **URL evidência sem `[N]`** (`diagnose_run.py:458`): síntese só extraía
   `[N]` via `CITE`; relatório com `https://...` (markdown/Source)
   sem `[N]` virava `uncited` no diagnose mas `unknown`/`failed` no
   verify. Fix: mesmo `extract_references`/`Classify` do verify; bare
   `utility`/`in_command` nunca pondera (como no verify); evidência fora
   do corpus = `unsupported` "citação fora do corpus" (nunca `uncited`);
   dentro entra em `cited_docs`; linhas de nota própria excluídas
   (mesmo `_is_own_note_line`).
2. **LACUNA sem gates** (`diagnose_run.py:513`): ramo sustentava após só
   premissa de entidade, sem gate de versão exata/família nem literal
   citado que o `check_support` aplica → LACUNA "compatível com 2.1.4"
   sem 2.1.4 no doc passava no diagnose, falhava no verificador. Fix:
   espelha gates (exata `versão exata ausente no doc citado`, família
   `família funcional ausente no doc citado`, literal `literal ausente
   no doc citado`); isenção de lacuna (`desconhecida`) preservada.
3. **Ponderação isentava qualquer premissa** (`verification_report.py:1586`):
   `sentence_misses` vazio com `support ok` vs check/diagnose `versão
   exata ausente`. Fix: regra estreita também na ponderação — numérico
   (`_is_numeric_comparison`) sustenta, funcional
   (`_claims_version_functionally`) reprova.

Prova: `tests/test_divergencias_auditores.py` (11 testes, RED 3→GREEN);
foco 73 passed, EXIT=0; ampla 536 passed + 1 falha pré-existente ambiente
(`retriever_timeout`, sem `gpt_researcher`, igual na árvore limpa).
Efeito isolado em cópia congelada accept24 (`/tmp/opencode/accept24-frozen2`,
`state.json` md5 igual ao original, original intacto): diagnose 49/2/66 →
39/12/66 (10 LACUNA versão/liter agora `unsupported`); verify `ok` →
`partial` com 8 misses — convergindo com check (`partial`), sem novo run.
**RA8 segue PENDENTE** (cobertura, não veracidade).

## Missão 4 — 3 contratos v2 (2026-10-31, HEAD `a656535`)

Estado (evidência: `git log` + `git status`, 2026-10-31): branch
`feat/product-v1`, HEAD `a656535` ("fix(verify,diagnose): 3 divergências
unificadas (TDD 11 passed; sem push)"); produto = `a70d837` + 3 fixes de
divergência (Sessão 13); árvore rastreada limpa (só untracked
pré-existente `.planning/.active_plan`); baseline DOWN restaurada
(vast/searxng/embeddings; gateway UP). Registro só em plano + docs;
**nenhuma lógica produto tocada**.

Contratos v2 (objetivo da Missão 4; implementação fora de escopo deste passo):

1. **inferência positiva** — hoje a inferência só é contida/recusada
   (declarada/LACUNA, Sessão 8 + Missão 3 provada no accept24). Falta o
   lado positivo: condições estreitas sob as quais uma inferência PODE ser
   `supported` (âncora + relação auditadas em separado; frase com ≥2
   entidades exige citação de interoperabilidade com ≥2 entidades no
   mesmo doc; fora disso, declarada/LACUNA, nunca promoção silenciosa).
2. **consistência entrega** — camadas de entrega convergem para o mesmo
   veredito: relatório §8 × `verification.json` (check/verify/ponderação)
   × diagnose. Resíduos que motivam: renderer-§8 `not_run/sem citações`
   vs auditor final `ok` (mensagem, accept24); verify `ok` vs check
   `partial` pré-Sessão 13 (unificado em cópia: verify → `partial` com
   8 misses). Invariantes: denominador nunca reduzido; divergência
   excerto-vs-full explícita via `hash_source`, nunca silenciosa.
3. **identidade/atribuição** — toda afirmação atribuída tem entidade
   resolvida + origem declarada (`fabricante vs independente vs usuário
   vs inferência`, R11.2; `user://` fora do corpus, citável só como
   premissa explícita sem número, Sessão 8). Sem identidade literal no
   excerto = LACUNA de identidade declarada (caso local-memory,
   accept24), nunca promoção por proximidade-em-listagem (classe
   accept20/23: assessor `insufficient` × revisor reprova).

**versão-premissa PRESERVADA** (invariante, regra estreita Missão 3 +
Sessão 13, sem flexibilizar): comparação numérica contra mínimo declarado
= sustentada (premissa explícita + doc de corpus com a tag); compat
funcional/integração sem fonte que mencione a versão = LACUNA (`versão
exata ausente` / `família funcional ausente` / `literal ausente`);
ponderação aplica a mesma regra estreita (numérico sustenta, funcional
reprova). Os 3 contratos v2 herdam essa regra, não a redefinem.

Instruções conflitantes — varredura 2026-10-31, a remover / manter removidas:

1. **Isenção ampla de premissa** (`_is_user_premise` isentando qualquer
   premissa): conflita com versão-premissa estreita + ponderação estreita
   (Sessão 13). Manter removida: só premissa numérica sustenta.
2. **Promoção de combinação plausível como `supported`**: conflita com
   v2-1 + trava interop (Missão 3 provada: combinação recusada por
   escrito no accept24). Manter removida: sem citação de
   interoperabilidade = LACUNA explícita.
3. **LACUNA sem gates como `supported`** (só premissa de entidade):
   conflita com v2-1/v2-2 (Sessão 13: espelho dos gates versão
   exata/família + literal). Manter removida.
4. **Bare `utility`/`in_command` ponderando veredito**: conflita com
   v2-2 (Sessão 13: nunca ponderam, como no verify). Manter removida.
5. **Evidência fora do corpus como `uncited`/ok**: conflita com v2-2
   (Sessão 13: fora do corpus = `unsupported` "citação fora do corpus",
   nunca `uncited`). Manter removida.
6. **Divergência excerto-vs-full silenciosa**: conflita com v2-2
   (`hash_source` + `excerpt_vs_fulltext`, Sessão 8). Manter removida:
   divergência sempre explícita.
7. **Redução de denominador para fechar RA8**: conflita com v2-2
   (denominador estável, §M6; RA8 PENDENTE por cobertura retrieval-bound,
   não por critério ajustável). Manter removida.
8. Instruções superadas Missão 2 seguem removidas: run-vast-UP,
   rounds-fixo, 5-itens-como-requisito, pausa-mid-model (ver seção
   Missão 2 acima).

## Missão 4 — 3 contratos v2 IMPLEMENTADOS (2026-10-31, TDD)

Base: produto `a656535` (3 divergências unificadas); semântica Missão 3 +
Sessão 13. Mesma entrada nos 3 auditores, genérico sem nomes
(Widget Alpha/Beta). `tests/test_missao4_contratos.py` (17 testes, RED
10→GREEN).

1. **Inferência positiva** (`verification_report.py`, `tools/diagnose_run.py`):
   POS doc-interop (menciona ambas, forma cheia) → `supported` + canal
   `declared`/`declared_inference` com premissas (quais docs/entidades) +
   limites (janela auditada, sem extrapolar); NEG docs separados →
   `declared`/LACUNA explícita (complementaridade plausível, não integração
   testada), nunca `unsupported` genérico; extrapolação ("integração
   testada", "ausência de conflitos" sem doc-interop) → rejeitado.
   `logo` não é marcador (`_has_inference_marker` só inferência/inferencia/
   inference/inferido). Versão numérica vs funcional preservada (numérica
   sustenta, funcional sem fonte reprova; gates antes/decisivos).
   Mecanismo: `_entity_mentioned` com fronteira + eid derivado `e-*`
   ignorado; `_sentence_supported` com identidade antes de overlap +
   atribuição estrita na frase (token "widget" não nomeia Beta).
2. **Consistência entrega** (`adaptive_coordinator.py`, `report_renderer.py`):
   two-pass — re-render do delivery com a verificação final (support
   re-auditado no markdown entregue) para o §8 apresentar a auditoria
   efetivamente concluída, não snapshot pré-delivery; dedupe de notas
   `tighten` no re-render (idempotente); gate vazio mantido (só vazio real
   sem URL e sem [N] é `not_run`). Prova: accept24 §8 `not_run`/`sem
   citações` era snapshot da 1ª verificação; após two-pass o §8 reflete o
   `support ok/partial` final com numbers estável e cited coerente.
3. **Identidade/atribuição** (`adaptive_coordinator.py`,
   `verification_report.py`): match eid com fronteira/forma cheia (ignora
   `e-*`/`eN`, exige `\b`); `_evaluation_refs_have_identity` novo
   (genérico, `_identity_matches`+`_singleton_rare` no texto auditado) —
   covered/partial com entity_id sem doc da entidade é demitido a
   insufficiency com nota (nunca promove por proximidade-em-listagem);
   bypass quando a entidade não tem parte distintiva (legado preservado).
   `_rank_unfetched` com fronteira de token + desempate por identidade
   (parte distintiva na URL) antes da ordem; `_entity_doc` com slug por
   token (não substring). Caso DoozieSoftware/everything-opencode
   (planner.md genérico) vs timrichardson/opencode-planner corrigido pelo
   mecanismo geral (doc genérico não menciona "opencode-planner" na forma
   cheia → não atribui a e-planner), sem hardcode de nomes.

Prova isolada em CÓPIAS congeladas (originais intactos, md5 igual):
accept23 (`/tmp/opencode/accept23-missao4/state.json`, md5
`840ed3ed…` igual ao original): check `ok` 63/82 (declared 15 +
declared_inf 35), diagnose 49/1/66 + declared 14, verify `failed`
(resolvidos 4, sem unknown — failed honesto pelas 4 LACUNA semânticas,
misses 0). accept24 (`/tmp/opencode/accept24-missao4/state.json`, md5
`233a3ef6…` igual): check `partial` 55/83 (declared 11 + 27), diagnose
39/12/66 + declared 5, verify `partial` (resolvidos 5, misses 8× literal
`opencode-local-memory` — LACUNA de identidade declarada, sem promoção).
Sem novo run real. **RA8 segue PENDENTE** (cobertura, não veracidade).

Instruções conflitantes — varredura 2026-10-31: nenhuma restante ativa
nos prompts (writer/assessor já estreitos: numérica sustenta, funcional =
LACUNA; interop exigida; user:// fora do corpus). Mantidas removidas as 8
da Missão 4 + 4 da Missão 2.

## Sessão 16 (2026-10-31) — identidade estrita: 2 resíduos do contrato v2-3

1. **Fronteira forma cheia** (`adaptive_coordinator.py:941`):
   `_identity_matches` usava `frase in doc` (substring) — "Widget Alpha"
   casava "Widget Alphabeta". Agora exige `(^| )frase($| )` no texto
   normalizado, mesmo conceito de `_entity_mentioned`. Caso: doc só com
   prefixo → `_evaluation_refs_have_identity` False → covered/partial
   com entity_id demitido a insufficiency (gate existente, sem mexer).
   Single-token fallback e `_singleton_rare` intactos (fora do escopo;
   singletons raros como "planner" seguem presença).
2. **Slug não-basta** (`:1058`): `_evaluation_refs_have_identity`
   auditava `f"{url}\n{corpo}"` — slug com o nome satisfazia identidade
   sem o corpo mencionar a entidade. Agora audita só o corpo
   (alinha a `_entity_corpus_docs`, que usa só corpo). Outros chamadores
   `f"{url}\n{texto}"` (excerpt 2115, discovery 3309/3440) intactos —
   fora do escopo pedido. TDD 2 RED→GREEN; ampla 555 passed + 1 falha
   ambiente pré-existente; sem push.

## Resultado accept25 (evidência: `/home/thomaskyn/hermes-runs/accept25/`, HEAD `4b40bbe`)

Run real sob `4b40bbe` (hashes 8/8 OK pré/pós, sem edição no run), mesma
pergunta/config/infra DOWN (curl 000 pré/pós; vast NÃO subido por decisão —
colapso YouTube provado no accept21; SearXNG/embeddings impossíveis neste
lane, condições registradas no RELATORIO_ACCEPT25.md). 437s, EXIT=0.

- Cobertura oficial 0/35 + 0 N/A; diagnose missing 11/selection 22/
  partial_legit 2 (sem ok, sem assessor_error); síntese 62/9/55 + declared
  26; sentença 59 + 12 unsupported com reason + 33 sem citação;
  `unsupported_claims []`; verification execution ok/question partial/
  review partial/**support ok** (2ª vez consecutiva); overall **partial —
  RA8 segue PENDENTE**.
- 3 contratos v2 provados em run real (previsto cópia congelada accept24):
  4 combinações §8 em `declared` (extrapolação recusada); §8-Anexo = verify
  final (two-pass, numbers 41/24/24/24/6/10 estável, sem `not_run`, sem
  nota duplicada); bandonker 3× LACUNA identidade sem promoção;
  citations 103/evidence 74/resolved 5/unknown [] (Missão 3 intacta).
- 5 nomes (planner, planning-with-files, Plannotator, opencode-review,
  bandonker; bandonker = LACUNA de identidade no excerto, declarada;
  erskingardner fora da seleção por motivo do plano; URLs alternativos não
  investigados, sem fato afirmado). 0 URLs nuas.
- Resíduos registrados sem corrigir: `selection_context` 22 (assessor trouxe
  docs genéricos — miss de seleção, sem leniência); `review partial`
  (revisão incompleta + 72 votos sem falha técnica); 4 `sem sobreposição`
  honestas; monopólio-break e M8 sem alvo.
- Intervalo `a70d837..a656535`: produto real = `a656535`
  (`tools/diagnose_run.py` +97 Div1/Div2 + `verification_report.py` +6 Div3
  ponderação estreita + `tests/test_divergencias_auditores.py` 11 TDD);
  `8040f87` no intervalo é só docs do accept24 (zero produto — excluído).
  Validação por teste cobrindo cada mudança (RED→GREEN + foco/ampla + cópia).

## Nota pós-accept25 — embeddings UP, path native sem uso (sem produto)

- `172.17.0.1:8082` UP (`/health` 200, `{"status":"ok"}`), mas o path
  `native` do accept25 fez **zero requests** (manifest/counters/verification
  sem embedding; hits em `state.json` são texto de corpus). Conexão/
  demonstração integrada fica para o próximo lane; produto intocado.
