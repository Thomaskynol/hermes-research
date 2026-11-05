# Reconciliação do accept43 — corpus congelado

## Escopo e versões

Missão: demonstrar interpretação de pergunta, candidatos, fontes e auditoria;
gerar comparação útil sem editar manualmente a resposta. Não é novo aceite RA8.

- Base verificada: `feat/product-v1` em `e40e4645cfafc9d489891aca81df5b2ccc5d7e0b`.
  Havia somente o seletor de plano alterado e o plano desta tarefa não rastreado;
  ambos foram preservados. Nenhum reset/descarte.
- Marco final de produto: `a2109660db904055994db85ef0ab543b4f32d450`, publicado em
  `origin/feat/product-v1`. Autor/committer: `Thomaskynol <thomaskynol@gmail.com>`.
- Origem preservada:
  `/home/thomaskyn/hermes-runs/accept43/adaptive_accept43/adaptive_20261104-001959-Descubra_e_compare_cinco_plugi/`.
- Evidências novas persistentes, dentro do workspace gravável:
  `/home/thomaskyn/Projetos/hermes-research-dev/runs/accept43-reconciliation/`.
  Esse diretório está ignorado pelo Git; não há ZIP nem corpus grande versionado.
- Ambiente desta reprodução: host, `/home/thomaskyn/miniconda3/bin/python`
  **3.13.12**. O accept43 original registrou Python **3.14.6**. Não são o mesmo
  interpretador. `opencode --version` executado localmente retornou **v2.2.5**;
  **2.1.4 é premissa controlada do harness**, preservada separadamente.
  O comando foi repetido durante a reprodução em 2026-11-05 00:11 UTC e
  retornou novamente v2.2.5. O campo `at` do harness registra quando o valor
  informado foi incorporado ao run, não o instante exato dessa nova consulta.
- Skills aplicadas: Planning with Files, Superpowers systematic-debugging,
  test-driven-development (incluindo writing-good-tests) e verification-before-completion.
  Plano: `.planning/2026-11-03-reconciliacao-accept43/`. Não houve subagentes nem
  revisão independente nesta sessão; a revisão externa solicitada fica a cargo
  do acompanhamento do usuário.

## Esperado × observado antes de corrigir

As expectativas abaixo derivam da pergunta e das fontes locais. O ledger é
objeto de inspeção, não oráculo exclusivo. Números entre colchetes nesta seção
são os **números do relatório original**, conferidos em `state.report.numbers`.

