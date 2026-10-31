# Rodada integrada de correção (produto) + run real accept18

Data: 2026-10-31. Branch `feat/product-v1`. Sem push; produção intocada;
`/home/thomaskyn/.hermes` intocado (run em `/tmp/hermes-real-run/accept18`).

Contexto: o fix de alocação (`2dc0797`) e a run accept17 estão commitados
e o resumo está em `docs/ALLOC_FIX_ACCEPT17.md`; o reinício do servidor
zerou `/tmp`, então os artefatos da accept17 se perderam (sem re-execução:
trabalho concluído). Esta rodada re-estabelece a base de evidência a
partir do repo + casos controlados novos + UMA run real nova (accept18).

## 0. Protocolo seguido

Para cada um dos 5 problemas: caso controlado antes/depois (mesmas
entradas, evidências comparáveis; RED observado antes do GREEN) + teste
de regressão. Depois, UMA run real pelo produto (mesma pergunta do
aceite em `docs/ACEITE_V1_RESULTADO.md` §1, medium, max-rounds 3,
run-id accept18, `/tmp`). Sem perseguir percentual; RA8 segue PENDENTE
salvo evidência real; sem flexibilizar sustentação.

## 1. RELEVÂNCIA/IDENTIDADE (`66255bb`)

Sintoma (accept17): PDFs cetic/saúde/tese, scribd, instagram, espelho
uptodown, open-code.ai vs opencode.ai, blogs genéricos — material alheio
qualificado como utilizável porque compartilha vocabulário genérico
("opencode", "plugin", "review") com a pergunta/alvo.

Causa: o snippet gate (`_hit_gated_by_snippet`) exigia sobreposição de
*qualquer* termo; sem noção de entidade, blog genérico e homônimo
passavam. A qualificação aceitava qualquer texto não-vazio.

Correção (só `adaptive_coordinator.py` + teste novo):
- `_entity_distinctive_tokens`: partes distintivas do nome (label+id,
  >=4 chars, menos conjunto genérico compartilhado — sem nomes de
  caso). Sem parte distintiva, ou op sem entidade: gate legado
  bit-idêntico.
- Op liderado por entidade exige ≥1 menção distintiva no hit
  (título/snippet/URL); senão gated com nota "sem menção à entidade".
  Homônimos que diferem só por separador passam quando citam a parte
  distintiva (menção real decide, sem heurística de domínio).

Caso controlado: `tests/test_identity_gate.py` (8 testes) — blog
genérico sem "planner" gated; homônimo open-code.ai e espelho uptodown
gated; doc da entidade fetched; op sem entidade e entidade sem parte
distintiva preservam o legado.

## 2. ORÇAMENTO DE ANÁLISE (`62b8037`)

Sintoma (accept17): 53 utilizáveis nunca avaliados — teto JSON
(12000 chars) + lotes em ordem de prefixo que 3 rounds não alcançam.

Causa: seleção do assessor ordenava fontes → reservas → refs prévias →
não-enviados (ordem de evidência) → enviados; o corte do teto caía
sempre sobre o mesmo sufixo, e slots reservados/refs de células já
cobertas e reenvios de já-enviados lotavam cada chamada.

Correção (`make_model_assessor`, mesmos limites — max_docs, teto JSON,
model calls intactos; só muda QUEM ocupa os slots):
- `_open_priority`: células abertas (não covered/partial no
  `set_previous_evaluations`) primeiro; termos da dimensão aberta.
- Fontes/reservas de entidades com células abertas primeiro; refs
  citadas SÓ por covered vão para o último tier; não-enviados sobre
  entidade/dimensão aberta antes do restante; já-enviados nunca
  recrowdam o lote (só preenchem sobra).
- Lotes cortados seguem não-enviados → a próxima round os carrega.
- Sem analisar HTML indiscriminadamente: nenhuma inclusão nova, só
  reordenação; nota de priorização vai para `cuts`.

Caso controlado: `tests/test_selection_budget.py` (4 testes) — entidade
aberta primeiro, lote cortado carregado sem repetição, limites
respeitados, ordem estável sem priors. Ajuste honesto de 1 fixture
existente (`test_s07`, `test_review_85dac79.py`): amarrava a propriedade
de segurança (ref fora da seleção rejeitada — preservada) à ordem de
prefixo (trocada pelo requisito); fixture agora empata em aboutness e
o prefixo decide como antes.

