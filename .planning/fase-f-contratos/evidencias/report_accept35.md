# Relatório de pesquisa: Descubra e compare cinco plugins para melhorar planejamento, implementação, testes e revisão de código no OpenCode. Considere a versão instalada neste computador. Investigue compatibilidade, funcionalidades demonstradas, dependências, custos, manutenção e limitações. Justifique quais combinam entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie funcionalidades documentadas de inferências.

Relatório gerado pelo renderer a partir do estado real; texto do modelo preservado como síntese.

**Status da cobertura:** parcial (proportion=0.03636363636363636) · **Motivo de parada:** rounds

**Cobertura:** 2/55 células obrigatórias — covered required (criterion, entity) cells / (total required cells minus not_applicable cells with scope evidence); not_applicable cells listed separately, never counted as covered

## 1. Resposta direta / resumo executivo

# Comparação de cinco plugins OpenCode — planejamento, implementação, testes e revisão

> Versão instalada neste computador: 2.1.4 [contexto informado pelo usuário, não evidência coletada]. Cobertura informada no plano: `partial`, 2/55 células requeridas, `plan_id opencode-plugins-compare`, `plan_version 19`, `run_id accept35` [dado do plano, não evidência coletada]. Estado por candidato informado no plano para melhoria de planejamento: planning-with-files `covered`, opencode-planner `partial`, opencode-code-review `insufficient`, opencode-plugin-peers `insufficient`, opencode-review-sun-praise `insufficient` [dado do plano, não evidência coletada].

### 0. Nota metodológica — conjunto exigido e fora do corpus

- Conjunto de comparação exigido é exatamente: planning-with-files, opencode-planner, opencode-code-review, opencode-plugin-peers, opencode-review [dado do pedido, sem substituição].
- planning-with-files tem fonte própria no corpus ([10]): página descreve plugin nativo OpenCode por OthmanAdi ([10]).
- planning-with-files tem segunda fonte do mesmo projeto no corpus ([26]): repositório distingue memória de agente de gerenciamento de estado ativo ([26]).
- opencode-planner tem fonte própria no corpus ([8]): página adiciona agente dedicado de planejamento antes da implementação ([8]).
- opencode-code-review tem fonte própria no corpus ([11]): página descreve revisão de pull requests com subagentes e pontuação por confiança ([11]).
- opencode-plugin-peers com fonte própria [20] está fora do corpus: nenhum documento do corpus trata dessa entidade, por isso estado não verificado — não se afirma presença nem ausência, item sem célula investigada = LACUNA com causa de fonte ausente.
- opencode-review com fonte própria [12] está fora do corpus: nenhum documento do corpus trata dessa entidade, por isso estado não verificado — não se afirma presença nem ausência, item sem célula investigada = LACUNA com causa de fonte ausente.
- Alternativas descobertas mas NÃO investigadas, sem afirmação de fatos sobre elas: opencode-plugin-peers, opencode-plugin-peers, opencode-plugin-peers, opencode-plugin-peers, opencode-plugin-peers [lista do pedido, não investigadas].
- Explorado fora da seleção e que não conta na comparação: memory@opencode-marketplace [dado do plano, motivo no plano, sem fatos afirmados aqui].
- Documentos [13] e [5] não são fonte própria de nenhum dos cinco exigidos: o primeiro publica sob `@bandonker/opencode-*` ([13]), o segundo é lista curada de plugins e recursos para OpenCode ([5]).

### 1. Planejamento

- Documentado: planning-with-files gerencia estado ativo de execução: fases, status, dependências e verificação de conclusão da tarefa em trabalho ([10]).
- Documentado: planning-with-files distingue isso de memória de agente: vetores e grafos ajudam a recordar fatos de sessões passadas, enquanto ele gerencia fases e dependências da execução ativa ([26]).
- Documentado: opencode-planner adiciona agente dedicado para planejamento somente-leitura antes da implementação ([8]).
- Documentado: opencode-planner é emulação do agente experimental de plano, sem dependência rígida de modo experimental, embora essa configuração habilite ferramenta de saída de plano ([8]).
- LACUNA planejamento para opencode-code-review: nos excertos examinados da fonte própria não há descrição de melhoria de planejamento, só revisão e conformidade ([11]).
- LACUNA planejamento para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus, sem célula investigada, nada a afirmar sobre planejamento.

### 2. Implementação

- Documentado: planning-with-files organiza execução em arquivos de planejamento persistentes por projeto e superfície auditável, sem executar recordação de fatos passados como memória vetorial ([10]).
- Documentado: opencode-planner prevê uso do agente de plano como ponto de partida para personalização antes de implementar ([8]).
- LACUNA implementação para opencode-code-review: excertos da fonte própria descrevem auditoria de mudanças, não geração ou implementação de código ([11]).
- LACUNA implementação para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus, sem célula investigada.

### 3. Testes

- LACUNA testes para planning-with-files: excertos examinados da fonte própria não descrevem geração, execução ou avaliação de testes ([10]).
- Documentado parcial: opencode-planner lista comandos de desenvolvimento e integração, sem afirmar melhoria de testes do código do usuário ([8]).
- LACUNA testes para opencode-code-review: fonte própria menciona detecção de bugs focada em mudanças e análise de histórico, não execução de suíte de testes ([11]).
- LACUNA testes para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus, sem célula investigada.

### 4. Revisão de código

- Documentado: opencode-code-review revisa pull requests com múltiplos subagentes especializados e pontuação baseada em confiança para filtrar falsos positivos ([11]).
- Documentado: opencode-code-review usa 4 subagentes paralelos que auditam mudanças de forma independente ([11]).
- Documentado: opencode-code-review pontua problemas e filtra abaixo de limiar documentado como 80 ([11]).
- Documentado: opencode-code-review inclui verificação de conformidade com diretrizes de projeto, detecção focada em mudanças e contexto de histórico ([11]).
- Documentado: opencode-code-review define papéis por modelo para triagem, diretrizes, resumo e conformidade ([11]).
- LACUNA revisão para planning-with-files: excertos examinados da fonte própria não descrevem revisão de código, só gerenciamento de fases e conclusão ([26]).
- LACUNA revisão para opencode-planner: excertos examinados da fonte própria não descrevem revisão de código, só planejamento somente-leitura ([8]).
- LACUNA revisão para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus, sem célula investigada.