| Caso | Esperado | Observado em e40e464 sobre o congelado | Classificação |
|---|---|---|---|
| 1 — entidades | Cinco plugins, plataforma e versão como contexto | `_required_entities` inclui OpenCode; matriz e recomendação o tratam como sexto candidato | Defeito reproduzível |
| 1 — globais | Combinações, sobreposições e forma da resposta têm uma avaliação global | Matriz repete globais em todas as colunas; resumo conta “sem cobertura” artificial por candidato | Defeito reproduzível |
| 1 — denominador | 10 critérios por candidato × 5 + 6 obrigações globais/contextuais = 56; 7 N/A históricas fora = 49 | Ledger original conta 56−7=49, sem multiplicar globais; a falha da matriz não demonstra erro nessa fórmula | Hipótese de denominador duplicado refutada |
| 2 — identidade | Documento e identidade de repositório devem concordar | [1] é README próprio, obtido, analisado e incluído no writer, mas nome decorado exige “erskingardner” no corpo e gera “sem fonte” | Defeito reproduzível |
| 2 — jira | Aproveitar README já analisado, distinguindo catálogo e produtos Jira distintos | [33] obtida/analisada na rodada 6, não incluída no writer; piso usa catálogo do `source_url` | Defeito de seleção/aproveitamento; ausência de conteúdo refutada |
| 2 — Octto | Não confundir armazenamento, análise e escrita | [41] obtida, nunca enviada ao assessor nem ao writer; avaliação deriva de artigo secundário | Defeito de alocação/seleção; análise do README refutada |
| 3 — achados | Justificativa e referências de cada candidato atual | `Ledger.compute` escolhe primeiro elemento de `applies_to`, inclusive e2 fora da seleção; justificativas antigas aparecem como atuais | Defeito reproduzível |
| 3 — seleção | Pertinência e evidência substancial prevalecem sobre menções superficiais | Caminho de troca usa ≥3 URLs que nomeiam a entidade; o nome “fontes próprias” não confere primariedade | Defeito reproduzível |
| 3 — recomendação | Explicar utilidade, adequação e limites | Fallback ordena covered/partial/refs e repete estados, sem justificar adoção funcional | Defeito reproduzível |
| 4 — conclusão | Distinguir lacuna, parcial, rejeição factual e incompletude | Votos não reprovam fatos; documento técnico chama de “reprovado” | Erro documental; detalhamento abaixo |
| 4 — extração | Bullets factuais preservados, com omissões e teto observáveis | Heading e bullets sem ponto final são unidos; seis claims não cobrem fatos substantivos em vários blocos | Defeito reproduzível |
| 4 — premissa | Versão fornecida não transforma complementaridade em afirmação do usuário | `_is_user_premise` desvia a frase inteira pela ocorrência de marcador da versão | Defeito reproduzível |
| 5 — busca | Critério global conserva objeto da pergunta e verifica pertinência | `Combinações que combinam entre si opencode` admite páginas de cores e combinatória; obtidas/utilizáveis/analisadas na rodada 4 | Defeito reproduzível; não é problema de um domínio específico |

**Já corrigido antes desta missão, demonstrado especificamente:** o render de
e40e464 foi salvo em `baseline/report-head.md`; os controles de polaridade,
co-menção sem execução e veto idempotente continuam passando em
`test_accept42_audit_scope.py`/`test_accept42_report_shape.py`. O anexo separado
já estava implementado em `a4b2237`; o relatório original de d3b081a não o
exercitava. Não reimplementamos esses mecanismos. Corrigimos o escopo e conteúdo
da matriz/recomendação que ainda permaneciam incorretos.

## Fontes locais e vínculo de identidade

O README [1], `https://github.com/erskingardner/opencode-code-review`, contém
“OpenCode Code Review Plugin”, quatro subagentes paralelos, confiança 0–100
com limiar 80, instalação, análise de histórico e modelos padrão via OpenRouter.
Esses trechos sustentam revisão automatizada documentada, não execução de teste
de compatibilidade feita nesta missão. O crédito a `agent-r3n` não prova que o
repositório mudou de proprietário/nome. Não há metadados de redirect/rename
suficientes para estabelecer essa hipótese: **mudança de nome não verificável**.

O README [33], `https://github.com/shreyanshrana/opencode-jira`, descreve tickets
do usuário em sprints ativos na sidebar. Declara OpenCode V2 **2.1.2+**, Jira
Cloud e Scrum board; exclui V1 e Jira Data Center. A premissa 2.1.4 atende ao
mínimo numérico, o que não prova funcionamento integrado. Há instruções de
instalação npm/CLI, autenticação, comandos de desenvolvimento e licença MIT.
Os materiais de MCP Jira e de outro fornecedor não são esse plugin.

O README [41], `https://github.com/vtemian/octto`, descreve brainstorming em
navegador, perguntas interativas, revisão visual do plano, agentes bootstrapper/
probe/octto e gravação em `docs/plans/`. Inclui tipos de interface e configuração
de modelos/porta. Isso é conteúdo funcional substancial já disponível; não
comprova geração/execução de testes. O corpus não prova que os tempos promocionais
“10 minutos → 2 minutos” foram medidos no ambiente desta missão.

As cópias legíveis estão em `baseline/ref-13.txt`, `ref-19.txt` e `ref-20.txt`.
Esses nomes usam a numeração recalculada da inspeção, **não** a numeração do
relatório original. Para revisão inequívoca, prevalecem as URLs acima.

## Auditoria original reconciliada

