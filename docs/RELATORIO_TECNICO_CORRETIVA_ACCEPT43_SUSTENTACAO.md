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

## Attempt 3 — vr:1569 fechado + propagação total (produto `47f4fe7`)

Proveniência (replay determinístico, sem `--model`, exit 0):
`runs/accept43-corretiva-attempt3/replay/` — `code_head=47f4fe7`,
`synthesis_sha=790a9a06ba346b81` (histórico accept43),
`rendered_sha=5265f941bf85bdf4`, seleção =
[OpenCode Code Review (erskingardner), opencode-jira,
opencode-marketplace, Plannotator, Octto],
`included_urls` 6 URLs (teto 12000 chars) =
`[13]` erskingardner, `[32]` opencode.im/plugins, `[17]` marketplace,
`[42]` yodev, `[34]` plannotator.ai, `[27]` opencode.ai docs-pt.
Correspondência: fix1 (`runs/accept43-corretiva-fix1/replay/`,
`rendered 2ccd71921fa467a2`, `code_head ced8afb` pré-corretiva,
`audited 790a9a06ba346b81`) == relatório externo;
attempt2 (`runs/accept43-corretiva-attempt2/replay/`,
`rendered e8e741755b151af8`, `code_head d13b9ae`) == atual-parcial
pós-corretiva sem os 2 fechamentos deste passe;
attempt3 == produto atual com os 2 fechamentos.
`module_hashes_unchanged=True`, `original_unchanged=True`
(congelado intacto, sem nova coleta).

Seleção/evidência (mesma seleção, todas superfícies):
matriz + Achados §3 + recomendação qualificam `[19]`/`[4]`
(e `[39]`/`[37]`/outros fora) como `[N] (fora dos excertos)` —
30× no attempt3 vs 10× no attempt2 (só matriz).
Causa: `_refs` sem `included_urls` em Achados, recomendação-fallback
e critérios globais; fix passa `included_urls` nesses 3 pontos
(`report_renderer.py` Achados/recomendação/global).
`39/42` (síntese histórica §1: excertos do plano original) vs
`0/13`/`0/42` (§2/§3 recomputado frozen: 12000 chars de 4369084,
6 docs de 42 no teto atual) = snapshot histórico vs recomputado
frozen, não zero histórico; síntese histórica identificada como
artefato histórico (`REPRODUÇÃO — corpus congelado`,
`synthesis_sha` carimbado); relatório atual corresponde ao estado
final selecionado (refs do escopo vigente).
2 inferências marketplace×Plannotator `[17][34]` e
marketplace×GitHub Workflow Agent `[17][42]` permanecem
`declared_inference` partial com limites (nunca
supported/integração testada) — correto.

Fonte `[2]` aproveitada-na-publicação, refutada p/ promoção:
blog `https://blog.vtemian.com/project/octto/`
(doc_hash `60fc4f4c56f66752`, 19745 chars) declara
"Code Review: Side-by-side diffs" (baseline `ref-2.txt:1-3`,
`source-2.txt:3`) no contexto "14 Rich Input Types …
Decision Controls … Code Review …" = tipo de widget de input
(`show_options`/`show_diff`/`ask_code`), não fluxo de revisão
de código (sem PR, sem review linha-a-linha, sem blame/threshold).
`[20]` repo confirma: só "Review the final plan visually" +
"show_diff | Side-by-side code diff" (`model-09-prompt e5/e16`)
como input-type, não revisão. Insuficiência concreta:
trocar `[4]`/`[19]` por `[2]` em `included_urls` dentro do teto
exigiria re-rank humano arbitrário (sem ganho de veredito:
Octto revisão seguiria insuficiente — widget ≠ revisão) e nova
síntese por chamada nova sem necessidade; sem aumentar teto/coleta,
decisão rastreável: manter `[2]` fora com alcance marcado
(`[2]` obtido/avaliado/ledger-retido, 19745 chars usable §7),
sinal diff-UI preservado nas refs marcadas, sem `covered` por
decreto, sem abstração 5-níveis.

Verificador `vr:1569` FECHADO (era risco residual aceito):
isenção mesma-oração alcançava inventada vizinha.
Causa: `_premise_ok` marcava qualquer versão na oração com
marcador+comparação. Fix: exigir adjacência ao marcador
(≤40 chars, mesma oração via `_CLAUSE_SPLIT_RE`, qualquer
ocorrência vale p/ o tipo — T2a preservado) + só
`_USER_CONTEXT_MARKERS` (sem isenções por INFERÊNCIA/LACUNA/
negação). Controles: inventada vizinha, homônimo
`Alpha×Alphabeta`, doc outro projeto, funcionalidade inventada
rejeitam; tag inventada/doc estrangeiro/homônimo/interop-sem-doc
continuam rejeitando (`tests/test_accept43_corretiva_attempt3.py`
6 testes red→green + 23 existentes verdes).

