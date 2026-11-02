# Relatório técnico — Fase F: 4 contratos + aceite accept41

Data: 2026-11-02 · Branch: `feat/product-v1` · Código sob aceite: `934f373`
Run: `/home/thomaskyn/hermes-runs/accept41/` (run_id `accept41`) ·
Relatório do produto: `/home/thomaskyn/hermes-runs/accept41/adaptive_accept41/report.md`
Runs preservados: accept35/36/37/38/39/40 (intocados).

## 1. Congelamento e ambiente

- HEAD pré == pós: `934f373849ac5d66edd0c7fcf7d181ed2205bd44`; `hashes.frozen` ==
  `hashes_post.frozen`. Nenhuma edição durante o run.
- Embeddings só llama.cpp 8082 (`harrier-oss-v1-0.6b`): pré `235087/4368` →
  pós `256336/4540` (+21249 gerados, +172 cache, com efeito). Sem outro/CPU/externo.
- `opencode v2.2.5` observado; premissa controlada `installed_opencode_version=2.1.4`
  separada (contexto do usuário, §1 linha 15/29). Mesma pergunta accept35, medium.
- `RUN_DONE EXIT=0`, elapsed 1299s. Consumo: q16/30, e88/120, model 8/16 na decisão,
  rounds 7, 803.8s/1800s. Stop `rounds`, max_rounds=6 source=default (hook 3→…→6
  por by_cells), 15 lacunas, folga total — limite honesto, não esgotamento.

## 2. Resultado

| Métrica | accept40 (ac81ae9) | accept41 (934f373) |
|---|---|---|
| Cobertura | 5/40 (0.125) | **2/41 (0.0488)** — 10 N/A fora do denominador |
| Diagnose (51) | — | missing 13, partial 8, sel_ctx 18, ok 2, na_bare 7, na_scoped 3 |
| Síntese | — | 57 / 10 / 155 (sup/não-sup/sem-cit), declared 21 |
| Verificação | overall partial | **overall partial**; support ok (51/16/37); review partial; execution ok |
| Corpus | — | 50 desc / 43 obt / 43 usáv / 43 anal / 6 usados / 8 citados; leitura 1,2% |
| Citações | — | unknown=[], unsupported_claims=[], false_absence ausente |

Churn auto-plan repetido (finalistas code-review/review/marketplace/jira/envsitter) —
delta entre runs não é causal. Demonstração dos contratos repousa em replays +
testes + traços de produção, não em delta.

## 3. Os 4 contratos em produção

1. **Planejador→assessor.** 15/15 critérios com description operacional no plano v1;
   zero "Definição do critério não fornecida" nas evaluations; sem warning de colapso
   (plano manteve per_candidate). Fail-closed preservado sem abortar o run.
2. **Corpus→seleção→relatório.** sun-praise [9] obtido+usável e citado; nenhuma
   afirmação "fora do corpus" contradiz a bibliografia (1 ocorrência legítima em nota
   metodológica, linha 124). Veto disparou de verdade no run (`veto fora-do-corpus`
   em §8-notas). Estágios 50/43/43/43/6/8 distinguem obtida≠selecionada≠analisada.
3. **Descoberta→finalistas.** Notas "sem substituto no plano" + alternativas listadas;
   nenhuma troca inventada (demo C3 offline já provou o par comparativo até o
   Markdown em valid-fase-f/c3-substitution/). Sem carimbo "sem substituição" no corpo.
4. **Síntese→avaliação.** §1-§11 com 4 INFERÊNCIAs marcadas+citadas+limitadas
   ([3][8], [3][9], [29][8][9], [8][9]); §3-combinações parcial reconciliada com a
   inferência; ausência de interop segue LACUNA sem apagar a inferência.
   Corpo §§1–7 limpo: zero códigos de entidade, zero jargão/Skipped/legenda/[(fonte)].

## 4. Triagem residual (sem problema material corrigível no escopo)

1. **§1-vs-§3 defasado (classe nova, causa conhecida):** §3-c1 diz faltar fonte
   utilizável p/ opencode-review mas §1 documenta [9]; c2 "não investigado" mas §2
   cobre compat por entidade; §3-sobreposições "sem fonte para opencode-review" mas
   §1-§11 infere com [8][9]. Causa: texto do assessor (round inicial, preservado por
   monotonicidade) vs síntese posterior; sem canal de reconciliação pós-síntese p/
   globais não-combinação. Estender a promoção a todos os globais é mudança maior —
   fila, não defeito desta etapa (cobertura parcial já declarada).
2. **Overlap segue com recall baixo em PT→EN:** 16 unsupported "sem sobreposição"
   são informativos (support ok por gates: unknown=[], claims=[], false_absence
   ausente); o auditor subestima paráfrase, sem afrouxar gates.
3. **Cosméticos:** linha 126 vaza `ponytail:` (texto do harness ecoado pelo modelo na
   síntese — gerador não filtra eco de modo de sessão); notas "sem substituto"
   repetidas no anexo §8 (só dedup exato). Sem efeito factual.
4. Leitura 1,2% do corpus; saturação não demonstrada; parada por limite default.

## 5. Verificação

- Suite: **733 OK, skipped=10 (pré-existentes), EXIT 0** (log `/tmp/opencode/fase_f_suite4.log`).
- Revisão independente da higiene (ses_e64568cab): 0🔴 4🟡, todos corrigidos com TDD
  (RED 7→GREEN 8) antes do congelamento accept41.
- URLs §7: 30 números, todos obtidos+usáveis; `citations_unknown=[]`.
- Commits locais (sem push): 934f373 (higiene+fixes). `.planning/.active_plan` alheio.

## 6. Entrega e limite

Atendimento **parcial**: 4 contratos demonstrados em produção + replay + testes;
relatório honesto (2/41, 15 lacunas, parada por limite). Não validado: reconciliação
§1-vs-§3 p/ globais (fila §4.1), recall total do overlap, leitura além de 1,2%.
