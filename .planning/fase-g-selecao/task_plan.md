# Fase G — evidência selecionada chega à avaliação

## Objetivo
Corrigir causas gerais que impedem fontes pertinentes de chegarem ao assessor e à síntese, sem regras por nome de produto, e demonstrar pesquisa útil sobre cinco plugins OpenCode.

## Critérios observáveis
1. Rótulo PT de dimensão (planejamento, implementação, testes, revisão, compatibilidade, dependências, custos, manutenção, funcionalidades) alcança a seção EN correspondente; menção genérica não vira suporte.
2. O par (url, célula) só é marcado como exibido quando o excerto enviado contém entidade + termo da dimensão; reenvio focado dispara quando a seção ficou fora.
3. Teste de regressão detecta o defeito original (RED antes do fix) e o fix passa.
4. Run real congelado em HEAD pós-fix, dir exclusivo, sem editar produto durante execução; report/matriz/verificação descrevem a mesma entrega.
5. Sem push/PR/deploy/prod; 8082 preservado; 2.1.4 é premissa de entrada, não versão observada.

## Hipóteses (accept41)
- H1: `_shown[url]` marcava todas as células pedidas, matando o reenvio focado para fontes já enviadas. Evidência: `_shown.update(_req_now)` + `_resend_for_open_cells` retorna [] com shown cheio; 18 selection_context.
- H2: ponte PT→EN não cobria dimensões do produto; `_cell_locality_hit` para c6/e4 falhava com termos ['revisao','codigo'] e passava ao adicionar 'review'. Evidência: simulação no state accept41.
- H3: limite de rounds default=6 pode ser vinculante com folga; reavaliar após o fix, sem aumentar tetos globais silenciosamente.

## Fases
1. TDD e fix inicial (concluído; commit 64e0a3c; suite 738 OK).
2. Revisão independente (cavecrew-reviewer) e correções (concluído; 3 tentativas; commit 38141b1; suite 746 OK).
3. Run real accept42 em HEAD congelado 38141b1 (encerrado EXIT=0, 1782s, max-rounds 12 explícito; 8082 up; SearXNG/gateway DOWN; fallback com timeout).
4. Reconciliação report/matriz/verificação; CONTINUIDADE; commit local (concluído: ACEITE §17, MATRIX RA8+tabela, 12/55 partial, support ok).

## Evidência
- `/home/thomaskyn/hermes-runs/accept41/` (baseline)
- `/home/thomaskyn/hermes-runs/accept42/` (novo run em 38141b1)
- `tests/test_fase_g_selection_evidence.py` (13 testes)
- Revisão: ses_e6012bbadffe8jYBEVPkSN5qWB (3 tentativas)
- Resíduos aceitos: janela de foco 600 chars; teste multi-entidade do sort de reenvio; sem re-review após acentos/plurais.