## 3. ALCANCE DAS AUSÊNCIAS (`1f508e6`)

Sintoma: vereditos missing_dimension generalizavam excertos (~0,4% dos
chars) para o corpus; "não investigado por orçamento" indistinguível de
"desconhecido-legítimo".

Correção:
- Cada avaliação carrega `examined` (docs da seleção, chars de excerto
  e coletado, round da chamada que a produziu).
- Cada critério do bloco ganha `examined_scope` (doc/trecho vs corpus):
  por entidade — "excerto examinado (E/N)", "não examinado por
  orçamento (N docs fora da seleção)", "desconhecido-legítimo (nada no
  corpus)"; renderizado nos Achados ("Alcance examinado: …").
- Reconciliação: `_accumulate_reading` conta `docs_excerpted_unique`
  além de `docs_excerpted` (batches); a linha de Leitura agora diz
  "B batches de excerto em U docs únicos de C coletados; avaliados
  únicos pelo assessor: A" + "batches contam repetições entre chamadas".

Caso controlado: `tests/test_examined_scope.py` (5 testes).

## 4. CITAÇÃO×ENTIDADE (`1bf60da`)

Sintoma (accept17): writer citava [4][5]/[5][4] em bloco onde só um doc
tratava da entidade.

Correção:
- Prompt do writer: citar APENAS docs que contêm a entidade e o fato;
  cada número na mesma frase deve resolver para doc que menciona a
  entidade; INFERÊNCIA/LACUNA exige premissa (ver §5).
- `_tighten_citations` (`verification_report.py`), aplicado no render
  após `_rewrite_refs`: remove número cujo doc não menciona nenhuma
  entidade nomeada na frase — SOMENTE quando resta ≥1 citação que
  sustenta (número desconhecido e frase só-frouxa seguem para a
  auditoria; sem mascarar lacunas). Notas vão para `state["notes"]`.

Caso controlado: `tests/test_citation_tightening.py` (6 testes).

## 5. S2 SEM ISENÇÃO AUTOMÁTICA (`c8a7d55`)

Sintoma: INFERÊNCIA/LACUNA marcadas com isenção automática; FPs do
heurístico no diagnose mascaravam o problema e a citação frouxa real
do writer passava.

Correção (`verification_report.py` + `tools/diagnose_run.py`, mesmo
comportamento nos dois auditores):
- Lacuna exige premissa: frase nomeando entidade só é sustentada se
  ≥1 doc citado menciona a entidade (`premise_docs` registrado nas
  declarações); senão unsupported ("entidade não mencionada no doc" /
  "premissa sem doc da entidade").
- `_entity_mentioned`: forma exata OU ≥2 tokens de conteúdo (len≥4)
  compartilhados — doc "OpenCode Plugin" sustenta "OpenCode Eclipse
  Plugin"; "opencode agents" × doc "opencode-planner" (só 1 token)
  continua rejeitado.
- `_mentions_version_gap`: frase que declara a versão
  desconhecida/ausente não falha no gate de versão (a ausência é o
  conteúdo); versão afirmada continua exigindo match.
- Writer: INFERÊNCIA/LACUNA citam os docs da entidade consultados.

Casos que diferenciam (todos verificados RED no HEAD e GREEN agora,
`tests/test_s2_premises.py`, 11 testes): FP rótulo, FP versão,
frouxa real (check_support E diagnose), âncora de inferência intacta.

## 6. Run real accept18

Artefatos: `/tmp/hermes-real-run/accept18/adaptive_accept18/`
(`report.md`, `result.json`, `verification.json`, `counters.json`,
`manifest.json`, `state.json`, `checkpoint.jsonl`). Re-render offline
pós-run (mesmos inputs, sem modelo/rede — só reaplica render com o fix
de escopo; síntese/avaliações/evidências byte-idênticas; proveniência
em `state.notes`).

