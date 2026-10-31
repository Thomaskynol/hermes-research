# Aceite da primeira versão — reabertura e resultado (2026-10-26 a 2026-10-29)

Pergunta de aceite (literal, usada em todas as execuções):

> Descubra e compare cinco plugins para melhorar planejamento, implementação,
> testes e revisão de código no OpenCode. Considere a versão instalada neste
> computador. Investigue compatibilidade, funcionalidades demonstradas,
> dependências, custos, manutenção e limitações. Justifique quais combinam
> entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie
> funcionalidades documentadas de inferências.

Contexto explícito fornecido à entrada (nunca inspecionado pelo produto):
`--context installed_opencode_version=2.1.4`.

## 1. Entrada isolada (eixo 5)

Caminho único, sem tocar produção (`/home/thomaskyn/.hermes` intocado):

```bash
cd /home/thomaskyn/Projetos/hermes-research-dev
export SEARXNG_URL=http://172.18.0.2:8888
R=accept11
python3 gpt_researcher_integration.py "<pergunta>" medium \
  --mode adaptive --transport native --model-transport opencode \
  --model opencode-go/muse-spark-1.3-contributor \
  --auto-plan --max-rounds 3 \
  --control-dir /tmp/hermes-real-run/$R/control --run-id $R \
  --output-dir /tmp/hermes-real-run/$R --context installed_opencode_version=2.1.4
```

Controle em tempo real, na mesma run: `python3 run_control.py --run-dir
/tmp/hermes-real-run/accept11/control status` → exit 0, `phase: round`,
`round: 1`, `run_id: accept11`, contadores e documentos (verificado durante a
execução). Pausa/retomada/cancelamento já demonstrados em
`docs/HERMES_E2E_DEMO.md`.

## 2. O que falhava e o que foi corrigido (mecanismos gerais)

| Run | Sintoma observado | Causa raiz | Correção (commit) |
|---|---|---|---|
| accept1–3 | cobertura 0.0, consultas de lacuna genéricas | query de lacuna não usava o alvo; falhas de canal não apareciam no relatório | D1/D2 (`5976c06`) |
| accept3 | poluição por ambiguidade PT | termos da pergunta sem âncora | âncoras + snippet gate (`f9387a2`, `a83981f`) |
| accept4 | 41 candidatos, `propose_entity` disparava mas sumia | ids propostos colidiam com e1–e5 do plano | remap + herança (`3e8b628`) |
| accept5 | run morria com 54 avaliações e orçamento restante | 1 payload não-lista do assessor virava `TransportError` fatal | 1 retry limitado, contado no budget (`0cad02a`) |
| accept6 | entidades descobertas versionadas, nunca investigadas | gaps só por critério; fonte própria não virava alvo | gaps por célula + `read_source` + prompt enumera células (`54294f7`) |
| accept7 | cobertura 0.0 com lixo (npm/ripgrep) | plano com entidades-placeholder e caminhos locais como queries | proíbe placeholder, descarta caminho local, `_query_label` (`6b54fe7`) |
| accept8 | 6 candidatos reais, 1 avaliação cada, sem virar cobertura | critérios todos globais; writer cortava fontes citadas | `per_candidate` + writer prioriza citadas (`92361db`) |
| accept9 | denominador 83, 12 entidades | sem teto de candidatos | `candidate_target` + teto na cobertura (`7f79ac6`) |
| accept10 | 3 dos 5 exigidos sem excerto | candidato de lista virava exigido sem menção na fonte | gate de menção na fonte própria (`cd0c12b`) |
| accept11 | `cited: 0` na tabela com 7 citações no texto | snapshot lido antes de `record_cited` | tabela usa as citações do próprio render (`d96a114`) |
| accept12 | 25 afirmações "não suportadas" na auditoria pós-hoc | `state.json` salvo com chaves alfabéticas; auditoria resolvia `[n]` contra ordem errada | numeração `[n]→URL` persistida no artefato; diagnose e `check_support` usam-na (`9552100`, E2) |
| accept12 | fatos de licença/custo no doc, ausentes do excerto | janela de 1200 chars pontuada globalmente; rodapé do doc nunca entrava | excerpt por dimensão com cota por grupo + sub-grupos âncora (`9552100`, E1) |
| accept13 | critério "diferencie documentado de inferência" sempre `insufficient` | avaliado contra excertos; nenhum excerto tem a propriedade da resposta | critérios `synthesis:true` avaliados contra a síntese (parcial máx.) (`23b503d`, S1) |
| accept13/genus1 | declaração de lacuna legítima reprovada por overlap baixo | auditoria exigia overlap textual do vazio | declarações de lacuna e inferências marcadas auditadas sem exigir overlap (`2fea859`, S2) |
| accept14 | c12 (`synthesis`) ficou `insufficient` mesmo com síntese separando documentado/inferência | extrator do S1 não removia backticks; síntese cita `` `https://…` `` | S1 reconhece URL em code span (`e32525d`; ensaio no caso real: c12→partial) |