| Claim original | Resultado final | Votos válidos | Falhas técnicas |
|---|---|---|---|
| 0 — alternativa workspace | sustained | 2 sustained, 1 partial | 0 |
| 1 — cobertura informada | gap | 3 gap | 0 |
| 2 — alcance informado | gap | 3 gap | 0 |
| 3 — compatibilidade, truncada na extração | gap | 3 gap | 0 |
| 4 — lacuna de combinação jira/Octto | sustained | 3 sustained | 0 |
| 5 — nota operacional residual | partial | 3 partial | 0 |

Há seis julgamentos com quórum e 18 votos válidos. Há **zero `unsupported`**.
`accepted:false` não é sinônimo de falso nem de rejeição factual. A extração
registrou uma claim incompleta, truncada e atribuída ao bloco errado; vários
blocos de funções substantivas ficaram sem claims. Isso explica
`verdict_state: revisão incompleta`, apesar de todos os itens extraídos terem
votos. `unsupported_claims:[]` vale somente para esses itens.

Na reextração da mesma síntese pelo código atual foram encontrados 43 itens,
25 selecionados e 18 adiados pelo teto original; nenhum truncado. Isso demonstra
o caminho corrigido e a aplicação do teto, **não** completude da extração de
todas as afirmações relevantes. Não se compara número de blocos, frases do
verificador e claims semânticas como se fossem a mesma unidade. Registro:
`reextraction-current.json`, sem votos novos nessa inspeção isolada.

A frase de complementaridade marketplace/Plannotator agora segue o canal de
inferência. O trecho sobre versão é uma ressalva, não origem das demais
afirmações. Casos controlados aceitam complementaridade prudente com premissas
citadas e limites; rejeitam funcionalidade falsa acompanhada de marcador do
usuário, atribuição a fork e promoção de co-menção para integração testada.

## Mecanismos corrigidos e controles negativos

- `entity_identity.py` distingue seleção de candidatos e obrigação contextual.
  Identidade exige título/nome no corpo junto da origem; link único no catálogo
  obtido pode vincular proprietário. Fork com mesmo README não herda identidade;
  nomes decorados não exigem que decoração editorial apareça no README.
- Ledger conserva avaliações por célula. Após substituição, arquiva células do
  removido e conclusões globais dependentes da seleção; outras células válidas
  permanecem. A entrega mostra justificativa e referência do candidato correto.
- Assessor e writer reservam fontes primárias identificadas antes de catálogos.
  A seleção compara primariedade e conteúdo pertinente; há testes nos dois
  sentidos: uma primária vence várias menções e menções não derrubam uma primária.
- Consultas globais incluem o objeto da pergunta. Snippet e conteúdo obtido são
  confrontados com esse contexto, preservando raw/obtenção e razão de exclusão.
  O controle cruzado aceita as mesmas páginas quando cores são o assunto.
- Plano não é cortado no meio do JSON antes do assessor; os tetos de documentos,
  excertos, chamadas e esforço não foram elevados. Seleções atuais guardam os
  excertos efetivamente enviados e seus hashes.
- Extração preserva títulos, bullets e continuação com negrito. Afirmação de preço
  com fonte ausente permanece revisável como lacuna, sem inventar conteúdo.
- Marcadores de premissa têm escopo restrito. Cache de normalização usa o
  conteúdo, e a identidade de citações preserva a URL mesmo em documentos de
  bytes iguais. Resíduo `ponytail` não chega ao relatório do usuário.

## Validação e reprodução

Comandos no host, a partir da raiz do repositório, interpretador acima:

```sh
python -m unittest discover -s tests
python -m unittest discover -s tests -p test_accept43_reconciliation.py -v
python scripts/run_replay_offline_validation.py --output-dir runs/accept43-reconciliation/offline-21
```

- Suíte: **868 testes, 10 skips, exit 0** em `suite-29.log`.
- Focados: `na-scope-green.log` e `annex-green.log`, incluindo `adaptive_entry`
  com construtores reais até report/verification persistidos; só transportes
  externos controlados. Rede proibida, inclusive 8082.
