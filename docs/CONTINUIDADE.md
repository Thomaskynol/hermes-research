# CONTINUIDADE — aceite v1, branch `feat/product-v1`

> Ponto de entrada para retomar o trabalho. Plano ativo:
> `.planning/agent-reach-accept21/` (`task_plan.md`, `findings.md`, `progress.md`).
> Última atualização: 2026-10-31 (accept25: run real sob `4b40bbe`, 0/35
> partial, support ok 2ª vez, 3 contratos v2 provados, RA8 pendente;
> sem push). Commit local sem push.
>
> HEADs: produto `4b40bbe` (Missão 3 + 3 divergências + Missão 4 v2 +
> identidade estrita, executado no run accept25, hashes frozen reconferidos
> pré/pós-run); docs + matriz sync Missão 4/accept25 (este passo).

## Objetivo e escopo

Fechar o aceite v1: **RA8 `passed` em run real, sem flexibilizar**.
Os 5 itens "Sem validação" (`docs/ACEITE_V1.md`, seção Limites) são
**limites declarados (skips), não critérios de aceite** — item não
validado não vira requisito adicional automaticamente. Conferência
contra modelagem v1.1 + matriz (`findings.md`, Missão 2):

- **PENDENTE legítimo:** (1) gateway vast local no ar em run real
  (R3.1 = BLOQUEADO por ambiente).
- **Fora de escopo / limite documentado:** (2) deep 10h (referência, não
  cota — modelagem §6); (3) `conduct_research` (segunda interface, sem R
  distinto; ponta a ponta já REAL via CLI); (4) pausa mid-model (limite
  conhecido do roteiro; R14.3 REAL entre rounds); (5) multiusuário
  (sem requisito na modelagem/matriz).

Condição inegociável: **RA8 segue PENDENTE, sem flexibilizar** — o `verification`
do accept20 falhou corretamente por 1 inferência com versão vinda do contexto
do usuário, e o diagnose concordou (sem divergência).

## Branch e HEADs

- Branch: `feat/product-v1`.
- `b1cf76c` — base congelada do run accept21 (hashes produto reconferidos
  pré/pós-run, sem edição durante o run).
- `d665550` — **só docs** do run accept21 (plano + findings; sem produto).
- `817a77b` — **produto**: pool-reserve B3 + mention-window B4
  (`adaptive_coordinator.py` +207), auditoria granular B2/B5
  (`verification_report.py` +232), 2 testes novos (10 passed).
  Hashes workdir == frozen do run: `9b3a577a…` / `dcff1404…`.
- `a704463` — **produto**: quebra de monopólio single-host sem transcrição
  + mistura por diversidade (`native_transport.py`) e gate de quote/versão
  em LACUNA + ponderação no `verify_support` (`verification_report.py`),
  2 testes novos (`test_web_monopoly_break`, `test_lacuna_quote_gate`).
  Suíte combinada fresca pós-commit: **84 passed** (8 arquivos).
- `776af89` — docs do accept21 + suíte (HEAD congelado do run accept22;
  hashes reconferidos pré/pós-run, sem edição durante o run).
- `534c946` — **só docs** do accept22 (findings/progress/CONTINUIDADE;
  `git show --stat` confirma zero arquivo produto). Produto segue ==
  `a704463`; hashes workdir conferem com `hashes.frozen` do accept22.
- `15443a5` — **docs + 1 teste estrito** (Missão 2: coerência do plano;
  tautologia `or True` vira asserção RED→GREEN, 20 passed; matriz sync
  accept22 + escopo REAL-vs-PENDENTE; sem lógica produto alterada).
- `49508fe` — **produto**: consultado-vs-mencionado + inferência por
  premissas + fato-usuário + janela (`verification_report.py`,
  `report_renderer.py`, `scripts/citation_audit.py`, `tools/diagnose_run.py`
  + `tests/test_consultado_inferencia_usuario_janela.py`, 13 testes;
  foco 137 passed). Executado no run accept23 (hashes 8/8 OK pré/pós-run).
- `cc1bf1c` — **só docs** do accept23 (plano + findings + CONTINUIDADE;
  `git show --stat` confirma zero arquivo produto). Produto segue ==
  `49508fe`. Base da Missão 3 (Sessão 10: 3 contratos registrados).
