# Relatório técnico — Fase E: controle, aceite e demonstração integrada

Data: 2026-11-02 · Branch: `feat/product-v1` · Commit do código sob aceite: `a492bdd`
Run de aceite: `/home/thomaskyn/hermes-runs/accept35/` (run_id `accept35`) ·
Relatório final do produto: `/home/thomaskyn/hermes-runs/accept35/adaptive_accept35/report.md`
Run de referência preservado: `/home/thomaskyn/hermes-runs/accept34/` (intocado).

## 1. Congelamento e ambiente (aceite válido)

- HEAD pré == pós: `a492bdd7fc33ad831256699e8049d1d85cfe7dff`; `hashes.frozen` ==
  `hashes_post.frozen` (10 módulos); `diffstat` vazio de produto. Nenhuma edição
  durante o run.
- Embeddings exclusivamente llama.cpp 8082 existente (`harrier-oss-v1-0.6b`):
  pré `prompt_tokens_total 125606 / cached 1752` → pós `146352 / 2444`
  (+20746 gerados, +692 cache, com efeito). Sem outro modelo/CPU/externo.
- `opencode v2.2.5` observado no harness; premissa controlada da pergunta:
  `installed_opencode_version=2.1.4` (contexto informado pelo usuário).
- Mesma pergunta do accept34, perfil medium, output-dir próprio. `RUN_DONE EXIT=0`,
  elapsed 1157.8s. Consumo: queries 19/30, extrações 85/120, model 12/16 (10/16 na
  decisão + 2 de finalização), rounds 8, tempo 704.4s/1800s na decisão.
- Parada: `reason=rounds`, `max_rounds=7 source=default` (hook 3→5→7 por by_cells),
  15 lacunas abertas, folga em todos os demais tetos — limite honesto registrado,
  não esgotamento (item v, §7).

## 2. Resultado comparável (com churn declarado)

| Métrica | accept34 (3da5de8) | accept35 (a492bdd) |
|---|---|---|
| Cobertura | 0/55 (0.0) | **2/55 (0.036)** — c2×pwf, c10×pwf covered |
| Diagnose | sel_ctx 14, missing 23, partial 18, ok 0 | sel_ctx 20, missing 12, partial 15, ok 2, assessor_error 6 |
| Síntese | 41 / 7 / 103 (sup/não-sup/sem-cit) | 35 / 9 / 104, declared 15 |
| Verificação | overall partial; support ok; review partial | overall partial; support ok; review partial; execution ok |
| Corpus | 28 docs obtidos | 46 descobertos / 40 obtidos / 40 usáveis / 40 analisados / 6 usados / 12 citados |
| Leitura | 2,5% dos caracteres | 1,5% (90296/6064610) |

Planos/finalistas churnaram de novo (auto-plan: pwf/oplanner/ocreview/peers/
sun-praise vs slim/Context7/gh-workflow/refactoring), corpus e denominador
mudaram juntos — o delta 0→2 covered **não** é atribuído causalmente aos fixes.
A demonstração dos fixes repousa em: replay controlado sobre artefatos congelados
+ testes + traços de produção abaixo, não em delta entre runs.

## 3. Demonstração dos 5 itens em produção

- **(i) M-A via caminho integrado.** F1 confirmado em runtime: registro de assessment
  em `state.json` carrega `"cuts": "lote por diversidade: 3 célula(s) required
  aberta(s) priorizada(s); limites intactos; boilerplate ignorado …"` — antes a nota
  morria em `last_selection` efêmero (`grep diversidade` era 0/0/0). Casos do replay
  sobre dados congelados: (A) sem priors, mesmos tetos, diversidade 8/24 com
  valterpatrick+upstash-context7 e nota de 10 células vs controle 9/24 sem nota —
  seleção muda; (B) priors finais, nota presente mas prefixo 13 > 9 do teto (regime
  tardio onde o corte 12k esconde o reorder) + `{}` legítimo quando nada cobre
  (sem-ganho mantém seleção). Evidência: `/home/thomaskyn/hermes-runs/valid-fase-e/replay_accept34_diversity.json`.
- **(ii) Context7 avaliação-vs-síntese (lição aplicada).** O padrão "positivo
  documentado mas audit-unsupported por overlap PT→EN" reapareceu em 6 frases
  `Documentado: opencode-code-review … [11]` (overlap 0.00–0.14). Verificação manual:
  o doc [11] (erskingardner/opencode-code-review, 4044 chars) contém literalmente
  "multiple specialized subagents", "4 parallel subagents", "threshold at 80",
  "Focused on changes, not pre-existing issues" — as frases são **sustentadas pela
  fonte**; o não-suporte é falso-negativo do gate de overlap por tradução
  (tokens PT≠EN: "subagentes" vs "subagents"), não alucinação do writer. Support
  permaneceu `ok`; gates de versão/citação intactos. Limitação de recall do auditor
  registrada, sem afrouxar gates.