Claim 3 — investigação conferível (sem revisar 53 claims):
texto integral id 3 =
"- opencode-marketplace: LACUNA nos excertos enviados para planejamento,
o excerto trata de instalação de plugins e não estabelece recurso de
planejamento (https://github.com/nikiforovall/opencode-marketplace)."
Origem: síntese `c3700bb`-live reaplicada frozen em
`reproduction-b671207-replay/state.json`; docs/trechos `e62-e136`
fundiam `e62-e96` marketplace real (install/update/list, sem
planejamento) + `e97-e136` config-pack alienígena
(`fmnapoli/opencode-config-pack`: `jira-feature-planner`/OpenSpec,
outro mantenedor). Votos: `model-04` gap vazio (sem correção) vs
`model-07`/`model-10` unsupported anti-fusão ("usar somente e62-e96",
"remover e97-e136 … pacotes distintos não podem ser fundidos").
Publicado vs registros: célula marketplace-planejamento LACUNA
correta contra `e62-e96`; correção dos votos aponta contaminação
do pacote de evidência, não erro da LACUNA. Conclusão: erro de
empacotamento por entidade + contexto inadequado; auditor aplica
anti-fusão corretamente (`_is_package_doc` fronteira +
`_select_evidence` só docs do próprio pacote; sem doc próprio →
gap, nunca pacote alheio). Caminho exercitado com contexto
corrigido (`frozen-check.log`: `CLAIM3-ANCHORS` só marketplace,
`marketplace=True`); chamadas novas só onde prompt/contexto mudou
(nenhuma neste passe — seleção/contexto claim3 idênticos;
correspondência `module_hashes_unchanged`/`original_unchanged`,
prompts byte-idênticos); reuso idêntico demonstrado; quórum/critérios
preservados; 2–1 preservado sem reversão.

Validação attempt3 (lida como usuário, não só hash/contagem):
`red.log` (3 falhas esperadas no baseline HEAD: vizinha mesma-oração,
recomendação/Achados nus) → green pós-fix (6/6);
`tests/test_accept43_corretiva_attempt3.py` + `test_accept43_corretiva_sustentacao.py`
29 OK; suíte 916 OK/10 skips exit 0; offline 11/11 exit 0;
`frozen-check.log` (rescope rewrite uni-entidade, `[13]` supported,
numérica+LACUNA supported+declared, anchors claim3 só marketplace);
replay zero-live exit 0 overall `partial` (review `not_run`,
claim 3 2–1 preservado); leitura: síntese histórica com alcance
declarado, matriz/Achados/recomendação com `[N] (fora dos excertos)`,
INFERÊNCIAs com limites sem prometer integração, LACUNAs de
compatibilidade 2.1.4 explícitas, fontes §7 íntegras.

Addendum reviewer-confirmado (produto `c1d507f`): fallback `_rf` rendia
refs nuas quando justifications vazias (ramo details já qualificava via
`_refs`). Fix mínimo em mecanismo geral: `refs` guarda `(num,key)` e `_rf`
aplica a mesma qualificação com `included_urls` (`_inc_f`); `included=None`
ou dentro permanece nu (`report_renderer.py:1614`,`:1652`; teste
`test_recommendation_fallback_rf_marks_outside_when_details_empty`
red→green: `fontes [2]` nu no baseline → `[2] (fora dos excertos)` pós-fix,
`[1]` interno segue nu). Re-rodado: focados 30 OK (7 attempt3 + 23
sustentação), suíte 917 OK/10 skips, offline 11/11, frozen-check OK,
replay zero-live novo `code_head=c1d507f`,
`rendered_sha=fb2319bdc8899e01` (anterior `5265f941bf85bdf4`;
diff só timestamps de geração — conteúdo idêntico, 30× fora-dos-excertos,
releitura do trecho confirma qualificação); `synthesis_sha` inalterado
`790a9a06ba346b81`; correspondência fix1==externo / attempt2==atual-parcial
mantida.

## Attempt 4 — síntese nova + revisão nova pelo caminho do produto (`10cb10d` + lane-1)

Proveniência (replay + live, corpus congelado attempt3, sem nova coleta):
fonte `runs/accept43-corretiva-attempt3/replay/` (só leitura; seleção 5
nomes, `included_urls` 6, `synthesis_sha=790a9a06ba346b81` histórico);
destino exclusivo `runs/accept43-corretiva-attempt4/` (`frozen-baseline/`
+ `live/` + `RELATORIO_VALIDACAO.md` + `REVISAO_ACCEPT43_ATTEMPT4.zip`).
`code_head=10cb10d` + diff lane-1 (sem reedição). Assessor 0 chamadas
novas (81 herdadas revalidadas — sem fonte de replay byte-idêntica p/
este corpus); writer 1 reaplicado byte-idêntico (md5 `7f4a049d…`,
`audited_sha=9dd8f0b7b7f05258` ≠ histórico — síntese inédita); auditoria
9 lotes live (`model-02..10`, `opencode-go/muse-spark-1.3-contributor`,
10/10 `returned` no passe final; tentativas intermediárias falharam por
causas registradas — processo morto, `writer-replay-from` com nome
errado, 2 lotes com `opencode_no_text` transiente — sem aproveitamento
parcial, sem simulação). `module_hashes_unchanged=true`,
`original_unchanged=true`, `tokens/cost=unknown`. Embeddings
desabilitados; CLI do gerador com permissões negadas.

Revisão exercitada (caminho `make_review_fn` → `semantic_review`,
quórum 3 votos, 0 falhas técnicas): 63 claims extraídos da síntese nova,
25 selecionados, 25/25 julgados — 23 sustained, 1 partial (id 39), 1
unsupported (id 0, 2–1, sem reversão). Id 5 (equivalente ao claim 3,
LACUNA marketplace-planejamento) SUSTAINED 2–1 com blocos só-marketplace
(sem `fmnapoli`, sem `jira-feature-planner`; votos sustained citam a CLI
do marketplace; gap vazio). Id 0 (seleção fundindo 5 pacotes) UNSUPPORTED
2–1: evidência anexada só code-review+marketplace; mesma doutrina
anti-fusão do claim 3 aplicada simetricamente (correção: 1 afirmação por
pacote — guia p/ writer futuro, sem mudança de produto).
`verification.json` corresponde ao relatório (`rendered_sha=16ce6771…`).

Octto sem estreitar, relações pelo tipo certo: síntese nova documenta
Octto integral (perguntas clicáveis, follow-ups, plano p/ aprovação,
fragments; compat sem versão = LACUNA 2.1.4; revisão = LACUNA
delimitada; bun test = projeto próprio). [2] só §7; [20] nu em §1
(em `included_urls`); [4] qualificado fora-dos-excertos. 5 INFERÊNCIAs
delimitadas (3 complementaridade + 2 sobreposição; suporte: "nunca
supported por âncora"); nenhuma integração testada.

Validação: focada 131 OK + ampla 920 OK/10 skips exit 0 (produto intacto
lane-1). Overall `failed` honesto. Residuais (sem mudança de produto):
escopo §2/§3 stale; 2 notas §5 ruidosas; lotes variam entre runs;
claim-0 pede guia writer; overlap PT×EN é limite conhecido (revisão
semântica sustentou 23/25).

### RETIFICAÇÃO explícita — descrição de [20] no anexo do attempt3

O `EVIDENCIAS_REVISAO.md` do attempt3, §1 ("[20] ... (dentro de
`included_urls`, única ref da célula") e §3b (`RESCOPE-REWRITE-OUT ...
([20])`), está ERRADO e fica RETIFICADO: [20]
(`https://github.com/vtemian/octto`) NÃO constava de
`writer_included_urls` do attempt3 (= `[13],[32],[17],[42],[34],[27]`);
o `([20])` citado era a saída impressa do demo `frozen-check.py`
(chamada direta a `_rescope_sentence_to_entity`), NÃO a célula publicada.
A célula real (matriz Octto/revisão, parcial) é insuficiente com [4]
(fora-dos-excertos), já qualificada pelo renderer — como a lane-1
demonstrou (`_rescope_cells_to_excerpts` só aceita refs 100% in-excerpt;
reescrita com citações removidas + refs de `covering`). Nenhum veredito
do attempt3 muda com esta retificação (a qualificação já estava correta
no artefato; o erro era só descritivo no anexo).

Residuais documentados (não corrigir neste passe):
- Tests com `make_plan` de 1 entidade cobrem o contrato, não o arranjo real
de N entidades (cobertura, não defeito de produto).
- `_CLAUSE_SPLIT_RE` sem split em ponto: cross-sentença ≤40 chars é teórico
(sem reprodução no corpus atual); split ingênuo em ponto quebraria `2.1.4`.
- Janela 40-chars não calibrada p/ aposição longa (T2a cobre caso curto; sem
caso real; calibração futura se observado).

## Attempt 5 — itens 1–4 (mecanismo geral, TDD RED→GREEN)

Proveniência (replay + live, corpus congelado attempt3, sem nova coleta):
fonte `runs/accept43-corretiva-attempt3/replay/` (só leitura);
destino exclusivo `runs/accept43-corretiva-attempt5/` (`frozen-baseline/`
+ `live/` + `RELATORIO_VALIDACAO.md` +
`REVISAO_ACCEPT43_ATTEMPT5.zip`; intermediários de transiente preservados,
varreduras superadas removidas). `code_head=5fdec47` + diff lane attempt5.
Assessor 0 chamadas novas (81 herdadas revalidadas); writer 1 nova
(síntese nova); auditoria 15 novas (5 lotes × 3 votos, 16/16 `returned`
no passe final; 1 tentativa com lote >100KB motivou fracionamento por
orçamento, 2 transientes `opencode_no_text` em tentativas intermediárias).
`module_hashes_unchanged=true`, `original_unchanged=true`.

Causa-raiz por item (1 correção por causa, 41 testes novos em
`tests/test_accept43_corretiva_attempt5.py`, todos RED antes de GREEN;
negativos conservados — 961 OK/10 skips + offline 10/10):

1. claim-0: extração fundia N pacotes num claim com anchors truncados
   ([:3]) e pacotes não detectados (Plannotator/Octto fora do `_PKG_RE`).
   FIX: decomposição interna em sub-claims single-package (sentenças de
   enumeração com URL/[n] próprio por pacote, sem verbo de relação),
   cada um com packages/anchors/evidence próprios; relação preservada
   inteira. Live: 5 sub-claims julgados por pacote (gap/partial,
   0 unsupported em seleção).
2a. `_annotate_examined_scope` idempotente congelava `0/13` pré-write.
   FIX: `force=True` pós-write e rebuilds → `6/13 (11983 chars)`.
2b. `_assess_synthesis_criteria` só agia em insufficient/uninvestigated;
   `c_combo`/`c_overlap` (não-`synthesis:true`) jamais avaliados. FIX:
   re-derivação de partial com `synthesis:<sha>` (nunca covered) +
   `_assess_delivered_relations` (inferência + limites + ≥2 premissas
   citadas, entidades exigidas, tabela/contexto excluídos como premissa,
   lookahead de limites): combo/overlap partial, docinf re-derivada.
2c. insufficient herdado vs janela do writer. FIX:
   `_reexamine_insufficient_post_write` (entidade+dimensão na janela →
   partial com refs, teto respeitado; senão "não re-examinada
   pós-write" em vez de negar; canonical fallback p/ source_url de
   docs). Live: 8 células → partial (incl. todo o eixo Octto).
2d. Notas §5 com refs representativas p/ todas as entidades + matching
   por tokens vindos de slug. FIX: `entity_evaluations[eid].references`;
   strip de URLs em `_entity_mentioned`; `_pair_reconciliation_notes`
   exige forma cheia com fronteira + máscara de homônimo (0 notas
   Alibaba neste passe); debug interno fora do corpo §5.
3. LACUNA delimitada ("nos trechos apresentados", "LACUNA para/em/de",
   "no trecho apresentado/avaliado" + ausência, "Não verificado:"
   líder) ia ao overlap (falso-negativo por construção) → canal
   declarado com premissa verificada. Positivos com overlap literal:
   pontes PT→EN (automatizada/subagentes/paralelos/agrupada/categoria/
   comandos/projeto/...) + bigrama distintivo não-título com palavra
   rara. Inferência com 2 premissas + limites nunca exige interop
   (skip do unsupported; fabricated/homônimo/foreign seguem
   rejeitados). Posse de fonte provada pela citação do próprio doc
   (veto a doc alheio). Procedência não é claim.
4. Octto: 2ª fonte admitida por gap aberto + afinidade de sítio/owner
   + dimensão (blog [2] admitido e cortado pelo teto 12000 — registrado
   em cuts; listões e fork same-slug rejeitados); corte com
   `ancora:revisao` retém show_diff/diff/syntax; e13 re-avaliado na
   nova janela (teto partial).

Revisão exercitada (25/25 quórum, 0 falhas técnicas): 15 sustained,
6 partial, 4 gap, 0 unsupported. `verification.json` corresponde
(`rendered_sha=bd9b93e3…`). Overall `partial` honesto. Residuais
documentados no RELATORIO_VALIDACAO (R1–R6): recomendação sem marca,
evidência fora da janela mostrada, abstração writer vs léxico,
versão sem premissa marcada, notas cross-dimensão, blog cortado pelo
teto, meta-linguagem pontual do modelo.
