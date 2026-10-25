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