Correção adicional: URL dentro de literal citado (`"plugin": ["x@git+https://…"]`)
deixou de ser substituída por `[fora do corpus]` (`de7c979`).

## 3. Resultado do accept11 (run iniciado em `cd0c12b`; renderer corrigido depois em `de7c979`/`d96a114`)

- Artefatos: `/tmp/hermes-real-run/accept11/adaptive_accept11/`
  (`report.md`, `result.json`, `verification.json`, `counters.json`,
  `manifest.json`, `state.json`).
- Perfil medium; 3 rodadas + varredura inicial; 441 s; 42 documentos;
  53 fetches; 7 chamadas de modelo; 4 rodadas.
- Contadores: discovered 50, obtained 41, usable 41, analyzed 31,
  used_in_synthesis 7, cited 7 (após `d96a114`; antes a tabela dizia 0 —
  verificado por re-render do `state.json` real, sem nova chamada de modelo).
- Cobertura: **0.025 (1/40 células), parcial**; motivo de parada `rounds`.
- Verificações independentes: execution `ok`; question `partial` (11 critérios
  pendentes); review `partial`; support `failed` (2 falhas registradas por
  motivo, URL fora do corpus sinalizada).
- Cinco candidatos exigidos, sem substituição, todos com fonte no corpus:
  `opencode-planner` [2], `Plannotator` [6], `oh-my-opencode-slim` [4],
  `dzianisv plugin-testing` [5], `opencode-daytona` [3].
- O relatório entrega: comparação lado a lado, funcionalidades demonstradas
  com trecho literal, dependências, custos (lacuna explícita), manutenção,
  limitações, combinações/sobreposições classificadas em DOCUMENTADO /
  INFERÊNCIA / LACUNA, fontes numeradas com alcance lido e a contradição
  entre a justificativa da cobertura e os excertos disponíveis.

## 4. O que ainda não está resolvido (limitações reais)

1. **Cobertura baixa e não comparável entre runs.** O denominador mudou a cada
   correção (global → por célula → teto → gate). 0.025 significa 1 de 40
   células obrigatórias com evidência forte; o relatório responde à pergunta
   com lacunas explícitas, mas não pode ser declarado completo.
2. **Justificativa do assessor não é verificada contra o excerto.** No
   accept11 ele afirmou `V2 only` e `pin 0.6.0` sem esses trechos no corpus; o
   relatório detecta e declara a contradição. Desde `2fea859` (S2) existe a
   5ª dimensão de verificação (`support`): cada frase citada da síntese é
   checada contra o doc citado (overlap ≥0.35 ou ≥2 palavras raras, mais
   presença da entidade), com declarações de lacuna e inferências marcadas
   auditadas sem exigir overlap do vazio. O `support` **não altera a
   cobertura** — sinaliza em `verification.json` e nas limitações. Estado:
   genus1 `ok` (37/37); accept14 com 4 `unsupported` reais sinalizados.
3. **Sem conector de inspeção local.** A versão instalada só entra como
   contexto informado; o produto não lê `~/.config/opencode` nem o binário.
4. **Tokens e custos desconhecidos** (nunca zero). `model_calls` conta
   chamadas de fronteira, não requisições internas do provedor.
5. **Canal web primário (gateway vast local :8001) segue fora**; SearXNG
   auto-hospedado (IP de bridge frágil) e ddgs cobriram a coleta, com `via`
   registrado.
6. **Snippet gate não filtra lixo que compartilha vocabulário**; hits sem
   snippet são lidos às cegas (e contam no orçamento).

## 5. Generalização (outro assunto)

`docs/VALIDACAO_REAL_ACADRUN5.md`: pergunta FAIR-RAG, perfil com orçamento
explícito, `criteria_ok = 1.0`, revisão ACCEPTED, contadores
16/10/10/8/7/7. Evidência de que os mecanismos não são específicos de
OpenCode.

