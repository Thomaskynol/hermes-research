# CONTINUIDADE — estado atual primeiro, histórico abaixo (`feat/product-v1`)

> **Estado atual — resposta attempt4 accept43: síntese NOVA + revisão NOVA (2026-11-05 UTC):**
> branch `feat/product-v1`, produto `10cb10d` + diff lane-1 (sem reedição;
> sem push ainda). Fonte: `runs/accept43-corretiva-attempt3/replay/` (só
> leitura); destino exclusivo `runs/accept43-corretiva-attempt4/`.
> Baseline frozen sem `--model` exit 0 (seleção idêntica, efeitos lane-1:
> 5/13 + c_combo parcial). Passe live (`--model
> opencode-go/muse-spark-1.3-contributor`, `--assessment-calls 0`):
> assessor 0 chamadas novas (81 herdadas revalidadas), writer 1 reaplicado
> byte-idêntico (síntese inédita "Comparação de cinco plugins",
> `audited_sha=9dd8f0b7…`), auditoria 9 lotes live (model-02..10, 75 slots,
> 0 falhas). Review real: 25/25 com quórum — 23 sustained, 1 partial
> (id 39, jira-MIT), 1 unsupported (id 0, 2–1, fusão de 5 pacotes
> rejeitada sem reversão). Claim-equivalente ao claim 3 = id 5 (LACUNA
> marketplace-planejamento, NÃO forçado a 3): SUSTAINED 2–1 com evidência
> só-marketplace (sem config-pack nos blocos; nenhum voto usa pacote
> alheio). Octto com escopo integral (perguntas/fragments/plano p/
> aprovação; revisão=LACUNA delimitada); [2] só na bibliografia, [20] nu
> (em included_urls), [4] qualificado fora-dos-excertos; INFERÊNCIAs só
> complementaridade/sobreposição com limites (nunca integração testada).
> `verification.json` corresponde ao relatório (`rendered_sha=16ce6771…` ==
> sha256 do report). Overall `failed` HONESTO (claim-0 fusão + overlap
> PT×EN; sem reversão, sem edição de artefato). Residuais documentados no
> RELATORIO_VALIDACAO: escopo §2/§3 stale ("0/13") por anotação idempotente
> pré-write sem rebuild pós-write; 2 notas §5 ruidosas (matcher sem
> dimensão); composição de lotes varia entre runs; guia writer futura
> (1 afirmação por pacote). Focada 131 OK + ampla 920 OK/10 skips exit 0
> (produto intacto lane-1). ZIP:
> `runs/accept43-corretiva-attempt4/REVISAO_ACCEPT43_ATTEMPT4.zip` (report
> + verification + annex + RELATORIO_VALIDACAO). Técnico atualizado com
> adendo attempt4 + RETIFICAÇÃO [20]. Próximo passo: validação do
> orquestrador (sem push por enquanto).

> **Estado atual — corretiva attempt3 accept43 (2026-11-05 UTC):**
> branch `feat/product-v1`, produto `47f4fe7` + testes locais (sem push).
> Fechados os 2 residuais do gate externo: `vr:1569` (isenção mesma-oração
> → adjacência ≤40 chars ao marcador, mesma cláusula; T2a preservado; sem
> isenções por INFERÊNCIA/LACUNA/negação) e propagação `[N] (fora dos excertos)`
> em TODAS superfícies (matriz+Achados+recomendação, 30× vs 10×;
> `[19]`/`[4]` qualificados; `[2]` refutado p/ promoção com justificativa:
> widget `show_diff` ≠ revisão PR). Claim 3 investigado com texto integral,
> origem `c3700bb`, `e62-e96` vs `e97-e136`, votos 04-gap vs 07/10-unsupported
> anti-fusão; caminho anti-fusão exercitado (`frozen-check.log`).
> Proveniência: fix1==externo (`2ccd71921fa467a2`/`ced8afb`/`790a9a06ba346b81`),
> attempt2==atual-parcial (`e8e741755b151af8`/`d13b9ae`),
> attempt3==atual (`5265f941bf85bdf4`/`47f4fe7`/`790a9a06ba346b81`).
> `39/42` histórico vs `0/13`/`0/42` frozen explicados; INFERÊNCIAs
> `[17][34]`/`[17][42]` partial com limites. Suite 916 OK/10 skips + offline
> 11/11 exit 0; replay zero-live exit 0 overall `partial` (review `not_run`,
> claim 3 2–1 preservado). Técnico atualizado:
> `docs/RELATORIO_TECNICO_CORRETIVA_ACCEPT43_SUSTENTACAO.md`. RA8 pendente.
> Próximo passo: validação do orquestrador (sem push por enquanto).

> **Estado anterior — corretiva accept43 sustentação/avaliação/claim3 (2026-11-05 UTC):**
> branch `feat/product-v1`, produto + testes locais (sem push). Os 4 itens foram
> corrigidos em mecanismo geral (1 correção por causa, TDD red→green T1–T4 com
> 8 testes em `tests/test_accept43_corretiva_sustentacao.py`): rescope reescreve
> frase multi-entidade ao escopo uni-entidade (ordinal por posição textual);
> refs fora de `included_urls` publicadas como `[N] (fora dos excertos)`; notas
> §5 com carimbo da síntese; verificadores aceitam numérico+premissa+LACUNA
> (canal LACUNA), fato próprio no excerto (base inequívoca) e ausências
> "LACUNA nos excertos/sem fonte/sem trecho/não estabelece" como LACUNA-janela,
> mais ponte PT→EN de escopo; empacotamento de evidência por entidade sem fusão.
> Controles que rejeitam (tag inventada, doc estrangeiro, homônimo, interop sem
> doc) intactos. Suite 895 OK/10 skips + offline exit 0; replay zero-live
> `runs/accept43-corretiva-fix1/replay/` (exit 0, overall `partial`; review
> `not_run` — claim 3 2–1 preservado sem novos votos); checagem congelada
> b671207 só-leitura com os 3 vereditos-caso corrigidos; 4 unsupported residuais
> idênticos sob código `b671207` intacto (sem regressão). Técnico:
> `docs/RELATORIO_TECNICO_CORRETIVA_ACCEPT43_SUSTENTACAO.md`. RA8 segue pendente.
> Próximo passo: revisão independente (gate do orquestrador).

> **Estado atual — revisão independente exercitada (2026-11-05 UTC):** branch
> `feat/product-v1`, produto `b671207` + testes (locais, sem push). Os três
> achados do reviewer foram corrigidos em mecanismo geral e demonstrados por
> reprodução integrada `runs/accept43-reconciliation/reproduction-b671207-replay/`
> (12/12 replays idênticos, zero chamadas live — síntese e evidências
> inalteradas): premises só pares corretos + trio com 3 refs, matriz Octto-revisão
> em parcial com limite e só [20], rótulo único de inferência, `missing/inferred`
> vazios, `c_overlap` partial, overall `failed` preservado pelo claim 3 sem relação
> com estes achados, 53/25/28 explícitos. Suite 887/10 skips + offline 11/11
> (a revalidar no fechamento). RA8 segue pendente. Próximo passo definido
> pelo solicitante.

> **Estado anterior — defeitos accept43 corrigidos em mecanismo (2026-11-05 UTC):**
> branch `feat/product-v1`, produto `c3700bb` + testes `fea9fb7` (locais, sem
> push). Os dois defeitos materiais foram corrigidos em mecanismo geral
> (writer guidance + reescrita determinística no renderer) e demonstrados por
> reprodução integrada `runs/accept43-reconciliation/reproduction-c3700bb-live/`
> (assessor ×2 reaplicado, escrita ×1 e votos ×9 novos reais, sem coleta/rede):
> comparação com premissa por candidato e limites explícitos, zero "Sobreposição
> parcial/documentada" no `report.md`, `missing_entity_sources` e
> `inferred_comparisons` vazios no `verification.json`. Verificação corresponde
> ao texto: overall `failed` preservado por 1 `unsupported` semântico (2–1,
> atribuição indevida documentada, sem reversão) e revisão incompleta (53/25/28
> explícitos). Residuais registrados no relatório técnico (promoção de globais,
> molde novo de LACUNA). 37 adiados do replay anterior seguem intactos em
> `runs/accept43-reconciliation/reproduction-a210966-replay/`. Técnico:
> `docs/RELATORIO_TECNICO_RECONCILIACAO_ACCEPT43.md` § final; suite 874/10
> skips + offline-22 11/11, exit 0. RA8 segue pendente (cobertura parcial).
> Próximo passo definido pelo solicitante.