- Runner histórico: **11/11 suítes, exit 0**, `offline-21/` e `offline-21.log`.
  Não é utilizado como única prova dos casos desta missão.
- REDs: `red.log`, `baseline-contracts-final-red.log`, `body-gate-red.log`,
  `partial-selection-red.log`, `plan-truncation-red.log`, `hardwrap-red.log`,
  `global-stale-red.log`, `catalog-owner-red.log`. O primeiro ensaio do caso de
  seleção parcial teve fixture sem qualificação; foi corrigida antes da
  demonstração válida, sem enfraquecer o ledger.
- `render-only-1`/`2`/`3` foram interrompidos durante diagnóstico de custo de
  normalização; não são entregas. `profile-support.txt`/`profile-finalize.txt`
  registram a medição. `render-only-4` terminou, mas preserva a síntese antiga:
  comprova reprocessamento, não escrita nova.

A reprodução com gerador real está em
`runs/accept43-reconciliation/reproduction-e3b6274-live/`, usando
`opencode-go/muse-spark-1.3-contributor`, até 18 chamadas, sem retries ocultos,
duas reavaliações e finalização atual. Prompts/respostas e chamadas são
persistidos. Busca, fetch e embeddings no coordenador ficam bloqueados; não
há novo teste de plugins instalados nem coleta atual da web. Custos/tokens
desconhecidos permanecem desconhecidos. Código não é editado durante a execução.

### Primeira escrita nova e correções posteriores

Em `reproduction-e3b6274-live/` a primeira escrita real teve falhas técnicas:
seis lotes da auditoria excederam 100.000 caracteres e duas chamadas da CLI
retornaram vazias; houve 74 votos técnicos falhos e nenhum dos 25 itens obteve
quórum. `accepted:false` e revisão incompleta não são reprovação factual.
A deduplicação de blocos preserva a evidência integral e mantém o teto;
nenhuma passagem adicional é executada para compensar limite.

Em `reproduction-1b2c309/` as duas respostas do assessor foram reaplicadas
com prompts verificados byte a byte; escrita e votos são chamadas novas reais.
Foram 10 chamadas reais, rede de fontes/embeddings bloqueada. Todas as 25 claims
selecionadas tiveram quórum: 19 sustained, 5 partial, 1 gap, zero unsupported,
um voto técnico falho. A extração detectou 67 itens e adiou 42 pelo teto;
assim a revisão continua incompleta. O verificador de suporte ficou partial,
com 32 frases sinalizadas: são alertas a inspecionar, não 32 falsidades
comprovadas. A revisão semântica incide sobre a síntese, e o suporte do
Markdown entregue é verificado separadamente. Hashes do código e da origem
permaneceram iguais antes/depois.

A leitura de 1b2c309 revelou três defeitos adicionais: inferência atribuída ao
critério de descoberta, terceiro homônimo acrescentado a um par e afirmação de
que a fonte examinada não mencionava o próprio candidato. O commit `ca1122c`
restringe a promoção ao critério pertinente, restringe a combinação aos
selecionados e reconcilia ausência de identidade com o excerto examinado.
Outro teste rejeita a atribuição a projeto com palavras compartilhadas. As
quatro regressões falharam na base anterior e passaram após as correções.
Suíte: 826 testes, 10 skips, exit 0; replay histórico 11/11, exit 0.

A reprodução `reproduction-ca1122c/` terminou com escrita e votos reais:
25 itens selecionados tiveram quórum, com 21 sustained, um partial, um
unsupported e dois empates; 45 dos 70 itens extraídos ficaram para revisão
posterior. O item unsupported combinava cinco candidatos com fontes próprias
em uma só claim, enquanto a seleção de evidências para o voto tinha teto de
três fontes. O julgamento existe, mas essa causa não prova falsidade das duas
fontes ausentes do lote. `1057f2d` separa enumeração apenas quando cada parte
tem sua própria referência; teste negativo preserva enumerações sem referências
individuais. O mesmo commit demonstra a frase congelada de marketplace e
Plannotator como inferência parcial ancorada em dois documentos, sem confundir
premissa do harness, compatibilidade e integração testada. Regressões com
premissas inventadas continuam rejeitadas.

