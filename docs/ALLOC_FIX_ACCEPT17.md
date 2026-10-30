# Correção do defeito de alocação (c4–c10 famintos) + run real accept17

Data: 2026-10-30. Branch `feat/product-v1`. Commits locais: `2dc0797`
(fix + 9 testes de regressão). Sem push; produção intocada.

## 1. Causa raiz (genus8 + accept16)

Três mecanismos combinados travavam os mesmos top-3 gaps com delta 0.0:

1. `prioritize_gaps` ordenava por `impact × expected_gain`, mas o ledger
   (`coverage_ledger.py:compute`) nunca preenche esses campos — todo gap
   pontuava 1×1 = ordem do plano, imóvel entre rounds, cega a tentativas.
   (`adaptive_coordinator.py:732`, antes do fix).
2. `select_ops` expandia por entidade e fazia interleave **intra**-round,
   mas truncava em `cap` (`max_ops_per_round` = 3 no medium) sempre na
   mesma posição — c4–c10 nunca alcançados, round após round. Round-robin
   `c83b892` deu spread intra-round mas total idêntico (genus8: 4/26).
3. `entity_id` do sub-gap se perdia no op e nos `attempts` (só
   `criterion_id`), então a fome por célula era invisível; todas as
   queries seguiam lideradas pela 1ª entidade do `applies_to`
   (genus8: tudo "Django…"; accept16: tudo "opencode-planner…").

Evidência real: genus8 r1–r3 miraram `[c1,c2,c3]` com delta 0.0;
accept16 r1–r2 miraram `[c1,c2,c3]` (r2 todo `nogain`), r3 `[c2,c3,c4]` —
c5–c11 per_candidate nunca receberam op direcionado.

## 2. Correção (`2dc0797`, só `adaptive_coordinator.py` + teste novo)

- `prioritize_gaps(gaps, state=None)`: tentativas consecutivas sem ganho
  útil (`new_useful`/`confirmed`) dividem o escore; ganho útil reseta o
  decaimento; empate → menos tentativas → ordem original. Sem `state`,
  ordem legada bit-idêntica.
- `select_ops`: sub-gaps ordenados pela célula menos tentada; tentativas
  filtradas por célula (legado sem `entity_id` conta p/ todas);
  `entity_id`/`entity_label` propagados ao op e a todos os registros de
  `attempts`; `_resume_loop` passa `state`.
- `_summarize_ops` inclui `entity_id` (aditivo; diagnose futura por célula).

Semântica preservada: prioridade (`impact×gain`) continua primária;
orçamento (`cap`, `max_rounds`, `model calls`) intacto — a correção só
muda **quais** gaps ocupam os slots, nunca quantos.

## 3. Caso controlado antes/depois (mesmas entradas, genus8 real)

Script `/tmp/alloc_before_after.py`: 10 critérios (c1–c8 × 3 entidades,
c9–c10 globais), cap 3, 3 rounds, tudo `failed` (padrão genus8, delta 0.0).

ANTES (`a37ef49`): r1–r3 = `[c1,c2,c3]`, tudo Django-led, `entity_id=None`;
`c4–c10` nunca mirados.
DEPOIS (`2dc0797`): r1 `[c1,c2,c3]` → r2 `[c4,c5,c6]` → r3 `[c7,c8,c9]`,
com `entity_id` propagado; só `c10` aguarda o 4º round.
Regressão: `tests/test_allocation_fairness.py` (9 testes: decaimento,
reset por ganho útil, rotação de entidades, simulação multi-round sem
monopólio, `cap` respeitado).

## 4. Run real accept17 vs accept16 (mesma pergunta §1, medium, max-rounds 3)

