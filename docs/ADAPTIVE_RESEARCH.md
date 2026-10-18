# Modo adaptativo (primeiro fluxo integrado)

Investigação NL → plano estruturado → coleta → cobertura → lacunas →
encerramento → relatório + auditoria. Offline por padrão nos testes;
validação com rede/modelo real está pendente (ver Limitações).

## Uso

```bash
# legado (default, caminho atual intacto — comparação)
python3 gpt_researcher_integration.py "pergunta" light --coverage-plan plan.json
# adaptativo: plano explícito
python3 gpt_researcher_integration.py "pergunta" light --mode adaptive --coverage-plan plan.json
# adaptativo: plano gerado pelo modelo configurado (+1 chamada, reparo limitado)
python3 gpt_researcher_integration.py "pergunta" light --mode adaptive --auto-plan
# limites por execução (sem editar código)
DEPTH_OVERRIDES_JSON='{"budget_queries": 20}' python3 ... --mode adaptive \
  --coverage-plan plan.json --max-rounds 3 --output-dir /tmp/adapt_out
```

Sem `--coverage-plan` nem `--auto-plan`, o modo adaptativo recusa iniciar
(nunca inventa um plano).

## Componentes e reaproveitamento

| Novo | Responsabilidade |
|---|---|
| `adaptive_planner.py` | NL → plano validado (`validate_plan` existente). Fronteira injetável `model_client`; reparo ≤1 tentativa, contabilizado; falha → `PlanError`, nunca plano fictício. |
| `adaptive_state.py` | Estado por execução (pedido, config, plano+versões, evidências+ids, avaliações, rodadas, consumo, pendências, motivo). Escrita atômica (tmp+fsync+rename); `load` marca in-progress como `interrupted`; runs nunca misturam. |
| `adaptive_coordinator.py` | Lógica real do ciclo (sob teste; nunca mockado). Fronteiras injetadas: `search_fn`, `fetch_fn`, `assess_fn`, `writer_fn`, `auditor_fn`, `clock`. |
| `tests/test_adaptive_research.py` | 18 casos offline (comparação de ferramentas + investigação explicativa). |

| Reaproveitado (intocado salvo nota) | Uso no caminho adaptativo |
|---|---|
| `coverage_ledger.py` | plano/cobertura/estados/regras; separação pergunta × claims × sustentação |
| `depth_profiles.py` | `resolve` + `decide_stop` (coverage/novelty/budget/blocked); `vast_max` limita leituras por op |
| `run_budget.py` | teto agregado (queries/extrações/fontes/tempo); +`reseed()` p/ resume (aditivo) |
| `run_checkpoint.py` | checkpoint JSONL entre etapas (fontes/queries/aprendizados) |
| `semantic_review.py` | auditor default (quórum/empates/falhas/extração); semântica nunca move cobertura |
| `run_trace.py` | `new_run_id` |
| gpt-researcher 0.16.0 (`/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages/gpt_researcher`) | encapsulado na entrada de produção: **uma** `conduct_research()` como varredura inicial; rodadas de lacuna usam `quick_search()` direcionado; nunca repete a pergunta original |

## Contratos

- Plano: descreve o trabalho ESPERADO (`plan_id`, `entities`, `criteria`,
  `open_discovery`, `initial_paths`, restrições/premissas). Campos de
  pré-satisfação/resultado são rejeitados. Atualizações de descoberta aberta
  viram nova versão; exigências do usuário nunca encolhem (`record_plan_version`
  recusa drops silenciosos).
- Cobertura: `covered` exige justificativa+origem+refs em evidência utilizável;
  `partial` só vale seu alcance; falha de acesso → `blocked`; negativa
  fundamentada (`negative_conclusion`) pode cobrir; `proportion` = cobertos /
  obrigatórios (null sem avaliação; sem 1.0/0.5).
- Cada rodada persiste: lacunas-alvo, ops, evidências novas, delta de cobertura,
  insuficiências, decisão. Ops registradas == ops executadas.