Na leitura de `ca1122c`, foram encontrados outros problemas: algumas células
N/A afirmam que descrições de escopo excluem atividades, embora os trechos
citados não comprovem essa exclusão; a fórmula 18/47, portanto, não comprova
denominador correto. Além disso, a justificativa de compatibilidade na matriz
chama 2.1.4 de versão instalada informada pelo usuário, apesar de ser premissa
do harness. O resumo executivo distingue a origem, mas isso não corrige a
contradição nas células. São defeitos do produto, não lacunas legítimas do
corpus. A promoção indevida de sobreposição ao critério de combinações e a
declaração de que uma entidade nunca foi mencionada apesar de constar de
excerto anterior foram corrigidas em `1991edf` com testes RED/GREEN.

### Reprodução `1991edf` e leitura da entrega

`reproduction-1991edf/` terminou com código e origem inalterados, duas
respostas reais de assessor reaplicadas com prompts idênticos e dez chamadas
novas reais: uma escrita e votos, sem busca/fetch nem embeddings. A seleção
final contém os cinco plugins, com fontes próprias para jira e Octto. O
verificador registrou `overall: failed`: 25 julgamentos com quórum, 19
`sustained`, dois `partial` e quatro `unsupported`, sem falhas técnicas de
voto. A extração foi incompleta; o quórum dos itens selecionados não afirma
que toda a síntese foi revisada. A reprovação é preservada no artefato.

Na inspeção dos quatro votos desfavoráveis, três cobram que a URL do próprio
repositório apareça no corpo do README, embora a URL seja a origem efetiva da
fonte obtida. O quarto corrige uma ressalva de que os comandos de Octto não
foram confirmados no **excerto examinado** usando o documento integral, que de
fato contém `show_diff` e `ask_code`; os termos não aparecem no prompt do
writer. Esses aspectos explicam as objeções e não autorizam converter o
veredito em aprovação. Também demonstram uma perda de informação na seleção:
o texto integral permite falar de diffs lado a lado, mas o writer não recebeu
esse trecho, apesar de uma avaliação no próprio relatório utilizá-lo.

O marco `4bca6a1`, publicado após esses achados, preserva no excerto do writer
até dois detalhes raros encontrados nas próprias fontes citadas por achados,
sem elevar o teto. O controle com o README congelado registrou que
`show_diff` e `ask_code` passaram de ausentes para presentes com seus
significados; 11.989/12.000 caracteres foram selecionados e a fatia do
documento ficou em 2.000. O controle negativo impede uma referência a outro
documento de orientar essa escolha. O mesmo marco separa o anexo técnico da
saída principal na entrada integrada e conserva resumo do estado de auditoria.

O plano congelado descreve o critério de testes como criação ou execução,
mais restrito do que melhorar testes, inclusive por contribuição indireta.
Essa diferença permanece no plano histórico; o assessor recebe instrução
explícita para considerar também contribuições indiretas. A correção
posterior conserva no denominador N/A cuja exclusão não foi comprovada e
arquiva o julgamento anterior. Ela aceita uma exclusão explícita sobre o
mesmo candidato e critério, e rejeita outra entidade ou apenas não executar.
O reconhecedor é conservador e textual: exclusões válidas por paráfrase,
tradução ou inferência de escopo podem ficar insuficientes; isso não prova que
sejam falsas. A matriz também atribuía 2.1.4 ao usuário, embora o cabeçalho
reconhecesse a premissa do harness; controle com origem realmente `user`
assegura que essa origem não seja reclassificada. A reprodução posterior
deve ser lida com esses limites, não declarada aceita por causa dos testes.