> **Estado anterior — reconciliação accept43 (2026-11-04 local):** branch
> `feat/product-v1`, produto `a210966`, publicado em origin. A missão permanece
> **parcial**: os mecanismos corrigidos e os casos controlados foram exercitados,
> mas a comparação final ainda tem uma referência incompleta e uma formulação
> conflitante sobre sobreposição documentada/inferida, ambas sinalizadas no
> relatório. Não há base para declarar atendimento integral nem RA8 concluído.
> Próximo passo: corrigir a atribuição à fonte primária analisada e a redação da
> relação em mecanismo geral, testar também fontes que documentem uma relação
> entre projetos, e revalidar o texto e a verificação. Não atribuir uma fonte só
> porque consta no ledger, nem converter alertas ou votos em aprovação.
>
> A reprodução final `runs/accept43-reconciliation/reproduction-a210966-replay/`
> aplica o produto `a210966` ao corpus congelado: duas respostas do assessor e
> nove respostas da auditoria reaplicadas com prompts idênticos, escrita real
> anterior reaplicada com prompt idêntico exceto ID do run, zero novas chamadas
> nessa reprodução, sem coleta/embeddings. A escrita e os votos foram reais em
> `reproduction-bbecdc9-2`; as duas avaliações foram reais em
> `reproduction-8e728c2`. Na reprodução final: 25 itens com quórum, 19 sustained,
> seis partial, zero unsupported e falhas técnicas, 37 itens adiados; revisão e
> suporte parciais. O suporte cobre o Markdown final; os votos semânticos cobrem
> a síntese indicada pelo hash, não todo o Markdown. `accepted:false` permanece.
> Suite `suite-29.log`: 868 testes, 10 skips; runner `offline-21`: 11/11.
> O reconhecedor de exclusões de escopo é conservador e pode não reconhecer
> paráfrases válidas. A descrição de testes no plano histórico é estreita, embora
> a avaliação atual admita contribuição indireta. A premissa do harness 2.1.4
> está separada de `opencode v2.2.5` observado no host. Não houve nova prova de
> funcionamento integrado dos plugins.
>
> Técnico: `docs/RELATORIO_TECNICO_RECONCILIACAO_ACCEPT43.md`; evidências:
> `/home/thomaskyn/Projetos/hermes-research-dev/runs/accept43-reconciliation/`.
> Origem accept43, produção e Hermes ativo preservados. O plano preexistente e
> seu seletor foram preservados; não incluídos nos commits de produto.

> **Histórico corrigido (accept42→accept43, UTC 2026-11-04):** missão executada. Produto em
> 3 commits sobre `4ce8cef` (`a5a37f9` descoberta, `0a4719b` auditoria,
> `ac7aa6c` relatório) + 3 fixes residuais registrados em `a4b2237`
> (scope frasal, `technical_annex.md`, matriz/recomendação determinísticas).
> Run accept43 EXIT=0 sobre `d3b081a` (hashes pré==pós): overall `partial`
> (question 0.122, review incompleto por extração, 6/6 com quórum, support ok, stop
> `time` 1873s≥1800s). RA8 segue PENDENTE. Técnico:
> `docs/RELATORIO_TECNICO_MISSAO_ACCEPT42_43.md`. Runs:
> `/home/thomaskyn/hermes-runs/accept42/` (intacto),
> `/home/thomaskyn/hermes-runs/accept43/`; replays `/tmp/replay-accept43/`,
> `/tmp/replay-accept43b/`.
>
> Residuais e docs já registrados em `a4b2237`/`e40e464` e publicados.
> A reconciliação atual identificou defeitos remanescentes de escopo/identidade;
> “accepted:false” no original não era reprovação factual: 2 sustained, 3 gap,
> 1 partial; extração incompleta. Não há aqueles commits a fazer.

> **Histórico (2026-11-03):** HEAD `747ed29` (docs; produto congelado
> e validado em `38141b1`), branch `feat/product-v1`, push em dia
> (`feat/product-v1`=`747ed29`, `main`=`38141b1`). accept42
> **reconciliado**: 12/55 `partial`, 15/15 critérios avaliados,
> support `ok`, overall `partial` honesto; causa da inanição (Fase G)
> eliminada — resíduos são rigor do assessor + ruído do diagnose
> (amostra auditada), sem mudança de produto. RA8 segue PENDENTE.
> Plano ativo: `.planning/fase-g-selecao/task_plan.md`; deepwork:
> `.slim/deepwork/missao-accept42-selecao/progress.md`.
>
> Não declarar aceite: RA8 exige cobertura completa. A versão 2.1.4 é
> premissa de entrada do experimento; a versão observada do OpenCode
> deve ser lida do ambiente/artefatos.


## Pendências históricas à época (fase 3)

1. **accept42 reconciliado (2026-11-03)** — 12/55 `partial`, 15/15
   critérios avaliados, support `ok`, overall `partial` honesto; ACEITE
   §17 + MATRIX (RA8, tabela accept41/42) atualizados. RA8 segue
   PENDENTE; sem mudança de produto; sem novo run sem hipótese nova.
2. **RA8** — cobertura da pergunta continua aberta; accept41 ficou
   `2/41 partial` com 18 selection_context e 13 missing_dimension. O
   accept42 deve mostrar se as correções aumentam a cobertura útil.
3. **SearXNG/gateway** — sem container SearXNG e gateway 8001 parado;
   o run usa os canais disponíveis e registra a degradação. Não declarar
   bloqueio externo sem confirmar impacto no corpus do run.
4. **Resíduos Fase G** — janela de foco limitada a 600 chars; teste
   multi-entidade do sort de reenvio ausente; revisão final não repetida
   após ajustes de acento/plural (suite cobre). Registrar como limitação,
   não como aceite.

## Próxima ação histórica (fase 3)

Ler os artefatos do accept42 (relatório, diagnose, verification,
counters), comparar com accept41 e decidir se a entrega é útil/parcial.
Corrigir causa geral se houver defeito demonstrável; não repetir run sem
hipótese nova. Atualizar CONTINUIDADE e commit local dos docs.


## Push (2026-11-03, tarefa complementar)

- Repositório: `git@github.com:Thomaskynol/hermes-research.git`.
- Publicado: `feat/product-v1` → `38141b1`; `main` → `38141b1`
  (remoto vazio, mesmo HEAD, sem trocar o checkout ativo).
- Remoto anterior (`origin`) apontava para caminho local não-git
  (`/home/thomaskyn/.hermes/deep_research_outputs/gpt_researcher`);
  URL substituída após constatar que não era repositório. Sem
  force-push, sem reescrita de histórico.
- Identidade local configurada: `Thomaskynol <thomaskynol@gmail.com>`
  (só neste repositório; vale para novos commits).
- Autoria antiga divergente (sem reescrita, hashes preservados):
  commits intermediários como `hermes-dev <hermes-dev@local>`
  (ex.: `f3fb458`, `934f373`, `ac81ae9`); demais como
  `Thomas Kyn de Oliveira <thomaskyn@localhost.localdomain>`
  (ex.: `38141b1`, `64e0a3c`, `0e6ad16`). Nenhum commit nosso é de
  terceiro; são identidades locais anteriores do mesmo trabalho.