- `d2e5438` — docs do plano (Missão 3 registrada, HEAD `cc1bf1c`).
- `a70d837` — **produto**: 3 contratos ([N] resolve + versão-premissa +
  complementaridade; `verification_report.py` + `tools/diagnose_run.py` +
  `adaptive_coordinator.py` + `tests/test_missao3_contratos.py`, 16 testes;
  prova isolada em cópia congelada do accept23). Executado no run accept24
  (hashes 8/8 OK pré/pós-run, sem edição no run).
- `a656535` — **produto**: 3 divergências unificadas (Div1
  extract/Classify + Div2 gates versão/literal + Div3 ponderação estreita;
  `tools/diagnose_run.py` +97, `verification_report.py` +6,
  `tests/test_divergencias_auditores.py` 11 testes TDD; `8040f87` no
  intervalo é só docs do accept24, zero produto — excluído).
- `5a4a78b` — **produto**: 3 contratos v2 (inferência positiva, entrega
  two-pass, identidade/atribuição; 17 testes TDD).
- `4b40bbe` — **produto**: identidade estrita (forma cheia com fronteira +
  corpo decide em refs; 2 testes TDD). Executado no run accept25
  (hashes 8/8 OK pré/pós-run, sem edição no run).

## Resultado accept25 (evidência em `/home/thomaskyn/hermes-runs/accept25/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 437s.
  Código `4b40bbe` (hashes 8/8 OK pré/pós-run, sem edição no run).
  Provisionamento investigado antes do run: vast provisionável
  (`fastapi/uvicorn/httpx` OK) mas NÃO subido — accept21 provou
  colapso YouTube com vast UP; SearXNG impossível (sem imagem/script;
  condição: `docker pull searxng/searxng`); embeddings impossível (sem
  launcher; condição: harrier UP em `172.17.0.1:8082`).
- Cobertura **0/35 + 0 N/A (0%)** (missing 11, selection_context 22,
  partial_legit 2; sem ok, sem assessor_error); síntese diagnose 62/9/55
  + declared 26; sentença 59 sustentadas + 12 unsupported com reason
  (versão/identidade/overlap) + 33 sem citação; `unsupported_claims []`,
  `outside_corpus []`; **support `ok` (2ª vez consecutiva)**;
  **overall `partial`; RA8 segue PENDENTE**.
- Prova real dos 3 contratos v2 (previsto na cópia congelada: check partial,
  diagnose + declared, verify partial): **confirmado** — 4 frases-combinação
  do §8 em canal `declared` (nenhuma promoção silenciosa, extrapolação
  recusada); §8-Anexo reflete verify final (two-pass, numbers estável,
  sem `not_run`); bandonker sem identidade isolada = 3 LACUNA declaradas,
  sem promoção por listagem. Citations 103, evidence 74, resolved 5,
  unknown [] (Missão 3 intacta).
- Corpus web sem YouTube (41 descobertos/24 usáveis, 10 citados, 6 na
  síntese): **5 nomes** (opencode-planner, planning-with-files, Plannotator,
  opencode-review, bandonker — este último LACUNA de identidade no excerto,
  declarada; `opencode-code-review` erskingardner fora da seleção por motivo
  do plano; URLs alternativos não investigados, sem fato afirmado).
- Resíduos sem corrigir (sem edição de produto neste lane): `selection_context`
  22 (assessor trouxe docs genéricos em vez dos docs da entidade — miss de
  seleção, sem leniência); `review partial` (revisão incompleta + 72 votos
  sem falha técnica); 4 `sem sobreposição` honestas; monopólio/M8 sem alvo.

## Resultado accept24 (evidência em `/home/thomaskyn/hermes-runs/accept24/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 715s.
  Código `a70d837` (hashes 8/8 OK pré/pós-run, sem edição no run).
  Provisionamento investigado antes do run: vast provisionável
  (`vast_local_retriever.py`, deps OK) mas NÃO subido — accept21 provou
  colapso YouTube com vast UP; SearXNG impossível (sem imagem/script;
  condição: `docker pull searxng/searxng`); embeddings impossível (sem
  launcher; condição: harrier UP em `172.17.0.1:8082`).
