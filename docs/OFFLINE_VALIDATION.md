# Validação offline — replay (árvore dev)

Árvore dev: `/home/thomaskyn/Projetos/hermes-research-dev` (branch `dev/baseline-20261018`).
Produção: `/home/thomaskyn/.hermes/deep_research_outputs/gpt_researcher` (HEAD `0b730e0`) — **somente leitura**.
Nunca escrever em `/opt/data` (bind RW do container `hermes-gateway` → produção). Execução só via snapshot temporário `/tmp/replay_dev` dentro do container (ver § Execução).

Runner: `scripts/run_replay_offline_validation.py` (portátil, sem novas dependências — só stdlib).
Não altera `semantic_review.py`, fluxo de pesquisa, nem expectations/asserts das suítes.
Preserva remapeamento histórico `/opt/data/...` → fixtures via `OFFLINE_FIXTURE_MAP` e bloqueio offline via `sys.addaudithook(socket.connect/getaddrinfo/sendto)` propagado às 11 suítes filhas.
Retorna não-zero se qualquer suíte falhar; registra `execution_outputs_reviewed.json` com `suite/command/exit_code/duration_s/combined_stdout_stderr` sem mascarar falha como sucesso.

## Como executar (offline, sem tocar produção)

Pré-inspeção (host):

```bash
docker ps
docker inspect hermes-gateway  # só Mounts
docker exec hermes-gateway /opt/data/home/.agent-reach-venv/bin/python --version
docker exec hermes-gateway /opt/data/home/.agent-reach-venv/bin/pip list 2>/dev/null | grep -i -E 'gpt|langchain|ollama|pytest|httpx'
```

Snapshot temporário (host → container; `rsync`/`docker cp` sem `-H`, sem links; nunca escrever em `/opt/data`):

```bash
docker exec hermes-gateway mkdir -p /tmp/replay_dev
docker cp /home/thomaskyn/Projetos/hermes-research-dev/. hermes-gateway:/tmp/replay_dev/
```

Dentro do container, do snapshot:

```bash
python -c "import sys; sys.path.insert(0,'/tmp/replay_dev'); import semantic_review; print(semantic_review.__file__)"  # deve apontar /tmp/replay_dev
PYTHONPATH=/tmp/replay_dev python /tmp/replay_dev/scripts/run_replay_offline_validation.py \
  --frozen-report /tmp/replay_dev/fixtures/RELATORIO_CORRIGIDO_184601.md \
  --frozen-evidence /tmp/replay_dev/fixtures/replay_corrigido_evidence.json \
  --output-dir /tmp/replay_out
# defaults já são portáteis (fixtures/ + validation/ relativos à árvore); flags acima são explícitas para auditoria.
```

Teste `--output-dir` e offline:

```bash
# saídas vão para /tmp/replay_out, nada novo em validation/ do snapshot
ls -1 /tmp/replay_out
# controle offline: socket.connect deve levantar RuntimeError sob o hook do runner (ver § Execução ETAPA D)
```

Preservar resultados fora dos congelados: copiar `/tmp/replay_out` para log temporário fora do Git ou resumir aqui; nunca sobrescrever `fixtures/` congelados.

## Fixtures (bytes/hashes preservados, versionados sob `fixtures/`)

| arquivo | sha256 |
|---|---|
| `fixtures/semantic_review.py` (raiz, não fixtures) | `93087dc82f8fbadb9802146195473458c6d1ab7d36aeed4c110caa6a5557f57a` |
| `fixtures/gpt_researcher_integration.py` (raiz) | `972f5d95b7fdbe6815058e7fc52b5da3c49bd3fa41d1ceadee24d71c3a7816b7` |
| `fixtures/relatorio_daytona_original.md` | `4952cc655ef2c636d79eac25d26df6450bfed502515a717d8aae8c37a2783d27` |
| `fixtures/corpus_context_original.json` | `309880552fadcd7b71b500549b2d9dda84f9e0128953eeb4bf5c934168de3892` |
| `fixtures/RELATORIO_CORRIGIDO_184601.md` (cópia frozen de `output/RELATORIO_CORRIGIDO_184601.md`) | `55b658951b2bc67d18a0ac78b81b5ad42e374f826350564cdf28c477b968ff9d` |
| `fixtures/replay_corrigido_evidence.json` (cópia frozen de `runs/replay_corrigido_evidence.json`) | `c58dae0e6a6fa6104c13c9f0736ccd0d6ff51f7aa3b2d96247169ef16410668c` |

