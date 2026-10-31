# Task Plan: agent-reach-accept21 — destravar os 5 bloqueadores do aceite v1

## Goal

Validar em run real (accept21) os 5 itens "Sem validação" do ACEITE_V1.md
mais as 2 correções pós-accept20 (cc0f3ff, b81e8f6), sem flexibilizar o RA8.

## Next Step

Subir serviços on-demand (vast :8001, searxng :8888) e rodar accept21 com
as correções cc0f3ff + b81e8f6 já no código.

## Current Phase

Phase 1

## Phases

### Phase 1: Continuidade registrada (docs + plano)

- [x] Plano `.planning/agent-reach-accept21/` criado (modo autonomous)
- [x] `docs/CONTINUIDADE.md` escrito como ponto de entrada
- [x] Estado de branch/ambiente registrado a partir de evidência (git + ss/docker)
- **Status:** complete

### Phase 2: Subir dependências on-demand

- [ ] Subir vast_local_retriever (:8001) e SearXNG (:8888); conferir `/healthz`
- [ ] Registrar SEARXNG_URL efetiva (IP de bridge pode mudar)
- **Status:** pending

### Phase 3: Run accept21 (correções cc0f3ff + b81e8f6 sob teste)

- [ ] Rodar pergunta de aceite com código HEAD (inclui cc0f3ff + b81e8f6)
- [ ] Checar: RA8 sem flexibilizar; contexto-usuário ⇒ LACUNA; M8 pool declarado
- **Status:** pending

### Phase 4: Cobrir os 5 bloqueadores "Sem validação"

- [ ] (1) gateway vast local no ar durante run real
- [ ] (2) perfil deep 10h
- [ ] (3) `conduct_research` ponta a ponta da biblioteca
- [ ] (4) pausa no meio de chamada ao modelo (limite conhecido: só entre rounds)
- [ ] (5) multiusuário
- **Status:** pending

### Phase 5: Fechar aceite

- [ ] Atualizar `docs/ACEITE_V1_RESULTADO.md` com rodada accept21
- [ ] `check-complete.sh` verde
- **Status:** pending

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