- Cobertura **9/56 + 0 N/A (16,1%)** (ok 8, partial_legit 14, missing 15,
  assessor_error 11, selection_context 7, synthesis_unsupported 1);
  síntese diagnose 49/2/66; sentence 38 sustentadas + 13 LACUNA com reason
  + 25 sem citação; `unsupported_claims []`, `outside_corpus []`;
  **support `ok` (primeira vez: accept21 partial, accept22/23 failed)**;
  **overall `partial`; RA8 segue PENDENTE**.
- Prova real dos 3 contratos (previsto na cópia congelada: citations 68,
  evidence ~50, resolved ≥4): **confirmado** — citations 68, evidence 51
  (era 0), resolved 5 (era 0), unknown []; versão numérica 2.1.4≥2.1.2
  sustentada + funcional sem fonte = LACUNA (`versão exata ausente`, 3×);
  5 frases-combinação LACUNA + "INFERÊNCIA NÃO SUSTENTADA, NÃO AFIRMAR".
- Corpus web sem YouTube (30 descobertos/16 usáveis, 8 citados, 6 na
  síntese): **5 nomes** (planner, planning-with-files, Plannotator,
  handoff, local-memory — este último LACUNA de identidade no excerto,
  declarado; `c-discover` synthesis_unsupported pelo elo fraco).
- Resíduos sem corrigir (sem edição de produto neste lane): snapshot do
  renderer-§8 diz `support not_run/sem citações verificáveis` (camada
  claim/URL-nua) vs auditor final `support ok` — divergência de mensagem,
  sem efeito no veredito; `selection_context 7` (miss do assessor, não
  leniência).

## Riscos amarelos (limitações registradas — sem refatorar)

Achados de revisão classificados amarelos (não-críticos; nenhum teste
prova bug crítico — **sem refatoração neste passo**; reavaliar só com
evidência de teste). Espelho resumido em `docs/REQUIREMENTS_MATRIX.md`
§ Escopo.

- **Janela legado `u>start`** (`adaptive_coordinator.py:473`, `take()`):
  caminho sem grupos usa `any(start < uend and u > start)` — janela que
  começa antes mas invade o span usado não é dedupada; caminho com
  grupos (B4) usa `u < end` estrito. Mantido por testes de regressão do
  preenchimento legado.
- **Ranking low** (`_rank_unfetched`, l.1311): contagem de ocorrências
  de substring na URL; empate mantém ordem original. Sem ranking
  semântico — URL fraca pode vencer empate.
- **Nota duplicada** (`select_ops`, l.1537): nota `pool reserve:` anexada
  por round; mesmo alvo em N rounds ⇒ N notas. Cosmético, sem efeito
  lógico (reserva em si é dedupada por `used_in_batch`/evidência/falha).
- **Single-hit transcrição** (`native_transport.py:287`,
  `_needs_diversity`): 1 hit com marcador `[transcript]/[spoken]`
  isenta a página inteira da mistura por diversidade — suprime fallback
  mesmo com restante da página monopolizada.
- **Versão major nua** (`verification_report.py:150`,
  `_text_versions`): regex só casa `\d+\.\d+`/`Vn`; "versão 2" isolada
  é invisível ao gate — par "v2" (frase) × "2.1.4" (doc) decide no
  overlap genérico, não em lógica de versão.
- **LACUNA overlap 0** (`verify_support`): frase LACUNA com citação
  in-corpus mas overlap 0 ⇒ unsupported. 17 casos no accept22 —
  rigor correto, volume residual a acompanhar.
- **B5 convergência** (`verify_support` l.1028 + `_selection_window`
  l.189): ponderação `sentence_support` quando a citação é do doc da
  entidade; convergência/estabilidade entre rounds provada só em unit
  (accept21/22 sem alvo: M8 sem disparo, monopólio sem alvo).
  Divergência excerto-vs-auditado fica explícita via `hash_source`,
  nunca silenciosa.

## Resultado accept23 (evidência em `/home/thomaskyn/hermes-runs/accept23/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 588s.
  Código `49508fe` (hashes 8/8 OK pré/pós-run, sem edição no run).
- Cobertura **0/55 + 0 N/A (0%)** (ok 0, partial_legit 24, missing 14,
  assessor_error 17; sem selection_context/synthesis_unsupported);
  síntese diagnose 49/1/66; verification-sentença 48/50 ok + 15 LACUNA +
  1 inferência declarada; **verification overall `failed`**;
  **RA8 segue PENDENTE**.
