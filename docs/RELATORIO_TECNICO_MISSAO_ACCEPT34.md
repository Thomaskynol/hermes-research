# Relatório técnico — missão accept34 (gargalos pós-31 + aceite)

Data: 2026-11-01 · Branch: feat/product-v1 · Código congelado: `3da5de8`
(a remontar: AGENTS.md +3 pontos, fix M-A/M-B em `adaptive_coordinator.py`,
`tests/test_accept34_cell_diversity.py` + fixture `accept33_c9e6.json`)

## 1. Congelamento e ambiente (evidência, não alegação)

- HEAD pré-run == pós-run: `3da5de8`; `diff hashes.frozen hashes_post.frozen` → idênticos
  (único diffstat no período: `progress.md` do plano, só docs).
- `opencode v2.2.5` observado no host (pergunta usa `2.1.4` como premissa controlada).
- Embeddings só llama.cpp existente `http://172.17.0.1:8082/v1`
  (`harrier-oss-v1-0.6b`): manifest registra 8 calls / 151 cache hits /
  14490 prompt tokens, última com efeito real
  ("rerank semântico de 28 docs; só reordena"); métricas do servidor
  pré→pós: prompt_tokens_total 111664→125606, cached 1204→1752.
- Sem edição de produto durante o run; sem push/PR/deploy.

## 2. Resultado do run accept34 (`/home/thomaskyn/hermes-runs/accept34/`)

- EXIT=0, elapsed 873.89s. Consumo: queries 18/30, extractions 49/120,
  model_calls 11 (ledger 9 no stop + write/audit), rounds 8, web 13 ok / 12 falhas
  por motivo (0 não resolvidas), tempo 705.4s/1800s.
- Stop `rounds`: `max_rounds=7 source=default` (hook adotou 3→5→7; by_cells
  vincula/empata em 40/8=5 e 50/8=7); único teto vinculante, 15 lacunas abertas,
  folga em todos os demais — parada não-justificada por comparabilidade
  (registrado no próprio `stop.detail`).
- Verificação: overall **partial** (accept33: failed).
  execution=ok, question=partial (0/55), review=partial, **support=ok**
  (accept33: failed) — 0 citações desconhecidas, 0 claims de revisão sem
  suporte; 148 citações (91 com evidência, 10 resolvidas), corpus 28.
- Diagnose externa (`tools/diagnose_run.py`, 55 required):

| bucket | accept33 (56) | accept34 (55) |
|---|---|---|
| selection_context | 31 | 14 |
| missing_dimension_evidence | 14 | 23 |
| partial_legit | 10 | 18 |
| assessor_error | 0 | 0 |
| ok | 1 | 0 |

Síntese: 41 sustentadas, 7 não-sustentadas (overlap), 103 sem citação.

## 3. Atribuição honesta (o que o run prova e o que não prova)

- **M-B (isenção do writer) DEMONSTRADO em produção.** Marcadores presentes no
  relatório: "Versão instalada 2.1.4 é [contexto informado pelo usuário], não
  evidência coletada" (§1), "sem menção a 2.1.4 no documento, versão exata
  desconhecida" (×7), "Versão informada pelo usuário" nas linhas de
  compatibilidade, "fora do corpus" na nota metodológica. As 4 reprovações
  version/quote-gate do accept33 não se repetiram; support failed→ok sem
  afrouxar nenhum gate.
- **M-A (diversidade de lote) SEM TRAÇO em runtime.** `grep diversidade`
  em state.json/checkpoint/counters → 0 ocorrências; `selection.cuts`
  persistido traz só "ordem semântica no restante". Ou a reordenação gulosa
  nunca encontrou ganho, ou não há trilha — indistinguível no artefato.
  Queda selection_context 31→14 **confundida por churn**: finalistas,
  critérios, corpus (45→28 docs) e plano (v11→outro) mudaram juntos;
  sem corpus/plano congelado, sem causalidade. M-A segue validado só por
  teste unitário (RED→GREEN com `new_state` real).
- **Resend só-required CONFIRMADO em runtime:** todas as notas "reenvio de
  quarentena" miram entidades `cand-*` (required); zero alvos fora do teto
  (classe do bug accept33 c×e7 eliminada na trilha observada).
- RA8 continua pendente: overall=partial (question/review partial, 0/55);
  support=ok é dimensão, não atendimento da missão.