- Chave SSH usada: `~/.ssh/thomaskynol_github` via `GIT_SSH_COMMAND`
  (sem alteração no `~/.ssh/config`).
- Sem workflows de CI (`.github` inexistente); push não dispara
  pacotes, releases nem deploy.
- Orientação vigente: publicar código em desenvolvimento não equivale
  a declarar o produto aprovado. Fazer novos pushes ao concluir
  marcos validados desta missão. A atualização de continuidade e o plano da
  fase G mencionados naquele momento foram registrados em commits posteriores;
  essa nota histórica não representa pendência atual de publicação.


## Correções de leitura — contratos vigentes (A1–A6, `test_accept28_causes.py`)

Fatos observados preservados; o que muda é a leitura. As seções
históricas abaixo mantêm o texto original.

- **"support ok 3ª vez" (accept28)** — fato: o auditor marcou `support
  ok`. Correção (A6): support ok só sustenta veredito com question/review
  sem partial e sem misses do oráculo; accept28 teve question `partial`
  → overall `partial`, RA8 pendente. Contar "3ª vez" não é aceite.
- **Teto G5 contava só `discovered`** — fato: G5 subcontava o teto.
  Correção (A1): teto conta **todas** as required; `unexplored`
  reconciliado; writer nunca chama required de alternativa.
- **G6 token solto** — fato: token de reserva sem vínculo auditável.
  Correção (A1/A2): reserva com vínculo + trilha de avaliações por round
  para auditoria.
- **`N/A→insufficient` livre** — fato: a conversão ocorria sem evidência.
  Correção (A2): N/A delimitado respeitado; conversão exige evidência nova.
- **"integração testada" sem doc-interop** — fato: C9 combinação sem
  âncora rotulada. Correção (A4): inferência prudente declarada nunca é
  integração testada sem doc-interop com ≥2 formas cheias (vale nos dois
  espelhos); sem isso é LACUNA — foi o que moveu o diagnose 54/10→53/11.

## Instruções superadas

- **SUPERADA — run-com-vast-UP** (Missão 2): accept21 rodou vast UP e o
  corpus colapsou em funil YouTube sem transcrição (0/15); controle
  passou a vast DOWN.
- **SUPERADA — max-rounds-3 como cota fixa**: era default por
  comparabilidade entre runs, não cota da modelagem (§6); vigente A5
  (stop `rounds` com registro proporcional + fonte user/default).
- **SUPERADA — 5-itens-como-requisito**: são limites declarados (skips),
  não critérios de aceite.
- **SUPERADA — pausa-mid-model como ação**: limite conhecido do roteiro;
  R14.3 REAL entre rounds.
- **SUPERADA — isenção ampla de premissa / promoção de combinação
  plausível / LACUNA sem gates / bare utility ponderando /
  fora-do-corpus como `uncited`/ok / divergência excerto-vs-full
  silenciosa / redução de denominador** (Missão 4): vigentes contratos
  v2 + A3 (identidade universal em refs covered/partial) + A4
  (complementaridade declarada, nunca integração testada) + A6 (sem
  support ok com question partial + misses do oráculo). Motivos
  registrados: URL nua não conta (vale `[N]`/citação com identidade);
  afirmação existencial sem âncora vira LACUNA.

---

## Histórico preservado (texto original — ler com as Correções acima)

## Objetivo e escopo

Fechar o aceite v1: **RA8 `passed` em run real, sem flexibilizar**.
Os 5 itens "Sem validação" (`docs/ACEITE_V1.md`, seção Limites) são
**limites declarados (skips), não critérios de aceite** — item não
validado não vira requisito adicional automaticamente. Conferência
contra modelagem v1.1 + matriz (`findings.md`, Missão 2):

- **PENDENTE legítimo:** (1) gateway vast local no ar em run real
  (R3.1 = BLOQUEADO por ambiente).
- **Fora de escopo / limite documentado:** (2) deep 10h (referência, não
  cota — modelagem §6); (3) `conduct_research` (segunda interface, sem R
  distinto; ponta a ponta já REAL via CLI); (4) pausa mid-model (limite
  conhecido do roteiro; R14.3 REAL entre rounds); (5) multiusuário
  (sem requisito na modelagem/matriz).

Condição inegociável: **RA8 segue PENDENTE, sem flexibilizar** — o `verification`
do accept20 falhou corretamente por 1 inferência com versão vinda do contexto
do usuário, e o diagnose concordou (sem divergência).

## Branch e HEADs

- Branch: `feat/product-v1`.
- `b1cf76c` — base congelada do run accept21 (hashes produto reconferidos
  pré/pós-run, sem edição durante o run).
- `d665550` — **só docs** do run accept21 (plano + findings; sem produto).
- `817a77b` — **produto**: pool-reserve B3 + mention-window B4
  (`adaptive_coordinator.py` +207), auditoria granular B2/B5
  (`verification_report.py` +232), 2 testes novos (10 passed).
  Hashes workdir == frozen do run: `9b3a577a…` / `dcff1404…`.
- `a704463` — **produto**: quebra de monopólio single-host sem transcrição
  + mistura por diversidade (`native_transport.py`) e gate de quote/versão
  em LACUNA + ponderação no `verify_support` (`verification_report.py`),
  2 testes novos (`test_web_monopoly_break`, `test_lacuna_quote_gate`).
  Suíte combinada fresca pós-commit: **84 passed** (8 arquivos).
- `776af89` — docs do accept21 + suíte (HEAD congelado do run accept22;
  hashes reconferidos pré/pós-run, sem edição durante o run).
- `534c946` — **só docs** do accept22 (findings/progress/CONTINUIDADE;
  `git show --stat` confirma zero arquivo produto). Produto segue ==
  `a704463`; hashes workdir conferem com `hashes.frozen` do accept22.
- `15443a5` — **docs + 1 teste estrito** (Missão 2: coerência do plano;
  tautologia `or True` vira asserção RED→GREEN, 20 passed; matriz sync
  accept22 + escopo REAL-vs-PENDENTE; sem lógica produto alterada).
- `49508fe` — **produto**: consultado-vs-mencionado + inferência por
  premissas + fato-usuário + janela (`verification_report.py`,
  `report_renderer.py`, `scripts/citation_audit.py`, `tools/diagnose_run.py`
  + `tests/test_consultado_inferencia_usuario_janela.py`, 13 testes;
  foco 137 passed). Executado no run accept23 (hashes 8/8 OK pré/pós-run).
- `cc1bf1c` — **só docs** do accept23 (plano + findings + CONTINUIDADE;
  `git show --stat` confirma zero arquivo produto). Produto segue ==
  `49508fe`. Base da Missão 3 (Sessão 10: 3 contratos registrados).
- `d2e5438` — docs do plano (Missão 3 registrada, HEAD `cc1bf1c`).
- `a70d837` — **produto**: 3 contratos ([N] resolve + versão-premissa +
  complementaridade; `verification_report.py` + `tools/diagnose_run.py` +
  `adaptive_coordinator.py` + `tests/test_missao3_contratos.py`, 16 testes;
  prova isolada em cópia congelada do accept23). Executado no run accept24
  (hashes 8/8 OK pré/pós-run, sem edição no run).
- `a656535` — **produto**: 3 divergências unificadas (Div1
  extract/Classify + Div2 gates versão/literal + Div3 ponderação estreita;
  `tools/diagnose_run.py` +97, `verification_report.py` +6,
  `tests/test_divergencias_auditores.py` 11 testes TDD; `8040f87` no
  intervalo é só docs do accept24, zero produto — excluído).
- `5a4a78b` — **produto**: 3 contratos v2 (inferência positiva, entrega
  two-pass, identidade/atribuição; 17 testes TDD).
- `4b40bbe` — **produto**: identidade estrita (forma cheia com fronteira +
  corpo decide em refs; 2 testes TDD). Executado no run accept25
  (hashes 8/8 OK pré/pós-run, sem edição no run).

