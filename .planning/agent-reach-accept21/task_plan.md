# Task Plan: agent-reach-accept21 — destravar os 5 bloqueadores do aceite v1

## Goal

Fechar o aceite v1 com RA8 `passed` em run real, sem flexibilizar critério.
Os 5 itens "Sem validação" do ACEITE_V1.md são **limites declarados
(skips), não critérios de aceite**: item não validado não vira requisito
adicional automaticamente — ver conferência em `findings.md`
(Missão 2, HEAD `15443a5`).

## Next Step

Missão 3 — 3 contratos, sem flexibilizar; depois re-run cobrindo prova
isolada. RA8 segue pendente até overall `passed` em run real
(accept23: 0/55 failed honesto sob `49508fe`; `selection_context` zerou —
sai da lista de resíduos ativos).

Contratos: (1) `[N]` resolve — contador/extrator enxerga citação in-text
`([N])`, não só URL nua (resíduo accept23: evidence/resolved 0 vs sentença
48/50); (2) versão-premissa — versão vinda de premissa explícita
(usuário/contexto) não reprova como inferência; gate tag-exata vs família
funcional com conclusões separadas; (3) inferência-complementaridade —
frase que nomeia ≥2 entidades exige citação de interoperabilidade
(doc com ≥2 entidades), senão LACUNA explícita (complementaridade plausível
vs integração testada).

## Current Phase

Phase 7 (Missão 3: 3 contratos)

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
  (0 ocorrências); sai da lista de resíduos ativos, sem ação associada
- [ ] Re-run da pergunta de aceite cobrindo correções pendentes de prova real
- [ ] Atualizar `docs/ACEITE_V1_RESULTADO.md` com nova rodada
- [ ] `check-complete.sh` verde
- **Status:** pending (só re-run + docs; sem re-investigar `selection_context`)

### Phase 6 (Missão 2): Coerência do plano — COMPLETE

- [x] 4 inconsistências registradas em `findings.md` (instruções superadas
  removidas: run-vast-UP, rounds-fixo, 5-itens-como-requisito, pausa-mid-model)
- [x] Estado HEAD `15443a5` + config efetiva registrados
- [x] Obrigatoriedade dos 5 itens conferida (modelagem v1.1 + matriz)
- [x] `docs/CONTINUIDADE.md` atualizado como ponto de entrada
- **Status:** complete (commitado em `bf5507b` + `cc1bf1c`; nada pendente)

### Phase 7 (Missão 3): 3 contratos — IN PROGRESS

- [x] Missão registrada (este plano + `findings.md` + `progress.md` Sessão 10
  + `docs/CONTINUIDADE.md` como ponto de entrada); sem lógica produto
- [ ] (1) `[N]` resolve — extrator/contador resolve citação in-text `([N])`
  → tabela-fonte (accept23: evidence/resolved 0 vs sentença 48/50)
- [ ] (2) versão-premissa — versão de premissa explícita não reprova como
  inferência; gate tag-exata vs família funcional, conclusões separadas
- [ ] (3) inferência-complementaridade — ≥2 entidades na frase exige doc de
  interoperabilidade (≥2 entidades), senão LACUNA explícita
- **Status:** in-progress (contratos registrados; implementação fora de escopo
  desta sessão)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Plano em `.planning/agent-reach-accept21/` (slug exato, sem prefixo de data) | Escopo exigido pelo orquestrador; `init-session` gerou prefixo `2026-10-31-`, renomeado via `mv` e `.active_plan` atualizado |
| RA8 não flexibilizado | `verification` do accept20 falhou por 1 inferência com versão de contexto do usuário; diagnose concordou (sem divergência) |
| Sem alteração de código produto neste passo | Escopo restrito a docs + plano |

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `init-session.sh` criou `2026-10-31-agent-reach-accept21` em vez do slug exato | `mv` para `agent-reach-accept21` + `.active_plan` reescrito; re-attest após editar `task_plan.md` |
| Instruções superadas permaneciam como pendentes (run vast-UP, rounds fixo, 5 itens como requisito) | Missão 2: Phases 2–4 marcadas superadas/reclassificadas; Next Step = residual real (selection_context), não re-run cego |
