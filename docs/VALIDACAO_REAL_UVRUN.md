# Validação real NÃO-RAG — uv vs pip (auto-plan, spark)

Assunto fora de RAG/gpt-researcher, plano gerado pelo modelo (`--auto-plan`,
sem coverage-plan). Modelo `opencode-go/muse-spark-1.3-contributor` via CLI
(`model_transport=opencode`). Transporte nativo. Perfis light, max_rounds=2.

## uvrun2 (antes do fix de extração)

STOP `rounds`, partial, proportion 0.0, 3 rounds (0+2), 128s, EXIT=0.
Contadores 12/8/8/8/6/6. Diagnóstico: evidências eram HTML cru gigante
(50–600K chars, Next.js single-line); o corte do assessor pegava só
head/metadata → avaliações `insufficient` honestas. `verify_support=failed`
correto: relatório continha 1 URL fora do corpus + 2 além da base de síntese
(modelo esticou citações, verificação pegou). review=partial, execution=ok.
Fix aplicado: `_visible_text()` (adaptive_coordinator) remove head/script/
style e stripa tags antes do excerto substantivo.

## uvrun3 (com fix de extração) — artefatos em /tmp/hermes-real-run/uvrun3

STOP `rounds`, partial, proportion 0.0, 3 rounds, 113s, EXIT=0.
Excertos abriram no título/corpo (stripping 88K/50K/45K chars de markup).
Round 1 atingiu 0.25 (c1 covered, c2/c4 partial); round 2 regrediu para 0.0:
sem evidência nova (ops failed/nogain), o assessor rebaixou os estados e o
coordenador aplicou. Cobertura não era monotônica (bug real, não alucinação
do teste). Fix: `_assess_round` rejeita rebaixamento cujas refs não incluem
URLs incorporadas após a avaliação anterior (contradictory/blocked livres;
upgrade livre); nota `downgrade without new evidence rejected`.
Cobertura: `tests/test_monotonic_coverage.py` (4 testes OK).

## uvrun6 (fix de monotonia do ledger) — prova ponta a ponta

Dir: `/tmp/hermes-real-run/uvrun6/adaptive_20261025-025909-Como_o_uv_gerencia_cache_e_res`.
STOP `rounds`, partial, proportion **0.2** (antes: 0.0), 3 rounds, 132s, EXIT=0.
r0: 6 ev/0.0 → r1: 5 ev novas/0.2 (c2 covered) → r2: 0 ev novas/**0.2 mantido**
(c2 covered preservado; sem notas de downgrade porque o assessor não tentou
rebaixar desta vez, e o ledger agora reflete o merge).
Contadores 16/11/11/11/6/8. `verify_support=failed` correto: relatório cita 3
URLs nunca obtidas (docs.astral.sh layout/scripts, BENCHMARKS.md) — modelo
esticou citações, verificação pegou (11/14 resolvidas). execution=ok,
question=partial, review=partial (0 claims extraídas).

## uvrun4

Mesmo comando do uvrun3 com o fix de monotonia; dir
/tmp/hermes-real-run/uvrun4. Objetivo: cobertura final 0.25 em vez de 0.0.
(Superado pelo uvrun6, que prova o mesmo fix com proporção 0.2 mantida.)