- **(iii) Finalistas sem documentação.** F3 em produção: `fonte própria` ×31;
  §0 do relatório: peers/review com "fonte própria fora do corpus → estado não
  verificado — não se afirma presença nem ausência, LACUNA com causa de fonte
  ausente" (fallback neutro pós-revisão, sem afirmação forte de ausência em erro).
  Mecanismo geral confirmado: `_old_ok` exige tudo-insuficiente+zero-refs, por isso
  partial-holders nunca saem por substituição — sem exceção por nome.
- **(iv) Inferências de combinação.** F2 em produção: §10 com 3× `INFERÊNCIA de
  complementaridade/sobreposição` marcada, citada ([10][11], [8][11], [10][8]) e
  limitada ("sem prova de integração testada… integração afirmada continua
  LACUNA") — canal declarado/partial do verifier, sem exigir interoperabilidade;
  ausência de interop segue LACUNA sem apagar a inferência. c12/c13 corretamente
  abertas (sem matriz de interoperabilidade no corpus).
- **(v) Política de parada.** Cadeia verificada: base 3 (default medium) →
  proporcional (mínimo de tetos, by_cells vinculou 3→5→7) → guard → stop `rounds`
  com detalhe "parada não-justificada por comparabilidade". Nenhuma fórmula prova
  esgotamento (hipótese ~8 células/round observou 2/55); cobertura 0.036 < 0.60
  bloqueia estruturalmente qualquer stop por saturação; round 7 ainda agregou
  revisões (c3/c5 oplanner insufficient→partial). Classificação: parada por **limite
  configurado**, honesta e corretamente registrada.

## 4. Triagem residual (sem problema material corrigível no escopo)

1. Bucket `assessor_error` ×6 do diagnose é **rotulagem incorreta da ferramenta**,
   não erro do produto: c8/c9/c10 têm `description` vazia no plano (auto-plan só
   gerou labels) e o assessor registrou honestamente "Definição do critério não
   fornecida". Citar doc + insufficient com critério indefinido é comportamento
   correto. Limitação conhecida do `tools/diagnose_run.py`; fora do escopo (i–v).
2. Gate de overlap tem recall reduzido em paráfrase PT→EN e em declarações
   negativas ("nenhuma contradição", [26][26] com dupla citação idêntica) —
   verificado manualmente contra a fonte nos 6 casos [11]. Preservar gates;
   considerar futuramente similaridade por embeddings já existentes, sem afrouxar.
3. Cosméticos do writer sem efeito factual: entidade repetida 5× na linha 24;
   `[26]` citado duas vezes na mesma frase; next-steps chamam [20] (página de
   categoria) de "fonte própria" de peers em tensão com o status "fora do corpus".
   Não material: nenhuma afirmação factual decorre desses trechos.
4. `assessor_error` à parte, `selection_context` 20 e `missing_dimension` 12 são o
   estado real do corpus (1,5% lido; 2 finalistas sem fonte) — cobertura parcial
   honesta, não defeito corrigível dentro dos tetos autorizados.

## 5. Arquivos e verificação

- Fixes: `adaptive_coordinator.py` (+~95/−2, genérico, verifier intocado, tetos
  intactos) + `tests/test_fase_e_controle.py` (7 testes). TDD RED→GREEN; revisão
  independente (1🔴 corrigido com teste RED-primeiro, 1🟡 documentado, 2❓ resolvidos).
- Suite final: **655 OK, skipped=10 (pré-existentes), EXIT 0** (log `/tmp/opencode/fase_e_full.log`).
- URLs: 40 números, todos bem-formados, `citations_unknown=[]`; §7 estável; §5 sem
  URLs truncadas (defeito da Fase D ausente neste run).
- Commits locais (sem push): `a492bdd` (fixes); este relatório + CONTINUIDADE +
  plano em commit seguinte. `.planning/.active_plan` alheio preservado.

## 6. Entrega e limite

Atendimento **parcial**: comportamentos (i–v) demonstrados com evidência de
produção + replay + testes; relatório do produto honesto (parcial 2/55, 15
lacunas, parada por limite). Não validado: saturação/esgotamento (exigiria rodadas
além do teto, fora da autorização), recall total do gate de overlap, leitura além
de 1,5% do corpus. Próximo passo autorizado: nova pergunta de aceite ou ampliação
de teto explícita pelo usuário — nunca repetição cega do mesmo run.