## 4. Leitura de usuário do relatório final

Relatório honesto como parcial: 0/55 declarado no topo, §1 separa
documentado/INFERÊNCIA/LACUNA, §5 lista 15 lacunas com próximo passo, §6
nega completude, §7 tem numeração estável com alcance lido integral
(ex. [19] yodev 49724/49724 usable), §8 publica contadores
(35/28/28/28/7/9) e "2.5% dos caracteres incluídos", duplicata declarada.
Limites vistos: títulos "não registrado", URLs de próximo passo truncadas
(§5, ver §6), overlap baixo em paráfrase traduzida (ver §5).

## 5. Revisão independente direcionada (cav-2) — triagem com evidência

1. **§1 frase Context7 [4][26] "sem sobreposição" → REFUTADA.** Doc [26]
   contém literalmente "Context7 fetches current documentation directly from
   source repositories" (state.json evidence, 3507 chars); a frase é
   paráfrase/tradução fiel. Falso-negativo do audit de overlap (PT×EN);
   a regra B5 (overlap nunca força falha) salvou o veredito correto.
   Limitação conhecida do auditor, sem mudança de contrato nesta missão.
2. **§3 Ranger/Refactoring "parcial" vs §1 "sem fonte própria" →**
   **refutada como contradição material.** Os partials têm refs reais
   (opendock Testing p/ Ranger c4/c10; yodev p/ Refactoring c3/c7) e caem em
   partial_legit/missing_dimension; §1 nega *fonte própria* e afirmações de
   *combinação/sobreposição* — ambas seguem verdadeiras. Resta só um
   excesso verbal em §1 ("nenhuma célula sustentada") sem efeito no placar
   (0/55). Sem fix de código; registrado.
3. **§5 URLs truncadas (`...vale-la-)`) → DEFEITO REAL, CORRIGIDO.**
   Causa-raiz: `src[:80]` em `_gap_next` (`coverage_ledger.py`). A URL
   completa é recuperável via §7 [19], mas o próximo passo saía
   incopiável. Fix: URL integral (2 linhas) + teste de regressão
   `test_gap_next_keeps_long_source_url_whole` (URL >80 chars; falharia
   antes por construção — `[:80]` nunca contém a URL inteira).
   Artefato accept34 preservado como está (congelado); fix vale p/ runs futuros.
4. **support=ok "estreito" (5 frases overlap + 29 sem citação) →**
   **semântica pré-existente, não defeito.** support falha só com citação
   desconhecida/fora do corpus ou claim de revisão sem suporte; overlap é
   informativo (B5). §8 mostra question/review partial ao lado — nenhuma
   completude sugerida. Registrado como limitação de leitura, sem mudança.
5. **execution=ok com parada precoce → semântica pré-existente.**
   execution=processo sem falhas não resolvidas; cobertura curta cai em
   question=partial. Consistente; sem mudança.

## 6. Fila de problemas — estado final

- Corrigidos nesta missão: lote-resend fora do teto (filtro required),
  isenção do writer (4 gates), URL truncada no next (este relatório).
- Conhecidos, não corrigíveis nesta autorização/escopo: stop rounds por
  default com lacunas abertas (exigiria mudar orçamento default ou
  budget/saturação decidindo — decisão de produto); churn auto-plan entre
  runs (exige plano+corpus congelados p/ comparar código); overlap ×
  tradução no auditor; M-A sem trilha de engajamento (observar em runs
  futuros; proposta: persistir estatística de cobertura, não implementado).
- Nenhum problema material corrigível restante dentro da autorização.

## 7. Artefatos

- Run: `/home/thomaskyn/hermes-runs/accept34/` (run.sh, stdout.log,
  HEAD/diffstat/hashes/status/metrics/opencode_version .frozen,
  diagnose_accept34.json, adaptive_accept34/{report.md, verification.json,
  manifest.json, state.json, result.json, checkpoint.jsonl, counters.json})
- Relatório final (entrega): `/home/thomaskyn/hermes-runs/accept34/adaptive_accept34/report.md`
- Código: `coverage_ledger.py` (`_gap_next` sem `[:80]`),
  `tests/test_accept29_causes.py` (+1 regressão)
- Suíte: 648 testes OK, 10 skips, EXIT=0 (log /tmp/opencode/accept34b_full.log).