## Resultado accept25 (evidência em `/home/thomaskyn/hermes-runs/accept25/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 437s.
  Código `4b40bbe` (hashes 8/8 OK pré/pós-run, sem edição no run).
  Provisionamento investigado antes do run: vast provisionável
  (`fastapi/uvicorn/httpx` OK) mas NÃO subido — accept21 provou
  colapso YouTube com vast UP; SearXNG impossível (sem imagem/script;
  condição: `docker pull searxng/searxng`); embeddings impossível (sem
  launcher; condição: harrier UP em `172.17.0.1:8082`).
- Cobertura **0/35 + 0 N/A (0%)** (missing 11, selection_context 22,
  partial_legit 2; sem ok, sem assessor_error); síntese diagnose 62/9/55
  + declared 26; sentença 59 sustentadas + 12 unsupported com reason
  (versão/identidade/overlap) + 33 sem citação; `unsupported_claims []`,
  `outside_corpus []`; **support `ok` (2ª vez consecutiva)**;
  **overall `partial`; RA8 segue PENDENTE**.
- Prova real dos 3 contratos v2 (previsto na cópia congelada: check partial,
  diagnose + declared, verify partial): **confirmado** — 4 frases-combinação
  do §8 em canal `declared` (nenhuma promoção silenciosa, extrapolação
  recusada); §8-Anexo reflete verify final (two-pass, numbers estável,
  sem `not_run`); bandonker sem identidade isolada = 3 LACUNA declaradas,
  sem promoção por listagem. Citations 103, evidence 74, resolved 5,
  unknown [] (Missão 3 intacta).
- Corpus web sem YouTube (41 descobertos/24 usáveis, 10 citados, 6 na
  síntese): **5 nomes** (opencode-planner, planning-with-files, Plannotator,
  opencode-review, bandonker — este último LACUNA de identidade no excerto,
  declarada; `opencode-code-review` erskingardner fora da seleção por motivo
  do plano; URLs alternativos não investigados, sem fato afirmado).
- Resíduos sem corrigir (sem edição de produto neste lane): `selection_context`
  22 (assessor trouxe docs genéricos em vez dos docs da entidade — miss de
  seleção, sem leniência); `review partial` (revisão incompleta + 72 votos
  sem falha técnica); 4 `sem sobreposição` honestas; monopólio/M8 sem alvo.

## Resultado accept24 (evidência em `/home/thomaskyn/hermes-runs/accept24/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 715s.
  Código `a70d837` (hashes 8/8 OK pré/pós-run, sem edição no run).
  Provisionamento investigado antes do run: vast provisionável
  (`vast_local_retriever.py`, deps OK) mas NÃO subido — accept21 provou
  colapso YouTube com vast UP; SearXNG impossível (sem imagem/script;
  condição: `docker pull searxng/searxng`); embeddings impossível (sem
  launcher; condição: harrier UP em `172.17.0.1:8082`).
- Cobertura **9/56 + 0 N/A (16,1%)** (ok 8, partial_legit 14, missing 15,
  assessor_error 11, selection_context 7, synthesis_unsupported 1);
  síntese diagnose 49/2/66; sentence 38 sustentadas + 13 LACUNA com reason
  + 25 sem citação; `unsupported_claims []`, `outside_corpus []`;
  **support `ok` (primeira vez: accept21 partial, accept22/23 failed)**;
  **overall `partial`; RA8 segue PENDENTE**.
- Prova real dos 3 contratos (previsto na cópia congelada: citations 68,
  evidence ~50, resolved ≥4): **confirmado** — citations 68, evidence 51
  (era 0), resolved 5 (era 0), unknown []; versão numérica 2.1.4≥2.1.2
  sustentada + funcional sem fonte = LACUNA (`versão exata ausente`, 3×);
  5 frases-combinação LACUNA + "INFERÊNCIA NÃO SUSTENTADA, NÃO AFIRMAR".
- Corpus web sem YouTube (30 descobertos/16 usáveis, 8 citados, 6 na
  síntese): **5 nomes** (planner, planning-with-files, Plannotator,
  handoff, local-memory — este último LACUNA de identidade no excerto,
  declarado; `c-discover` synthesis_unsupported pelo elo fraco).
- Resíduos sem corrigir (sem edição de produto neste lane): snapshot do
  renderer-§8 diz `support not_run/sem citações verificáveis` (camada
  claim/URL-nua) vs auditor final `support ok` — divergência de mensagem,
  sem efeito no veredito; `selection_context 7` (miss do assessor, não
  leniência).

## Riscos amarelos (limitações registradas — sem refatorar)

Achados de revisão classificados amarelos (não-críticos; nenhum teste
prova bug crítico — **sem refatoração neste passo**; reavaliar só com
evidência de teste). Espelho resumido em `docs/REQUIREMENTS_MATRIX.md`
§ Escopo.

- **Janela legado `u>start`** (`adaptive_coordinator.py:473`, `take()`):
  caminho sem grupos usa `any(start < uend and u > start)` — janela que
  começa antes mas invade o span usado não é dedupada; caminho com
  grupos (B4) usa `u < end` estrito. Mantido por testes de regressão do
  preenchimento legado.
- **Ranking low** (`_rank_unfetched`, l.1311): contagem de ocorrências
  de substring na URL; empate mantém ordem original. Sem ranking
  semântico — URL fraca pode vencer empate.
- **Nota duplicada** (`select_ops`, l.1537): nota `pool reserve:` anexada
  por round; mesmo alvo em N rounds ⇒ N notas. Cosmético, sem efeito
  lógico (reserva em si é dedupada por `used_in_batch`/evidência/falha).
- **Single-hit transcrição** (`native_transport.py:287`,
  `_needs_diversity`): 1 hit com marcador `[transcript]/[spoken]`
  isenta a página inteira da mistura por diversidade — suprime fallback
  mesmo com restante da página monopolizada.
- **Versão major nua** (`verification_report.py:150`,
  `_text_versions`): regex só casa `\d+\.\d+`/`Vn`; "versão 2" isolada
  é invisível ao gate — par "v2" (frase) × "2.1.4" (doc) decide no
  overlap genérico, não em lógica de versão.
- **LACUNA overlap 0** (`verify_support`): frase LACUNA com citação
  in-corpus mas overlap 0 ⇒ unsupported. 17 casos no accept22 —
  rigor correto, volume residual a acompanhar.
- **B5 convergência** (`verify_support` l.1028 + `_selection_window`
  l.189): ponderação `sentence_support` quando a citação é do doc da
  entidade; convergência/estabilidade entre rounds provada só em unit
  (accept21/22 sem alvo: M8 sem disparo, monopólio sem alvo).
  Divergência excerto-vs-auditado fica explícita via `hash_source`,
  nunca silenciosa.

## Resultado accept23 (evidência em `/home/thomaskyn/hermes-runs/accept23/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 588s.
  Código `49508fe` (hashes 8/8 OK pré/pós-run, sem edição no run).
- Cobertura **0/55 + 0 N/A (0%)** (ok 0, partial_legit 24, missing 14,
  assessor_error 17; sem selection_context/synthesis_unsupported);
  síntese diagnose 49/1/66; verification-sentença 48/50 ok + 15 LACUNA +
  1 inferência declarada; **verification overall `failed`**;
  **RA8 segue PENDENTE**.
- Corpus de listagem sem YouTube (47 descobertos/12+ hosts, 18 usáveis,
  18 analisados, 0 erro grave): **5 nomes com identidade**
  (lit-opencode, opencode-planner, Plannotator, opencode-handoff,
  opencode-local-memory). Failed por 4 LACUNA [27,3,14,17] ancoradas em
  listagens (classe accept20, 17 lá e cá) + 1 frase `[8]` sem overlap.
  Sem URLs nuas (classe accept19/22 ausente).
