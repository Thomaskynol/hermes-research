# Task Plan: agent-reach-accept21 — destravar os 5 bloqueadores do aceite v1

## Goal

Fechar o aceite v1 com RA8 `passed` em run real, sem flexibilizar critério.
Os 5 itens "Sem validação" do ACEITE_V1.md são **limites declarados
(skips), não critérios de aceite**: item não validado não vira requisito
adicional automaticamente — ver conferência em `findings.md`
(Missão 2, HEAD `15443a5`).

## Next Step

accept27 EXECUTADO sob `5080a84` (boost semântico funcional no path native:
4 calls 8082 ok, 36 vetores, 14475 tokens, cache 51; seleção/writer
influenciados com gates intactos; coverage 0.333 partial, overall partial;
RA8 segue pendente — gargalo cobertura/teto, não veracidade). Fechar Phase 5
(ACEITE_V1_RESULTADO + check-complete). Próximo run só sob nova hipótese
explícita.

## Current Phase

Phase 11 (accept27: boost semântico funcional no path native — PROVA OBTIDA)

## Phases

### Phase 1: Continuidade registrada (docs + plano)

- [x] Plano `.planning/agent-reach-accept21/` criado (modo autonomous)
- [x] `docs/CONTINUIDADE.md` escrito como ponto de entrada
- [x] Estado de branch/ambiente registrado a partir de evidência (git + ss/docker)
- **Status:** complete

### Phase 2: Subir dependências on-demand — SUPERADA (runs accept21/22 já executados)

- [x] accept21 rodou com vast UP on-demand (colapsou 0/15); desligado pós-run
- [x] accept22 rodou com vast DOWN + SearXNG DOWN confirmados pré/pós-run
- **Status:** superseded — não repetir "subir vast + rodar accept21";
  baseline atual é DOWN confirmado; subir serviço só sob nova hipótese explícita

### Phase 3: Runs accept21/accept22 — SUPERADA (evidência registrada)

- [x] accept21 (HEAD `b1cf76c`): 0/15 + 0 N/A, verification `partial`, 343s
- [x] accept22 (HEAD `776af89`, produto `a704463`): 11/54 + 0 N/A,
  verification `failed` honesto, 658s
- [x] RA8 segue PENDENTE em ambos, sem flexibilizar
- **Status:** superseded — `max-rounds 3` era config desses runs, não
  requisito fixo (rodadas são controle independente, R6.4 / modelagem §6)

### Phase 4: Os 5 itens "Sem validação" — RECLASSIFICADOS (Missão 2)

- Itens do ACEITE_V1.md § Limites são skips/limites, não critérios de aceite
- Conferência de obrigatoriedade contra modelagem v1.1 + matriz em
  `findings.md` (Missão 2): separa REAL vs PENDENTE legítimo vs fora de escopo
- **Status:** in-progress (só o item 1 é pendência legítima; demais são
  limite documentado ou fora de escopo — não bloqueiam o aceite)

### Phase 5: Fechar aceite

- [x] `selection_context` 16 (residual accept22) — zerou no accept23
  (0 ocorrências); reapareceu como 7 no accept24 (miss do assessor sobre
  corpus distinto, não leniência do produto — acompanhar por corpus,
  sem ação de produto associada)
- [x] Re-run da pergunta de aceite cobrindo correções pendentes de prova real
  (accept24 sob `a70d837`: 9/56 partial, support ok, 3 contratos provados)
- [x] Re-run sob `4b40bbe` cobrindo os 3 contratos v2 + identidade estrita
  (accept25: 0/35 partial, support ok 2ª vez, v2-1/v2-2/v2-3 confirmados)
- [x] Matriz sync Missão 3 + accept24 (estava parada no accept22);
  RA8 alfinetado PENDENTE (cobertura parcial, retrieval-bound)
- [ ] Atualizar `docs/ACEITE_V1_RESULTADO.md` com nova rodada
- [ ] `check-complete.sh` verde
- **Status:** in-progress (falta ACEITE_V1_RESULTADO + check-complete;
  sem re-run sem nova hipótese)

### Phase 6 (Missão 2): Coerência do plano — COMPLETE

- [x] 4 inconsistências registradas em `findings.md` (instruções superadas
  removidas: run-vast-UP, rounds-fixo, 5-itens-como-requisito, pausa-mid-model)
- [x] Estado HEAD `15443a5` + config efetiva registrados
- [x] Obrigatoriedade dos 5 itens conferida (modelagem v1.1 + matriz)
- [x] `docs/CONTINUIDADE.md` atualizado como ponto de entrada
- **Status:** complete (commitado em `bf5507b` + `cc1bf1c`; nada pendente)

### Phase 7 (Missão 3): 3 contratos — PROVA REAL OBTIDA (accept24)

