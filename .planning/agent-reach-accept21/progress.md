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