- Fixes: inferência-contida exercitada e segurou (2× declarada, combinação
  recusada, c12 insufficient); fato-usuário contido 2º run (`user://` fora
  do corpus); janela sem divergência; monopólio/b81e8f6 sem alvo.
  Resíduo sem corrigir: contador de citações cego a `([N])`
  (evidence/resolved 0; sentença 48/50 é a camada que vale).
- Antes/depois vs accept22: 11/54→0/55 por corpus de listagem (produto E
  corpus distintos — sem causalidade isolável); melhorou: 0 URLs nuas,
  inferências contidas, fato-usuário contido, janela auditada.

## Resultado accept22 (evidência em `/home/thomaskyn/hermes-runs/accept22/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4,
  **vast DOWN + SearXNG DOWN** (curl 000 pré e pós-run), EXIT=0, 658s.
- Cobertura **11/54 + 0 N/A (20,4%)** (ok 10, partial_legit 11, missing 16,
  selection_context 16, synthesis_unsupported 1); síntese 65/9/59;
  **verification overall `failed`**; **RA8 segue PENDENTE**.
- Corpus saudável sem YouTube (31 descobertos/11 hosts, 28 usáveis,
  22 analisados, 0 assessor_error): **5 nomes com identidade**
  (lit-opencode, opencode-browser, plugin-testing/dzianisv,
  opencode-plugins/jadmadi, Context7). Failed por 5 URLs nuas fora do
  corpus + 3 inferências de combinação reprovadas [12,13,14] + 17 LACUNA
  sem overlap — métodos de acordo, sem leniência em URL nua.
- Fixes: cc0f3ff com sinal positivo fraco (classe accept20 ausente;
  sentença compat declara LACUNA contida); quote-gate manteve `failed`
  em URL nua (leniência accept21 estreitada ao caminho de índices `[N]`);
  monopólio-break e b81e8f6 sem alvo (sem monopólio; M8 sem disparo).
  Residual: selection_context 16; c11/c12 insufficient.
- Contraste causal: vast DOWN 11/54 vs vast UP 0/15, mesma config
  (ddgs+extração cobrem; funil YouTube sem transcrição colapsa).

## Resultado accept21 (evidência em `/home/thomaskyn/hermes-runs/accept21/`)

- Config: pergunta do aceite, medium/max-rounds-3, contexto 2.1.4, EXIT=0, 343s.
- Cobertura **0/15 + 0 N/A** (15× `missing_dimension_evidence`); síntese
  7/79/15; **verification overall `partial`**; **RA8 segue PENDENTE**.
- Corpus colapsou em funil YouTube sem transcrição (`yt_live_fetches=0`,
  40/2/2, 0 entidades) — utilidade **nula como guia**, mas **negativo honesto**.
- `cc0f3ff`/`b81e8f6` **não exercitadas** (sem afirmação de versão; M8 sem
  disparo). Fixes B2–B5 acima também **não exercitados** em run real.
- Regressão registrada sem corrigir: 15 frases LACUNA com citação fora do
  corpus ⇒ só `partial` (accept19 falhava corretamente 1 citação assim) —
  suspeita de **leniência LACUNA × citação**.

## Serviços (2026-10-31, pós-run accept24)

- `hermes-gateway` UP (9119/8081). **vast `:8001` DOWN** (accept21 subiu
  on-demand e desligou; accept22, accept23 e accept24 rodaram com DOWN
  pré/pós confirmado; accept24: provisionável mas não subido — decisão
  registrada no RELATORIO_ACCEPT24.md). SearxNG DOWN (sem imagem docker;
  condição: `docker pull searxng/searxng`), embeddings DOWN (sem launcher;
  condição: harrier UP em `172.17.0.1:8082`) — ver tabela de
  provisionamento no RELATORIO_ACCEPT24.md.

## Ambiente e configuração efetiva

- CLI: `opencode v2.2.5` (verificado com `opencode --version` em 2026-10-31).
- Serviços (observado em 2026-10-31 via `docker ps` + `ss -ltn`):
  `hermes-gateway` UP (9119/8081); **vast, searxng e embeddings STOPPED** —
  sobem on-demand (`:8001` e `:8888` sem listener).
- Retriever (docstring de `vast_local_retriever.py`):
  `RETRIEVER=custom,searx,duckduckgo,arxiv`,
  `RETRIEVER_ENDPOINT=http://127.0.0.1:8001/`,
  `SEARX_URL=http://127.0.0.1:8888/`.
- Atenção: `SEARXNG_URL` do roteiro usa IP de bridge (`http://172.18.0.2:8888`) —
  **frágil, pode mudar**; revalidar com `/healthz` → 200 antes de cada run.

## Correções validadas só em unit test (pendentes de run real)

| Commit | O que muda | Validado até agora |
|--------|------------|--------------------|
| `cc0f3ff` | contexto do usuário não é evidência (regra estreita Missão 3: comparação numérica contra mínimo declarado = sustentada (premissa+corpus); compat funcional/integração sem fonte que mencione a versão = LACUNA); bucket `na_scoped` no diagnose | unit test + **contido em 2 runs reais (accept22: 1º sinal; accept23: 2º sinal, `user://` fora do corpus)** |
| `49508fe` | consultado-vs-mencionado + inferência-por-premissas + fato-usuário + janela | foco 137 passed + **exercitado em run real (accept23: inferência contida, fato-usuário contido 2º run, janela sem divergência)**; resíduo: contador cego a `([N])` (registrado, sem corrigir) |
| `a70d837` | 3 contratos: `[N]` resolve + versão-premissa + complementaridade | 16 testes (TDD RED→GREEN) + prova isolada em cópia congelada + **PROVADO em run real accept24: support failed→ok, evidence 0→51, resolved 0→5; versão numérica sustentada; combinação recusada**; resíduos: renderer-§8 `not_run` vs auditor `ok` (mensagem, sem efeito), `selection_context 7`, local-memory sem identidade literal |
| `a656535` | 3 divergências: URL evidência sem `[N]`, LACUNA com gates, ponderação estreita | 11 testes TDD (`test_divergencias_auditores.py`, RED 3→GREEN) + 73 foco verde + efeito isolado em cópia accept24 (diagnose 49/2→39/12, verify ok→partial, convergindo com check); sem novo run real |
| este passo | identidade estrita: `_identity_matches` exige forma cheia com fronteira (`Widget Alphabeta` não casa `Widget Alpha`, como `_entity_mentioned`); `_evaluation_refs_have_identity` audita só o corpo, slug da URL sozinho não basta (alinha a `_entity_corpus_docs`) | 2 testes TDD (`test_missao4_contratos.py`, RED 2→GREEN; arquivo 19 passed, versão-premissa + POS/NEG intactos) + combinados 65 passed + ampla 555 passed (1 falha ambiente pré-existente, igual na árvore limpa); sem novo run real |
| `b81e8f6` | M8: entidade fraca sem troca registra pool não explorado | só unit test (M8 sem disparo em accept21 e accept22) |
| `817a77b` | B3 pool-reserve; B4 mention-window; B2/B5 auditoria granular | 10 passed (2 arquivos novos); sem prova em run real |
| `a704463` | quebra de monopólio single-host + diversidade; gate de quote em LACUNA | unit test + suíte 84 passed; accept22 sem alvo para monopólio, quote-gate manteve `failed` em URL nua |

Unit tests pós-commit: `test_audit_granularity` + `test_pool_reserve_mention_window`
10 passed, mais `test_web_monopoly_break` + `test_lacuna_quote_gate`
(suíte combinada fresca 84 passed). Accept22 deu primeiro sinal real
parcial (ver seção accept22 acima); prova isolada das quatro correções
segue pendente.

## Bloqueios, hipóteses e próxima ação

