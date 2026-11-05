# Corretiva accept43 — sustentação/avaliação/claim3 (mecanismo geral)

Missão: corrigir em mecanismo geral os 4 itens da reconciliação accept43
sobre o corpus congelado b671207, sem nova coleta, sem aumentar limites,
preservando originais e votos. Branch `feat/product-v1`, sem push.

## Causa-raiz e correção (1 por causa, TDD red→green)

| Item | Causa confirmada no código | Mudança | Arquivo:linha |
|---|---|---|---|
| §1 rescope | `_rescope_cells_to_excerpts` copiava a sentença-limite multi-entidade por eid (`for _lb,_eid in named`, mesma `_u`) e filtrava refs p/ só covering → célula uni-entidade publicava frase de 3 entidades com 1 ref | `_rescope_sentence_to_entity`: reescreve ao escopo uni-entidade (cláusula do alvo com marcador de limite, ordinal resolvido pela posição textual entre candidatos exigidos não-contexto, cabeça multi-entidade e cauda comparativa descartadas); sem cláusula honesta, desiste do alvo em vez de copiar | `adaptive_coordinator.py:8590` (`_rescope_ordinal_order`), `:8642` (rewrite), `:8893` (integração) |
| §1/§3 fora-da-janela | `_template_section` propagava refs verbatim (`_refs` sem `included_urls`); [2][4][37][39] citados como excertos | `_refs` com `included` opcional: ref fora de `included_urls` rende `[N] (fora dos excertos)`; matriz passa a seleção vigente; comportamento antigo intacto quando `included=None` | `report_renderer.py:502`, `:1703` |
| §1 notas | `_pair_reconciliation_notes` e notas coberto×LACUNA sem identidade da síntese reconciliada (pareciam pendência atual em replay) | Carimbo `(síntese {sha12})` nas duas notas = alcance histórico declarado; contratos dos testes preservados | `report_renderer.py:1781`, `:1862`, `:1266` |
| §2 numérico+LACUNA | Ramo inferência exigia 2 entidades no mesmo doc (`_audit_inference`); `_is_user_premise` recusava isenção sob marcador de inferência; detector LACUNA não cobria o molde "nos excertos… não estabelece/sem trecho/sem fonte" | Detector + `premissa controlada/contexto` como marcadores; gate de versão no ramo LACUNA isenta só a tag exata adjacente (≤40 chars) ao marcador, sob comparação numérica; demais tags seguem exigidas no citado | `verification_report.py:205`, `:853`, `:1440` |
| §2 [13] falso-negativo | `_strict` só forma cheia decorada (nunca casa a prosa sem "erskingardner") → `named` frouxo armava trava interop via entidade espúria + fallback `entidade não mencionada` + teto polaridade | `_strict` aceita base inequívoca (regra já vigente em `named_selected`/`strict_named_in_sentence`); fronteira composta vale p/ a forma que casou (homônimo segue rejeitado) | `verification_report.py:1280` |
| §2 ponte PT→EN | Gate lexical sem cognatos de escopo ("plano/visual/detalhada/equivalente/profundidade" × "plan/visual/detailed/equivalent/depth") | 5 cognatos indisputáveis em `_PT_EN_SUPPORT` (só recall, denominador intacto) | `verification_report.py:125` |
| §4 fusão | `_select_evidence` ancorava por menção solta/overlap (`p in txt`, `hits>=2`, tokens distintivos) → LACUNA isolada do marketplace julgada contra evidência fundida (marketplace+config-pack) | Frase de ausência: âncoras restritas aos docs do próprio pacote (`_is_package_doc`); sem doc próprio, cai em sem-evidência (gap), nunca em pacote alheio | `semantic_review.py:460`, `:1026` |

Exemplo real (congelado b671207, só leitura):
in: "INFERÊNCIA de sobreposição parcial em revisão entre OpenCode Code
Review, Plannotator e Octto, porque o primeiro … ([13]) e o segundo …
([34]), enquanto o terceiro tem apenas revisão visual de plano … ([20]),
por isso não afirmar …" →
out: "Octto tem apenas revisão visual de plano demonstrada nos excertos
enviados e sem base equivalente de code review detalhada ([20])".

Controles que continuam rejeitando (regressões verdes no mesmo arquivo de
teste): tag inventada sem premissa, atribuição a doc estrangeiro, homônimo
(`Widget Alpha` × `Alphabeta`), integração sem doc-interop.

## Validação (código atual; passe attempt 2 em `runs/accept43-corretiva-attempt2/`,
passe anterior em `runs/accept43-corretiva-fix1/`)

- Regressões `tests/test_accept43_corretiva_sustentacao.py` (23 testes: T1–T4 +
  remediação attempt 1 + attempt 2): red no baseline anterior ao passe
  (falhas pelos motivos esperados) → green pós-fix.