- [x] Missão registrada (este plano + `findings.md` + `progress.md` Sessão 10
  + `docs/CONTINUIDADE.md` como ponto de entrada); sem lógica produto
- [x] (1) `[N]` resolve — **PROVADO accept24**: citations 68, evidence 51
  (era 0), resolved 5 (era 0), unknown []; support failed→ok
- [x] (2) versão-premissa — **PROVADO accept24**: 2.1.4≥2.1.2 sustentada
  ([5]); funcional sem fonte = LACUNA `versão exata ausente` (3×);
  fato-usuário contido (3º run, `user://` fora do corpus)
- [x] (3) inferência-complementaridade — **PROVADO accept24**: 5 frases
  LACUNA + "INFERÊNCIA NÃO SUSTENTADA, NÃO AFIRMAR"; sem promoção indevida
- [x] Re-run da pergunta de aceite cobrindo prova isolada dos 3 contratos
  (accept24, HEAD `a70d837`, 715s, EXIT=0, hashes 8/8 OK pré/pós)
- **Status:** complete (prova real; RA8 segue pendente — overall `partial`
  por cobertura 9/56, não por veracidade; ver Phase 5)

### Phase 8 (pós-accept24): 3 divergências unificadas — IMPLEMENTADO (TDD)

- [x] (1) diagnose extrai URLs evidência sem `[N]` (mesmo
  `extract_references`/`Classify` do verify; bare utility nunca pondera;
  fora do corpus = failed, nunca uncited)
- [x] (2) ramo LACUNA do diagnose espelha gates do `check_support`
  (versão exata/família + literal citado; sem eles, LACUNA com versão
  ausente falha)
- [x] (3) ponderação aplica regra estreita (numérico sustenta, funcional
  reprova; sem isenção ampla de `_is_user_premise`)
- [x] TDD `tests/test_divergencias_auditores.py` (11 testes, RED 3→GREEN;
  positivo+negativo pela mesma entrada nos 3 auditores)
- [x] Efeito isolado em cópia congelada accept24 (original intacto, md5
  igual): diagnose 49/2/66 → 39/12/66; verify `ok` → `partial` com 8
  misses — convergindo com check, sem novo run real
- **Status:** complete (código + testes; RA8 segue PENDENTE; sem push)

> Nota histórica (implementação, Sessão 11): `verify_support` resolve
> in-text `([N])` via `state[report][numbers]` (fallback tabela §7);
> prompts estreitados versão-premissa; trava interop unificada
> (marcado + genérico + diagnose). Prova isolada em cópia congelada do
> accept23 precedeu o run real.

### Phase 9 (Missão 4): 3 contratos v2 — IMPLEMENTADA (TDD)

- [x] Missão implementada (este plano + `findings.md` + `progress.md` Sessão 15
  + `docs/CONTINUIDADE.md`; `tests/test_missao4_contratos.py` 17 testes,
  RED 10→GREEN; sem run real)
- [x] (v2-1) inferência positiva — POS doc-interop (menciona ambas) →
  supported + declared (premissas+limites); NEG docs separados →
  declared/LACUNA explícita (não unsupported genérico); extrapolação
  (integração testada/ausência conflitos sem fonte) → rejeitado; espelhado
  nos 3 auditores com canal declared; `logo` não é marcador; versão
  numérica vs funcional preservada
- [x] (v2-2) consistência entrega — two-pass (render §8 após verify final)
  + dedupe de notas; sem "sem citações verificáveis" com refs válidas;
  numbers estável, cited coerente
- [x] (v2-3) identidade/atribuição — eid derivado e-* ignorado, forma cheia
  com fronteira; refs de evaluation exigem identidade
  (`_identity_matches`+`_singleton_rare`); `_rank_unfetched` desempata por
  identidade, não substring; atribuição genérica sem hardcode (caso
  Doozie/everything-opencode vs timrichardson/opencode-planner corrigido
  pelo mecanismo)
- [x] versão-premissa PRESERVADA (regra estreita Missão 3/Sessão 13:
  comparação numérica contra mínimo declarado = sustentada
  (premissa+corpus); compat funcional/integração sem fonte que mencione
  a versão = LACUNA `versão exata ausente`; ponderação estreita idem)
- [x] Instruções conflitantes listadas para remover (ver `findings.md`
  Missão 4: isenção ampla de premissa, promoção de combinação plausível,
  LACUNA sem gates, bare utility ponderando, fora-do-corpus como
  `uncited`/ok, divergência silenciosa, redução de denominador)
- **Status:** complete (código + testes; cópias accept23/24 sem novo run;
  RA8 segue PENDENTE; sem push)

### Phase 10 (accept25): run real dos 3 contratos v2 — PROVA OBTIDA