Durante `reproduction-4bca6a1`, a resposta do primeiro assessor expôs uma
causa ainda anterior: seu prompt chamava o contexto do harness de informado
pelo usuário; além disso, o filtro de identidade descartava a avaliação de
versão da plataforma mesmo quando a chave estruturada a identificava. A
reprodução registra esses fatos como ocorreram, sem alterar suas respostas.
Uma correção desses caminhos foi preparada em cópia isolada enquanto o run
estava congelado, com controles de origem usuário/harness, vínculo com a
plataforma correta e rejeição de chave de outra plataforma.

O marco `8e728c2` transporta origem explícita até o assessor e a entrada
pública. Na CLI, `--context` registra configuração do harness por padrão;
`--context-origin user-provided` declara contexto realmente informado pelo
usuário. Uma retomada não mistura fatos de origens distintas. Premissa
vinculada pela chave à plataforma pode ser avaliada como parcial, sem prova
de funcionamento; chave de outra plataforma não é atribuída. A correção
também distingue documento obtido de excerto selecionado e orienta a síntese
a não negar comandos de teste presentes nem apresentá-los como recursos
para testar código do usuário. Os controles foram executados pela entrada
integrada e há controles negativos de origem e identidade.

`reproduction-4bca6a1` terminou com 12 chamadas reais, duas avaliações
reais, escrita e votos reais; hashes do código e da origem permaneceram
inalterados. A matriz registrou 18/56, com zero N/A; o número não afirma
aceite da pergunta nem corrige a descrição histórica estreita de testes.
Os 25 itens escolhidos tiveram quórum: 20 sustained, um partial, um gap e
três unsupported; outros 39 itens extraídos ficaram fora do teto. Não houve
falha técnica de voto e `overall: failed` foi preservado.

Dois julgamentos unsupported apontaram corretamente que os excertos de
marketplace e Octto incluem `bun test` em seções de desenvolvimento. A
síntese havia negado a menção; o comando testa o próprio projeto e não
demonstra que o produto ajude o usuário a testar outro código. O terceiro
reprovou a descrição de diffs e editor do Octto, apesar de a fonte primária
consultada nomear esses recursos sob “Code Review”; o voto não é prova de que
o trecho esteja ausente. A inspeção também encontrou a frase genérica que
confundia fontes obtidas fora da seleção do writer com fontes fora do corpus,
e uma variante da atribuição incorreta da versão em uma célula. Foram criados
controles desses dois casos e orientação ao writer para separar testes do
próprio projeto de funcionalidades para o usuário, sem impor um produto.

`reproduction-8e728c2` executou duas avaliações, escrita e votos reais,
com 12 chamadas ao gerador e hashes estáveis; não houve busca, coleta nem
embeddings. Os 25 itens selecionados tiveram quórum: 20 sustained, um partial,
quatro gap, zero unsupported e zero falhas técnicas de voto. Outros 40 itens
extraídos foram adiados pelo teto. `overall: partial` reflete a revisão e a
pergunta incompletas, não constitui aprovação integral. A matriz registrou
18/56 sem N/A e mostra ajuda parcial de Octto para testes: o README exemplifica
pergunta sobre estratégia de testes por funcionalidade, não execução autônoma.
A entrada de versão ficou parcial com origem harness; o comando local observou
v2.2.5 separadamente.

A leitura posterior ainda detectou: variantes de “nenhum trecho nomeia” que
contradiziam a identidade presente nos excertos; menção interna de contexto
como “não investigado”; descoberta global sem atualização apesar de cinco
candidatos investigados; e inferências que nomeavam três entidades com fonte
para apenas duas. O verificador registrava alertas de frase, mas agregava
support `ok`; isso não demonstrava que toda atribuição estivesse correta.
Há controles para essas falhas, para ausência de um fato distinto da identidade
e para inferência prudente com duas fontes independentes. A reconciliação da
descoberta é parcial: a seleção identificada não comprova sozinha todos os
requisitos de busca e completude.

