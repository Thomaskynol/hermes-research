# Findings — gargalos residuais pós-accept31

## Fatos (evidência)
- accept31: cobertura 1/53 + 2 N/A = partial; overall partial (execution ok; question/review/support partial); contadores 27/25/25/25/6/9; stop `rounds` com folga (queries 10/30, extractions 40/120, model 7/16, 409s/1800s). Fontes: `diagnose_accept31.json` (buckets 29 selection_context / 11 missing / 7 assessor_error / 5 partial_legit / 1 ok, total 55), `adaptive_accept31/report.md:5-9,383-402`, `verification.json:19-23`.
- accept30 contraste: 0/55, overall failed, buckets 32 selection_context / 10 missing / 13 partial (total 55).
- Mecanismos (adaptive_coordinator.py): `make_model_assessor(max_docs=24, excerpt_chars=1200, json_budget=12000)` l.2810; tiers ordenados l.2980–3047 (reserva entidade → prior_refs → resend_open M1 → sem_order about_open → resto → prior_ref_closed → sent); corte JSON l.3151–3154 (~8 blobs/chamada); `_resend_for_open_cells` l.2655 (1/célula, identidade + termo dimensão ≤1500 chars da menção, par url×célula nunca exibido); `_relevant_excerpt` l.892 (janela global + groups round-robin + entity pin, limite único 1200); `_rank_unfetched` l.2014 (só tokens da URL); `proportional_max_rounds` l.465 + `_maybe_adopt_proportional_rounds` l.497 (M3/M5 re-adoção na expansão; by_cells 15→2 inicial, 55→7 nunca adotado no run accept31 porque M5 é pós-run).
- Preservar (comprovado): M1 quarentena+trilha, M2 pin-conta-turno, M3/M5 proporcional, M4 rodízio gap_query, G5 candidatas/plataforma, G6 reserva, N/A delimitado, identidade universal, oráculo condicional, 633 testes OK pós-M5, diagnose congelado inalterado.

## Hipótese de trabalho (Phase 3)
Doc certo para a célula aberta é reenviado, mas o excerto de 1200 chars escolhe a janela pelo ranking global e a passagem de sustentação (termo da dimensão daquela célula + menção da entidade) não chega ao assessor → `selection_context` persiste e `overlap<0.35` reprova na síntese. Teste RED deve demonstrar exatamente isso antes de qualquer fix.

## O que NÃO fazer
- Aumentar tetos (JSON/docs/chamadas) ou afrouxar overlap/identidade/N-A/inferência/user-corpus.
- Hardcode de plugin/fonte/resposta; alterar denominador; edição manual de relatório como "correção".

## Resultados (pós-fix, runs reais)
- accept32 (HEAD 9c311ad): 0/56 partial; missing=20, selection_context=18, assessor_error=16, partial=2, ok=0. Resend-focus reduziu selection_context (29→18).
- Causa-raiz hook M5: `new_state` inicializa stop={reason:None}/report={} nunca-None → guarda sempre-True pós-início; base v1 (0 cells) silenciosa. Testes usavam state manual (mock-behavior gap).
- accept33 (HEAD 4615ccb, guarda por decisão real + trace note): ADOTADO 3→7 em produção, 8 rounds; missing=14, sel_ctx=31, assessor=0, partial=10, ok=1 (1/56); síntese 47/4/119; overall failed (support: 4 LACUNA sem literal).
- Residual: largura de seleção por lote (12k) + by_model=by_cells=7; 16 lacunas abertas com folga total. Detalhe em docs/RELATORIO_TECNICO_MISSAO_GARGALOS_POS31.md.