- Corpus de listagem sem YouTube (47 descobertos/12+ hosts, 18 usáveis,
  18 analisados, 0 erro grave): **5 nomes com identidade**
  (lit-opencode, opencode-planner, Plannotator, opencode-handoff,
  opencode-local-memory). Failed por 4 LACUNA [27,3,14,17] ancoradas em
  listagens (classe accept20, 17 lá e cá) + 1 frase `[8]` sem overlap.
  Sem URLs nuas (classe accept19/22 ausente).
- Fixes: inferência-contida exercitada e segurou (2× declarada, combinação
  recusada, c12 insufficient); fato-usuário contido 2º run (`user://` fora
  do corpus); janela sem divergência; monopólio/b81e8f6 sem alvo.
  Resíduo sem corrigir: contador de citações cego a `([N])`
  (evidence/resolved 0; sentença 48/50 é a camada que vale).
- Antes/depois vs accept22: 11/54→0/55 por corpus de listagem (produto E
  corpus distintos — sem causalidade isolável); melhorou: 0 URLs nuas,
  inferências contidas, fato-usuário contido, janela auditada.

## Resultado accept22 (evidência em `/home/thomaskyn/hermes-runs/accept22/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 658s.
- Cobertura **11/54 + 0 N/A (20,4%)** (ok 10, partial_legit 11, missing 16,
  selection_context 16, synthesis_unsupported 1); síntese 65/9/59;
  **verification overall `failed`**; **RA8 segue PENDENTE**.
- Corpus saudável sem YouTube (31 descobertos/11 hosts, 28 usáveis,
  22 analisados, 0 assessor_error): **5 nomes com identidade**
  (lit-opencode, opencode-browser, plugin-testing/dzianisv,
  opencode-plugins/jadmadi, Context7). Failed por 5 URLs nuas fora do
  corpus + 3 inferências de combinação reprovadas [12,13,14] + 17 LACUNA
  sem overlap — métodos de acordo, sem leniência em URL nua.
- Fixes: cc0f3ff com sinal positivo fraco (classe accept20 ausente;
  sentença compat declara LACUNA contida); quote-gate manteve `failed`
  em URL nua (leniência accept21 estreitada ao caminho de índices `[N]`);
  monopólio-break e b81e8f6 sem alvo (sem monopólio; M8 sem disparo).
  Residual: selection_context 16; c11/c12 insufficient.
- Contraste causal: vast DOWN 11/54 vs vast UP 0/15, mesma config
  (ddgs+extração cobrem; funil YouTube sem transcrição colapsa).

## Resultado accept21 (evidência em `/home/thomaskyn/hermes-runs/accept21/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4, EXIT=0, 343s.
- Cobertura **0/15 + 0 N/A** (15× `missing_dimension_evidence`); síntese
  7/79/15; **verification overall `partial`**; **RA8 segue PENDENTE**.
- Corpus colapsou em funil YouTube sem transcrição (`yt_live_fetches=0`,
  40/2/2, 0 entidades) — utilidade **nula como guia**, mas **negativo honesto**.
- `cc0f3ff`/`b81e8f6` **não exercitadas** (sem afirmação de versão; M8 sem
  disparo). Fixes B2–B5 acima também **não exercitados** em run real.
- Regressão registrada sem corrigir: 15 frases LACUNA com citação fora do
  corpus ⇒ só `partial` (accept19 falhava corretamente 1 citação assim) —
  suspeita de **leniência LACUNA × citação**.

## Serviços (2026-10-31, pós-run accept24)

- `hermes-gateway` UP (9119/8081). **vast `:8001` DOWN** (accept21 subiu
  on-demand e desligou; accept22, accept23 e accept24 rodaram com DOWN
  pré/pós confirmado; accept24: provisionável mas não subido — decisão
  registrada no RELATORIO_ACCEPT24.md). SearxNG DOWN (sem imagem docker;
  condição: `docker pull searxng/searxng`), embeddings DOWN (sem launcher;
  condição: harrier UP em `172.17.0.1:8082`) — ver tabela de
  provisionamento no RELATORIO_ACCEPT24.md.

## Ambiente e configuração efetiva