- **Bloqueios:** serviços vast/searxng parados (on-demand, esperado);
  SearXNG com IP frágil; risco de flake do assessor no round 0 (não-lista 2×
  no accept19); variância de retrieval single-run (~±0,1) pode mascarar ganhos.
- **Hipóteses:** `cc0f3ff` elimina a classe de falha do `verification` do
  accept20 sem derrubar `ok` legítimos; `b81e8f6` reduz `missing` silencioso
  no M8. Detalhes em `.planning/agent-reach-accept21/findings.md`.
- **Instruções superadas (removidas na Missão 2, seguem removidas):**
  run-com-vast-UP, rounds-3-como-fixo, 5-itens-como-requisito,
  pausa-mid-model como ação.
- **Instruções conflitantes Missão 4 (removidas, seguem removidas):**
  isenção ampla de premissa, promoção de combinação plausível, LACUNA sem
  gates, bare utility ponderando, fora-do-corpus como `uncited`/ok,
  divergência excerto-vs-full silenciosa, redução de denominador.
  Nenhuma restante ativa nos prompts (writer/assessor estreitos).
- **Lição do accept19 (não repetir):** run rodou sobre código desatualizado por race
  com o commit — **conferir `git rev-parse HEAD` antes de cada run**.
- **Próxima ação (accept25 EXECUTADO — 3 contratos v2 provados em run real,
  RA8 segue pendente):** hipótese do run era a primeira prova real sob
  `4b40bbe` (Missão 4 v2 + identidade estrita) — cumprida: POS→declared,
  two-pass §8=final, identidade sem promoção; support ok 2ª vez; overall
  `partial` por cobertura (0/35), não por veracidade — gargalo é
  corpus/seleção (`selection_context 22`, `assessor_error 0`), não
  leniência. Nota: embeddings `:8082` UP mas path native fez zero requests
  — conexão/demonstração integrada fica para o próximo lane, sem produto
  neste lane. Fechar Phase 5 (ACEITE_V1_RESULTADO + check-complete); próximo
  run só sob nova hipótese explícita.
  - (1) `[N]` resolve — **PROVADO em run real**: citations 68, evidence
    51, resolved 5, unknown [] (accept24); `support failed→ok`;
  - (2) versão-premissa — **PROVADO em run real**: 2.1.4≥2.1.2 sustentada
    ([5]); funcional sem fonte = LACUNA `versão exata ausente` (3×);
    fato-usuário contido (3º run);
  - (3) inferência-complementaridade — **PROVADO em run real**: 5 frases
    LACUNA + "INFERÊNCIA NÃO SUSTENTADA, NÃO AFIRMAR"; diagnose sem
    promoção indevida.

## Accept26 (2026-10-31) — sonda de embeddings no path native PROVADA

- Produto mínimo (TDD RED→GREEN, 6 testes `test_native_embeddings.py`):
  `_assess_round` faz 1× `POST {EMBEDDING_SERVER_URL}/embeddings` por rodada
  (default `http://172.17.0.1:8082/v1`, modelo `harrier-oss-v1-0.6b`);
  registra endpoint/modelo/prompt_tokens em `state["embeddings"]` + nota;
  manifest expõe o resumo. Nunca levanta, nunca gasta budget, nunca altera
  avaliações; down = `unavailable` + efeito, sem fallback; `sync_config.py`
  intocado. `adaptive_coordinator.py` +101, `run_manifest.py` +25,
  `adaptive_state.py` +1.
- Run real `hermes-runs/accept26` (8082 UP, light, native, max-rounds 2,
  EXIT=0, stop `rounds`, coverage `partial` 0.04): **3 probes ok**
  (prompt_tokens 58 cada) em state+notas+manifest; `--metrics`
  `prompt_tokens_total` 16→76 (repeats no KV-cache: cached 117 ≈ 2×58).
  Usou embeddings: `_assess_round`. Dispensou: planner, search/fetch,
  writer, auditor, budgets. Contadores 35/25/25/25/6/7. Relatório:
  `hermes-runs/accept26/RELATORIO_ACCEPT26.md`. RA8 segue pendente
  (gargalo é corpus/seleção, não veracidade).

## Accept27 (2026-11-01) — boost semântico funcional no path native PROVADO

- Produto (TDD RED→GREEN, 18 testes `test_native_embeddings*.py`):
  `_semantic_boost` ranqueia candidatos (query estável pergunta+dimensões
  do plano; docs truncados a 1500 chars) via batch `embed_texts_native`
  (1 chamada/rodada só com hashes novos; cache por hash de conteúdo;
  `HERMES_NATIVE_EMBEDDINGS=0` desliga); entrega ao assessor pelo hook
  opcional `set_semantic_rank` (custom sem hook: inalterado) que reordena
  SÓ os lotes não-enviados; writer usa o rank como desempate no restante
  (refs/piso intactos). Só reordena: reservas de entidade, seleção
  prévia e gates (`_evaluation_refs_have_identity`, seleção, `verify_support`)
  intactos. Down = `unavailable` + efeito, sem raise, sem fallback, seleção
  antiga. Registro separado do gerador: `state["embeddings"]`
  (calls+totals) e `manifest.embeddings` (server_calls/vectors/
  prompt_tokens_total/cache_hits). Sonda record-only virou diagnóstico
  manual (`_probe_native_embeddings`, sem auto-call). `adaptive_state.py`
  e `verification_report.py`/`diagnose` intocados.
- Demo corpus congelado `/tmp/demo_emb27` (md5 intacto antes/depois,
  mesmas entradas e limites): (a) seleção antiga `[D1,D2]` perdia D3
  (insuficiência preservada) e nova `[D1,D3]` recupera com `covered`
  (1 batch real 8082: 1012 tokens, 4 vetores, rank D3>D1>D2);
  (b) D2 na seleção mas `identity mismatch` rejeita (applied=[]);
  (c) excertos chegam ao writer com refs (`included_urls=[D3,D1,D2]`,
  blocos `Fonte <url>:` no prompt). Detalhe em `RESULTADO.md` + JSONs.
- Run real `hermes-runs/accept27` (8082 UP, vast DOWN como controle,
  medium, native, max-rounds 3, `HERMES_NATIVE_EMBEDDINGS=1`): EXIT=0,
  stop `rounds`, 501s, coverage `partial` 0.333 (8 covered + 11 partial +
  7 insufficient), model_calls 7 (gerador, separado), contadores
  37/34/34/30/6/6, verification overall `partial`. **4 calls 8082**
  (1/round, `http://172.17.0.1:8082/v1` + `harrier-oss-v1-0.6b`),
  36 vetores, 14475 prompt_tokens, cache_hits 51 (0→7→15→29); métricas
  servidor 3125→17460 (+14335) + cached +140 = 14475 reconciliado;
  manifest separa embeddings do gerador; writer com corte `ordem
  semântica`. Gates: 15 identity-mismatch rejeitadas, 0 outside-selection,
  0 down. Sem causalidade vs accept26 (perfis distintos). Relatório:
  `hermes-runs/accept27/RELATORIO_ACCEPT27.md`. RA8 segue pendente
  (teto de rounds/cobertura, não veracidade).

## Accept28 (2026-11-01) — pergunta ORIGINAL do aceite (pesquisa, sem produto)

- Congelamento: HEAD `95b0ec7`, diffstat vazio, sha256 de 11 arquivos
  produto idênticos pré/pós-run (`hashes.frozen == hashes_post.frozen`);
  `opencode v2.2.5` à parte; pergunta usa `installed_opencode_version=2.1.4`
  como ENTRADA via `--context` (sem presumir versão). Infra medida pré/pós:
  vast `:8001` DOWN (controle), SearXNG DOWN (sem imagem, sem fallback),
  embeddings 8082 UP (`harrier-oss-v1-0.6b`).
