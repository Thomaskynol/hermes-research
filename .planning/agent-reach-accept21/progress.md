# Progress — agent-reach-accept21

## 2026-10-31 — Sessão 1: inicialização da continuidade (fixer)

- Inicializado plano via `init-session.sh --autonomous "agent-reach-accept21"`;
  renomeado para o slug exato `.planning/agent-reach-accept21/`
  (`.active_plan` atualizado).
- Verificado: branch `feat/product-v1` HEAD `b1cf76c`; `opencode v2.2.5`;
  `hermes-gateway` UP (9119/8081); :8001/:8888 sem listener (STOPPED on-demand).
- Escritos: `task_plan.md`, `findings.md`, `progress.md` (este arquivo),
  `docs/CONTINUIDADE.md`.
- Nenhum código produto tocado (escopo: só docs + plano).
- Próximo: Phase 2 — subir vast (:8001) + SearXNG (:8888), checar `/healthz`.

## 2026-10-31 — Sessão 2: run accept21 (fixer, lane isolado)

- Congelado HEAD `b1cf76c` + `git diff --stat` + sha256 de
  `adaptive_coordinator.py` (`9b3a577a…`) e `verification_report.py`
  (`dcff1404…`) em `/home/thomaskyn/hermes-runs/accept21/*.frozen`.
  Hashes reconferidos após o run: idênticos (sem edição produto no run).
- Entrada do experimento: `installed_opencode_version=2.1.4` (contexto);
  instalada real `opencode v2.2.5` registrada à parte (sem presumir).
- Infra medida (curl curto, sem presumir IP): vast :8001 UP on-demand
  (`degraded`: youtube ok; github/bilibili broken por `gh`/`bili` ausentes;
  desligado pós-run, baseline restaurada); SearXNG DOWN (localhost + bridge
  `172.18.0.2`, sem imagem docker); embeddings :8082 DOWN; gateway 9119 UP.
- Run real (run.sh congelado; medium, max-rounds 3, native+opencode
  `muse-spark-1.3-contributor`): parada `rounds`, 343s, EXIT=0, 40/2/2,
  16 avaliações (14 insufficient + 2 partial).
- **Cobertura 0/15 + 0 N/A** (diagnose: 15× `missing_dimension_evidence`);
  síntese 7/15/79; **verification overall `partial`**
  (execution ok, question/review/support partial). **RA8 segue PENDENTE.**
- Causa do zero: funil YouTube (38/40 descobertos via vast UP) sem
  transcrição (`yt_live_fetches=0`, teto 2 não usado) — 15 MB de HTML
  boilerplate, 0 candidatos (`entity_id null`), LACUNA honesta geral.
- cc0f3ff/b81e8f6 **não exercitadas** (sem afirmação de versão; M8 sem
  disparo por vacuidade). Possível regressão registrada sem corrigir:
  15 frases LACUNA com citação fora do corpus ⇒ só `partial`
  (accept19 falhava corretamente 1 citação assim).
- Entrada exercitada: `gpt_researcher_integration._adaptive_main` via CLI;
  outputs em `/home/thomaskyn/hermes-runs/accept21/` (fora do repo e do
  /tmp); `.hermes` intocado; sem push.
- Utilidade: nula como guia de plugins; válida como negativo honesto +
  expôs modo de falha single-channel (5/52→0/15 entre runs idênticos).

## 2026-10-31 — Sessão 3: commit produto + continuidade (fixer)

- Commit produto `817a77b` (local, sem push): `adaptive_coordinator.py`
  (B3 `_pick_pool_reserve` + B4 janela da menção via `entity_terms` +
  `_mention_positions`), `verification_report.py` (B2 granularidade por
  bullet + B5 `_window_hash`/`_selection_window`/ponderação
  sentence_support), `tests/test_audit_granularity.py` +
  `tests/test_pool_reserve_mention_window.py` (5+5, 10 passed).
  Separado do docs `d665550` (produto vs docs).
- Hashes workdir == frozen do run (`9b3a577a…`/`dcff1404…`): o commitado é
  exatamente o validado; nada mudou durante o run.
- Serviços pós-run: gateway 9119/8081 UP; vast :8001 DOWN (baseline
  restaurada); SearXNG e embeddings DOWN.
- `docs/CONTINUIDADE.md` atualizado (HEADs, hashes, resultado accept21,
  serviços, próxima ação). Nenhuma lógica produto alterada além do commit.
- Próximo: run controlado com vast DOWN + fix leniência LACUNA, depois
  accept22 nos 5 bloqueadores.

## 2026-10-31 — Sessão 4: suíte combinada fresca + commit produto (fixer)

