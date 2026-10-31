# CONTINUIDADE — aceite v1, branch `feat/product-v1`

> Ponto de entrada para retomar o trabalho. Plano ativo:
> `.planning/agent-reach-accept21/` (`task_plan.md`, `findings.md`, `progress.md`).
> Última atualização: 2026-10-31 (Sessão 9: run accept23 real sob
> `49508fe` — 0/55 failed honesto, 5 nomes, 4 correções exercitadas;
> RA8 segue PENDENTE). Commits produto e docs separados (sem push).
>
> HEADs: produto `49508fe` (consultado/mencionado + inferência-por-premissas
> + fato-usuário + janela; executado no run accept23, hashes frozen
> reconferidos pré/pós-run); docs evoluem sem tocar produto.
> `git show --stat` do intervalo prova docs-only (plano + CONTINUIDADE).

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

## Resultado accept23 (evidência em `/home/thomaskyn/hermes-runs/accept23/`)

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

## Serviços (2026-10-31, pós-run)

- `hermes-gateway` UP (9119/8081). **vast `:8001` DOWN** (accept21 subiu
  on-demand e desligou; accept22 e accept23 rodaram com DOWN pré/pós
  confirmado). SearxNG DOWN (sem imagem docker), embeddings DOWN — igual
  ao accept20.

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
| `cc0f3ff` | contexto do usuário não é evidência (⇒ `LACUNA` no prompt); bucket `na_scoped` no diagnose | unit test + **contido em 2 runs reais (accept22: 1º sinal; accept23: 2º sinal, `user://` fora do corpus)** |
| `49508fe` | consultado-vs-mencionado + inferência-por-premissas + fato-usuário + janela | foco 137 passed + **exercitado em run real (accept23: inferência contida, fato-usuário contido 2º run, janela sem divergência)**; resíduo: contador cego a `([N])` (registrado, sem corrigir) |
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
  pausa-mid-model como ação. Não re-executar sem nova hipótese explícita.
- **Lição do accept19 (não repetir):** run rodou sobre código desatualizado por race
  com o commit — **conferir `git rev-parse HEAD` antes de cada run**.
- **Próxima ação:** investigar `assessor_error` 17 recorrente
  (proximidade-em-listagem, accept20 e accept23) + contador de citações
  cego a `([N])`, sem flexibilizar critério; depois re-run cobrindo as
  correções pendentes de prova isolada (Phase 5). RA8 segue pendente até
  overall `passed` em run real. (`selection_context` zerou no accept23 —
  sai da lista de resíduos ativos.)

## Referências

- Roteiro: `docs/ACEITE_V1.md`
- Resultado acumulado: `docs/ACEITE_V1_RESULTADO.md` (§16 = accept19/accept20)
- Relatórios: `/home/thomaskyn/hermes-runs/accept19/DIAGNOSIS_accept18.md`,
  `/home/thomaskyn/hermes-runs/accept20/RELATORIO_ACCEPT20.md`
- Contrato reach: `docs/AGENT_REACH.md`