- CLI: `opencode v2.2.5` (verificado com `opencode --version` em 2026-10-31).
- Serviços (observado em 2026-10-31 via `docker ps` + `ss -ltn`):
  `hermes-gateway` UP (9119/8081); **vast, searxng e embeddings STOPPED** —
  sobem on-demand (`:8001` e `:8888` sem listener).
- Retriever (docstring de `vast_local_retriever.py`):
  `RETRIEVER=custom,searx,duckduckgo,arxiv`,
  `RETRIEVER_ENDPOINT=http://127.0.0.1:8001/`,
  `SEARX_URL=http://127.0.0.1:8888/`.
- Atenção: `SEARXNG_URL` do roteiro usa IP de bridge (`http://172.18.0.2:8888`) —
  **frágil, pode mudar**; revalidar com `/healthz` → 200 antes de cada run.

## Correções validadas só em unit test (pendentes de run real)

| Commit | O que muda | Validado até agora |
|--------|------------|--------------------|
| `cc0f3ff` | contexto do usuário não é evidência (regra estreita Missão 3: comparação numérica contra mínimo declarado = sustentada (premissa+corpus); compat funcional/integração sem fonte que mencione a versão = LACUNA); bucket `na_scoped` no diagnose | unit test + **contido em 2 runs reais (accept22: 1º sinal; accept23: 2º sinal, `user://` fora do corpus)** |
| `49508fe` | consultado-vs-mencionado + inferência-por-premissas + fato-usuário + janela | foco 137 passed + **exercitado em run real (accept23: inferência contida, fato-usuário contido 2º run, janela sem divergência)**; resíduo: contador cego a `([N])` (registrado, sem corrigir) |
| `a70d837` | 3 contratos: `[N]` resolve + versão-premissa + complementaridade | 16 testes (TDD RED→GREEN) + prova isolada em cópia congelada + **PROVADO em run real accept24: support failed→ok, evidence 0→51, resolved 0→5; versão numérica sustentada; combinação recusada**; resíduos: renderer-§8 `not_run` vs auditor `ok` (mensagem, sem efeito), `selection_context 7`, local-memory sem identidade literal |
| `a656535` | 3 divergências: URL evidência sem `[N]`, LACUNA com gates, ponderação estreita | 11 testes TDD (`test_divergencias_auditores.py`, RED 3→GREEN) + 73 foco verde + efeito isolado em cópia accept24 (diagnose 49/2→39/12, verify ok→partial, convergindo com check); sem novo run real |
| este passo | identidade estrita: `_identity_matches` exige forma cheia com fronteira (`Widget Alphabeta` não casa `Widget Alpha`, como `_entity_mentioned`); `_evaluation_refs_have_identity` audita só o corpo, slug da URL sozinho não basta (alinha a `_entity_corpus_docs`) | 2 testes TDD (`test_missao4_contratos.py`, RED 2→GREEN; arquivo 19 passed, versão-premissa + POS/NEG intactos) + combinados 65 passed + ampla 555 passed (1 falha ambiente pré-existente, igual na árvore limpa); sem novo run real |
| `b81e8f6` | M8: entidade fraca sem troca registra pool não explorado | só unit test (M8 sem disparo em accept21 e accept22) |
| `817a77b` | B3 pool-reserve; B4 mention-window; B2/B5 auditoria granular | 10 passed (2 arquivos novos); sem prova em run real |
| `a704463` | quebra de monopólio single-host + diversidade; gate de quote em LACUNA | unit test + suíte 84 passed; accept22 sem alvo para monopólio, quote-gate manteve `failed` em URL nua |

Unit tests pós-commit: `test_audit_granularity` + `test_pool_reserve_mention_window`
10 passed, mais `test_web_monopoly_break` + `test_lacuna_quote_gate`
(suíte combinada fresca 84 passed). Accept22 deu primeiro sinal real
parcial (ver seção accept22 acima); prova isolada das quatro correções
segue pendente.

## Bloqueios, hipóteses e próxima ação

- **Bloqueios:** serviços vast/searxng parados (on-demand, esperado);
  SearXNG com IP frágil; risco de flake do assessor no round 0 (não-lista 2×
  no accept19); variância de retrieval single-run (~±0,1) pode mascarar ganhos.
