# Task Plan: gargalos residuais pós-accept31 (seleção/ranking/orçamento)

## Goal
Elevar cobertura útil e sustentada do benchmark plugins-OpenCode sem flexibilizar RA8: reduzir `selection_context` por entrega de trechos pertinentes por célula aberta, preservando gates de identidade, N/A delimitado, inferência declarada e reserva de finalização.

## Next Step
Aguardar fim do run accept33 (RUN_DONE em /home/thomaskyn/hermes-runs/accept33/stdout.log); reconciliar trace notes `proporcional:`, max_rounds adotado e cobertura vs 0/56; depois fechar Fase 5.

## Current Phase
Phase 4 (accept32 concluído + causa-raiz do hook achada e corrigida; run accept33 em curso)

## Phases

### Phase 1: Confronto accept31 × pedido + rastreio pipeline
- [x] Confrontar relatório final accept31 com pergunta e RA8 (lane exp-1)
- [x] Rastrear pedido→plano→descoberta→coleta→seleção→avaliação→síntese (lane exp-2)
- [x] Verificar mecanismos no código (orquestrador)
- **Status:** complete

### Phase 2: Critérios observáveis + escopo do fix
- [x] Definir critérios positivo/negativo antes de implementar
- [x] Escolher mecanismos de maior impacto, sem hardcode de entidade
- **Status:** complete

### Phase 3: Fix TDD (dono: @fixer, único writer em adaptive_coordinator.py + tests/)
- [x] RED: teste reproduz doc-resend cuja janela de sustentação não chega ao assessor (mesmo doc, mesmos limites 1200/12k)
- [x] GREEN: excerto por-URL prioriza a célula aberta que motivou o envio (criterion+entity da célula), dentro dos mesmos limites
- [x] Sem regressão: suite pertinente + diagnose congelado accept30/31 inalterado onde o caminho não é exercitado
- **Status:** complete (commit 9c311ad; revisado cavecrew 0🔴)

### Phase 4: Validação integrada + runs reais accept32/accept33
- [x] Run real accept32 sobre código congelado, diretório exclusivo, HEAD+hashes+infra medidos, 8082 reconciliado (+10588/118 cached)
- [x] Diagnose accept32: 0/56 partial; missing=20, selection_context=18 (era 29), assessor_error=16, partial=2, ok=0
- [x] Causa-raiz do hook proporcional morto: `new_state` inicializa stop{} /report={} nunca-None → guarda M5 sempre verdadeiro pós-início; base calculou sobre v1 com 0 células silenciosa
- [x] Fix TDD do hook (commit 4615ccb): guarda detecta decisão real; trace note sempre que cells!=last; 4 testes com new_state REAL; full 638 OK skipped=10
- [x] Run real accept33 em curso (fundo; reconciliar trace notes, max_rounds, cobertura)
- [x] Reconciliado: ADOTADO 3→7, 8 rounds, 1/56; gargalo residual = largura de lote
- [x] Ler Markdown final como usuário (accept32 parcial + accept33 sumário: honesto, LACUNA declaradas)
- **Status:** complete

### Phase 5: Entrega e continuidade
- [x] Relatórios técnico + final persistentes, commits coesos, CONTINUIDADE atualizada
- [ ] Revisão independente pertinente sem induzir parecer
- **Status:** in_progress (falta só revisão independente + commit final)

### Phase 5: Entrega e continuidade
- [ ] Relatórios técnico + final persistentes, commits coesos, CONTINUIDADE atualizada
- [ ] Revisão independente pertinente sem induzir parecer
- **Status:** pending

## Critérios observáveis (fix Phase 3)
Positivos (devem passar):
- P1: doc em `_sent` que sustenta célula aberta sem refs (identidade + termo da dimensão ≤1500 chars da menção) é reenviado (já ocorre — preservar) E o excerto enviado contém a janela de sustentação (termo da dimensão ou menção da entidade daquela célula).
- P2: com N células abertas e teto JSON 12k inalterado, o lote prioriza diversidade de células (sem repetir par url×célula já exibido junto); limites max_docs/teto/chamadas intactos.
- P3: gates intactos: identidade universal, N/A delimitado, inferência declarada nunca vira integração testada, user:// fora do corpus, reserva de finalização.
Negativos (devem continuar rejeitados):
- N1: doc genérico sem identidade da entidade não sustenta célula (identity mismatch rejeita).
- N2: fora-do-corpus como citação não vira covered.
- N3: URL nua sem identidade não conta.

## Decisões feitas
| Decisão | Rationale |
|---|---|
| Causa nova não é exigida; trabalhar pendências conhecidas seleção/ranking/orçamento | Missão autoriza; regra anti-repetição impede só pesquisa cega sem hipótese |
| M5 (re-adoção proporcional) já implementado pós-accept31, ainda sem run real — validar em accept32, não reimplementar | Evitar duplicar trabalho; HEAD atual inclui M5 |
| Fix foca no excerto por-URL orientado à célula do reenvio, não em aumento de teto | Teto JSON/chamadas são limites autorizados; evidência mostra doc certo enviado mas janela errada exibida |
| Sem nomes de plugins/fontes no produto; só tokens do plano/pergunta + kind-words genéricas | Evitar hardcode de benchmark (contratos A1–A6/G5) |
| Critérios antes da implementação; replay congelado preserva originais | AGENTS §5, sem revalidar runs antigos além do necessário |

## Erros/pendências
| Item | Estado |
|---|---|
| accept30/31: selection_context 29–32 dominante; síntese 16 unsupported por overlap<0.35 excerto-vs-full | Hipótese: janela global esconde passagem da célula (verificar no RED) |
| accept32: selection_context 18 (caiu de 29), mas missing 20 + assessor_error 16, cobertura 0/56 | Plano churnou v1→v15; hook proporcional morto explica stop rounds com folga total |
| Hook M5 nunca adotou no accept32: guarda `stop/report is not None` sempre-True (new_state nunca tem None); testes usavam state manual (mock-behavior gap) | Fix 4615ccb: guarda por decisão real + trace note sempre; accept33 dirá se rounds sobem 3→7 |
| by_cells inicial 2 sobre plano v1 15 células; M5 re-adota na expansão | Aguardando prova em run real |
| gap_query/pool: e2 monopoliza; pool exige overlap>0 | Fora do escopo deste fix; observar após P1/P2 |