- Parada (`stop.reason`): `criteria_ok` | `saturation` | `rounds` | `budget` |
  `time` | `blocked` | `failure` — separado de `question_coverage.status` e do
  veredito semântico. Saturação com pendentes = parcial. `flow_end` do legado
  nunca prova completude. Tokens/custos: medidos só com dados reais, senão
  `"unknown"`.
- Resumo de `load` em retomada: estados `in-progress` → `interrupted`
  (sem promessa de exactly-once).

## Execução e recuperação

Estado em `<output-dir>/adaptive_<run_id>/`: `state.json`, `report.md`,
`result.json` + `checkpoint.jsonl`. Retomar:

```bash
# mesma pergunta + mesmo run dir (config armazenada vence; só limites podem
# ser estendidos, registrados em notes)
run_adaptive(..., resume=True, run_dir=..., run_id=...,
             overrides={"max_rounds": 5})
```

Trabalho concluído é preservado (duplicatas detectadas por hash, sem
contagem dupla); consultas concluídas não se repetem silenciosamente.

## Reprodução offline

```bash
python3 -m pytest tests/test_adaptive_research.py tests/test_question_coverage.py -q
```

Validação completa isolada (snapshot, sem tocar produção): ver
`docs/OFFLINE_VALIDATION.md` + § Validação vinculada abaixo.

## Validação vinculada

Rodada 2026-10-18 ~11:52 UTC, branch `fix/review-981c030` (base `981c030`),
snapshot isolado `/tmp/adaptive_snapshot` (`PYTHONPATH=/tmp/adaptive_snapshot`,
`--output-dir /tmp/adaptive_out_981c030fix`, offline via audithook,
sem `sync_config`/credenciais, sem tocar `/opt/data` nem `~/.hermes`):

- Revisão: `PYTHONPATH=/tmp/adaptive_snapshot python -m unittest discover
  -s /tmp/adaptive_snapshot/tests -p test_review_regressions.py -v`
  → **14 passed** (R01–R14 verdes), exit 0, Python 3.14.6.
- Novos: `PYTHONPATH=/tmp/adaptive_snapshot python -m unittest discover
  -s /tmp/adaptive_snapshot/tests -p "test_adaptive*.py" -v`
  → **26 passed** (18 adaptativos + 8 entrada real offline), exit 0.
- Cobertura: `... -p "test_question*.py"` → **11 passed**, exit 0.
- Baseline histórica: `PYTHONPATH=/tmp/adaptive_snapshot python
  /tmp/adaptive_snapshot/scripts/run_replay_offline_validation.py
  --frozen-report .../RELATORIO_CORRIGIDO_184601.md --frozen-evidence
  .../replay_corrigido_evidence.json --output-dir /tmp/adaptive_out_981c030fix`
  → **11/11 suítes exit 0** (83 casos históricos preservados, sem alterar
  expectations/fixtures), modo offline.
- Hashes do snapshot testado (sha256): coordinator `443f087b…`,
  ledger `7d5cc810…`, state `bf7c60a5…`, planner `d5e084be…` (intocado),
  integração `b1b3b962…`, budget `d1542019…` (intocado).
- Entrada real offline: `tests/test_adaptive_entry.py` exercita
  `adaptive_entry()` com transportes simulados e planner/assessor/writer/
  coordinator/persistência reais (sem substituir `run_adaptive` nem o
  assessor por avaliações prontas).
- Registros antigos em `validation/` são histórico, não prova; evidência
  fresca está nos logs do pacote transferível.

## Limitações (não feito aqui)

- Nenhuma pesquisa real executada neste incremento; validação com
  rede/modelo real (`_adaptive_main` com `GPTResearcher`/`litellm`) permanece
  pendente e deve ocorrer em ambiente com credenciais.
- Concorrência: executada sequencialmente com o limite registrado; paralelismo
  real com o mesmo teto é trabalho futuro.
- Uma chamada externa pode conter múltiplas buscas/chamadas internas; a
  contagem atual trata 1 invocação de fronteira como 1 chamada de modelo
  (documentado como shortcut em `adaptive_coordinator.py`); atribuição fina
  por chamada interna é trabalho futuro.