### 5. Compatibilidade com versão instalada

- Documentado com isenção: planning-with-files declara suporte a OpenCode V1 + V2 como plugin nativo, versão do plugin v1.2.0 ([10]).
- LACUNA compatibilidade funcional: versão exata do OpenCode 2.1.4 [informado pelo usuário] tem sem menção no documento citado acima, por isso compatibilidade funcional com 2.1.4 não é sustentada ([10]).
- Documentado com isenção: opencode-planner documenta instalação compartilhada V1/V2 e instalação só V2 com campo plural de configuração, versão do plugin 0.6.0 ([8]).
- LACUNA compatibilidade funcional: versão exata 2.1.4 [informado pelo usuário] tem sem menção no documento citado acima, comparação numérica contra mínimo inexiste e integração afirmada seria LACUNA ([8]).
- LACUNA compatibilidade para opencode-code-review: fonte própria sem menção de versão do OpenCode nos excertos examinados, versão do plugin desconhecida / sem menção no documento ([11]).
- LACUNA compatibilidade para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus, nenhuma afirmação sobre 2.1.4 [informado pelo usuário].

### 6. Dependências

- LACUNA dependências para planning-with-files: excertos examinados não listam dependências de runtime do plugin OpenCode, só menção a métodos de instalação de skills ([10]).
- Documentado parcial: opencode-planner exige configuração de campo singular ou plural conforme V1/V2 e rejeita campo desconhecido em V1 ([8]).
- Documentado: opencode-code-review instala por cópia de agentes, comando e plugin para diretórios de configuração, com notificações em sistemas suportados ([11]).
- LACUNA dependências para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus.

### 7. Custos

- Documentado parcial: planning-with-files declara licença MIT, sem preço de uso documentado nos excertos ([10]).
- Documentado parcial: opencode-planner declara licença MIT, sem preço de uso documentado nos excertos ([8]).
- LACUNA custos para opencode-code-review: excertos examinados da fonte própria não informam preço, licença ou custo operacional, crédito como porte de outro projeto ([11]).
- LACUNA custos para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus.

### 8. Manutenção

- Documentado: planning-with-files informa 3 lançamentos nos últimos 90 dias com mais recente 1.2.0 há cerca de 1 mês ([10]).
- Documentado parcial: opencode-planner usa publicação com notas automáticas e sem segredo de token para publicação, sem datas de manutenção nos excertos ([8]).
- LACUNA manutenção para opencode-code-review: excertos examinados da fonte própria sem menção de versão, data, issues ou frequência ([11]).
- LACUNA manutenção para opencode-plugin-peers e opencode-review: fontes próprias fora do corpus.

### 9. Limitações

- Documentado: planning-with-files não substitui memória de agente para recordar fatos passados, atua só sobre estado da tarefa ativa ([26]).
- Documentado: opencode-planner não adiciona campo plural em configuração compartilhada V1/V2 porque V1 rejeita campo desconhecido ([8]).
- Documentado: opencode-code-review foca em mudanças e filtra abaixo do limiar, sem cobrir problemas pré-existentes fora do diff ([11]).
- Contradição: nenhuma contradição direta entre fontes da mesma entidade verificada nos excertos — as duas fontes de planning-with-files concordam sobre estado ativo ([10]).

### 10. Quais combinam e quais se sobrepõem

- INFERÊNCIA de complementaridade: planning-with-files organiza fases e dependências enquanto opencode-code-review audita mudanças com subagentes, funções distintas que se complementam em fluxo planejar-executar-revisar, limites sem prova de integração testada nem ausência de conflitos, integração afirmada continua LACUNA ([10]) ([11]).
- INFERÊNCIA de complementaridade: opencode-planner planeja de forma somente-leitura antes de implementar enquanto opencode-code-review revisa depois de implementar, complementaridade de etapa distinta, limites sem teste de integração conjunta, compatibilidade funcional não afirmada ([8]) ([11]).
- INFERÊNCIA de sobreposição: planning-with-files e opencode-planner sobrepõem-se em planejamento, o primeiro com estado e conclusão e o segundo com agente de plano pré-implementação, limites sem medida de redundância e sem decisão de exclusão mútua ([10]) ([8]).
- LACUNA combinação/sobreposição para opencode-plugin-peers e opencode-review: sem fonte no corpus não há premissa verificável para afirmar combinação, sobreposição ou conflito.

Não verificado: dependências externas, custos operacionais, manutenção atual e compatibilidade funcional com 2.1.4 [informado pelo usuário]; risco de usar atribu

## 2. Escopo, critérios, método e configuração efetiva

- **Pergunta:** Descubra e compare cinco plugins para melhorar planejamento, implementação, testes e revisão de código no OpenCode. Considere a versão instalada neste computador. Investigue compatibilidade, funcionalidades demonstradas, dependências, custos, manutenção e limitações. Justifique quais combinam entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie funcionalidades documentadas de inferências.
- **Data:** 2026-11-02T05:39:40Z (gerado em 2026-11-02T05:58:57Z)
- **Perfil:** medium
- **Amplitude:** 3 | **Profundidade:** 2
- **Rodadas:** 7 (Rodadas concluídas: 7)
- **Concorrência:** 4
- **Orçamento:** limites={'time_s': 1800, 'queries': 30, 'unique_sources': 150, 'extractions': 120, 'yt_live_fetches': 8}; consumido=unknown; tokens=unknown; custo=unknown
- **Critérios:** 15 | **Entidades:** 18
- **Coleta por canal:** web: 17 ok / 9 falha(s)


## 3. Achados por critério