- Suíte: 910 testes, OK, 10 skips, exit 0 (`runs/accept43-corretiva-attempt2/suite.log`;
  passe anterior: 895 em `runs/accept43-corretiva-fix1/suite-final.log`). Offline
  runner: exit 0 (`runs/accept43-corretiva-attempt2/offline.log`).
- Replay zero-live (script `reproduce_frozen_report.py` sem `--model`,
  exit 0, `runs/accept43-corretiva-attempt2/replay-run.log`): síntese histórica
  reprocessada; rescope/renderer/verificação com o código novo; review `not_run`
  (sem novos votos — claim 3 2–1 preservado, sem reversão); overall `partial`
  (b671207 era `failed` pelo voto claim 3 não re-elicitado aqui). Matriz com 10×
  `(fora dos excertos)`; notas com linha de alcance da síntese. Leitura como
  usuário: células uni-entidade, alcances explícitos, sem prometer integração.
- Checagem congelada `runs/accept43-corretiva-attempt2/frozen-check.log`
  (só leitura do `reproduction-b671207-replay/`, sem rede/modelo, re-executada
  após cada mudança deste passe): [13]-positivo → supported sem unsupported
  (era `entidade não mencionada`); numérica+LACUNA jira → supported+declared
  (era interop unsupported); anchors claim3 só marketplace; rewrite uni-entidade
  sobre a sentença real.
- 4 unsupported residuais do replay reauditados contra o código `b671207`
  intacto em /tmp: vereditos idênticos (2 `sem sobreposição` por recall de
  overlap PT×EN, 2 complementaridade sem doc-interop) — pré-existentes, sem
  regressão.

## Cobertura dos 10 do attempt 1 (IDs por arquivo:linha + estado)

O gate attempt 1 citou 10 (2🔴+7🟡+1❓), todos com file:line — a linha
`tests:78/208` fundia 2 achados distintos numa linha, daí a conta aparente
8+2. Attempt 2 confirmou 2🔴+4🟡 resolvidos; os refinamentos viraram o lote
attempt 2. Nenhum pendente de mapeamento.

| ID | Achado attempt 1 | Estado |
|---|---|---|
| `ac:8895` 🔴 | None do rescope mantinha covered | Resolvido (attempt 1; parcial com alcance) |
| `sr:1026` 🔴 | Ausência sem doc próprio fundia | Resolvido (attempt 1; anchors zerados) + fronteira em `_is_package_doc` (attempt 2 item 1) |
| `sr:460`+`vr:853` 🟡 | Moldes nus desviavam prosa | Resolvido (attempt 1, condicionados) + refinado mesma-oração (attempt 2 item 2) |
| `vr:1409` 🟡 | Premissa frouxa 2-tokens | Resolvido (attempt 1, `_strict_doc`) + refinado veto monorepo (attempt 2 item 4) |
| `vr:125` 🟡 | Cognatos só-recall | Resolvido (attempt 1, veto positivo) + refinado veto monorepo (attempt 2 item 4); gate direto revertido p/ calibração |
| `rr:1781` 🟡 | Sha inline quebrava dedup/compare | Resolvido (attempt 1→2: linha separada, texto estável) |
| `tests:78` 🟡 | Cobertura ordinal/textual/None | Resolvido (guards + red→green no mesmo arquivo) |
| `tests:208` 🟡 | Cobertura T4 + negativos homônimo/multi-doc | Resolvido (guards + red→green no mesmo arquivo) |
| `docs:55` ❓ | Critério [2] fora de `included_urls` | Resolvido na publicação (tabela acima); promoção pendente (sem re-rank) |

Risco residual aceito pelo orquestrador — `vr:1569` mesma-oração: a isenção
marca todas as versões exatas da oração com marcador+comparação; oração única
com 2.1.4 válido + versão inventada isentaria ambas. ACEITO com critério:
estreitar p/ versão adjacente ao marcador arriscaria falso unsupported em
frases válidas multi-versão (padrão T2a), e o caso exige versão inventada
dividindo a oração com comparação numérica válida (probabilidade baixa;
revisitar se observado em run real).

## Remediação do gate reviewer (attempt 2)

| Achado | Correção (1 por causa) | Arquivo:linha | Teste |
|---|---|---|---|
| (1) substring em URL | `_pkg_url_hit` com fronteira alfanumérica (6 checks `in` → 1 helper) | `semantic_review.py:_is_package_doc` | `test_package_doc_match_rejects_longer_sibling_slug` |
| (2) coocorrência em frase inteira | Molde+alcance na mesma oração (`_clauses_of`; ponto nunca separa versão) | `verification_report.py:_CLAUSE_SPLIT_RE` + `is_lacuna_declaration` | `test_window_cooccurrence_requires_same_clause` |
| (3) `demonstrad` divergente | Template também ausência no semantic (direção forçada por `test_sem_dimensao_demonstrada`, contrato aprovado) | `semantic_review.py:_ABSENCE_WRITER_TEMPLATE_RE` | `test_demonstrada_template_aligned_across_gates` |
| (4) veto veta monorepo | Pula veto quando `cur == _own`; repo próprio sem nomeação vale frouxa S2 | `verification_report.py:_strict_doc`, `_vetoed_mention` | `test_monorepo_sibling_doc_is_not_vetoed` (LACUNA + positiva) |
| (5) janela 40 chars | Isenção só p/ valor com ocorrência em oração com marcador E comparação numérica | `verification_report.py` gate LACUNA | `test_second_unrelated_version_not_exempted` |
| (6) contagem 895 vs 905 | Atualizado: 910 + logs | técnico § Validação | — |
| (7) tabela 6/10 | Cobertura acima (8 IDs + 2 declarados não-recuperáveis) | técnico | — |