- Suíte combinada FRESCA (`-p no:cacheprovider`, sem cache), 8 arquivos —
  4 focos (`test_audit_granularity`, `test_pool_reserve_mention_window`,
  `test_web_monopoly_break`, `test_lacuna_quote_gate`) + regressão
  (`test_accept19_corrections`, `test_product_core`, `test_support_check`,
  `test_s2_premises`):
  `84 passed in 1.41s`, EXIT=0.
- Comando FULL:
  `/home/thomaskyn/miniconda3/bin/python -m pytest
  tests/test_audit_granularity.py tests/test_pool_reserve_mention_window.py
  tests/test_web_monopoly_break.py tests/test_lacuna_quote_gate.py
  tests/test_accept19_corrections.py tests/test_product_core.py
  tests/test_support_check.py tests/test_s2_premises.py -p no:cacheprovider -q`
  (84 coletados; `python3` do brew não tem pytest — usado o do conda).
- Log persistente fora do /tmp:
  `/home/thomaskyn/hermes-runs/accept21-combined/pytest_combined_fresh.log`;
  exit code verdadeiro capturado via `$?` imediato (sem pipe).
- A falha isolada de `test_web_monopoly_break` quando combinado
  (reportada) NÃO reproduziu: verde de primeira, nenhuma edição no produto
  (regra: verde ⇒ não mexer).
- Higiene: produto sem nomes de origens/plugins (só a palavra genérica
  "plugin" num docstring "generic, no plugin names").
- Commit produto `a704463` (local, sem push):
  `native_transport.py` (quebra de monopólio single-host sem transcrição +
  mistura por diversidade) + `verification_report.py` (gate de quote/versão
  em LACUNA + ponderação no `verify_support`) + 2 testes novos
  (`test_web_monopoly_break`, `test_lacuna_quote_gate`). Separado de docs.
- Próximo: run controlado accept22 (vast DOWN + SearXNG DOWN baseline)
  exercitando os 2 fixes; RA8 segue pendente até evidência do run.

## 2026-10-31 — Sessão 5: run accept22 com vast DOWN (fixer, lane isolado)

- Congelado HEAD `776af89` + `git diff --stat` (vazio; só untracked
  `.planning/.active_plan` pré-existente) + sha256 de 5 arquivos produto
  (`hashes.frozen`) em `/home/thomaskyn/hermes-runs/accept22/*.frozen`.
  Hashes reconferidos após o run: idênticos (sem edição produto no run).
  `adaptive_coordinator.py` igual ao frozen accept21 (`9b3a577a…`).
- Entrada do experimento: `installed_opencode_version=2.1.4` (contexto);
  instalada real `opencode v2.2.5` registrada à parte (sem presumir).
- Infra medida (curl curto, pré E pós-run): vast :8001 DOWN (000, sem
  processos, nada subido on-demand); SearXNG DOWN (localhost + bridge
  `172.18.0.2`); embeddings :8082 DOWN; gateway 9119 UP (302).
  Baseline restaurada por construção (nada foi ligado).
- Run real (run.sh = template accept21 com dirs accept22; medium,
  max-rounds 3, native+opencode `muse-spark-1.3-contributor`): parada
  `rounds`, **658s**, EXIT=0, 31/28/28/22, 7 síntese / 10 citados,
  55 avaliações (11 covered + 23 partial + 21 insufficient,
  **0 assessor_error**). Consumo: queries 10, extractions 37,
  **yt_live_fetches 0**, model_calls 8.
- **Cobertura oficial 11/54 + 0 N/A (20,4%)**; diagnose: ok 10,
  partial_legit 11, missing 16, selection_context 16,
  synthesis_unsupported 1 (c7/e5); síntese 65/9/59;
  **verification overall `failed`** (execution ok, resto partial/failed).
  **RA8 segue PENDENTE.**
- Causa do failed (3, métodos de acordo): 5 URLs nuas fora do corpus +
  3 claims de combinação-inferência reprovadas [12,13,14] + 17 frases
  LACUNA sem overlap suficiente. Renderer auto-declarou as URLs nuas.
- Utilidade: **5 nomes pertinentes com fonte** (lit-opencode,
  opencode-browser, plugin-testing/dzianisv, opencode-plugins/jadmadi,
  Context7); comparação parcial honesta; combinações = inferências
  declaradas (reprovadas pelo revisor); overlap = LACUNA.