Comando: `python3 gpt_researcher_integration.py "<pergunta §1>" medium
--mode adaptive --transport native --model-transport opencode
--model opencode-go/muse-spark-1.3-contributor --auto-plan --max-rounds 3
--control-dir /tmp/hermes-real-run/accept18/control --run-id accept18
--output-dir /tmp/hermes-real-run/accept18
--context installed_opencode_version=2.1.4`

Transporte: gateway vast fora; SearXNG fora (pós-reinício); coleta via
ddgs-fallback (sem chave), etiquetada `via` nos hits. 13 ops web
(6 done, 7 failed com motivo — execution `ok`); 38 fetches.

| | accept17 (perdida, `docs/ALLOC_FIX_ACCEPT17.md`) | accept18 |
|---|---|---|
| Candidatos exigidos | planner/marketplace/vscode/eclipse/oh-my-opencode | OpenCode, lit-opencode, opencode-planner, planning-with-files, opencode-local-memory, opencode-workspace |
| Cobertura | 8/36 = 0.2222, parcial | **4/55 = 0.0727, parcial** (denominador: 6 entidades × critérios + globais; percentual não é o ganho — ver distribuição) |
| Contadores | 85/63/63/10/6/7 | **37/28/28/28/6/4** (discovered/obtained/usable/analyzed/used/cited) |
| Parada | `rounds` (parcial honesta) | `rounds` (parcial honesta) |
| Diagnose | ok 8, partial_legit 13, missing_dim 5, assessor_error 7, selection_context 3, synth_unsup 0 | ok **4**, partial_legit **17**, missing_dim **3**, assessor_error **14**, selection_context **17**, synth_unsup **2** |
| Síntese | 60 / 21 / 41; support `failed` | **44 / 2 / 56**; support **`ok`** (28 citações, 0 fora do corpus) |
| Leitura | ~0,9% (texto) | **1,6% (49165/3006028 chars; 39 batches em 28 docs únicos de 28 coletados; avaliados únicos: 28)** — reconciliada no próprio texto |

Novos mecanismos ao vivo:
- **Identidade (5 gates)**: `opencode.ai/docs/*` (agents), dev.to genérico
  e `docs.plannotator.ai` gated para op `r3-c8-0` liderado por e3
  (opencode-planner) — sem menção a "planner". Docs oficiais genéricos
  seguem disponíveis para ops não-liderados por entidade (aboutness por
  slot, não exclusão do corpus).
- **Orçamento**: analyzed = usable = 28 únicos — nenhum utilizável ficou
  sem avaliação; assessor respondeu todas as células pedidas
  (40/40, 50/50, 50/50). `selection_context=17` aqui NÃO é lote
  faminto: são vereditos `insufficient` sem refs do próprio assessor
  sobre excertos examinados (comportamento de citação do modelo, não de
  seleção) — o alcance examinado (28/28) está em cada Achado.
- **Escopo**: 15/15 critérios com "Alcance examinado: excertos de
  28/28 docs únicos…"; 55/56 avaliações com `examined` da chamada.
- **Citação×entidade**: 0 ajustes necessários — o writer seguiu a regra
  (uma entidade por citação; INFERÊNCIA/LACUNA com premissas citadas,
  ex. `lit-opencode` exige V2 [8] + `opencode-planner` suporta V2 [1]).
- **S2**: as 2 unsupported da síntese são lacunas reais sinalizadas
  (versão ausente nos docs citados; dependências não documentadas no
  excerto) — não mascaradas, support continua honesto. RA8 PENDENTE.
- Sustentação sem flexibilização: cobertura parcial declarada; lacunas
  de retrieval (compat 2.1.4, custos, manutenção) seguem explícitas.

## 7. Verificação

- Suíte: **449 testes OK / 10 skipped** (base 414 + 35 novos) após a run
  (re-render não toca código; última mudança de código já coberta).
- Tentativas anteriores preservadas (nenhuma re-execução; artefatos
  accept17 perdidos com `/tmp` — registrado, não reconstruído).
- Commits locais (sem push): `66255bb` (identidade), `62b8037`
  (seleção), `1f508e6` (alcance), `1bf60da` (citação), `c8a7d55` (S2),
  `3faaed0` (escopo pós-S1/únicos). `git status` limpo fora esses.
- Caminho absoluto do relatório completo da run:
  `/tmp/hermes-real-run/accept18/adaptive_accept18/report.md`