## Remediação do gate reviewer (attempt 1) + aceite [2] (histórico)

| Achado | Correção (1 por causa) | Arquivo:linha | Teste |
|---|---|---|---|
| 🔴 None mantinha covered | Sem reescrita segura → partial com alcance (refs só excertos), nunca covered | `adaptive_coordinator.py:8895` | `test_multi_entity_without_safe_rewrite_falls_to_partial` (red `'covered' != 'partial'` → green) |
| 🔴 ausência sem doc próprio fundia | Ausência + `_own` vazio → anchors zerados (gap); price-fallback desligado p/ ausência | `semantic_review.py:1021` | `test_absence_without_own_doc_yields_no_anchors` |
| 🟡 moldes nus desviavam prosa | `sem fonte/trecho`, `não estabelece` só com coocorrência lacuna/excertos ou marca líder | `verification_report.py:is_lacuna_declaration`, `semantic_review.py:_is_absence_claim` | `test_bare_window_mold_without_lacuna_context_is_not_absence` + positivo-2-pacotes preservado |
| 🟡 premissa frouxa (2 tokens) | `_strict_doc`: estrita ou link próprio; veto a doc de outro dono no plano; posse indecidida mantém S2 | `verification_report.py:_strict_doc` + ramo LACUNA | `test_lacuna_premise_rejects_foreign_doc_sharing_two_tokens` |
| 🟡 cognatos só-recall | Revertido gate direto (quebrava calibração `test_parafrase_pt_en_sustenta`, contrato accept15 aprovado); remédio aplicado: veto a doc de outro dono no ramo positivo + negativo com plano não-relacionado | `verification_report.py:_vetoed_mention` no call positivo | `test_cognate_overlap_does_not_borrow_foreign_doc` |
| 🟡 sha inline quebrava dedup/compare | Texto da nota estável; alcance em linha separada (`... referem-se à síntese {sha12} ...`, fonte `synthesis_sha` carimbada cedo no `render_report`, idempotente) | `report_renderer.py:notas §5` | `test_reconciliation_notes_carry_separate_synthesis_scope` |
| Cobertura pedida | Ordinal trocado, ordem textual vs plano, None seguro, 2-pacotes→ambos, homônimo | mesmo arquivo de testes | 3 guards verdes-antes declarados; demais red→green |

Regressões achadas pela suíte durante o passe (2, ambas revertidas para o
contrato aprovado antes de prosseguir): gate direto quebrava
`test_parafrase_pt_en_sustenta` (ponte PT→EN é calibração accept15, recall
aprovado); premissa estrita pura quebrava
`test_lacuna_citing_entity_doc_is_sustained` (S2: menção frouxa vale com
posse indecidida) — solução: veto só a dono estrangeiro decidível.

Critério de aceite **[2] fora de `included_urls`: RESOLVIDO no nível
publicação** — cadeia mapeada: obtido ✓ (blog do autor, substantivo) →
avaliado ✓ (votos divididos) → ledger retido ✓ (refs da avaliação
preservadas) → publicado com alcance marcado ✓ (`[N] (fora dos excertos)`,
10× no replay) em vez de excerto nu ou apagamento. Polaridade espúria:
desarmada pela nomeação estrita (teto exige `len(named)>=2` estrito).
Perda de sinal diff-UI: parcial alternativo vive nas refs marcadas da
célula, não apagado. **Pendente (fora dos limites: sem re-rank):**
promoção de [2] p/ `included_urls` dentro do teto.

## Residuais (fora desta correção)
- Seleção não re-ranqueada p/ docs pertinentes dentro do teto (ex.: [2] segue
  fora de `included_urls` quando o teto corta; publicado agora com alcance
  marcado, sinal preservado, sem elevar limites).
- "Não verificado nos excertos" não é marcador LACUNA (fora do molde coberto).
- Revisão semântica segue com escopo = síntese (`audited_sha=synthesis`,
  declarado no `verification.json`); review do Markdown é a dimensão suporte.
- Taxonomia de 5 níveis de evidência não criada como abstração nova: coberta
  pelos estados existentes (covered/partial/insufficient + excerpt-scope +
  marca fora-dos-excertos).