- Run real `hermes-runs/accept28` (medium max-rounds 3, native+opencode
  `muse-spark-1.3-contributor`, `--auto-plan`,
  `HERMES_NATIVE_EMBEDDINGS=1`): EXIT=0, stop `rounds`, 603.7s, cobertura
  **6/55 + 0 N/A = 0.109 `partial`**, verification overall `partial`
  (execution ok, question/review partial, **support ok 3ª vez**),
  model_calls 7, contadores 43/22/22/22/9/6, ops 12 (9 ok/3 falha),
  fetches 30, queries 9. **8082 com efeito**: 4 calls, 23 vetores, 10168
  tokens, cache 47; servidor 17460→27577 (+10117) + cached +51 = 10168
  reconciliado. Contratos v2-1/v2-2/v2-3 observados (2.1.4 premissa [U],
  sem promoção selection_context, `[N]` intacto).
- Diagnose: ok 6, partial_legit 15, missing_dimension_evidence 18,
  selection_context 8, assessor_error 8 (este último = comportamento
  correto sobre listagens, bucket overstates — observação, não defeito);
  síntese 54 supported / 10 unsupported (LACUNA/INFERÊNCIA honesta) /
  71 uncited. Utilidade: 4 plugins com âncora + oh-my-opencode-slim
  LACUNA declarada (+ contradição do plano flagrada); nenhum plugin
  demonstra melhorar implementação/testes/revisão no corpus. Relatório:
  `hermes-runs/accept28/RELATORIO_ACCEPT28.md`. RA8 segue pendente.

## Pós-accept28 (2026-11-01) — 5 causas + 9 achados revisão, sem hardcode

- Lanes read-only: DESC-SELEÇÃO (G5 contava só discovered, G6 token solto,
  N/A→insufficient sem evidência nova, sem op descoberta sem nome),
  IDENT ([17] genérico pega carona em [1], c1 global vs síntese C1,
  C9 sem âncora rotulada integração testada), ORÇAMENTO (stop rounds sem
  proporção, max-rounds default por comparabilidade, support ok com
  question partial + misses).
- Fix único writer via TDD: tests/test_accept28_causes.py (36 testes:
  G5/G6/reserva/N-A direcional/hash conteúdo/identidade universal/
  sem-âncora/LACUNA/rounds proporcional+source/oráculo condicional/
  slug-URL/floor auditado); ajustes test_discovery_cells/identity_gate/
  na_swap para novo contrato. Sem literais de produto (shared tokens do
  plano+pergunta, kind-words genéricas).
- Evidência: causes 36/36 OK, suite 599 OK (595+4 novos, RED→GREEN do
  positivo; skipped=10 pré-existentes), ajuste de escopo em
  `verification_report.py:1045-1051` (`declared_inference` com scope
  explícito: LACUNA/complementaridade, não integração testada),
  diagnose congelado 54/10→53/11 (só C9 combinação vira LACUNA sem-âncora),
  repro R1/R2/R3 EXIT=0, hashes coordinator c6e90899 verification 64a30d45.
  Revisão cavecrew 1🔴+8🟡 aplicada; resíduo URL+corpo eliminado (2646/2923).
  Limites: sem revalidar runs antigos além accept28; diagnose_audit pós-hoc;
  HEAD 36ff960 ≠ run 95b0ec7; sem prod/8082 (offline).

## Accept29 (2026-11-01) — pesquisa real sobre 1364dc1: 4/40+6N/A=0.10 partial, support ok 4ª vez, stop rounds c/ reserva, 8082 14967 tokens reconciliado, 3+1 plugins sem testes demonstrado, RA8 pendente. Detalhe em `docs/RELATORIO_TECNICO_MISSAO_POS28_ACCEPT29.md`; relatório do produto em `/home/thomaskyn/hermes-runs/accept29/adaptive_accept29/report.md`.

## Fase A accept29-ativas (2026-11-01) — 5 causas + re-review, sem hardcode

- Review independente (cav-3: 1🔴+1🟡+4❓) + 5 lanes read-only; reconciliação em `.slim/deepwork/missao-accept29-ativas/`.
- Fix fix-3 (TDD 14 testes): G5 conta só candidatas (plataforma fora), descoberto=candidate, source harness/user/default + rounds proporcional, partial_declared, editorial no gerador, AGENTS.md +3 linhas (harness≠humano; causa antes de corrigir; sem repetir pesquisa).
- Re-review (cav-4): 0🔴 4🟡, 🔴 resolvido. Remediação fix-4 (4 testes): notes de descarte, dedup de gaps, na_cells com rótulo, partial com só-inferências.
- Evidência: suite 617 OK skipped=10 EXIT 0; diagnose accept29 antes==depois (46/44/14/76, sem regressão — run congelado não exercita os 4 caminhos).
- Commit Fase A abaixo (só produto+testes+CONTINUIDADE; AGENTS.md alterado no workdir, untracked).

## Fase B accept30/31 (2026-11-01) — seleção diagnosticada e corrigida, re-run justificado

- accept30 real (HEAD 3a2984b, EXIT 0): 0/55+0N/A, support failed (1 claim corretamente reprovado), overall failed; 8082 reconciliado; causa nova: selection_context 32 (quarentena `_sent` + teto JSON 12k; janela 1200 chars) + by_cells estimado 46 vs plano real 55.
- Fix fix-4 (TDD 8+4 testes): M1 reenvio p/ células abertas (cap 1/célula, trilha, par url×célula servida), M2 pin dimensão×menção (conta como turno do grupo), M3 rounds do plano real pré-loop, M4 rodízio gap_query; c4 vazia preservada insufficient.
- Gate Fase B: APROVAR COM RISCOS (0🔴 3🟡 remediados). Suite 629 OK skipped=10 EXIT 0; diagnose accept30 antes==depois (congelado).
- Commit Fase B abaixo; re-run accept31 com a hipótese nova (seleção), sem repetição sem causa.

## Fase B accept30/31 (2026-11-01) — causa seleção + hook proporcional

- accept30 real (HEAD 3a2984b, EXIT 0): 0/55+0N/A, support failed (1 claim corretamente reprovado), overall failed; 8082 reconciliado. Causa nova: quarentena `_sent` + teto JSON 12k (docs da r0 nunca recitados) + janela 1200 chars; by_cells usou estimativa 46 em vez de 55 reais.
- Fix M1–M4 + remediação 3🟡 (suite 629 OK). accept31 real (HEAD 06a5239, EXIT 0): 1/53+2N/A partial, overall partial; hook não adotou (plano v1 15 células). Fix M5: re-adoção em expansão (`_proportional_cells`), suite 633 OK skipped=10 EXIT 0, diagnose congelado idêntico, gate M5 sem issues.
- Commit Fase B abaixo. RA8 segue pendente (nenhum run com cobertura plena).

## Fase C gargalos pós-accept31 (2026-11-01) — resend-focus + hook proporcional em produção

- accept32 real (HEAD 9c311ad, EXIT 0, 571s): 0/56 partial; diagnose missing=20,
  selection_context=18 (era 29 — resend-focus com efeito), assessor_error=16,
  partial=2, ok=0. Stop rounds 3 source=default com folga total.
- Causa nova (código + runtime): `new_state` inicializa stop={reason:None}/report={}
  nunca-None → guarda M5 sempre-True pós-início → re-adoção impossível; base no
  plano v1 (0 cells) silenciosa. Testes M5 usavam state manual (mock-behavior gap).
- Fix accept33 (commit 4615ccb, TDD RED 3 falhas→GREEN): guarda por decisão real +
  trace note `proporcional:` sempre que cells!=last; 4 testes com new_state REAL;
  full 638 OK skipped=10 EXIT 0.
- accept33 real (EXIT 0, 1168s, freeze pré==pós, 8082 +22128/+224): hook ADOTOU 3→7
  em produção (2 trace notes), 8 rounds; diagnose missing=14, sel_ctx=31,
  assessor=0, partial=10, ok=1 (1/56); síntese 47/4/119; overall failed
  (support: 4 LACUNA honestas sem literal citado). Gargalo residual: largura de
  seleção por lote (teto 12k) + by_model=by_cells=7; 16 lacunas abertas com folga.
