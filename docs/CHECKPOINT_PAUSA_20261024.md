# Checkpoint de pausa — 2026-10-24 ~23:45 UTC (retomada após reiniciar o opencode)

## Estado do Git (limpo)
- Branch: `feat/product-v1` @ `4be5316` (docs matrix). Árvore limpa.
- Últimos commits: `4be5316` matrix → `96b35a7` retry CLI → `d1e6a86` teste pausa real →
  `0928d5b` extração JSON → `67e1ec4`/`273f7a9` canais → `221f38f` controle+manifesto.

## Pesquisa real concluída (ponta a ponta, ambiente isolado, /tmp/hermes-real-run/)
- Pergunta: limitações de RAG adaptativo na literatura + como gpt-researcher 0.16.0 as trata.
- Plan: /tmp/hermes-real-run/plan.json (2 entidades, 3 critérios, initial_paths com canal arxiv+github).
- Runner: /tmp/hermes-real-run/run_real.py (native + `opencode/glm-5.3-flash-free`,
  max_calls=8, max_rounds=1, max_ops_per_round=2, concurrency=2).
- Resultado: STOP rounds/parcial, contadores 8/6/6/6/6/6, 7 chamadas de modelo,
  report.md 14,9K PT-BR honesto e parcial, verification.json overall partial,
  manifest.json simulated=false. Artefatos em /tmp/hermes-real-run/run/.
- Comportamento observado: arxiv OK (FAIR-RAG, EvoR etc.); github nogain honesto;
  web 2 falhas `retriever_unavailable` registradas; c-trat blocked (nada no corpus
  sobre gpt-researcher); citações só do corpus (6/6 resolvidas).
- Quota free tier: lightning/beam/flint/mimo/deepseek esgotados (429); glm funcionou.
  Retry com backoff (15s+45s) já implementado em `model_transport.opencode_client`.

## Validações verdes
- Host: suite completa 200+ testes (só erro pré-existente `test_yt_enrich_fix`, httpx ausente).
- Container (`hermes-gateway`, snapshot /tmp/core_snap3): 201 testes OK.
- Matrix: sem PENDENTE; BLOQUEADO só R3.1; PARCIAL R6.6/R14.8 (tokens unknown).

## Próximo passo (retomada)
1. `git log --oneline -3` + `git status` (esperado: limpo em 4be5316).
2. Atualizar matriz com REAL: R2.x/R4/R7/R8.7/R12/R13/R14.3 (pesquisa real-rag-001),
   §16 (acadêmica parcial honesta, divergência, entrega verificável parcial).
3. Escrever `docs/VALIDACAO_REAL_RAG_001.md` a partir de /tmp/hermes-real-run/run/
   (report.md, verification.json, manifest.json, counters.json) + Agent Reach real
   (arxiv 160k chars, repo partial/metadata, page 60k via urllib, vídeo blocked honesto).
4. Revisão final contra matriz; corrigir viáveis; commit; resumo ≤25 linhas.
5. Opcional: segunda pesquisa real com github produtivo (query refinada p/ c-trat)
   se houver quota glm; sem quota, declarar pendente.
