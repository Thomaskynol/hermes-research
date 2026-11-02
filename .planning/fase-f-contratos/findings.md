# Achados Fase F (lanes 2026-11-03, refs: ses_e64f44d90ffeebY6qibWbe0vEE / ses_e64f44d8affeZNMnZLfuZJ3dJ4 / ses_e64f44d7fffe0aJpc3BI7BZWXu / ses_e64f44d7fffdg6sZ70GkHtTZBg)

## C1 — planejador→assessor (causa: auto-plan + validate fail-open)
- `adaptive_planner.build_plan_prompt:68-128` nunca pede `description`; todos os 15
  critérios v1→v19 do accept35 são label-only. `validate_plan` (ledger:95-139) não
  exige definition → fail-open. Assessor recebe só label (`assess` prompt :3567) e
  recusa corretamente ("Definição não fornecida" é output do modelo, 12 evals).
- Fix: (A) fail-closed em `validate_plan` (definition não-vazia p/ obrigatório) +
  (B) planejador produz 1–2 frases operacionais por critério (o que conta como
  evidência), validando presença+qualidade mínima antes de adotar.
- Repro em cópia: `valid-fase-f/c1-repro/state.json` (receita no lane C1).

## C2 — corpus→seleção→relatório (causa: seleção-do-writer vs corpus + piso viciado)
- Entidade `opencode-review-sun-praise`: source_url sun-praise obtida 05:41, usable
  2914/2914, nunca excluída; `_identity_matches` casa forma-cheia. Status "fora do
  corpus" veio de janela errada: writer viu só 6 `included_urls` (sun-praise fora);
  piso `_key=(ref_count,is_source)` (coordinator:3861) preferiu listing (awesome=4)
  à fonte própria (sun-praise=2, evals nunca a citaram); writer afirmou ausência
  sobre corpus integral; renderer numerou como [12].
- Fix: status em 4 estágios (obtida-usable/examinada-assessor/incluída-writer/
  analisada-célula); piso com prioridade absoluta a `source_url`; status usa corpo
  qualificado; veto no renderer: `fora do corpus` proibido quando
  `_entity_corpus_docs≠∅` (reescrever p/ `fora da seleção, LACUNA de análise` +
  ler-a-seguir); verificação falha em §0-ausência × §7-usable contraditórios.
- Peers [20]: mesmo bug de janela; card-em-listing (não doc dedicado) — considerar
  distinção dedicado-vs-listing.

## C3 — descoberta→finalistas (causa: `_old_ok` sem comparação)
- `_old_ok` (:5337): 1 partial qualquer (mesmo fraco) ou 1 eval com ref ⇒ False;
  partial-holders imutáveis; `_weak` só registra unexplored; order por id; sem
  comparação old-vs-novo. Writer carimba "conjunto exigido ... sem substituição"
  (indevido: pergunta pede descobrir-e-comparar; distinguir `user_context.targets`
  de seleção do processo).
- Fix: troca sse (a) novo tem ≥1 covered (ou ≥2 partial) com ref própria; (b)
  dominância estrita nos essenciais; (c) reason com tabela old-vs-novo; empate →
  mantém + unexplored; histerese (fingerprint, sem reversão por K rounds salvo nova
  evidência); ordenação por (delta_covered,delta_partial,id); 1 troca/chamada.
- Testes existentes a preservar: test_na_swap_reading:196/220, accept19:266, accept28:111.

## C4 — síntese→avaliação + relatório (causa: sem guidance + sem reconciliação + vazamentos)
- Assessor (prompt :3564) nada sabe de INFERÊNCIA marcada; c12/c13 globais avaliados
  1× no round 0; `_assess_synthesis_criteria` (:7034) só reavalia `synthesis:true`
  (só c15); ledger aceitaria partial com [10][11][8] (usáveis) se emitido.
- Verifier tem canal `partial_declared` (anchor_ok) mas `_finalize` diz "audit only,
  never touches question coverage" — reconciliação inexistente. Bônus: 2 INFERs §10
  caíram em `relation_ok True` (falso-positivo `_entity_mentioned` por tokens
  compartilhados); 3ª nem auditada (split/renumeração).
- Fix: (i) guidance do assessor espelhando complementarity (marcada+≥2
  premise-docs ⇒ partial; sem interop = LACUNA p/ integração, preserva partial);
  (ii) passo pós-audit em `_finalize` promovendo `partial_declared` a partial no
  ledger com refs premise-docs; nunca covered.
- Gerador (sem edição manual): gate de frase completa (nunca mid-word; completar/
  omitir/marcar); dedup em `_record_unexplored` + `_unexp_s`; estender
  `_DEBUG_NOTE_PREFIXES` (downgrade/not_applicable/identity-mismatch) + gate de
  idioma p/ anexo; paráfrase user-facing do scope; colapsar `discovery:` e
  `Alcance examinado` idênticos (1× + delta); corte em fronteira de frase (renderer:369).