- **Hipóteses:** `cc0f3ff` elimina a classe de falha do `verification` do
  accept20 sem derrubar `ok` legítimos; `b81e8f6` reduz `missing` silencioso
  no M8. Detalhes em `.planning/agent-reach-accept21/findings.md`.
- **Instruções superadas (removidas na Missão 2, seguem removidas):**
  run-com-vast-UP, rounds-3-como-fixo, 5-itens-como-requisito,
  pausa-mid-model como ação.
- **Instruções conflitantes Missão 4 (removidas, seguem removidas):**
  isenção ampla de premissa, promoção de combinação plausível, LACUNA sem
  gates, bare utility ponderando, fora-do-corpus como `uncited`/ok,
  divergência excerto-vs-full silenciosa, redução de denominador.
  Nenhuma restante ativa nos prompts (writer/assessor estreitos).
- **Lição do accept19 (não repetir):** run rodou sobre código desatualizado por race
  com o commit — **conferir `git rev-parse HEAD` antes de cada run**.
- **Próxima ação (accept25 EXECUTADO — 3 contratos v2 provados em run real,
  RA8 segue pendente):** hipótese do run era a primeira prova real sob
  `4b40bbe` (Missão 4 v2 + identidade estrita) — cumprida: POS→declared,
  two-pass §8=final, identidade sem promoção; support ok 2ª vez; overall
  `partial` por cobertura (0/35), não por veracidade — gargalo é
  corpus/seleção (`selection_context 22`, `assessor_error 0`), não
  leniência. Nota: embeddings `:8082` UP mas path native fez zero requests
  — conexão/demonstração integrada fica para o próximo lane, sem produto
  neste lane. Fechar Phase 5 (ACEITE_V1_RESULTADO + check-complete); próximo
  run só sob nova hipótese explícita.
  - (1) `[N]` resolve — **PROVADO em run real**: citations 68, evidence
    51, resolved 5, unknown [] (accept24); `support failed→ok`;
  - (2) versão-premissa — **PROVADO em run real**: 2.1.4≥2.1.2 sustentada
    ([5]); funcional sem fonte = LACUNA `versão exata ausente` (3×);
    fato-usuário contido (3º run);
  - (3) inferência-complementaridade — **PROVADO em run real**: 5 frases
    LACUNA + "INFERÊNCIA NÃO SUSTENTADA, NÃO AFIRMAR"; diagnose sem
    promoção indevida.

## Accept26 (2026-10-31) — sonda de embeddings no path native PROVADA

- Produto mínimo (TDD RED→GREEN, 6 testes `test_native_embeddings.py`):
  `_assess_round` faz 1× `POST {EMBEDDING_SERVER_URL}/embeddings` por rodada
  (default `http://172.17.0.1:8082/v1`, modelo `harrier-oss-v1-0.6b`);
  registra endpoint/modelo/prompt_tokens em `state["embeddings"]` + nota;
  manifest expõe o resumo. Nunca levanta, nunca gasta budget, nunca altera
  avaliações; down = `unavailable` + efeito, sem fallback; `sync_config.py`
  intocado. `adaptive_coordinator.py` +101, `run_manifest.py` +25,
  `adaptive_state.py` +1.
- Run real `hermes-runs/accept26` (8082 UP, light, native, max-rounds 2,
  EXIT=0, stop `rounds`, coverage `partial` 0.04): **3 probes ok**
  (prompt_tokens 58 cada) em state+notas+manifest; `--metrics`
  `prompt_tokens_total` 16→76 (repeats no KV-cache: cached 117 ≈ 2×58).
  Usou embeddings: `_assess_round`. Dispensou: planner, search/fetch,
  writer, auditor, budgets. Contadores 35/25/25/25/6/7. Relatório:
  `hermes-runs/accept26/RELATORIO_ACCEPT26.md`. RA8 segue pendente
  (gargalo é corpus/seleção, não veracidade).

## Referências

- Roteiro: `docs/ACEITE_V1.md`
- Resultado acumulado: `docs/ACEITE_V1_RESULTADO.md` (§16 = accept19/accept20)
- Relatórios: `/home/thomaskyn/hermes-runs/accept19/DIAGNOSIS_accept18.md`,
  `/home/thomaskyn/hermes-runs/accept20/RELATORIO_ACCEPT20.md`
- Contrato reach: `docs/AGENT_REACH.md`