### Descobrir e comparar cinco plugins para OpenCode — parcial
Material lista >=5 candidatos nomeados (planning-with-files, opencode-planner, opencode-code-review, suite bandonker, marketplace) e diretorio com 149 plugins, mas dimensoes de comparacao (custos, compat 2.1.4, combinacao/sobreposicao) seguem sem evidencia.
Referências: [10], [8], [11], [13], [3], [4]
Alcance examinado: excertos de 40/40 docs únicos das entidades (90296 chars de 6064610 coletados); global: excertos examinados (40/40 docs)

### Melhoria de planejamento — parcial
Excertos da fonte da entidade descrevem gerenciamento de estado de execução ativa: fases, status e dependências, além de superfície de planejamento auditável — melhoria direta de planejamento.
Referências: [26], [10]

| Entidade | Estado |
|---|---|
| planning-with-files | coberto |
| opencode-planner | parcial |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Melhoria de implementação — parcial
Fonte da entidade documenta gestão de fases/status/dependências e hooks de progresso, que afetam acompanhamento da implementação, sem demonstrar geração de código.
Referências: [26]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | parcial |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Melhoria de testes — insuficiente
Nenhum excerto do material selecionado documenta melhoria de testes pelo planning-with-files; tentativa registrada falhou.
Referências: [7]

| Entidade | Estado |
|---|---|
| planning-with-files | insuficiente |
| opencode-planner | insuficiente |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Melhoria de revisão de código — insuficiente
Nenhum excerto do material selecionado documenta revisão de código pelo planning-with-files.
Referências: [7]

| Entidade | Estado |
|---|---|
| planning-with-files | insuficiente |
| opencode-planner | parcial |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | parcial |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Compatibilidade com a versão instalada neste computador — parcial
Fonte declara compatibilidade OpenCode V1+V2; versão instalada 2.1.4 é premissa do usuário, sem menção nominal 2.1.4 na fonte — LACUNA parcial.
Referências: [10]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | insuficiente |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Funcionalidades demonstradas — parcial
Fontes da entidade demonstram funcionalidades: instalação via plugin, hooks PreCompact/PreComp, replay com nonce, recovery com consentimento e correção de ponteiros de plano.
Referências: [26], [10]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | parcial |
| opencode-code-review | parcial |
| opencode-plugin-peers | insuficiente |
| opencode-review | parcial |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Dependências — parcial
Fonte contrasta 'npx skills add' vs 'npm install' sob node_modules e frontmatter hooks, indicando dependências de instalação, sem lista completa de versões.
Referências: [26]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | parcial |
| opencode-code-review | parcial |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Custos — parcial
Fonte indica 'MIT License', sugerindo ausência de custo de licença, sem detalhar custos operacionais de modelos.
Referências: [26]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | insuficiente |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Manutenção — parcial
Fonte declara 'Actively maintained', versão v1.2.0/v3.12.0, changelog e contribuidores — manutenção demonstrada.
Referências: [10], [26]

| Entidade | Estado |
|---|---|
| planning-with-files | coberto |
| opencode-planner | parcial |
| opencode-code-review | insuficiente |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Limitações — parcial
Fonte delimita escopo: recovery com consentimento, quarentena cross-project, writers fail-closed e sem fallback para plano legado não relacionado.
Referências: [10]

| Entidade | Estado |
|---|---|
| planning-with-files | parcial |
| opencode-planner | parcial |
| opencode-code-review | parcial |
| opencode-plugin-peers | insuficiente |
| opencode-review | insuficiente |
Alcance examinado: excertos de 26/26 docs únicos das entidades (90296 chars de 6064610 coletados); planning-with-files: excerto examinado (2/2 docs); opencode-planner: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (2/2 docs); bandonker opencode suite (code-review): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-marketplace installer: desconhecido-legítimo (nada no corpus sobre a entidade); planner (everything-opencode): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin-peers: excerto examinado (2/2 docs); memory@opencode-marketplace: excerto examinado (1/1 docs); Plannotator for OpenCode: desconhecido-legítimo (nada no corpus sobre a entidade); opencode-review: excerto examinado (3/3 docs); open-code-review: excerto examinado (2/2 docs); opencode-agent-memory: excerto examinado (3/3 docs); opencode-memory: excerto examinado (9/9 docs); opencode-mem: excerto examinado (6/6 docs); opencode-supermemory: excerto examinado (4/4 docs); oh-my-opencode: excerto examinado (10/10 docs); opencode-workspace: excerto examinado (5/5 docs)

### Justificar quais plugins combinam entre si — insuficiente
Nenhuma fonte selecionada justifica combinacoes entre plugins; sem matriz de interoperabilidade.
Referências: [7], [4], [1]
Alcance examinado: excertos de 40/40 docs únicos das entidades (90296 chars de 6064610 coletados); global: excertos examinados (40/40 docs)

### Justificar quais plugins têm funções sobrepostas — insuficiente
Nenhuma fonte compara sobreposicao de funcoes; apenas descricoes isoladas por plugin.
Referências: [10], [8], [11]
Alcance examinado: excertos de 40/40 docs únicos das entidades (90296 chars de 6064610 coletados); global: excertos examinados (40/40 docs)

### Usar fontes atuais — parcial
Sinais de atualidade parciais: Recently active, verifications last 30 days, First published 2026-09-21, release 0.6.0, 2026; nem todas as fontes datadas.
Referências: [7], [13], [8]
Alcance examinado: excertos de 40/40 docs únicos das entidades (90296 chars de 6064610 coletados); global: excertos examinados (40/40 docs)

### Diferenciar funcionalidades documentadas de inferências — parcial
Síntese entregue separa material (3 marcadores: documentado, inferência, lacuna; 8 fonte(s) do corpus citadas).
Referências: [26], [5], [11], [12], [8], [20], [13], [10]
Alcance examinado: excertos de 40/40 docs únicos das entidades (90296 chars de 6064610 coletados); global: excertos examinados (40/40 docs)

## 5. Limitações, contradições, incertezas e não investigados