| | accept16 (base `d0ba933`+M7–M9) | accept17 (fix ativo) |
|---|---|---|
| Cobertura | 11/51 = 0.2157, parcial | 8/36 = 0.2222, parcial |
| Alvos gap r1/r2/r3 | [c1,c2,c3] / [c1,c2,c3] / [c2,c3,c4] | [c1,c2,c3] / [c4,c5,c6] / [c7,c8,c9] |
| Repetição sem ganho | r2 todo `nogain` nos mesmos | zero repetições; 9 critérios distintos |
| Queries lideradas por | sempre opencode-planner (e1) | e1 de cada critério (nenhum revisit → sem sinal p/ e2; ver §7) |
| Ops / outcomes | 13 ops (r3: 2 `failed` + 1 útil) | 12 ops, **12/12 `new_useful`**, 0 falhas |
| Contadores | 54/36/36/12/6/8 | 85/63/63/10/6/7 |
| Parada | `rounds` (parcial honesta) | `rounds` (parcial honesta) |
| Diagnose | ok 10, partial_legit 23, missing_dim 8, assessor_error 11 (maioria FP heurística), selection_context 2, synth_unsup 1 | ok 8, partial_legit 13, missing_dim 5, assessor_error 7 (idem, justificativas corretas — ex. 2.1.4 ausente), selection_context 3, synth_unsup 0 |
| Síntese | 44 suportadas / 2 não / 57 sem citação | 60 / 21 / 41; support `failed` (ver §5) |

Denominadores diferentes (51 vs 36): a descoberta sorteou candidatos
distintos (accept16: planner/plannotator/oh-my-opencode/marketplace/dzianisv;
accept17: planner/marketplace/vscode/eclipse/oh-my-opencode) — variância
single-run de retrieval já documentada (±0,1). **O percentual não é o
ganho; o ganho é a distribuição**: nenhum slot gasto em repetição estéril.

## 5. Sustentação (sem flexibilização)

`support` accept17 = `failed` honesto: 21 claims sem sustentação, quase
todas em dois grupos reais — (a) menções a `opencode-vscode`/`eclipse`
citando docs que não contêm a entidade; (b) compatibilidade `2.1.4`
e versões citadas contra docs que não declaram a versão. Nenhum ajuste
no validador foi feito para elevar cobertura; RA8 segue PENDENTE.

## 6. Critérios não investigados e motivos

- **Orçamento, não falha**: c10–c12 globais nunca mirados — 12 critérios
  para 9 slots de gap (`max_rounds=3`); parada `rounds` parcial e explícita.
- **Desconhecido-legítimo (retrieval-bound)**: c2 compat 2.1.4 (nenhuma
  fonte declara a versão instalada); c5 custos / c6 manutenção /
  c7 limitações de oh-my-opencode e marketplace (ausentes do corpus);
  c9/c10 combinações/sobreposições (sem evidência de análise conjunta).
- **Sistema (menor)**: `selection_context` = 3 (evidência existe, avaliação
  citou outras refs); 21 claims de síntese sem sustentação (§5) — problema
  de escrita/citação, sem efeito na cobertura.

## 7. Hipótese retrieval × alocação — reavaliação com evidência

**Qualificada, não refutada nem confirmada pura**: o defeito de alocação
era real e foi provado (antes/depois controlado + rotação ao vivo
r1→r3 sem repetição). Mas a taxa de cobertura ficou no mesmo patamar
(0.2157 → 0.2222) com rotação perfeita — o vinculante da **taxa** continua
sendo retrieval/corpus (dimensões ausentes: 2.1.4, custos, manutenção)
somado ao teto de 9 slots. Alocação determinava **quais** células tinham
chance (breadth); retrieval determina **quantas** convertem. Nota de
entidade: em accept17 todos os 12 ops deram `new_useful`, logo nenhum
critério foi revisitado e a rotação entre entidades (e1→e2) não disparou
no ao vivo — verificada offline (`test_entities_share_slots`,
`test_second_sub_leads_with_untried_entity`) e no Fix E genus7.

## 8. Verificação

- Suíte: **420 testes OK / 9 skipped** (base 411 + 9 novos).
- Artefatos: `/tmp/hermes-real-run/accept17/adaptive_accept17/`
  (`report.md`, `result.json`, `verification.json`, `counters.json`,
  `manifest.json`, `state.json`) + diagnose por buckets (§4).
- `/home/thomaskyn/.hermes` e produção intocados; commits locais, sem push.
