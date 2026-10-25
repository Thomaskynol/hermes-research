# Demo Hermes fim a fim — acompanhar, pausar, retomar, cancelar (ponto 3)

Demonstração em ambiente isolado de que uma pesquisa pode ser iniciada e
controlada externamente via arquivos (o contrato que o Hermes usa), sem
intervenção no processo.

Sintaxe real (verificada):
- `python3 run_control.py --run-dir <control-dir> status|pause|resume|cancel`
  (`--run-dir` é flag global ANTES do subcomando; não existe `request pause`).
- Lançamento: `--control-dir <dir> --run-id <id>`; retomada exige `--resume
  --run-id <id>` + MESMA pergunta e plano (guarda "runs never mix", saída 2).
- Controle padrão: `<out>/adaptive_<id>/control` (dir explícito recomendado).

## A. Pausa + retomada (uv, 3 rounds — janela real de pausa)

```bash
cd /home/thomaskyn/Projetos/hermes-research-dev
export SEARXNG_URL=http://172.18.0.2:8888
R=demo-pause
python3 gpt_researcher_integration.py \
  "Como o uv gerencia cache e quais os trade-offs em relacao ao pip?" light \
  --mode adaptive --transport native --model-transport opencode \
  --model opencode-go/muse-spark-1.3-contributor \
  --coverage-plan /tmp/hermes-real-run/uvplan.json \
  --max-rounds 3 --control-dir /tmp/hermes-real-run/$R/control \
  --run-id $R --output-dir /tmp/hermes-real-run/$R > /tmp/hermes-real-run/${R}.log 2>&1 &
# acompanhar: python3 run_control.py --run-dir /tmp/hermes-real-run/$R/control status
# pausar no meio da coleta (round>=1, antes do finalize):
python3 run_control.py --run-dir /tmp/hermes-real-run/$R/control pause
# assert: processo encerra; result.json stop.reason == "paused" (parcial)
# retomar (pergunta e plano IDÊNTICOS):
python3 gpt_researcher_integration.py \
  "Como o uv gerencia cache e quais os trade-offs em relacao ao pip?" light \
  --mode adaptive --transport native --model-transport opencode \
  --model opencode-go/muse-spark-1.3-contributor \
  --coverage-plan /tmp/hermes-real-run/uvplan.json \
  --max-rounds 3 --control-dir /tmp/hermes-real-run/$R/control \
  --resume --run-id $R --output-dir /tmp/hermes-real-run/$R
# assert: relatório final existe; cobertura final >= cobertura da pausa;
# fetches não duplicam (fontes concluídas reutilizadas)
```

## B. Cancelamento

Idem, com `pause` trocado por `cancel` ainda na coleta.
Assert: `stop.reason == "cancelled"` + estado preservado até o cancelamento.

## Critérios de aceite

- status.json observável durante a execução (fase/rodada/contadores/elapsed).
- pausa produz STOP `paused` identificável, sem perda do obtido.
- retomada não repete a coleta (fetches não duplicam) e conclui.
- cancelamento produz STOP `cancelled` + parcial identificável.

## Evidências registradas

- hermdemo2 (FAIR-RAG, 1 round): criteria_ok 1.0; review ok (5 claims);
  pausa chegou tarde (finalize) — run completou; status.json só tinha o
  write inicial + run_id="control" (basename). Correções aplicadas:
  `RunControl(run_dir, run_id=...)` + teste `test_explicit_run_id_overrides_dirname`.
- hermdemo4 (uv, 4 rounds): pausa emitida no round 2 NUNCA consumida
  (`control.taken.json` ausente, run completou `rounds`) + status.json só com
  o write inicial. Causa raiz: caminho novo chamava `_resume_loop(...)` SEM
  `control=control` (só a via resume passava). Fix em `adaptive_coordinator`
  + regressão `test_pause_in_gap_round_reaches_finalize_and_done`
  (vermelho→verde comprovado: FAIL sem o fix, OK com o fix). Commit `de403b2`.
- hermdemo5 (uv, status): `status.json` com `phase=done`, `run_id=hermdemo5`
  após a correção — status acompanha o run de verdade no caminho integrado.
- hermdemo6 (uv, PAUSA real): pause aos ~20s, no meio da coleta →
  `stop.reason="paused"` ("control pause requested"), parcial, rounds=0 com
  6 evidências preservadas, `control.taken.json` consumido, artefatos
  parciais completos (report/result/verification/counters/manifest),
  `status.json` done/paused, processo saiu limpo.
- hermdemo6 retomada (pergunta+plano idênticos): continuou 0→4 rounds,
  STOP `rounds` parcial 0.2, elapsed 217s, sem re-obtenção (fontes concluídas
  reutilizadas). Guarda "runs never mix" (pergunta diferente → recusa,
  saída 2, sem gastar modelo) provada na hermdemo1.
- hermdemo7 (uv, CANCEL real): cancel aos ~25s → `stop.reason="cancelled"`
  ("control cancel requested"), parcial, rounds=1, artefatos parciais
  completos, taken consumido, `status.json` done/cancelled, processo saiu.

Artefatos das demos em `/tmp/hermes-real-run/hermdemo{5,6,7}/` (fora do Git).