- [x] Hipótese explícita: primeira prova real sob `4b40bbe` (Missão 4 v2 +
  identidade estrita Sessão 16); congelamento pré/pós (HEAD/diffstat/
  hashes 8/8 OK, sem edição no run); provisionamento investigado
  (vast provisionável mas NÃO subido — colapso accept21; SearXNG/embeddings
  impossíveis, condições registradas)
- [x] (v2-1) — **PROVADO accept25**: 4 combinações §8 em `declared`
  (premissas+âncoras), extrapolação recusada; versão-preservada (5× LACUNA)
- [x] (v2-2) — **PROVADO accept25**: §8-Anexo = verify final, numbers
  estável, sem `not_run`, sem nota duplicada
- [x] (v2-3) — **PROVADO accept25**: bandonker 3× LACUNA identidade, sem
  promoção; selection_context 22 sem leniência; `[N]` resolve intacto
  (103/74/5/[])
- [x] support `ok` 2ª vez consecutiva; overall `partial` (0/35) por
  cobertura/seleção, não veracidade; `assessor_error 0` (era 11)
- **Status:** complete (evidência em `/home/thomaskyn/hermes-runs/accept25/`;
  RA8 segue PENDENTE; sem push)

### Phase 11 (accept27): boost semântico funcional no path native — PROVA OBTIDA

- [x] Hipótese explícita: primeira integração funcional dos embeddings no
  caminho realmente usado (sonda record-only accept26 → rerank com efeito);
  congelamento pré-run (HEAD `5080a84`, `HEAD.frozen`/`diffstat`/`hashes`
  em `/home/thomaskyn/hermes-runs/accept27/`; `hashes.frozen == árvore`
  pós-run; 1 literal editado na janela de lançamento, vigente desde o
  round 0 — efeito "dimensões" no state)
- [x] TDD RED→GREEN: 18 testes (`test_native_embeddings*.py`, fixtures
  genéricas, mock + guarda anti-socket; RED inicial 12 erros + 3 falhas
  com causa-raiz); suíte FULL fresca 563 OK (skipped=10), exit 0
- [x] Demo corpus congelado `/tmp/demo_emb27` (md5 intacto, mesmas entradas
  e limites): antiga perde D3 (`applied=[]`), nova recupera (`covered`);
  D2 de entidade errada rejeitado (`identity mismatch`); excertos com refs
  no writer
- [x] Run real (8082 UP, vast DOWN controle, medium max-rounds 3, native+
  opencode `muse-spark-1.3-contributor`, `HERMES_NATIVE_EMBEDDINGS=1`):
  EXIT=0, stop `rounds`, 501s, coverage partial 0.333 (8 covered + 11
  partial + 7 insufficient), model_calls 7, contadores 37/34/34/30/6/6,
  verification overall `partial`
- [x] 8082 com efeito: 4 calls (1/round,
  `http://172.17.0.1:8082/v1` + `harrier-oss-v1-0.6b`), 36 vetores, 14475
  tokens, cache_hits 51 (0→7→15→29); métricas servidor 3125→17460 (+14335)
  + cached 125→265 (+140) = 14475 reconciliado; manifest separa embeddings
  do gerador; writer com corte `ordem semântica no restante`
- [x] Gates intactos: 15 `identity mismatch` (rejeitadas), 0
  `outside selection`, 0 `indisponível`, nenhum raise/fallback; sem
  atribuição causal vs accept26 (perfis/corpora distintos)
- **Status:** complete (evidência em `/home/thomaskyn/hermes-runs/accept27/`
  + `RELATORIO_ACCEPT27.md`; RA8 segue PENDENTE; sem push)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Plano em `.planning/agent-reach-accept21/` (slug exato, sem prefixo de data) | Escopo exigido pelo orquestrador; `init-session` gerou prefixo `2026-10-31-`, renomeado via `mv` e `.active_plan` atualizado |
| RA8 não flexibilizado | `verification` do accept20 falhou por 1 inferência com versão de contexto do usuário; diagnose concordou (sem divergência) |
| Versão-premissa preservada na Missão 4 | Regra estreita Missão 3/Sessão 13 mantida como invariante dos 3 contratos v2; instruções conflitantes (isenção ampla, promoção indevida, LACUNA sem gates) listadas para remover, não para coexistir |
| Missão 4 implementada em lane próprio (TDD) | RED 10→GREEN, 17 passed; cópias frozen sem run real; sem push |

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `init-session.sh` criou `2026-10-31-agent-reach-accept21` em vez do slug exato | `mv` para `agent-reach-accept21` + `.active_plan` reescrito; re-attest após editar `task_plan.md` |
| Instruções superadas permaneciam como pendentes (run vast-UP, rounds fixo, 5 itens como requisito) | Missão 2: Phases 2–4 marcadas superadas/reclassificadas; Next Step = residual real (selection_context), não re-run cego |