Não depende de `output/`, `runs/` ou `validation/` não-versionados. `validation/` na árvore dev guarda apenas logs históricos da baseline.

## Ambiente validado e limitações

- 11 suítes em `scripts/test_semantic_*.py` = 83 casos históricos (9+8+11+11+16+1+7+6+4+3+7). Reconciliar funções encontradas vs testes executados (`-v` ou saída real); ver ETAPA D.
- Sem instalação de dependências, sem chamadas reais de modelo/rede, sem credenciais, sem `sync_config`.
- Documentos: `docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` (`3487df6f...`) e `docs/HANDOFF_PESQUISA_HERMES_20261018.md` (bytes integrais do handoff).
- Limitação: aprovação final ainda depende de execução fresca offline no Hermes (ETAPA D); registros antigos em `validation/` são histórico, não prova.

## Validação adaptativa fix/review-981c030 (snapshot isolado)

Snapshot: `cp -a <repo>/. /tmp/adaptive_snapshot/` (fora do Git).
Execução (sem tocar produção, sem `sync_config`/credenciais, offline via
audithook, `PYTHONPATH` do snapshot, `--output-dir /tmp`):

```bash
PYTHONPATH=/tmp/adaptive_snapshot python3 -m unittest discover \
  -s /tmp/adaptive_snapshot/tests -p test_review_regressions.py -v
# → 14 passed (R01–R14), exit 0
PYTHONPATH=/tmp/adaptive_snapshot python3 -m unittest discover \
  -s /tmp/adaptive_snapshot/tests -p "test_adaptive*.py" -v
# → 26 passed (18 adaptativos + 8 entrada), exit 0
PYTHONPATH=/tmp/adaptive_snapshot python3 -m unittest discover \
  -s /tmp/adaptive_snapshot/tests -p "test_question*.py" -v
# → 11 passed, exit 0
PYTHONPATH=/tmp/adaptive_snapshot python3 \
  /tmp/adaptive_snapshot/scripts/run_replay_offline_validation.py \
  --frozen-report /tmp/adaptive_snapshot/fixtures/RELATORIO_CORRIGIDO_184601.md \
  --frozen-evidence /tmp/adaptive_snapshot/fixtures/replay_corrigido_evidence.json \
  --output-dir /tmp/adaptive_out_981c030fix
# → 11/11 suítes exit 0 (83 casos históricos, expectations/fixtures intactos)
```

Import da entrada (`gpt_researcher_integration`) verificado em subprocesso
isolado: sem `/opt/data` em `sys.path`, módulos próprios resolvendo para o
snapshot, `bootstrap_runtime(do_sync=False)` sem `sync`.

## Validação adaptativa fix/review-85dac79 (snapshot isolado)

Snapshot: `cp -a <repo>/. /tmp/adaptive_snapshot_85dac79/` (fora do Git).
Execução (sem tocar produção, sem `sync_config`/credenciais, offline via
audithook, `PYTHONPATH` do snapshot, `--output-dir /tmp`):

