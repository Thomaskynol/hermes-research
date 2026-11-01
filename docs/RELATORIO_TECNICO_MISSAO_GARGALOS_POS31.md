# Relatório técnico — missão gargalos residuais pós-accept31 (accept32 + accept33)

Data: 2026-11-01. Branch: `feat/product-v1`. Pergunta: benchmark plugins-OpenCode
(5 plugins; planejamento/implementação/testes/revisão; compatibilidade; dependências;
custos; manutenção; limitações; combinações; sobreposição; fontes atuais; doc×inferência).

## 1. Resultado

| Run | HEAD | Cobertura | Stop | Overall (exec/question/review/support) |
|---|---|---|---|---|
| accept32 | 9c311ad | 0/56 partial | rounds 3 (source=default) | partial (ok/partial/partial/ok) |
| accept33 | 4615ccb | 1/56 partial (0.0178) | rounds 7 (source=default) | failed (ok/partial/partial/failed) |

Diagnose (56 required cells):
- accept32: missing=20, selection_context=18, assessor_error=16, partial_legit=2, ok=0.
  Síntese: 31 supported / 7 unsupported / 108 uncited.
- accept33: missing=14, selection_context=31, assessor_error=0, partial_legit=10, ok=1.
  Síntese: 47 supported / 4 unsupported / 119 uncited.

Suporte accept33: 4 claims unsupported — frases LACUNA honestas cujas citações não
contêm o literal (versão exata `2.1.4`, nomes de entidades); o verificador reprova
corretamente por literalismo. RA8 segue PENDENTE.

## 2. O que cada fix provou em produção

**Fix accept32** (`9c311ad`, `_relevant_excerpt` + `resend_focus`): excerto de URL
reenviada prioriza a janela conjunta menção+termo da célula aberta (≤1500/600 chars),
mesmos tetos 1200/12k. Efeito real: selection_context 29 (accept31) → 18 (accept32).
Sem regressão de gates (identidade, N/A, inferência, user-reserva intactos).

**Causa-raiz do hook proporcional morto (achado no accept32, não hipótese):**
`adaptive_state.new_state` inicializa `stop={"reason":None,...}` e `report={}` —
nunca None. O guarda M5 (`stop is not None or report is not None`) era portanto
SEMPRE verdadeiro pós-início → re-adoção impossível em qualquer run real. A base
calculava sobre o plano v1 (0 células — critérios ainda sem `applies_to`),
proposed=1≤3, silenciosa. Evidência runtime: `_proportional_cells`=0 final, zero
notes, max 3, plano v1→v15 (0→50 cells) sem adoção. Testes M5 passaram porque
montavam state manual com `stop=None` (mock-behavior gap: o teste não usava o
construtor real de estado).

**Fix accept33** (`4615ccb`, só o hook + teste novo): guarda pós-início detecta
DECISÃO real (`bool((stop or {}).get("reason"))` / `bool(report)`); sempre que
`cells != last`, escreve a key + UMA trace note
`proporcional: células … → proposto … vs vigente …: ADOTADO a→b | mantido — motivo`;
`cells==last` silencioso; resume-legado preservado (com trace). TDD RED→GREEN
(3 falhas pré-fix), full 638 OK skipped=10 EXIT 0.
Efeito real (accept33): notes `mantido` (base 0 cells) + `ADOTADO 3->7`
(50 cells); `config_applied.max_rounds=7`; 8 rounds (0+7) vs 4 no accept32;
assessor_error 16→0; missing 20→14; partial 2→10; supported 31→47.

## 3. Gargalo residual honesto (próxima hipótese, não fix neste incremento)

Com 7 rounds, o funil deslocou-se de rounds para **largura de seleção por chamada**:
selection_context 18→31. Mais descoberta (11 versões de plano, mais candidatas)
espalhada sobre o mesmo teto JSON 12k/lote → mais células abertas com doc
in-selection mas janela da dimensão fora do lote. O teto vinculante passou a ser
`by_model=(16-2)/2=7` empatado com `by_cells=7`: o próprio proporcional PowerShell
capa em 7 com model_calls=16. Stop aos 7 rounds com folga total
(queries 17/30, extractions 84/120, model 9/16) e 16 lacunas abertas — parada
ainda não-justificada por comparabilidade, agora por fórmula, não por bug.

Candidatos (não implementados): composição de lote por diversidade de células
abertas (P2 já exige não repetir par url×célula; falta priorizar células sem
cobertura no assembly do lote), e/ou reavaliar a fórmula by_model/by_cells
com decisão explícita registrada. Plano churnou nos dois runs (finalistas
diferentes entre accept32 e accept33) — comparabilidade entre runs continua
limitada por auto-plan, não só por código.

## 4. Verificações e limites

- Congelamento: HEAD/hashes pré==pós nos dois runs; 8082 com efeito real
  (accept32 +10588/+118 cached; accept33 +22128/+224). vast/searxng DOWN;
  `/opt/data` PermissionError e `cascade_fetcher` ausente degradados explicitamente.
- Suite: 638 OK skipped=10 EXIT 0 (baseline idêntico via stash). Diagnose só em
  runs congelados (nunca re-executada como prova de caminho novo).
- Revisão cavecrew do fix accept32: 0🔴 5🟡 (limites conhecidos declarados).
- Lição operacional: `&` no run.sh orfana o worker quando a task shell conclui —
  reconciliar por marcador RUN_DONE + pós-freeze, nunca por estado da task;
  próximo run em foreground ou setsid.
- Não verificado: run real do fix accept32 isolado do hook (accept32 já continha
  resend-focus; accept33 contém ambos — efeitos separados por diagnose, não por
  ablação com runs duplicados).

## 5. Artefatos

- Runs: `/home/thomaskyn/hermes-runs/accept32/` (report, verification.json,
  diagnose_accept32.json, stdout.log, freezes) e `.../accept33/` idem.
- Código: commits `9c311ad` (resend-focus) e `4615ccb` (hook trace+guarda).
- Testes: `tests/test_accept32_selection.py`, `tests/test_accept33_proportional.py`
  (este último usa `_state.new_state` REAL — regressão do mock-behavior gap).
