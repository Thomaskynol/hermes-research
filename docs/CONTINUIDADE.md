# CONTINUIDADE — aceite v1, branch `feat/product-v1`

> Ponto de entrada para retomar o trabalho. Plano ativo:
> `.planning/agent-reach-accept21/` (`task_plan.md`, `findings.md`, `progress.md`).
> Última atualização: 2026-10-31 (pós-accept22, HEAD `776af89`).
> Commits produto e docs separados (sem push).

## Objetivo e escopo

Fechar o aceite v1 destravando os **5 bloqueadores "Sem validação"**
(`docs/ACEITE_V1.md`, seção Limites):

1. Gateway vast local fora do ar (`127.0.0.1:8001`).
2. Perfil deep 10h.
3. `conduct_research` ponta a ponta da biblioteca.
4. Pausa no meio de chamada ao modelo (limite conhecido: pausa só vale entre rounds).
5. Multiusuário.

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
  on-demand e desligou; accept22 rodou com DOWN pré/pós confirmado).
  SearxNG DOWN (sem imagem docker), embeddings DOWN — igual ao accept20.

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
| `cc0f3ff` | contexto do usuário não é evidência (⇒ `LACUNA` no prompt); bucket `na_scoped` no diagnose | unit test + **sinal fraco em run real (accept22: classe accept20 ausente, sentença compat contida)** |
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
- **Lição do accept19 (não repetir):** run rodou sobre código antigo por race
  com o commit — **conferir `git rev-parse HEAD` antes de cada run**.
- **Próxima ação:** investigar `selection_context` 16 e o caminho de
  índices `[N]` fora da base de síntese (leniência residual do accept21),
  sem flexibilizar critério; depois re-run cobrindo os 5 bloqueadores
  (Phase 4). RA8 segue pendente até overall `passed` em run real.

## Referências

- Roteiro: `docs/ACEITE_V1.md`
- Resultado acumulado: `docs/ACEITE_V1_RESULTADO.md` (§16 = accept19/accept20)
- Relatórios: `/home/thomaskyn/hermes-runs/accept19/DIAGNOSIS_accept18.md`,
  `/home/thomaskyn/hermes-runs/accept20/RELATORIO_ACCEPT20.md`
- Contrato reach: `docs/AGENT_REACH.md`