```bash
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests -p test_review_85dac79.py -v
# → 8 passed (S01–S08), exit 0
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests -p test_review_regressions.py -v
# → 14 passed (R01–R14), exit 0
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests -p "test_adaptive*.py" -v
# → 26 passed (18 adaptativos + 8 entrada), exit 0
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests -p "test_question*.py" -v
# → 11 passed, exit 0
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests \
  -p "test_*85dac79.py" -v
# → 8 (S01–S08) + 2 (órfão) + 4 (execução única/canal/config/YT) +
#    4 contratos (skip no host sem lib; passam no container) verdes
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 python3 \
  /tmp/adaptive_snapshot_85dac79/scripts/run_replay_offline_validation.py \
  --frozen-report /tmp/adaptive_snapshot_85dac79/fixtures/RELATORIO_CORRIGIDO_184601.md \
  --frozen-evidence /tmp/adaptive_snapshot_85dac79/fixtures/replay_corrigido_evidence.json \
  --output-dir /tmp/adaptive_out_85dac79fix
# → 11/11 suítes exit 0 (83 casos históricos, expectations/fixtures intactos)
```

No container (`hermes-gateway`, venv
`/opt/data/home/.agent-reach-venv`, Python 3.13.5, `gpt-researcher 0.16.0`):

```bash
docker cp /home/thomaskyn/Projetos/hermes-research-dev/. \
  hermes-gateway:/tmp/adaptive_snapshot_85dac79/
docker exec hermes-gateway \
  /opt/data/home/.agent-reach-venv/bin/python -c \
  "import importlib.metadata as m; print(m.version('gpt-researcher'))"
# → 0.16.0 (via metadata, nunca __version__)
PYTHONPATH=/tmp/adaptive_snapshot_85dac79 \
  /opt/data/home/.agent-reach-venv/bin/python -m unittest discover \
  -s /tmp/adaptive_snapshot_85dac79/tests -p "test_*85dac79.py" -v
# → contratos passam com a biblioteca instalada; transportes externos
#    substituídos/bloqueados; módulos próprios do snapshot; sem produção.
```

Garantias demonstradas (S01–S08 + estáticos):

- Teto de modelo nos transportes efetivos (lotes/votos/reparos/retentativas);
  auditor padrão sem isenção, `SEMANTIC_REVIEW=0` respeitado; sem saldo p/
  revisão completa → não-revisado + parcial; teto zero = nenhuma chamada
  remota; sem retentativa após `TypeError` (contrato único adaptado antes).
- Avaliação registra fontes/trechos/hashes/cortes DAQUELA chamada; referência
  fora da seleção nunca justifica covered; unidades completas (sem corte
  arbitrário); lotes por relevância/não-enviados p/ >24 docs e rodadas
  posteriores. `propose_entity` atravessa o assessor → versionamento do plano.
- Qualificação reutilizada p/ strings (erro puro excluído; parciais/metadados
  com alcance); corte 2000 chars rastreável (cabeçalhos/separadores contam;
  `included_urls` só do prompt final); YouTube textual preservado, sem ASR.
- Avaliações acumuladas por (critério,entidade) com revisões explícitas;
  retomada sem regressão sem evidência invalidante; `_reconcile_resume`
  `orph→orphan` corrigido + ramo órfão testado; `run_id`/consumo preservados.
- Fiação real: `_adaptive_main` delega a `adaptive_entry` (mesmo caminho da
  CLI; teste direto sem duplicar lógica). Ver `docs/LIBRARY_CONTRACTS_85dac79.md`.
- Estáticos: `orph` corrigido; coerência config JSON × `SMART_LLM` × componentes
  validada no runtime (`_validate_runtime_config`); `prod_path` só explícito;
  `analyzed/used` em unidades de documentos/fontes.

Limitações explícitas (não apresentadas como teto global):

- 1 invocação de fronteira = 1 unidade de orçamento; voto do auditor = 1
  unidade; lotes autorizados por chunk sem chamada quando sem saldo. Requests
  internos da biblioteca (ex.: múltiplos requests por `quick_search`) não têm
  atribuição fina — declarados como não-protegidos.
- Validação offline (audithook, transportes simulados) + compatibilidade com a
  biblioteca instalada (assinaturas/versão/localização) — pesquisa real com
  modelo/rede (piloto) ainda pendente, sem tocar produção.
