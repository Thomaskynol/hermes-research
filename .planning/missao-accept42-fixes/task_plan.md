# Missão accept42 — correções (2026-11-03)

## Objetivo
Corrigir os 4 grupos de defeitos demonstrados no accept42 sem mascarar resultado: reconciliar evidência→avaliação→síntese, disciplinar descoberta/orçamento, corrigir scope da auditoria, separar relatório principal do anexo técnico. RA8 segue PENDENTE até run real validar.

## Critérios observáveis
1. Evidência válida avaliada (covered, ex.: c3×cand-pwf [11][23], c5×cand-planner [8], c10×cand-jira [25][28]) chega à síntese ou a divergência findings×síntese é sinalizada com alcance explícito; rótulo F3 nunca afirma "fora da seleção" para URL em writer_included_urls.
2. URLs asset/identicon/placeholder e caminhos GitHub não-leitíveis não entram no pool nem gastam extração; pool cheio evicta só (overlap 0 ∧ nunca fetched ∧ sem identidade); reserva exige menção de identidade da entidade do gap; 5 required não travam sem fonte própria.
3. Frase com negação/limite de interoperabilidade nunca recebe scope "integração testada"; documentado ≠ teste executado; denominadores (72 votos vs 0 falhas, 25 revisadas vs 1 com quórum, accepted false) documentados e contadores de julgamento separados de tentativa.
4. Principal contém resposta direta + matriz 5×critérios + combinações reconciliadas + recomendação; zero jargão interno no principal; anexo técnico separado preserva observabilidade; veto idempotente.
5. Sem hardcode de nomes/vencedores; tetos globais intactos (extractions 120, queries 30, rounds config, model 16); 2.1.4 é premissa de entrada; 8082 preservado; sem prod.

## Hipóteses (das 4 lanes, a confirmar em RED)
- H1 (lane1): dupla fonte sem reconciliação — writer vê janela 12k/2k, assessor vê full, renderer imprime ambos verbatim. Fix: pós-checagem findings×síntese + F3 checa included real.
- H2 (lane2): minerador promete o que o leitor recusa (same-repo links vs raw_readme_url); admissão FIFO sem evicção; reserva sem gate de identidade; promoção first-come-first-served. Fix: filtros na admissão + evicção + gate identidade + substitution funcional.
- H3 (lane3): classificadores de scope sem gate de polaridade; `OpenCode` como e1 cria 2ª entidade fantasma. Fix: gate negação/modalidade + verbo de teste exigido + enumeração fora do canal inference.
- H4 (lane4): síntese verbatim + veto não-idempotente + sem template comparativo. Fix: template obrigatório + renderer em dois arquivos + veto idempotente + reconciliação.

## Fases
1. Fix paralelo por arquivo (3 lanes: coordinator / verification / renderer), TDD RED→GREEN, testes separados por lane, suite verde.
2. Revisão independente (cavecrew-reviewer) dos diffs.
3. Remediação + re-verificação afetada.
4. Reproduções/replays congelados demonstrando cada correção (sem novo run ainda).
5. Run real final sobre código congelado (pergunta do aceite, effort medium, limites explícitos) + leitura do relatório como usuário.
6. Relatório técnico da missão + CONTINUIDADE + push de marcos.

## Evidência
- Base: `/home/thomaskyn/hermes-runs/accept42/` (preservar; reproduções em /tmp e diretórios próprios).
- Lanes: ses_e5e0a6ce4ffeXuTgQS1qAsft0d (síntese), ses_e5e0a6cd4ffed060P5aJAn655S (descoberta), ses_e5e0a6cd3ffeoCmOdSvwbxJehp (auditoria), ses_e5e0a6ccdffeMx8BprtYiLmWDm (relatório).
- Plano anterior: `.planning/fase-g-selecao/task_plan.md`.
