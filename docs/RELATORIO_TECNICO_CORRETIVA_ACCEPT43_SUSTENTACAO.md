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

## Validação (código atual, evidência em `runs/accept43-corretiva-fix1/`)

- Regressões `tests/test_accept43_corretiva_sustentacao.py` (T1–T4, 8 testes):
  red no código pré-fix (6 falhas pelos motivos esperados, log `red-T1-T4.log`,
  exit 1) → green pós-fix (8/8, sem enfraquecer os 2 controles negativos).
- Suíte: 895 testes, OK, 10 skips, exit 0 (`suite-final.log`). Offline runner:
  exit 0 (`offline-2.log`).
- Replay zero-live `replay/` (script `reproduce_frozen_report.py` sem `--model`,
  exit 0, `replay-run.log`): síntese histórica reprocessada; rescope/renderer/
  verificação com o código novo; review `not_run` (sem novos votos — claim 3
  2–1 preservado, sem reversão); overall `partial` (b671207 era `failed` pelo
  voto claim 3 não re-elicitado aqui). Matriz com 10× `(fora dos excertos)`;
  notas com carimbo de síntese. Leitura como usuário: células uni-entidade,
  alcances explícitos, sem prometer integração.
- Checagem congelada `frozen-b671207-check.log` (só leitura do
  `reproduction-b671207-replay/`, sem rede/modelo): [13]-positivo → supported
  sem unsupported (era `entidade não mencionada`); numérica+LACUNA jira →
  supported+declared (era interop unsupported); anchors claim3 só marketplace;
  rewrite acima sobre a sentença real.
- 4 unsupported residuais do replay reauditados contra o código `b671207`
  intacto em /tmp: vereditos idênticos (2 `sem sobreposição` por recall de
  overlap PT×EN, 2 complementaridade sem doc-interop) — pré-existentes, sem
  regressão.

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