O marco `bbecdc9` foi publicado após controles dessas inconsistências. A
comparação sobre os próprios votos e excertos de `8e728c2` mostrou que a
relação prudente Octto–marketplace pode ser ancorada em duas fontes sem
alegar integração testada; as duas inferências que nomeavam uma terceira
entidade sem citação para ela passam a ser sinalizadas como atribuição
incompleta, não como falsidade automaticamente comprovada. Critérios por
candidato deixam de listar todas as alternativas fora da seleção no alcance
comum; a lista completa permanece no anexo técnico, sem chamar de investigada
cada alternativa descoberta. A primeira tentativa da reprodução foi
interrompida após um replay, sem chamada real; `reproduction-bbecdc9-2`
retoma o trabalho em diretório novo e exclusivo.


### Reprodução final, limites e leitura como usuário

`reproduction-bbecdc9-2` reutilizou as duas respostas dos assessores de
`reproduction-8e728c2` após conferir os prompts byte a byte. A escrita e os
votos foram novas chamadas reais: dez chamadas ao gerador, sem busca ou fetch
novos e sem embeddings. Os 25 itens selecionados tiveram quórum: 19 sustained,
seis partial, zero unsupported e zero falhas técnicas; 37 dos 62 itens
extraídos foram adiados. Revisão incompleta não é reprovação factual. A escrita
atual descreveu corretamente o exemplo do README de Octto sobre estratégia de
testes, sem atribuir ao produto execução de testes do usuário.

O marco de produto `a210966` verifica suporte sobre o Markdown final, atualiza
cobertura após reconciliação e sinaliza comparações com entidades sem fonte ou
relação inferida. A reprodução final é:

- Relatório: `runs/accept43-reconciliation/reproduction-a210966-replay/report.md`.
- Verificação: `runs/accept43-reconciliation/reproduction-a210966-replay/verification.json`.
- Anexo: `runs/accept43-reconciliation/reproduction-a210966-replay/technical_annex.md`.
- Proveniência, hashes e consumo: `runs/accept43-reconciliation/reproduction-a210966-replay/reproduction.json`.

Essa reprodução não executou nova busca, coleta, embeddings ou chamada ao
modelo. Reaplicou assessor e nove respostas de auditoria apenas quando os
prompts eram idênticos, consumindo cada voto uma vez; a escrita foi reaplicada
com prompt idêntico exceto pelo ID do run. As respostas têm origem nas
execuções reais acima. O bloqueio de rede foi mantido e não há fallback de
embeddings. `module_hashes_unchanged` e `original_unchanged` são true.
A revisão semântica refere-se à síntese de hash `c126dde7313a7a27`; o suporte
verifica em separado o Markdown entregue, hash `4a49b58b88ec3bd0`. A revisão
não garante que toda afirmação relevante foi extraída nem que o Markdown inteiro
recebeu votos semânticos. `execution:not_run` não deve ser interpretado como
execução real nessa última reprodução.

**Resultado e pendência material:** o relatório compara cinco plugins e mantém
os critérios globais no seu escopo; identifica a versão observada e a premissa,
traz informação funcional, limites, referências e recomendação. Continua
parcial: numa comparação de três candidatos não há referência na própria frase
para Octto, apesar de a fonte primária já analisada conter informação pertinente.
O texto chama duas relações de sobreposição de documentadas, enquanto as notas
adjacentes esclarecem que são inferências entre funções de fontes separadas.
A frase com três candidatos não está entre os 25 itens julgados. A verificação
final registra suporte parcial e referência pendente; os alertas não equivalem
à solução da atribuição nem a veredito de falsidade. O reconhecimento de uma
relação documentada também precisa preservar o caso em que uma fonte primária
menciona outro projeto com identidade verificável. Uma tentativa de reescrita
automática foi retirada ao constatar que poderia reclassificar indevidamente
relações documentadas. Não se editou manualmente o relatório para escondê-lo.
Próximo passo: correção geral baseada em fonte e identidade, com positivos e
negativos, seguida de geração e verificação proporcionais. Não há bloqueio
externo demonstrado; é trabalho técnico ainda pendente nesta missão.