- Fixes: monopólio-break sem alvo (11 hosts, 1 YT — diversidade por canal
  morto, disparo não isolável); quote-gate manteve `failed` em URL nua
  (leniência accept21 estreitada ao caminho de índices `[N]`); cc0f3ff com
  primeiro sinal positivo fraco (classe accept20 ausente; sentença compat
  declara LACUNA contida); b81e8f6 sem alvo (M8 sem disparo).
  Residual: selection_context 16 de volta; c11/c12 insufficient.
- Outputs em `/home/thomaskyn/hermes-runs/accept22/` (fora do repo e do
  /tmp); `.hermes` intocado; sem push.

## 2026-10-31 — Sessão 6: revisão — teste estrito + matriz/CONTINUIDADE (fixer)

- RED: tautologia `or True` (`test_pool_reserve_mention_window.py:101`)
  provada vacuosa sobre ops fabricadas (antiga retorna `True` sempre).
- GREEN: `test_sem_pool` exige `_pick_pool_reserve→(None,None)` + zero
  `read_source` + zero nota; `test_reserva_respeita_falha` exige URL boa
  em `read_source` + nota `pool reserve`. Nenhum nome de plugin no teste.
- Foco fresco (`-p no:cacheprovider`): `test_pool_reserve` +
  `test_audit_granularity` + `test_lacuna_quote_gate` +
  `test_web_monopoly_break` = **20 passed, EXIT=0**. Produto intocado
  (hashes == `hashes.frozen` accept22).
- Docs: `REQUIREMENTS_MATRIX.md` (RA8 accept22 11/54 failed honesto +
  seções Entrega atual/Escopo REAL-vs-PENDENTE + 5 itens sem validação
  como limitação + HEADs frozen-vs-docs) e `CONTINUIDADE.md`
  (header/HEADs + seção Riscos amarelos, sem refatorar).
- Commit local docs+teste (sem push); próxima ação inalterada
  (selection_context 16, índices fora da base; depois 5 bloqueadores).

## 2026-10-31 — Sessão 7: Missão 2 — coerência do plano (fixer)

- HEAD `15443a5` (só docs+teste desde o run; produto == `a704463`);
  árvore rastreada limpa; gateway 9119/8081 UP, :8001/:8888/:8082 DOWN;
  `opencode v2.2.5`; config efetiva reconfirmada no código
  (`vast_local_retriever.py:11-14`).
- `task_plan.md`: Goal/Next Step reescritos; Phases 2–3 marcadas
  SUPERADAS (runs já executados; rounds-3 era config, não fixo);
  Phase 4 RECLASSIFICADA (5 itens = limites, não requisitos);
  Phase 6 (Missão 2) aberta.
- `findings.md`: seção Missão 2 com estado, config e conferência dos 5
  itens (só item 1 = PENDENTE legítimo/BLOQUEADO; itens 2/3/5 fora de
  escopo, item 4 limite documentado) + 4 inconsistências corrigidas.
- `docs/CONTINUIDADE.md`: header/HEADs/objetivo/próxima ação sincronizados.
- Nenhuma lógica de produto tocada (escopo: só plano + CONTINUIDADE).
- Próximo: commit local (sem push); depois investigar `selection_context`
  16 + índices `[N]` fora da base, sem flexibilizar.

## 2026-10-31 — Sessão 8: consultado/mencionado + inferência + fato usuário + janela (fixer, TDD)

- RED: `tests/test_consultado_inferencia_usuario_janela.py` novo (13 testes,
  genérico sem nomes de produto) falhou 11/13 no caminho real
  (check_support/verify_support/diagnose + citation_audit + renderer).
- GREEN (escopo: verification_report.py, report_renderer.py,
  scripts/citation_audit.py, tools/diagnose_run.py + testes focados):
  1) Consultado vs mencionado: normalize com aspas curvas, classify com
     npx/in_code (in_code nunca é consulta), `_rewrite_refs` não registra
     outside quando preserva literal, `verify_support` exclui linhas de nota
     própria e só evidence pondera unknown.
  2) Inferência por premissas: âncora E relação auditadas separadamente;
     INFERÊNCIA vira declared-inference (nunca supported por âncora); exige
     citação de interoperabilidade (doc com ≥2 entidades quando a frase
     nomeia ≥2), senão LACUNA explícita (complementaridade plausível vs
     integração testada).
  3) Fato usuário: `_corpus` (verify + renderer) exclui user://; citável como
     premissa explícita sem número, nunca LACUNA automática (isenta gate de
     versão do contexto); gate separado tag exata vs família funcional,
     conclusões separadas.
  4) Janela: síntese cita janela (writer_included_urls/chars/cuts +
     selection_hashes), LACUNA com escopo janela vs global
     (declared[].scope), auditoria na mesma janela ou diff
     excerto×full-text antes de "só links" (excerpt_vs_fulltext).
