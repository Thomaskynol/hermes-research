# Aceite v1 — usar o produto em ambiente isolado

Base: branch `feat/product-v1` (candidato `b3df5d7`), produção intocada.
Tudo abaixo roda na árvore de desenvolvimento, sem ativar nada na produção.

## Requisitos do ambiente

- `python3` com os módulos do repo (rode com cwd na raiz do repo).
- CLI `opencode` com modelo funcional (usado: `opencode-go/muse-spark-1.3-contributor`).
- `SEARXNG_URL` apontando ao SearXNG próprio (ex.: `http://172.18.0.2:8888` —
  IP de bridge, pode mudar; verificado com `/healthz` → 200).
- Rede para OpenAlex/arXiv/GitHub/docs; quota do modelo.

## Pergunta em linguagem natural (sem plan.json)

```bash
cd /home/thomaskyn/Projetos/hermes-research-dev
export SEARXNG_URL=http://172.18.0.2:8888
R=aceite1
python3 gpt_researcher_integration.py \
  "SUA PERGUNTA EM PORTUGUÊS" light \
  --mode adaptive --transport native --model-transport opencode \
  --model opencode-go/muse-spark-1.3-contributor \
  --auto-plan --max-rounds 2 \
  --control-dir /tmp/hermes-real-run/$R/control --run-id $R \
  --output-dir /tmp/hermes-real-run/$R > /tmp/hermes-real-run/${R}.log 2>&1 &
```

`--auto-plan` gera o plano via modelo (sem `coverage-plan`). Essa entrada
executa a versão desenvolvida: os módulos são os do cwd (`adaptive_coordinator`,
`native_transport`, `model_transport`, `research_counters`, `quantitative`,
`report_renderer`, `verification_report`, `run_control`); sem `--mode` o
CLI cai no legado (não usar no aceite).

## Acompanhar / pausar / retomar / cancelar / relatório

```bash
D=/tmp/hermes-real-run/$R/control
python3 run_control.py --run-dir $D status    # fase, rodada, contadores, elapsed, stop
python3 run_control.py --run-dir $D pause     # só vale entre rounds; consome 1 vez
python3 run_control.py --run-dir $D cancel
# retomar (pergunta E plano idênticos; só aceita estender limites):
python3 gpt_researcher_integration.py "MESMA PERGUNTA" light ... --resume --run-id $R ...
# relatório e evidências:
ls /tmp/hermes-real-run/$R/adaptive_*/   # report.md result.json verification.json counters.json manifest.json state.json
```

Pausa/cancel verificados ao vivo (hermdemo6/7): `stop.reason` =
`paused`/`cancelled`, parcial identificável, artefatos parciais completos.
Retomada verificada (0→4 rounds sem re-obter; pergunta diferente = recusa exit 2).
Limite conhecido: pausa só entre rounds/fases, nunca no meio de uma chamada
ao modelo.

## Limites que valem no aceite (não mascarados)

- Orçamento light: 600s, 12 consultas, 60 fontes únicas, 40 extrações,
  4 vídeos, 8 chamadas de modelo (fronteira), 2 rounds; reserva de
  finalização. Tokens/custos: desconhecidos, nunca zero.
- `support=failed` não impede `criteria_ok`: a entrega sai com a citação
  fora do corpus sinalizada em `verification.json` (caso acadrun5: 1 URL MDPI).
- Skips: 9 no host (3 rede-real acadêmica + 2 rede-real reach + 4 contratos
  sem biblioteca) / 5 no container (rede-real). Sem validação: gateway vast
  local (fora do ar), perfil deep 10h, `conduct_research` ponta a ponta da
  biblioteca, pausa no meio de chamada ao modelo, multiusuário.