**genus1 (2026-10-29, HEAD `23b503d`):** pergunta "compare httpx × requests ×
aiohttp (sync/async, timeout, pooling, versões, documentos oficiais,
documentado vs inferido)", mesmos perfil/transporte/modelo do aceite,
`/tmp/hermes-real-run/genus1/`. Resultado: cobertura **10/16 = 0.625,
parcial**, parada por **SATURATION** (novelty 0.00 — o produto parou
sozinho), 38 documentos, 47 fetches, 6 chamadas de modelo, execution `ok`,
review `partial` (12 claims, 0 unsupported), **support `ok` (37/37
resolvidas)** — a dimensão de sustentação aprova num assunto com corpus
denso. Diagnose: ok=6, partial_legit=4, selection_context=1,
missing_dimension=1, synthesis_unsupported=4 (uma é declaração de lacuna
legítima — motivou o S2), assessor_error=0. O acadrun5 continua válido como
prova de não-especificidade, mas tinha support reprovado; o genus1 é o caso
completo no outro assunto.

## 6. Estado do repositório

Branch `feat/product-v1`; HEAD `c83b892`; árvore limpa; **411 testes OK
(9 skipped)** no host; sem push/deploy; produção intocada; nenhum pacote de
revisão gerado.

## 7. Runs accept12–accept14 (comparáveis: mesma pergunta, config e contexto)

| Run | HEAD | Docs | Cobertura | Candidatos exigidos | Diagnose (40/36 células) |
|---|---|---|---|---|---|
| accept12 | `d92aa8e` | 45 | 3/36 = 0.0833 partial | planner, planning-toolkit, shannon, context-analysis, alibaba review | ok=3, partial_legit=15, selection_context=2, assessor_error=16 |
| accept13 | `9552100` (E1/E2) | 51 | 8/36 = 0.2222 partial | planner, Plannotator, dzianisv, oh-my-openagent, Context7 | ok=7, partial_legit=17, selection_context=4, assessor_error=5 |
| accept14 | `2fea859` (S1/S2) | 55 | 1/40 = 0.025 partial | planner, goal-plugin, Oh My OpenAgent, Context7, reflection | ok=1, partial_legit=14, selection_context=0, assessor_error=19 |
| accept15 | `e32525d` (S1 code-span) | — | 6/55 = 0.109 partial | planner, marketplace, oh-my-opencode, opencode-agents, type-inject | ok=6, partial_legit=24, missing_dimension=9, assessor_error=16; síntese 28/5/57 após `b4d61f8` |
| accept16 | era `d0ba933` + M7/M8/M9 (`34c760c`) | 40 evidências, 4 avaliações | 11/51 = 0.2157 partial | opencode-planner, plannotator, oh-my-opencode, opencode-marketplace, dzianisv-opencode-plugins | ok=10, partial_legit=23, missing_dimension=8, assessor_error=11 (maioria FPs de heurística, tipo c4-testes); selection_context=2, synthesis_unsupported=1; síntese 44/2/57 — ver §11 |