- Contratos antigos atualizados (nova semântica, sem flexibilizar):
  `test_support_check` (gate família + inferência declarada),
  `test_product_core` (evidence markdown para falha fora do corpus),
  `test_report_refs` (literal preservada fora de outside),
  `test_calibration` (versão exata). `test_yt_enrich_fix` falha pré-existente
  por `gpt_researcher` ausente (ambiente, sem relação).
- Foco fresco (`-p no:cacheprovider`): 137 passed, 6 skipped, EXIT=0
  (consultado/inferência/usuário/janela + s2 + lacuna + granularidade +
  accept19 + produto + pool + monopólio + diagnose + refs + calibração +
  síntese + gap). Suite ampla (sem 4 arquivos de config): 508 passed,
  15 skipped, 1 falha pré-existente ambiente.
- Efeito isolado em CÓPIA (`/tmp/opencode/accept22-copy/`, original intacto
  md5 igual): antes verification failed unknown 5 + corpus 30 + diagnose
  65/9; depois verification failed unknown [] (evidence 0, utility ignorada)
  + corpus 29 (sem user://) + diagnose 66/8 + check 54/70 ok com 4 lacunas,
  2 inferências declaradas, 1 premissa usuário; audit_window com
  writer_included_urls (7) + excerpt_vs_fulltext. RA8 segue PENDENTE
  (failed honesto por 3 inferências sem suporte semântico [12,13,14]).
- Próximo: commit local sem push; depois investigar selection_context 16
  residual, sem flexibilizar.

## 2026-10-31 — Sessão 9: run accept23 sob 49508fe + relatório + plano (fixer, lane isolado)

- Congelado HEAD `49508fe` + `git diff --stat` (vazio; só untracked
  `.planning/.active_plan` pré-existente) + sha256 de 8 arquivos produto
  (`hashes.frozen`) em `/home/thomaskyn/hermes-runs/accept23/*.frozen`.
  Hashes reconferidos após o run (`sha256sum -c` 8/8 OK) — sem edição
  produto no run. `adaptive_coordinator.py` igual ao frozen accept21/22.
- Entrada do experimento: `installed_opencode_version=2.1.4` (contexto);
  instalada real `opencode v2.2.5` registrada à parte (sem presumir).
- Infra medida (curl curto, pré E pós-run): vast :8001 DOWN (000, sem
  processos, nada subido on-demand); SearXNG DOWN (localhost + bridge
  `172.18.0.2`); embeddings :8082 DOWN; gateway 9119 UP (302).
  Baseline restaurada por construção (nada foi ligado).
- Run real (run.sh = template accept22 com dirs accept23; medium,
  max-rounds 3, native+opencode `muse-spark-1.3-contributor`): parada
  `rounds`, **588s**, EXIT=0, 47/18/18/18, 6 síntese / 4 citados
  (counters); consumo queries 11, extractions 19, **yt_live_fetches 0**,
  model_calls 7. 55 avaliações (32 partial + 23 insufficient, 0 covered).
- **Cobertura oficial 0/55 + 0 N/A**; diagnose: ok 0, partial_legit 24,
  missing 14, assessor_error 17 (sem selection_context/synthesis_unsupported);
  síntese diagnose 49/1/66; verification-sentença 48/50 ok + 15 LACUNA +
  1 inferência declarada; **verification overall `failed`**
  (execution ok, resto partial/failed). **RA8 segue PENDENTE.**
- Causa do failed: 4 LACUNA [27,3,14,17] (handoff/local-memory) ancoradas
  em listagens — revisor reprova por menção-do-nome; assessor marca
  insufficient citando o mesmo doc (classe accept20, 17 lá e cá).
  Sem URLs nuas (classe accept19/22 ausente).
- Utilidade: **5 nomes com identidade** (lit-opencode, opencode-planner,
  Plannotator, opencode-handoff, opencode-local-memory); guia parcial
  honesto (planner único com MIT/manutenção/limitações; handoff único com
  versão explícita ≥2.1.2); combinação recusada (c12 insufficient).
- Fixes `49508fe` exercitados: inferência-contida (2× declarada, combinação
  recusada); fato-usuário contido 2º run (`user://` fora do corpus);
  janela sem divergência; monopólio/b81e8f6 sem alvo. Resíduo registrado
  sem corrigir: contador de citações cego a `([N])` (evidence/resolved 0).
- Outputs em `/home/thomaskyn/hermes-runs/accept23/` (fora do repo e do
  /tmp); `.hermes` intocado; accept22 intacto; sem push.
