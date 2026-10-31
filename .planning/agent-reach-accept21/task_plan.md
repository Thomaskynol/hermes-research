# Task Plan: agent-reach-accept21 — destravar os 5 bloqueadores do aceite v1

## Goal

Fechar o aceite v1 com RA8 `passed` em run real, sem flexibilizar critério.
Os 5 itens "Sem validação" do ACEITE_V1.md são **limites declarados
(skips), não critérios de aceite**: item não validado não vira requisito
adicional automaticamente — ver conferência em `findings.md`
(Missão 2, HEAD `15443a5`).

## Next Step

Missão 4 REGISTRADA (HEAD `a656535`, sem push, sem lógica produto): 3
contratos v2 — (1) inferência positiva, (2) consistência entrega,
(3) identidade/atribuição; versão-premissa preservada (regra estreita
Missão 3); instruções conflitantes listadas para remover em `findings.md`.
Próximo: implementar os 3 contratos v2 em lane próprio, TDD RED→GREEN;
próximo run só sob nova hipótese explícita. RA8 segue pendente até
overall `passed` em run real (gargalo: cobertura/corpus, não veracidade).

## Current Phase

Phase 9 (Missão 4: 3 contratos v2 — registro, sem implementação)

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

### Phase 9 (Missão 4): 3 contratos v2 — REGISTRADA (sem implementação)

- [x] Missão registrada (este plano + `findings.md` + `progress.md` Sessão 14
  + `docs/CONTINUIDADE.md` como ponto de entrada); sem lógica produto
- [ ] (v2-1) inferência positiva — definir quando inferência PODE ser
  `supported` (condições positivas estreitas: âncora + relação auditadas
  em separado + citação de interoperabilidade quando a frase nomeia ≥2
  entidades); fora disso, declarada/LACUNA, nunca promoção silenciosa
- [ ] (v2-2) consistência entrega — camadas de entrega convergem
  (relatório §8 × `verification.json` × diagnose/check: mesmo veredito
  de suporte, denominador nunca reduzido, divergência excerto-vs-full
  explícita via `hash_source`, nunca silenciosa)
- [ ] (v2-3) identidade/atribuição — toda afirmação atribuída tem entidade
  resolvida + origem (`fabricante vs independente vs usuário vs
  inferência`, R11.2; `user://` fora do corpus, citável só como premissa
  explícita sem número); sem identidade literal = LACUNA declarada
  (caso local-memory accept24), nunca promoção
- [x] versão-premissa PRESERVADA (regra estreita Missão 3/Sessão 13:
  comparação numérica contra mínimo declarado = sustentada
  (premissa+corpus); compat funcional/integração sem fonte que mencione
  a versão = LACUNA `versão exata ausente`; ponderação estreita idem)
- [x] Instruções conflitantes listadas para remover (ver `findings.md`
  Missão 4: isenção ampla de premissa, promoção de combinação plausível,
  LACUNA sem gates, bare utility ponderando, fora-do-corpus como
  `uncited`/ok, divergência silenciosa, redução de denominador)
- **Status:** registrada (contratos a implementar em lane próprio,
  TDD RED→GREEN; RA8 segue PENDENTE; sem push)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Plano em `.planning/agent-reach-accept21/` (slug exato, sem prefixo de data) | Escopo exigido pelo orquestrador; `init-session` gerou prefixo `2026-10-31-`, renomeado via `mv` e `.active_plan` atualizado |
| RA8 não flexibilizado | `verification` do accept20 falhou por 1 inferência com versão de contexto do usuário; diagnose concordou (sem divergência) |
| Versão-premissa preservada na Missão 4 | Regra estreita Missão 3/Sessão 13 mantida como invariante dos 3 contratos v2; instruções conflitantes (isenção ampla, promoção indevida, LACUNA sem gates) listadas para remover, não para coexistir |
| Sem alteração de código produto neste passo | Escopo restrito a docs + plano |

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `init-session.sh` criou `2026-10-31-agent-reach-accept21` em vez do slug exato | `mv` para `agent-reach-accept21` + `.active_plan` reescrito; re-attest após editar `task_plan.md` |
| Instruções superadas permaneciam como pendentes (run vast-UP, rounds fixo, 5 itens como requisito) | Missão 2: Phases 2–4 marcadas superadas/reclassificadas; Next Step = residual real (selection_context), não re-run cego |
