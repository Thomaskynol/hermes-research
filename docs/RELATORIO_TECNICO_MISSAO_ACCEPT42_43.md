# Relatório técnico — missão accept42→accept43 (2026-11-04)

## Pedido
Corrigir os defeitos demonstrados no accept42 (12/55 partial, support ok) e entregar
resposta coerente e útil. Sem hardcode de nomes/vencedores, sem inflar tetos.

## Base e congelamento
- Produto accept43: HEAD `d3b081a` (3 commits: `a5a37f9` descoberta, `0a4719b`
  auditoria, `ac7aa6c` relatório + `d3b081a` plano). Residuais pós-run registrados
  em `a4b2237` (scope-doc-frasal, anexo separado, matriz/recomendação) e
  documentação em `e40e464`, já publicados. Não há esses commits a fazer.
- Run accept43: `/home/thomaskyn/hermes-runs/accept43/`, EXIT=0, código == `d3b081a`
  (hashes conferem pré/pós), pergunta do aceite, medium, `--max-rounds 12`
  (origem: harness), `2.1.4` = premissa de entrada. 8082 UP; vast 8001 DOWN;
  SearXNG DOWN (mesmo perfil do accept42). Stop: `time` (1873s≥1800s), 9/12 rounds.
- Accept42 preservado intacto; reproduções em `/tmp/replay-accept43/` (11/11 suites
  do runner offline OK) e `/tmp/replay-accept43b/`.

## Causas-raiz (lanes read-only, sem presumir ledger/síntese/diagnose)
1. **Dupla fonte sem reconciliação** (ses_e5e0a6ce…): assessor avalia full-text;
   writer recebe janela 12k/2k-por-doc; renderer imprime findings + síntese
   verbatim lado a lado. Casos: [25][28] (manutenção jira) e [23] (hooks pwf)
   cobertos mas fora dos 6 included → síntese declarou LACUNA; [8] (planner)
   truncado → LACUNA de revisão; [11] em included mas rotulado "fora da seleção"
   (modelo colou o número no template de [23]).
2. **Minerador promete, leitor recusa** (ses_e5e0a6cd…): same-repo links
   (issues/stargazers/releases/tree) agendados mas `raw_readme_url` recusa →
   `not_a_github_repo` gastando extração; admissão FIFO sem filtro (identicons,
   assets, SEU_USUARIO, .png) ocupava o pool 64 e rejeitava repos reais;
   reserva sem gate de identidade; promoção first-come-first-served travava 5
   required no 1º minuto; re-leitura dos mesmos 9 URLs nos rounds 8–12.
3. **Scope sem polaridade** (ses_e5e0a6cd…): dois emissores de 'integração
   testada' mediam overlap/co-mencção sem negação/modalidade; `OpenCode` como
   e1 criava 2ª entidade fantasma. Denominadores: 25 reviewed inclui 24 sem
   quórum; 72 votos-falha → 0 falhas finais + 24 `review_incomplete`;
   `accepted:false` correto (tentativa ≠ julgamento).
4. **Relatório mistura entrega com log** (ses_e5c…): síntese verbatim + veto
   não-idempotente (duplicação L21) + sem matriz comparativa nem recomendação;
   §§2/3/5/8/9 vêm do estado real.

## Correções (TDD RED→GREEN, sem nomes, tetos intactos)
- Coordinator: filtros de admissão (`_NON_REPO_OWNERS`, placeholders, extensões,
  `raw_readme_url is not None`), dedupe por identidade, evicção
  (overlap-0∧nunca-fetched∧sem-identidade), reserva com gate de identidade,
  substituição por dominância de fontes próprias (≥3, nunca p/ menos evidência),
  exclusão de variantes re-lidas, cap unificado nos dois laços de mineração,
  gravação de `technical_annex.md` (`_write_technical_annex`, falha nunca
  derruba a entrega). Testes: 23 em `test_accept42_discovery.py`.
- Verification: gate de polaridade (negação/limite/modalidade → teto partial/
  LACUNA), verbo de integração com família exata (integralmente/integridade
  excluídos), evidência de execução só frasal ('teste executado' etc. — tokens
  isolados 'funciona'/'tested' em boilerplate de 50KB causavam o residual
  L429/438 do accept43), enumeração do plano fora do canal inference,
  `claims_judged_quorum` separado de tentativa. Testes: 11 em
  `test_accept42_audit_scope.py`.
- Renderer: veto idempotente + veto F3 só se src∉included reais, reconciliação
  findings×síntese em PT claro (sem findings/full-text/janela no principal),
  matriz determinística de `_cell_state()` (== §3 por construção), fallback de
  recomendação ranqueando exigidos por (covered, partial, refs). Testes: 15 em
  `test_accept42_report_shape.py`.
- Revisão independente: APROVAR COM RISCOS + 4🟡, todos remediados com teste.
- Suíte: verde após cada incremento; final 795 OK skipped=10 EXIT=0.

## Replays (mecanismo, sem inferir causalidade de percentuais)
- `/tmp/replay-accept43/`: 7 inferências do accept42 → 0 'integração testada';
  F3 cand-pwf×[11] `incluida_writer=True` sem falso veto; 17 notas de
  reconciliação; junk recusado/dedup; reserva/substituição via testes.
- `/tmp/replay-accept43b/`: residuais do accept43 (2 frases → documentado;
  9 negações limpas; anexo 52KB separado do principal; 96 células zero
  divergência matriz×§3).

## Run accept43 — leitura como usuário
- `overall partial` honesto: execution ok, question partial 0.122 (6/49, 7 N/A
  fora do denominador), review partial (6/6 com quórum; **extração incompleta**),
  support ok. Votos originais: 2 sustained, 3 gap e 1 partial, nenhum
  unsupported, 18 votos válidos e zero falhas técnicas. `accepted:false` e
  `verdict_state: revisão incompleta` não significam reprovação factual.
  O texto anterior “reprovado explícito” estava incorreto. Parada por tempo
  registrada com pendências. Ver a reconciliação atual em
  `RELATORIO_TECNICO_RECONCILIACAO_ACCEPT43.md`.
- Utilidade: Plannotator útil; marketplace parcial-restrita; GHA parcial-fraca;
  jira parcial-mínima; Octto nula neste run. Nenhuma célula 'coberto' no §3 com
  LACUNA na síntese; rótulo F3 falso zerado; negações de integração honestas.
- Limitações: recomendação do modelo era genérica (fallback agora garante);
  matriz do modelo divergia (agora determinística); anexo ainda embutido no
  report deste run (fiação pronta p/ o próximo); funil 42→6, junk recorrente e
  11 transport failures (gateway/SearXNG DOWN); stop por tempo esgotou
  investigação. RA8 segue PENDENTE.