- Relatório do produto accept33 honesto (LACUNA declaradas, finalistas distintos —
  plano churna entre runs). RA8 segue pendente.
- Detalhe em `docs/RELATORIO_TECNICO_MISSAO_GARGALOS_POS31.md`; runs em
  `/home/thomaskyn/hermes-runs/accept32/` e `.../accept33/`.

## Fase D missão accept34 (2026-11-01) — AGENTS.md + diversidade de lote + isenção do writer, aceite parcial

- AGENTS.md +3 pontos (testes com construtores reais; parcial/incremento≠missão;
  bucket≠causa + alcance de revisão + estimativa≠limite≠consumo). Era untracked,
  agora versionado (commit 3da5de8).
- Fix accept34 (TDD RED 6 falhas→GREEN, `tests/test_accept34_cell_diversity.py` +
  fixture `accept33_c9e6.json` com new_state REAL): M-A (ancora:dependencias,
  resend só-required, `_open_cell_coverage` + reordenação gulosa do sufixo,
  mesmos tetos) + M-B (`_writer_gate_guidance`: isenção explícita, premissa
  do usuário marcada, sem literais indevidos, fora-do-corpus). Revisão cav-1:
  No issues (alcance limitado). Suite então 647 OK skipped=10 EXIT 0.
- accept34 real (`/home/thomaskyn/hermes-runs/accept34/`, HEAD/hashes pré==pós
  3da5de8, EXIT 0, 874s, 8082 +13942/+548 cached, opencode v2.2.5 observado,
  premissa controlada 2.1.4): q18/f49/m11/rounds8; stop rounds max_rounds=7
  source=default (hook 3→5→7, by_cells vincula/empata), 15 lacunas abertas,
  folga total. Diagnose (55): sel_ctx 14 (era 31), missing_dim 23 (era 14),
  partial 18 (era 10), ok 0. Síntese 41/7/103. Verification: support
  failed→ok, overall failed→partial (question/review partial, 0/55).
- Atribuição: M-B demonstrado em produção (isenção + premissa marcada; 4 gates
  não repetidos); M-A sem traço em runtime (grep diversidade=0) — queda
  sel_ctx confundida por churn (finalistas/critérios/corpus 45→28 mudaram);
  resend só-required confirmado (só alvos cand-*). RA8 segue pendente.
- Revisão direcionada cav-2 (3🔴1🟡1❓): Context7[4][26] refutada (doc contém
  "fetches current documentation directly from source repositories" —
  falso-negativo do overlap PT×EN); Ranger/Refactoring parcial refutada como
  contradição (refs reais; §1 nega fonte própria/combinações); URLs truncadas
  §5 defeito real — causa `src[:80]` em `_gap_next`, corrigido (URL integral
  + regressão em `test_accept29_causes.py`; URL completa em §7 [19]; artefato
  congelado preservado); support/execution = semânticas pré-existentes.
- Suite final 648 OK skipped=10 EXIT 0. Detalhe em
  `docs/RELATORIO_TECNICO_MISSAO_ACCEPT34.md`; entrega em
  `/home/thomaskyn/hermes-runs/accept34/adaptive_accept34/report.md`.
- Fila restante (fora desta autorização/escopo): stop default com lacunas
  abertas; churn auto-plan entre runs; overlap × tradução no auditor;
  observabilidade do engajamento M-A.

## Referências

- Roteiro: `docs/ACEITE_V1.md`
- Resultado acumulado: `docs/ACEITE_V1_RESULTADO.md` (§16 = accept19/accept20)
- Relatórios: `/home/thomaskyn/hermes-runs/accept19/DIAGNOSIS_accept18.md`,
  `/home/thomaskyn/hermes-runs/accept20/RELATORIO_ACCEPT20.md`
- Contrato reach: `docs/AGENT_REACH.md`

## Fase E controle+aceite (2026-11-02) — 5 itens demonstrados, aceite accept35 parcial
- Autorização: corrigir seleção/ranking, dimensionamento e demonstração (defaults/
  heurísticas internas, tetos globais intactos); validação controlada antes, sem
  nova pesquisa completa.
- Fixes em `adaptive_coordinator.py` (commit a492bdd): F1 cuts do assessor
  persistidos no registro de assessments; F2 `_writer_complementarity_guidance`
  (INFERÊNCIA marcada+citada, nunca integração testada); F3
  `_candidate_corpus_status` 3-vias com fallback neutro pós-revisão. Testes
  `tests/test_fase_e_controle.py` (7). Suite 655 OK skipped=10 EXIT 0.
- Revisão independente dos fixes (diff inline): 1🔴 corrigido (fallback neutro +
  teste RED-primeiro), 1🟡 documentado (teste 4 é caracterização), 2❓ resolvidos.
- Aceite accept35 sobre a492bdd congelado (HEAD/hashes pré==pós, 8082 +20746/+692
  cached, pergunta accept34 + premissa 2.1.4): EXIT=0; q19/e85/m12/rounds8; stop
  rounds 7 default, 15 lacunas, folga total. Cobertura 2/55 (c2/c10 pwf; era 0/55).
  Diagnose: sel_ctx 20, missing 12, partial 15, ok 2, assessor_error 6. Síntese
  35/9/104, declared 15. Support ok, overall partial.
- Produção confirma: nota "lote por diversidade: 3 célula(s)" em state.json (F1);
  3 INFERÊNCIAs marcadas+citadas §10 (F2); "fonte própria" ×31 + status fora do
  corpus neutro §0 (F3); isenções de versão; URLs §5 integrais, 40 números ok,
  unknown=[].
- Triagem: 6× [11] "unsupported" são falso-negativo do overlap PT→EN (fonte contém
  os literais — conferido); `assessor_error` ×6 é rotulagem do diagnose (c8/c9/c10
  sem description no plano); cosméticos sem efeito (repetição linha 24, [26][26]).
  Churn auto-plan repetido: delta entre runs não é causal.
- Entrega parcial: `docs/RELATORIO_TECNICO_MISSAO_FASE_E.md`;
  `/home/thomaskyn/hermes-runs/accept35/adaptive_accept35/report.md`.
  Fila: stop default com lacunas; churn auto-plan; recall do overlap; leitura 1,5%.

## Fase F contratos+aceite (2026-11-02) — 4 contratos demonstrados, aceite accept41 parcial
- Fixes: prompt preserva per_candidate + aviso de colapso; veto fora-do-corpus por
  frase; detector de contradição com identidade estrita; guarda anti-ausência-falsa
  (prompt + verifier `_false_absence_flags`); higiene user-facing (ids→rótulos,
  jargão→PT, N/A com escopo, corpo sanitizado, swap curado no corpo). Suite 733 OK.
- Demo C3 offline (valid-fase-f/c3-substitution/): reais inertes (correto) + par
  mínimo dispara troca real até o Markdown. Revisão 0🔴/4🟡, tudo corrigido (TDD).
- Aceite accept41 sobre 934f373 congelado (hashes iguais, 8082 +21249/+172):
  EXIT=0; q16/e88/m8/rounds7; stop rounds=6 default, 15 lacunas, folga total.
  Cobertura 2/41 (10 N/A fora do denominador); support ok; overall partial.
  Corpus 50/43/43/43/6/8; leitura 1,2%. Contrato 2 com veto disparado no run.
- Residual: §1-vs-§3 defasado p/ globais (assessor inicial vs síntese; fila);
  overlap com recall baixo (informativo); `ponytail:` ecoado na síntese; notas
  repetidas no anexo. Detalhe em `docs/RELATORIO_TECNICO_MISSAO_FASE_F.md`;
  entrega em `/home/thomaskyn/hermes-runs/accept41/adaptive_accept41/report.md`.