### Lacunas obrigatórias pendentes
- **Descobrir e comparar cinco plugins para OpenCode** (parcial): Material lista >=5 candidatos nomeados (planning-with-files, opencode-planner, opencode-code-review, suite bandonker, marketplace) e diretorio com 149 plugins, mas dimensoes de comparacao (custos, compat 2.1.4, combinacao/sobreposicao) seguem sem evidencia.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **Melhoria de planejamento** (parcial): Excertos da fonte da entidade descrevem gerenciamento de estado de execução ativa: fases, status e dependências, além de superfície de planejamento auditável — melhoria direta de planejamento.
  - Próximo passo: ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Melhoria de implementação** (parcial): Fonte da entidade documenta gestão de fases/status/dependências e hooks de progresso, que afetam acompanhamento da implementação, sem demonstrar geração de código.
  - Próximo passo: ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Melhoria de testes** (insuficiente): Nenhum excerto do material selecionado documenta melhoria de testes pelo planning-with-files; tentativa registrada falhou.
  - Próximo passo: ler a fonte própria de planning-with-files (https://www.opendock.net/plugins/opencode-planning-with-files/) nas seções da dimensão; ler a fonte própria de opencode-planner (https://github.com/timrichardson/opencode-planner) nas seções da dimensão; ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão
- **Melhoria de revisão de código** (insuficiente): Nenhum excerto do material selecionado documenta revisão de código pelo planning-with-files.
  - Próximo passo: ler a fonte própria de planning-with-files (https://www.opendock.net/plugins/opencode-planning-with-files/) nas seções da dimensão; ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão
- **Compatibilidade com a versão instalada neste computador** (parcial): Fonte declara compatibilidade OpenCode V1+V2; versão instalada 2.1.4 é premissa do usuário, sem menção nominal 2.1.4 na fonte — LACUNA parcial.
  - Próximo passo: ler a fonte própria de opencode-planner (https://github.com/timrichardson/opencode-planner) nas seções da dimensão; ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Funcionalidades demonstradas** (parcial): Fontes da entidade demonstram funcionalidades: instalação via plugin, hooks PreCompact/PreComp, replay com nonce, recovery com consentimento e correção de ponteiros de plano.
  - Próximo passo: ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão
- **Dependências** (parcial): Fonte contrasta 'npx skills add' vs 'npm install' sob node_modules e frontmatter hooks, indicando dependências de instalação, sem lista completa de versões.
  - Próximo passo: ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Custos** (parcial): Fonte indica 'MIT License', sugerindo ausência de custo de licença, sem detalhar custos operacionais de modelos.
  - Próximo passo: ler a fonte própria de opencode-planner (https://github.com/timrichardson/opencode-planner) nas seções da dimensão; ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Manutenção** (parcial): Fonte declara 'Actively maintained', versão v1.2.0/v3.12.0, changelog e contribuidores — manutenção demonstrada.
  - Próximo passo: ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Limitações** (parcial): Fonte delimita escopo: recovery com consentimento, quarentena cross-project, writers fail-closed e sem fallback para plano legado não relacionado.
  - Próximo passo: ler a fonte própria de opencode-plugin-peers (https://opencode.im/plugins?category=tools) nas seções da dimensão; ler a fonte própria de opencode-review (https://github.com/sun-praise/opencode-review) nas seções da dimensão
- **Justificar quais plugins combinam entre si** (insuficiente): Nenhuma fonte selecionada justifica combinacoes entre plugins; sem matriz de interoperabilidade.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **Justificar quais plugins têm funções sobrepostas** (insuficiente): Nenhuma fonte compara sobreposicao de funcoes; apenas descricoes isoladas por plugin.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **Usar fontes atuais** (parcial): Sinais de atualidade parciais: Recently active, verifications last 30 days, First published 2026-09-21, release 0.6.0, 2026; nem todas as fontes datadas.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **Diferenciar funcionalidades documentadas de inferências** (parcial): Síntese entregue separa material (3 marcadores: documentado, inferência, lacuna; 8 fonte(s) do corpus citadas).
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima

### Incertezas e material não verificado
- Melhoria de testes: insuficiente — Nenhum excerto do material selecionado documenta melhoria de testes pelo planning-with-files; tentativa registrada falhou.
- Melhoria de revisão de código: insuficiente — Nenhum excerto do material selecionado documenta revisão de código pelo planning-with-files.
- Justificar quais plugins combinam entre si: insuficiente — Nenhuma fonte selecionada justifica combinacoes entre plugins; sem matriz de interoperabilidade.
- Justificar quais plugins têm funções sobrepostas: insuficiente — Nenhuma fonte compara sobreposicao de funcoes; apenas descricoes isoladas por plugin.

### Notas da execução
- downgrade without new evidence rejected for ('c10', 'pwf'): kept covered (assessor said insufficient)
- downgrade without new evidence rejected for ('c10', 'oplanner'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c11', 'pwf'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c11', 'oplanner'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c11', 'ocreview'): kept partial (assessor said insufficient)

## 6. Conclusão e próximos passos

A investigação é **parcial**: há critérios obrigatórios sem cobertura suficiente (ver seção 5). A conclusão não pode ser apresentada como completa.

**Próximo passo:** ver detalhes por lacuna na seção 5 (15 pendente(s)); priorizar células com fonte própria indicada.

## 7. Fontes

Numeração estável do corpus obtido; nenhuma fonte é inventada pelo modelo.

| # | URL | Título | Obtida em | Tipo | Alcance lido |
|---|---|---|---|---|---|
| [1] | https://opencode.ai/docs/plugins/ | não registrado | 2026-11-02T05:41:03Z | page | 102552/102552 chars (usable) |
| [2] | https://opencode.ai/v2/docs/plugins | não registrado | 2026-11-02T05:41:03Z | page | 28257/28257 chars (usable) |
| [3] | https://github.com/nikiforovall/opencode-marketplace | NikiforovAll/opencode-marketplace | 2026-11-02T05:41:03Z | repository | 2794/2794 chars (usable) |
| [4] | https://opencode.im/ | não registrado | 2026-11-02T05:49:27Z | page | 235961/235961 chars (usable) |
| [5] | https://github.com/awesome-opencode/awesome-opencode | awesome-opencode/awesome-opencode | 2026-11-02T05:41:03Z | repository | 143071/143071 chars (usable) |
| [6] | https://www.opencode.cafe/ | não registrado | 2026-11-02T05:41:03Z | page | 31052/31052 chars (usable) |
| [7] | https://opencode.im/plugins | não registrado | 2026-11-02T05:41:03Z | page | 301637/301637 chars (usable) |
| [8] | https://github.com/timrichardson/opencode-planner | timrichardson/opencode-planner | 2026-11-02T05:41:03Z | repository | 15428/15428 chars (usable) |
| [9] | https://docs.plannotator.ai/open-source/agents/opencode | não registrado | 2026-11-02T05:41:03Z | page | 179470/179470 chars (usable) |
| [10] | https://www.opendock.net/plugins/opencode-planning-with-files/ | não registrado | 2026-11-02T05:41:03Z | page | 236721/236721 chars (usable) |
| [11] | https://github.com/erskingardner/opencode-code-review | erskingardner/opencode-code-review | 2026-11-02T05:41:03Z | repository | 4044/4044 chars (usable) |
| [12] | https://github.com/sun-praise/opencode-review | sun-praise/opencode-review | 2026-11-02T05:41:03Z | repository | 2914/2914 chars (usable) |
| [13] | https://www.opendock.net/plugins/bandonker--opencode-code-review/ | não registrado | 2026-11-02T05:41:03Z | page | 173849/173849 chars (usable) |
| [14] | https://composio.dev/content/best-opencode-plugins | não registrado | 2026-11-02T05:41:03Z | page | 306887/306887 chars (usable) |
| [15] | https://github.com/vichhka-git/opencode-shannon-plugin | vichhka-git/opencode-shannon-plugin | 2026-11-02T05:41:03Z | repository | 12043/12043 chars (usable) |
| [16] | https://www.opencode.asia/plugins/ | não registrado | 2026-11-02T05:41:03Z | page | 118899/118899 chars (usable) |
| [17] | https://github.com/jadmadi/opencode-plugins | jadmadi/opencode-plugins | 2026-11-02T05:41:03Z | repository | 8028/8028 chars (usable) |
| [18] | https://opencode.ai/docs/pt-br/plugins/ | não registrado | 2026-11-02T05:42:59Z | page | 104167/104167 chars (usable) |
| [19] | https://opencode.ai/docs/pt-br/ecosystem/ | não registrado | 2026-11-02T05:42:59Z | page | 53095/53095 chars (usable) |
| [20] | https://opencode.im/plugins?category=tools | não registrado | 2026-11-02T05:43:00Z | page | 282397/282397 chars (usable) |
| [21] | https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR | não registrado | 2026-11-02T05:49:27Z | page | 49724/49724 chars (usable) |
| [22] | https://allansantos-dv.github.io/opencode-marketplace/ | não registrado | 2026-11-02T05:43:00Z | page | 10681/10681 chars (usable) |
| [23] | https://github.com/anomalyco/opencode | anomalyco/opencode | 2026-11-02T05:43:00Z | repository | 4583/4583 chars (usable) |
| [24] | https://github.com/Nsomnia/everything-opencode/blob/main/docs/pt-BR/agents/planner.md | Nsomnia/everything-opencode | 2026-11-02T05:43:00Z | repository | 2296/2296 chars (usable) |
| [25] | https://npm.io/package/opencode-planner | não registrado | 2026-11-02T05:43:00Z | page | 118038/118038 chars (usable) |
| [26] | https://github.com/OthmanAdi/planning-with-files | OthmanAdi/planning-with-files | 2026-11-02T05:44:03Z | repository | 111242/111242 chars (usable) |
| [27] | https://github.com/alibaba/open-code-review | alibaba/open-code-review | 2026-11-02T05:44:03Z | repository | 13323/13323 chars (usable) |
| [28] | https://opencode.ai/docs/pt-br/agents/ | não registrado | 2026-11-02T05:44:03Z | page | 157545/157545 chars (usable) |
| [29] | https://dicastech.com.br/revisao-de-codigo-com-ia/ | não registrado | 2026-11-02T05:44:03Z | page | 151937/151937 chars (usable) |
| [30] | https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb | não registrado | 2026-11-02T05:44:03Z | page | 187490/187490 chars (usable) |
| [31] | https://opencode.ai/docs/pt-br/cli/ | não registrado | 2026-11-02T05:44:03Z | page | 103355/103355 chars (usable) |
| [32] | https://blog.cloudflare.com/ai-code-review/ | não registrado | 2026-11-02T05:44:03Z | page | 306973/306973 chars (usable) |
| [33] | https://github.com/chriswritescode-dev/opencode-memory | chriswritescode-dev/opencode-memory | 2026-11-02T05:46:19Z | repository | 29226/29226 chars (usable) |
| [34] | https://github.com/joshuadavidthomas/opencode-agent-memory | joshuadavidthomas/opencode-agent-memory | 2026-11-02T05:46:19Z | repository | 9467/9467 chars (usable) |
| [35] | https://opencode.im/categories/memory-context | não registrado | 2026-11-02T05:46:19Z | page | 117177/117177 chars (usable) |
| [36] | https://kd05.com/p/opencode-mem-memory-plugin-guide/ | não registrado | 2026-11-02T05:46:19Z | page | 48849/48849 chars (usable) |
| [37] | https://www.agent-memory.dev/docs/integrations/opencode | não registrado | 2026-11-02T05:47:50Z | page | 307178/307178 chars (usable) |
| [38] | https://www.opencode.asia/ecosystem/plugins/agent-memory/ | não registrado | 2026-11-02T05:47:50Z | page | 79342/79342 chars (usable) |
| [39] | https://dev.opencode.ai/docs/pt-br/ecosystem/ | não registrado | 2026-11-02T05:49:27Z | page | 53179/53179 chars (usable) |
| [40] | https://www.opendock.net/ | não registrado | 2026-11-02T05:49:28Z | page | 195180/195180 chars (usable) |

## 8. Anexo: verificações e contadores

### Verificações independentes
| Dimensão | Estado | Evidência |
|---|---|---|
| execution | ok | 10 campo(s) |
| question | partial | 7 campo(s) |
| review | partial | 11 campo(s) |
| support | ok | 17 campo(s) |
- execution: 9 falha(s) registradas por motivo
- question: 15 critério(s) obrigatório(s) pendente(s)

### Contadores de seis estágios
| Estágio | Documentos |
|---|---:|
| discovered | 46 |
| obtained | 40 |
| usable | 40 |
| analyzed | 40 |
| used_in_synthesis | 6 |
| cited | 12 |

| Relação | Documentos | Tipo |
|---|---|---|
| version | https://opencode.im/ ↔ https://opencode.im/ | trecho distinto da mesma URL (1 anterior(es)) |
| version | https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR ↔ https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR | trecho distinto da mesma URL (1 anterior(es)) |
| duplicate | http://www.opencode.im/plugins ↔ https://opencode.im/plugins | bytes idênticos em outra URL (republicação; independência desconhecida) |

**Leitura:** 1.5% dos caracteres do corpus incluídos em excertos avaliados (90296/6064610 chars; 76 batches de excerto em 40 docs únicos de 40 coletados; avaliados únicos pelo assessor: 40)
saturação de URLs novas ≠ análise esgotada; batches contam repetições entre chamadas, únicos não

### Notas técnicas (diagnóstico interno)
- semantic boost: 17 docs ranqueados (18 vetorizados, 0 do cache); top: https://opencode.im/, https://opencode.im/plugins, https://www.opendock.net/plugins/bandonker--opencode-code-review/
- discovery: critério c2 estendido a pwf (per_candidate)
- discovery: critério c3 estendido a pwf (per_candidate)
- discovery: critério c4 estendido a pwf (per_candidate)
- discovery: critério c5 estendido a pwf (per_candidate)
- discovery: critério c6 estendido a pwf (per_candidate)
- discovery: critério c7 estendido a pwf (per_candidate)
- discovery: critério c8 estendido a pwf (per_candidate)
- discovery: critério c9 estendido a pwf (per_candidate)
- discovery: critério c10 estendido a pwf (per_candidate)
- discovery: critério c11 estendido a pwf (per_candidate)
- discovery: critério c2 estendido a oplanner (per_candidate)
- discovery: critério c3 estendido a oplanner (per_candidate)
- discovery: critério c4 estendido a oplanner (per_candidate)
- discovery: critério c5 estendido a oplanner (per_candidate)
- discovery: critério c6 estendido a oplanner (per_candidate)
- discovery: critério c7 estendido a oplanner (per_candidate)
- discovery: critério c8 estendido a oplanner (per_candidate)
- discovery: critério c9 estendido a oplanner (per_candidate)
- discovery: critério c10 estendido a oplanner (per_candidate)
- discovery: critério c11 estendido a oplanner (per_candidate)
- discovery: critério c2 estendido a ocreview (per_candidate)
- discovery: critério c3 estendido a ocreview (per_candidate)
- discovery: critério c4 estendido a ocreview (per_candidate)
- discovery: critério c5 estendido a ocreview (per_candidate)
- discovery: critério c6 estendido a ocreview (per_candidate)
- discovery: critério c7 estendido a ocreview (per_candidate)
- discovery: critério c8 estendido a ocreview (per_candidate)
- discovery: critério c9 estendido a ocreview (per_candidate)
- discovery: critério c10 estendido a ocreview (per_candidate)
- discovery: critério c11 estendido a ocreview (per_candidate)
- discovery: bandonker fora da cobertura (sem menção na fonte própria; rastreado)
- discovery: critério c2 estendido a bandonker (per_candidate)
- discovery: critério c3 estendido a bandonker (per_candidate)
- discovery: critério c4 estendido a bandonker (per_candidate)
- discovery: critério c5 estendido a bandonker (per_candidate)
- discovery: critério c6 estendido a bandonker (per_candidate)
- discovery: critério c7 estendido a bandonker (per_candidate)
- discovery: critério c8 estendido a bandonker (per_candidate)
- discovery: critério c9 estendido a bandonker (per_candidate)
- discovery: critério c10 estendido a bandonker (per_candidate)
- discovery: critério c11 estendido a bandonker (per_candidate)
- discovery: mktplace fora da cobertura (sem menção na fonte própria; rastreado)
- discovery: critério c2 estendido a mktplace (per_candidate)
- discovery: critério c3 estendido a mktplace (per_candidate)
- discovery: critério c4 estendido a mktplace (per_candidate)
- discovery: critério c5 estendido a mktplace (per_candidate)
- discovery: critério c6 estendido a mktplace (per_candidate)
- discovery: critério c7 estendido a mktplace (per_candidate)
- discovery: critério c8 estendido a mktplace (per_candidate)
- discovery: critério c9 estendido a mktplace (per_candidate)
- discovery: critério c10 estendido a mktplace (per_candidate)
- discovery: critério c11 estendido a mktplace (per_candidate)
- semantic boost: seleção ['https://github.com/erskingardner/opencode-code-review', 'https://github.com/nikiforovall/opencode-marketplace', 'https://github.com/timrichardson/opencode-planner', 'https://opencode.ai/docs/plugins/', 'https://opencode.im/', 'https://opencode.im/plugins', 'https://www.opencode.asia/plugins/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/', 'https://www.opendock.net/plugins/opencode-planning-with-files/'] sob ordem ['https://opencode.im/', 'https://opencode.im/plugins', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/', 'https://www.opendock.net/plugins/opencode-planning-with-files/', 'https://opencode.ai/docs/plugins/', 'https://github.com/timrichardson/opencode-planner'] (gates de identidade/seleção intactos)
- discovery cheio (64): https://github.com/AllanSantos-DV/opencode-marketplace ignorado
- semantic boost: 25 docs ranqueados (9 vetorizados, 17 do cache); top: https://opencode.ai/docs/pt-br/plugins/, https://opencode.im/, https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR
- discovery: planner-everything-opencode fora da cobertura (sem menção na fonte própria; rastreado)
- discovery: critério c2 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c3 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c4 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c5 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c6 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c7 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c8 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c9 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c10 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c11 estendido a planner-everything-opencode (per_candidate)
- discovery: critério c2 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c3 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c4 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c5 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c6 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c7 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c8 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c9 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c10 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c11 estendido a opencode-plugin-peers (per_candidate)
- discovery: critério c2 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c3 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c4 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c5 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c6 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c7 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c8 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c9 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c10 estendido a memory-opencode-marketplace (per_candidate)
- discovery: critério c11 estendido a memory-opencode-marketplace (per_candidate)
- discovery: plannotator-opencode fora da cobertura (sem menção na fonte própria; rastreado)
- discovery: critério c2 estendido a plannotator-opencode (per_candidate)
- discovery: critério c3 estendido a plannotator-opencode (per_candidate)
- discovery: critério c4 estendido a plannotator-opencode (per_candidate)
- discovery: critério c5 estendido a plannotator-opencode (per_candidate)
- discovery: critério c6 estendido a plannotator-opencode (per_candidate)
- discovery: critério c7 estendido a plannotator-opencode (per_candidate)
- discovery: critério c8 estendido a plannotator-opencode (per_candidate)
- discovery: critério c9 estendido a plannotator-opencode (per_candidate)
- discovery: critério c10 estendido a plannotator-opencode (per_candidate)
- discovery: critério c11 estendido a plannotator-opencode (per_candidate)
- discovery: opencode-review-sun-praise fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c3 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c4 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c5 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c6 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c7 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c8 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c9 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c10 estendido a opencode-review-sun-praise (per_candidate)
- discovery: critério c11 estendido a opencode-review-sun-praise (per_candidate)
- semantic boost: seleção ['https://allansantos-dv.github.io/opencode-marketplace/', 'https://docs.plannotator.ai/open-source/agents/opencode', 'https://github.com/Nsomnia/everything-opencode/blob/main/docs/pt-BR/agents/planner.md', 'https://github.com/sun-praise/opencode-review', 'https://opencode.ai/docs/pt-br/ecosystem/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/plugins?category=tools', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR'] sob ordem ['https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://www.opendock.net/plugins/opencode-planning-with-files/', 'https://allansantos-dv.github.io/opencode-marketplace/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/'] (gates de identidade/seleção intactos)
- substitution: memory-opencode-marketplace -> opencode-review-sun-praise (memory-opencode-marketplace sem evidência referenciada após 2 rounds; opencode-review-sun-praise com fonte própria coletada e mencionada)
- discovery cheio (64): https://github.com/st01cs/devis ignorado
- discovery cheio (64): https://github.com/vtemian/octto ignorado
- discovery cheio (64): https://github.com/Netflix/Hystrix ignorado
- semantic boost: 32 docs ranqueados (9 vetorizados, 24 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- evaluation revised for ('c2', 'pwf'): partial -> covered (origin=web)
- evaluation revised for ('c3', 'pwf'): insufficient -> partial (origin=web)
- evaluation revised for ('c5', 'ocreview'): partial -> insufficient (origin=web)
- evaluation revised for ('c6', 'pwf'): insufficient -> partial (origin=user-provided)
- evaluation revised for ('c8', 'pwf'): insufficient -> partial (origin=web)
- evaluation revised for ('c9', 'pwf'): insufficient -> partial (origin=web)
- evaluation revised for ('c10', 'pwf'): partial -> covered (origin=web)
- semantic boost: seleção ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://github.com/OthmanAdi/planning-with-files', 'https://github.com/anomalyco/opencode', 'https://github.com/awesome-opencode/awesome-opencode', 'https://opencode.ai/docs/pt-br/agents/', 'https://opencode.ai/docs/pt-br/cli/', 'https://www.opendock.net/plugins/opencode-planning-with-files/'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- semantic boost: 32 docs ranqueados (1 vetorizados, 32 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- discovery: alibaba-open-code-review fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c3 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c4 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c5 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c6 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c7 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c8 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c9 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c10 estendido a alibaba-open-code-review (per_candidate)
- discovery: critério c11 estendido a alibaba-open-code-review (per_candidate)
- semantic boost: seleção ['https://blog.cloudflare.com/ai-code-review/', 'https://composio.dev/content/best-opencode-plugins', 'https://github.com/alibaba/open-code-review', 'https://github.com/jadmadi/opencode-plugins', 'https://github.com/vichhka-git/opencode-shannon-plugin', 'https://npm.io/package/opencode-planner', 'https://opencode.ai/docs/plugins/', 'https://opencode.ai/v2/docs/plugins', 'https://www.opencode.cafe/'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- discovery cheio (64): https://github.com/letta-ai/letta ignorado
- discovery cheio (64): https://github.com/supermemoryai/opencode-supermemory ignorado
- discovery cheio (64): https://github.com/CaiJimmy/hugo-theme-stack ignorado
- semantic boost: 36 docs ranqueados (5 vetorizados, 32 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- discovery: opencode-agent-memory fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c3 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c4 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c5 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c6 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c7 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c8 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c9 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c10 estendido a opencode-agent-memory (per_candidate)
- discovery: critério c11 estendido a opencode-agent-memory (per_candidate)
- discovery: opencode-memory fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-memory (per_candidate)
- discovery: critério c3 estendido a opencode-memory (per_candidate)
- discovery: critério c4 estendido a opencode-memory (per_candidate)
- discovery: critério c5 estendido a opencode-memory (per_candidate)
- discovery: critério c6 estendido a opencode-memory (per_candidate)
- discovery: critério c7 estendido a opencode-memory (per_candidate)
- discovery: critério c8 estendido a opencode-memory (per_candidate)
- discovery: critério c9 estendido a opencode-memory (per_candidate)
- discovery: critério c10 estendido a opencode-memory (per_candidate)
- discovery: critério c11 estendido a opencode-memory (per_candidate)
- discovery: opencode-mem fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-mem (per_candidate)
- discovery: critério c3 estendido a opencode-mem (per_candidate)
- discovery: critério c4 estendido a opencode-mem (per_candidate)
- discovery: critério c5 estendido a opencode-mem (per_candidate)
- discovery: critério c6 estendido a opencode-mem (per_candidate)
- discovery: critério c7 estendido a opencode-mem (per_candidate)
- discovery: critério c8 estendido a opencode-mem (per_candidate)
- discovery: critério c9 estendido a opencode-mem (per_candidate)
- discovery: critério c10 estendido a opencode-mem (per_candidate)
- discovery: critério c11 estendido a opencode-mem (per_candidate)
- discovery: opencode-supermemory fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-supermemory (per_candidate)
- discovery: critério c3 estendido a opencode-supermemory (per_candidate)
- discovery: critério c4 estendido a opencode-supermemory (per_candidate)
- discovery: critério c5 estendido a opencode-supermemory (per_candidate)
- discovery: critério c6 estendido a opencode-supermemory (per_candidate)
- discovery: critério c7 estendido a opencode-supermemory (per_candidate)
- discovery: critério c8 estendido a opencode-supermemory (per_candidate)
- discovery: critério c9 estendido a opencode-supermemory (per_candidate)
- discovery: critério c10 estendido a opencode-supermemory (per_candidate)
- discovery: critério c11 estendido a opencode-supermemory (per_candidate)
- semantic boost: seleção ['https://github.com/awesome-opencode/awesome-opencode', 'https://github.com/chriswritescode-dev/opencode-memory', 'https://github.com/joshuadavidthomas/opencode-agent-memory', 'https://github.com/nikiforovall/opencode-marketplace', 'https://kd05.com/p/opencode-mem-memory-plugin-guide/', 'https://opencode.ai/docs/plugins/', 'https://opencode.ai/v2/docs/plugins', 'https://opencode.im/', 'https://opencode.im/categories/memory-context'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- discovery cheio (64): https://github.com/rohitg00/agentmemory ignorado
- discovery cheio (64): https://github.com/letta-ai/letta ignorado
- semantic boost: 38 docs ranqueados (3 vetorizados, 36 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- semantic boost: seleção ['https://github.com/awesome-opencode/awesome-opencode', 'https://github.com/nikiforovall/opencode-marketplace', 'https://opencode.ai/docs/plugins/', 'https://opencode.ai/v2/docs/plugins', 'https://opencode.im/', 'https://opencode.im/plugins', 'https://www.agent-memory.dev/docs/integrations/opencode', 'https://www.opencode.asia/ecosystem/plugins/agent-memory/', 'https://www.opencode.cafe/'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- semantic boost: 40 docs ranqueados (3 vetorizados, 38 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- discovery: oh-my-opencode fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a oh-my-opencode (per_candidate)
- discovery: critério c3 estendido a oh-my-opencode (per_candidate)
- discovery: critério c4 estendido a oh-my-opencode (per_candidate)
- discovery: critério c5 estendido a oh-my-opencode (per_candidate)
- discovery: critério c6 estendido a oh-my-opencode (per_candidate)
- discovery: critério c7 estendido a oh-my-opencode (per_candidate)
- discovery: critério c8 estendido a oh-my-opencode (per_candidate)
- discovery: critério c9 estendido a oh-my-opencode (per_candidate)
- discovery: critério c10 estendido a oh-my-opencode (per_candidate)
- discovery: critério c11 estendido a oh-my-opencode (per_candidate)
- discovery: opencode-workspace fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a opencode-workspace (per_candidate)
- discovery: critério c3 estendido a opencode-workspace (per_candidate)
- discovery: critério c4 estendido a opencode-workspace (per_candidate)
- discovery: critério c5 estendido a opencode-workspace (per_candidate)
- discovery: critério c6 estendido a opencode-workspace (per_candidate)
- discovery: critério c7 estendido a opencode-workspace (per_candidate)
- discovery: critério c8 estendido a opencode-workspace (per_candidate)
- discovery: critério c9 estendido a opencode-workspace (per_candidate)
- discovery: critério c10 estendido a opencode-workspace (per_candidate)
- discovery: critério c11 estendido a opencode-workspace (per_candidate)
- semantic boost: seleção ['https://dev.opencode.ai/docs/pt-br/ecosystem/', 'https://github.com/awesome-opencode/awesome-opencode', 'https://github.com/nikiforovall/opencode-marketplace', 'https://opencode.ai/docs/plugins/', 'https://opencode.ai/v2/docs/plugins', 'https://opencode.im/', 'https://opencode.im/plugins', 'https://www.opencode.cafe/', 'https://www.opendock.net/'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- semantic boost: 40 docs ranqueados (0 vetorizados, 41 do cache); top: https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://dicastech.com.br/revisao-de-codigo-com-ia/, https://opencode.ai/docs/pt-br/plugins/
- evaluation revised for ('c3', 'oplanner'): insufficient -> partial (origin=web)
- evaluation revised for ('c5', 'oplanner'): insufficient -> partial (origin=web)
- semantic boost: seleção ['https://docs.plannotator.ai/open-source/agents/opencode', 'https://github.com/awesome-opencode/awesome-opencode', 'https://github.com/nikiforovall/opencode-marketplace', 'https://github.com/timrichardson/opencode-planner', 'https://opencode.ai/docs/plugins/', 'https://opencode.ai/v2/docs/plugins', 'https://opencode.im/', 'https://opencode.im/plugins', 'https://www.opencode.cafe/'] sob ordem ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://dicastech.com.br/revisao-de-codigo-com-ia/', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://allansantos-dv.github.io/opencode-marketplace/'] (gates de identidade/seleção intactos)
- synthesis criterion c15 -> partial (markers=3, cited=8)

## 9. Encerramento e rodadas

- **Motivo de parada:** rounds — max_rounds=7 consumed (source=default; queries 19/30; unique_sources 0/150; extractions 85/120; yt_live_fetches 0/8; model_calls 10/16; model_remaining 6; elapsed=704.4s/1800s; reserva de finalização preservada); teto de rounds foi o único vinculante com 15 lacuna(s) aberta(s) e folga nos demais tetos — parada não-justificada por comparabilidade; ampliar max_rounds ou deixar budget/saturação decidir
- **Rodadas concluídas:** 7
- **Parcial:** True