Leitura: E1/E2 elevaram a cobertura (accept13 8/36, com `selection_context`
caindo 19→4) porque fatos de licença/custo no rodapé dos docs passaram a
entrar no excerto. accept14 voltou a 1/40 **sem regressão de mecanismo**:
os 5 candidatos sorteados pelo gate de menção (goal-plugin, reflection…)
têm corpus mais pobre que os do accept13, e 19 `assessor_error` são
insuficiência legítima sobre excerto (ex.: "nenhuma informação de custo no
excerto"). A cobertura mede o par (pergunta × corpus obtido), não só o
produto — runs diferentes descobrem candidatos diferentes. O relatório de
cada run compara exatamente os 5 exigidos do seu plano, sem substituição.

## 8. Diagnóstico por buckets (`tools/diagnose_run.py`)

Cada célula obrigatória é classificada de forma reproduzível:

- `ok` — covered com referência.
- `partial_legit` — parcial com documento de suporte citado (evidência usada mas incompleta/truncada).
- `selection_context` — evidência existe no corpus, mas a avaliação não a usou (0 refs) → problema de seleção/excerto. **Causa predominante no accept11 (19/40)**; caiu para 4 no accept13 e 0 no accept14 após M1/M2/E1.
- `missing_dimension_evidence` — nenhuma fonte da entidade menciona a dimensão com termo forte → lacuna legítima.
- `assessor_error` — suporte existe e não foi usado (heurístico frouxo: superconta; a maioria é insuficiência legítima sobre excerto pobre — ver §7).
- `synthesis_unsupported` — afirmação da síntese sem sustentação (após S2, declarações de lacuna e inferências marcadas não contam aqui).

Auditoria da síntese (accept14): 16 suportadas, 4 não suportadas, 58 sem
citação — as 4 são problemas reais de síntese (ex.: entidade ausente no doc
citado), sinalizados pela dimensão `support`, sem alterar a cobertura.

## 9. Suficiência de esforço e rodadas

Mesma pergunta/config (accept11–14): evidência nova por rodada cai
(inicial 22–27, gap1 11–19, gap2 0–7, gap3 0–1); a cobertura estabiliza
após o gap1 porque o gargalo passa a ser avaliação/excerto, não coleta.
`model_calls` fica em 6–8. Conclusão: `max-rounds 3` é suficiente para o
perfil medium nesta pergunta; rodadas extras não elevariam a cobertura.
Limites explícitos do usuário continuam respeitados (orçamento medium nunca
estourado; parada `rounds` é parcial honesta, nunca aprovação forçada).

## 10. Entrada Hermes isolada — demonstração ponta a ponta (accept12)

Além do `status` em tempo real (§1): `run_control.py pause` numa run ativa
→ finalize parcial limpo entre rodadas (`stop: {reason: paused}`, 1 rodada,
28 evidências, 6 entidades, `report.md`/`verification.json` completos);
`--resume` com a mesma pergunta/plano → processo novo retomou do ponto de
parada (`round: 1`, contadores analyzed 8 / obtained 25 / discovered 29 /
cited 7 preservados, sem re-obter). Produção intacta o tempo todo.
Entrada NL isolada + pause/resume demonstrados ao vivo no accept12
(status em tempo real §1, pause limpo + `--resume` acima).

## 11. accept16 — resultado final (2026-10-30, mecanismos até `d0ba933` + M7/M8/M9)

- Cobertura **11/51 = 0.2157, parcial**, parada por `rounds`; 40
  evidências, 4 avaliações.
- 5 exigidos descobertos, **zero substituições** (M8 nunca disparou):
  `opencode-planner`, `plannotator`, `oh-my-opencode`,
  `opencode-marketplace`, `dzianisv-opencode-plugins`.
- M7 N/A funcional: `na=4` com evidência de escopo (ex.:
  `opencode-marketplace` N/A para planejamento/implementação —
  instalador, não planejador).
- M9 (métrica de leitura): 51.707 chars excerptados de 5.927.450
  coletados (~0,9%) — saturação de URL ≠ análise exaurida.
- Diagnose: ok=10, partial_legit=23, missing_dimension=8,
  assessor_error=11 (maioria FPs da heurística ferramenta, tipo
  c4-testes: assessor insufficient está correto, doc só menciona a
  dimensão de passagem), selection_context=2, synthesis_unsupported=1.
- Síntese: 44 suportadas / 2 não suportadas (cites fracos de menção em
  lista, overlap 0,12–0,20) / 57 sem citação.

## 12. Saga Fix E — escalonamento por entidade (2026-10-30; pergunta Django×FastAPI×Flask, medium, max-rounds 3)

| Run | Cobertura | O que mostrou |
|---|---|---|
| genus5 | 3/26 = 0.115 | `_short_gap_query` ignorava `gap.entity_id` (todas as queries Django-led, Flask faminto) |
| genus6 | 7/26 | Fix E (`1c68e3c`, só query builder) = no-op em produção: gaps de runtime nunca carregam `entity_id` |
| genus7 | 4/26 | Fix E-complete (`5304231`: `select_ops` expande gaps de critério per_candidate em sub-gaps por entidade) provou o mecanismo end-to-end: queries Flask-led apareceram (r1-c1-0-e3 `new_useful`), docs oficiais flask.palletsprojects.com entraram no corpus (2 URLs vs 0), e3 1 covered/4 partial/3 insuff (vs 0/2/6) — mas o total caiu 7/26→4/26 porque a expansão agrupada deixou c1 monopolizar os 3 slots de op toda rodada |
| genus8 | 4/26 | Round-robin interleave (`c83b892`, HEAD atual): spread intra-round confirmado (r1–r3 miram [c1,c2,c3] em vez de só c1), total idêntico 4/26, e3 0/0/8 — azar de retrieval (docs oficiais Django+Flask falharam em r0; corpus 5 FastAPI + 6 arxiv off-topic), e c4–c10 nunca mirados (mesmos top-3 gaps repetem com delta 0.0) |

Conclusão registrada: o gargalo vinculante agora é **retrieval**
(evidência de dimensão ausente), não escalonamento; **parar de iterar
alocação**.

## 13. Série outro assunto — Django×FastAPI×Flask (2026-10-30)

genus1 10/16 = 0.625 SATURATION support 37/37 (era pré-per_candidate,
planner set aplica explicitamente); genus2 1/10 — expôs bug
per_candidate não-vinculado (fix `b861763`: vincula per_candidate a
entidades predefinidas na adoção quando `open_discovery.needed` é
falso); genus3 7/26; genus4 7/26; genus5 3/26; genus6 7/26; genus7 4/26;
genus8 4/26. Variância single-run é dominada por retrieval.
(Os números do genus1 coincidem com o genus1 httpx do §5.)

## 14. Calibração Lane B (2026-10-30; corpus congelado accept15, `tools/run_calibration.py`, 25 casos a–f)

- Erros causados pelo validador: 12→1; ok 8→18; julgamento-de-modelo
  1→2 (desmascarado pelo fix); contexto 4→4 (provas estáveis: janela de
  excerto 1200 chars, sem retrieval de doc oficial).
- Residuais documentados: gap lexical inter-idioma (MIT em PT vs doc
  EN), ambiguidade dev-vs-user de sentido (b2, `known_limitation`),
  taxa de claims sem citação.

## 15. Limitações finais (2026-10-30, HEAD `c83b892`)

1. Cobertura parcial na pergunta de aceite (retrieval-bound: features de
   código-teste, compat 2.1.4, custos ausentes do corpus).
2. Residuais de suporte: inter-idioma + claims de escopo.
3. Sem conector local (versão instalada só via `--context`).
4. Tokens/custos desconhecidos.
5. Gateway vast fora; ponte SearXNG com IP frágil.
6. Variância de retrieval single-run (~±0,1 de cobertura entre configs
   idênticas).

## 16. Rodada accept19/accept20 — correções de identidade/síntese (2026-10-31, HEADs `c78331a`→`b81e8f6`)

Diagnóstico do accept18 (4 perguntas, evidência em
`/home/thomaskyn/hermes-runs/accept19/`): [27] (planning-with-files) morreu
na **seleção do writer** (ordem alfabética + teto 12k, refs por entidade
ignoradas); lit-opencode×lit.dev tinha **vínculo zero** (só custo de
orçamento); M8 em **deadlock** (qualquer ref bloqueia troca; pool de
substitutos vazio por desenho); `support: ok` × 2 unsupported do diagnose ×
`beyond` de 22 URLs = convenção de marca `LACUNA:` não reconhecida +
**tabela §7 contada como citação**. Correções gerais (conceito
identidade/entidade, não regra lexical): piso por entidade no writer +
refs de avaliações no ordenamento; identidade estrita (forma-cheia ou
token-único-raro no corpus); M8 com pool de descoberta + alternativas
não-exploradas declaradas; suporte excluindo tabela §7; marca inicial com
`lacuna` auditada pela premissa. Antes/depois controlado no estado
congelado: [27] fora→dentro do prompt; e5 28→1 doc; beyond 22→0; síntese
44/2→46/0. Testes: 476 passed / 15 skipped / 1 falha pré-existente de
ambiente (`requests` ausente; ocorre na árvore limpa).

`accept19`: tentativa falha preservada — race com o commit (usou código
antigo) + assessor flakou no round 0 (não-lista 2×); `support failed`
corretamente (síntese citava o SearXNG morto). `accept20` (código novo,
`rounds`, 48/14/14/14/6/7, 57 avaliações, **5/52 + 4 N/A**): 5 candidatos
com identidade real (lit-opencode coberto; shannon N/A com evidência +
fork contraditório declarado; oh-my-opencode/Context7/local-memory LACUNA
honesta com recusa de misattribution no texto); 1 combinação documentada;
`selection_context` 17→4; buckets `ok 5, partial_legit 10, na_scoped 4,
assessor_error 17 (todos corretos — classe proximidade-em-listagem),
missing 16`; síntese 37/1/76. `verification` overall **failed** por 1
inferência com versão de contexto do usuário — diagnose concorda (sem
divergência); **RA8 segue PENDENTE, sem flexibilizar**. Pós-run (unit
tests apenas, não validados em run): contexto do usuário não é evidência
(regra estreita Missão 3: comparação numérica contra mínimo declarado =
sustentada (premissa+corpus); compat funcional/integração sem fonte que
mencione a versão = LACUNA) no prompt (`cc0f3ff`); entidade fraca registra pool não explorado (`b81e8f6`).
Relatórios: `/home/thomaskyn/hermes-runs/accept19/DIAGNOSIS_accept18.md`,
`/home/thomaskyn/hermes-runs/accept20/RELATORIO_ACCEPT20.md`.
