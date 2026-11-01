# Relatório de pesquisa: Descubra e compare cinco plugins para melhorar planejamento, implementação, testes e revisão de código no OpenCode. Considere a versão instalada neste computador. Investigue compatibilidade, funcionalidades demonstradas, dependências, custos, manutenção e limitações. Justifique quais combinam entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie funcionalidades documentadas de inferências.

Relatório gerado pelo renderer a partir do estado real; texto do modelo preservado como síntese.

**Status da cobertura:** parcial (proportion=0.018867924528301886) · **Motivo de parada:** rounds

**Cobertura:** 1/53 células obrigatórias — covered required (criterion, entity) cells / (total required cells minus not_applicable cells with scope evidence); not_applicable cells listed separately, never counted as covered

**N/A:** 2 célula(s) fora do escopo documentado — fora do denominador, listadas nos Achados, nunca contam como cobertura.

## 1. Resposta direta / resumo executivo

# Comparação de plugins OpenCode — corpus restrito, cobertura parcial

> Cobertura informada: `partial`, `1/53` células requeridas, `na: 2`, `plan_id: opencode-plugins-compare`, `plan_version: 13`, `run_id: accept31`. Versão instalada: `2.1.4` [contexto informado pelo usuário, não evidência coletada]. Este relatório usa SOMENTE o corpus selecionado abaixo; fora dele, tudo é LACUNA/INFERÊNCIA marcada.

### 1. Conjunto exigido e status de seleção

- O plano exige exatamente: `opencode-code-review`, `opencode-shannon-plugin`, `opencode-plugin`, `oh-my-opencode`, `oh-my-opencode-slim`.
- `opencode-code-review` tem fonte própria com identidade e células investigadas no corpus ([1]).
- `opencode-shannon-plugin` tem fonte própria com identidade e células investigadas no corpus ([9]).
- `oh-my-opencode-slim` tem apenas menção com configuração e descrição genérica em fonte de terceiros, sem células investigadas; status: LACUNA/insuficiente como membro comparado ([4]).
- `oh-my-opencode` aparece apenas como dependência opcional para orquestração de agentes no documento de `opencode-shannon-plugin`, sem fonte própria/célula investigada; por isso é LACUNA como membro do conjunto exigido ([9]).
- Status de `opencode-plugin`: LACUNA com causa — sem fonte própria/célula investigada no corpus selecionado acima; não é apresentado como parte comparada sem essa ressalva.
- Explorado fora da seleção e NÃO contado: `opencode-code-review (@bandonker)` (`prop-bandonker-review`).
- Não investigados — nenhum fato afirmado sobre eles: `https://github.com/KeygraphHQ/shannon`, `https://github.com/vichhka-git/opencode-shannon-plugin/releases`, `opencode-plugin`, `oh-my-opencode`.

### 2. Compatibilidade com a versão instalada

- `opencode-shannon-plugin` declara requisito `opencode >= 1.0.150` ([9]).
- Comparação numérica: `2.1.4` [informado pelo usuário] satisfaz o mínimo `>= 1.0.150` declarado no corpus ([9]).
- Compatibilidade funcional de `opencode-shannon-plugin` com `2.1.4` é LACUNA, pois nenhum trecho do excerto cita `2.1.4` ([9]).
- Compatibilidade de `opencode-code-review` com `2.1.4` é LACUNA, pois nenhum trecho examinado cita versão mínima do OpenCode nem `2.1.4` ([1]).
- Compatibilidade de `oh-my-opencode-slim` com `2.1.4` é LACUNA, pois nenhum trecho examinado cita versão mínima do OpenCode nem `2.1.4` ([4]).
- Compatibilidade de `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem fonte própria no corpus selecionado para verificar qualquer requisito de versão.

### 3. Funcionalidades documentadas por critério

### 3.1 Planejamento

- `opencode-code-review` tem escopo documentado de revisão automatizada de PRs, sem tratar planejamento; célula `c2` é `not_applicable` na cobertura informada ([1]).
- Nenhum trecho examinado de `opencode-shannon-plugin` trata planejamento geral; excertos tratam penetração autônoma, logo planejamento é LACUNA/insuficiente ([9]).
- Nenhum trecho examinado de `oh-my-opencode-slim` trata planejamento como célula investigada; excertos falam apenas de organização/estrutura, logo é LACUNA/insuficiente ([4]).
- Planejamento em `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem fonte própria/célula no corpus selecionado.

### 3.2 Implementação

- Nenhum trecho examinado de `opencode-code-review` documenta geração/implementação de código; excertos documentam revisão de diff/PR, logo implementação é LACUNA/ausência verificada ([1]).
- Nenhum trecho examinado de `opencode-shannon-plugin` documenta implementação geral de software; excertos documentam pentest e geração de relatório, logo implementação é LACUNA ([9]).
- Implementação em `oh-my-opencode-slim` é LACUNA/insuficiente, pois o excerto só sustenta instalação via `plugin` e objetivo de organização ([4]).
- Implementação em `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem fonte própria/célula no corpus selecionado.

### 3.3 Testes

- `opencode-code-review` tem escopo de review de PR/diff (`max_diff_lines`, `trigger`, `custom_rules`), sem tratar geração ou execução de testes; célula `c4` é `not_applicable` na cobertura informada ([3]).
- `opencode-shannon-plugin` documenta pentest autônomo, não testes gerais de software; afirmar que cobre testes funcionais seria INFERÊNCIA não sustentada ([9]).
- Testes em `oh-my-opencode-slim` são LACUNA, pois nenhum trecho examinado trata testes ([4]).
- Testes em `opencode-plugin` e `oh-my-opencode` são LACUNA com causa: sem fonte própria/célula no corpus selecionado.

### 3.4 Revisão de código

- `opencode-code-review` realiza revisão automatizada de PRs com subagentes especializados e pontuação por confiança ([1]).
- `opencode-code-review` usa `cr-gatekeeper`/`cr-guidelines` com `haiku`, `cr-summarizer` com `sonnet` e `cr-compliance` com `opus` ([1]).
- `opencode-code-review` verifica conformidade com `CLAUDE.md`, foca em mudanças e usa `git history/blame` como contexto ([1]).
- `opencode-code-review` usa limiar `80` para filtrar falsos positivos ([1]).
- `opencode-shannon-plugin` gera relatório de segurança, não revisão de código geral; equivalência com code review é LACUNA, não afirmação sustentada ([9]).
- Revisão em `oh-my-opencode-slim`, `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem célula investigada/fonte própria no corpus selecionado.

### 4. Dependências

- `opencode-code-review` requer `Node.js 18+` e `pnpm` para desenvolvimento ([3]).
- `opencode-code-review` declara `Deps 1` e instalação por `npm i opencode-code-review` ([3]).
- `opencode-code-review` instala copiando agentes, comando e plugin para `~/.config/opencode/` ou `.opencode/` por projeto ([1]).
- `opencode-shannon-plugin` requer `Bun >= 1.3.9` ([9]).
- `opencode-shannon-plugin` requer build com `bun install && bun run build` e `docker build -t shannon-tools .` ([9]).
- `opencode-shannon-plugin` lista `Oh-My-OpenCode` como opcional para orquestração de agentes ([9]).
- `oh-my-opencode-slim` instala via `plugin: ["oh-my-opencode-slim"]` ([4]).
- Dependências de `opencode-plugin` e `oh-my-opencode` são LACUNA com causa: sem fonte própria no corpus selecionado.

### 5. Custos

- `opencode-code-review` é `MIT` ([3]).
- `opencode-shannon-plugin` é `AGPL-3.0` e baseado em `Shannon` ([9]).
- `opencode-shannon-plugin` documenta configuração econômica com `Claude Sonnet 4.5` e relatório com `Claude Opus 4.5`, sem valores monetários ([9]).
- Custo de uso/assinatura, tokens e infra de `opencode-code-review` são LACUNA, pois nenhum trecho examinado informa preços ([3]).
- Custo de `oh-my-opencode-slim`, `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem fonte própria/célula de custo no corpus selecionado.

### 6. Manutenção

- `opencode-code-review` está em `1.0.9`, publicado há `3 months ago`, com `Vulns 0` no excerto ([3]).
- `opencode-code-review` documenta `pnpm typecheck`, `lint`, `build`, `test` e `verify` ([3]).
- Manutenção/versão/data de `opencode-shannon-plugin` são LACUNA, pois nenhum trecho examinado informa versão ou data ([9]).
- Manutenção de `oh-my-opencode-slim`, `opencode-plugin` e `oh-my-opencode` é LACUNA com causa: sem fonte própria/célula no corpus selecionado.

### 7. Limitações documentadas

- `opencode-code-review` limita com `max_diff_lines: 500` ([3]).
- `opencode-code-review` usa `trigger.auto_on_idle: true` com `cooldown_seconds: 120` ([3]).
- `opencode-shannon-plugin` exige `Docker`/`shannon-tools` e modelos de fronteira, o que limita uso offline/econômico; INFERÊNCIA sobre peso seria além do corpus, então registra-se apenas o requisito documentado ([9]).
- Limitações de `oh-my-opencode-slim` são LACUNA além da ressalva documentada de só instalar quando precisar de mais estrutura ([4]).
- Limitações de `opencode-plugin` e `oh-my-opencode` são LACUNA com causa: sem fonte própria no corpus selecionado.

### 8. Combinações e sobreposições

- Combinação documentada: `opencode-shannon-plugin` + `oh-my-opencode`, pois o segundo é opcional para orquestração do primeiro ([9]).
- Demais combinações entre os cinco exigidos são LACUNA, pois nenhuma fonte do corpus compara ou testa interoperabilidade entre elas.
- Sobreposição afirmável: nenhuma sobreposição funcional é demonstrada no corpus entre `opencode-code-review` e `opencode-shannon-plugin`, pois um trata review de PR e o outro pentest ([1]).
- Sobreposição afirmável pelo outro lado: relatório de segurança de `opencode-shannon-plugin` não equivale a review de PR no corpus ([9]).
- Qualquer afirmação de sobreposição envolvendo `opencode-plugin`, `oh-my-opencode` ou `oh-my-opencode-slim` seria INFERÊNCIA; marca-se LACUNA por ausência de células comparativas.
- Diretório geral lista `146 Plugins`, sem sustentar fatos por entidade exigida ([6]).

### 9. Contradições, lacunas e não verificados

- Nenhuma contradição entre fontes da mesma entidade foi verificada nos excertos confrontados; prevalecem lacunas, não conflitos.
- Não verificado: funcionalidades, dependências, custos, manutenção e compatibilidade real com `2.1.4` de `opencode-plugin` e `oh-my-opencode` por falta de fonte própria.
- Não verificado: planejamento, implementação, testes e revisão para `oh-my-opencode-slim` além de organização/estrutura genérica ([4]).
- Não verificado: execução real, tokens/custos e integração funcional com `2.1.4` para todos; comparação numérica de mínimo não prova funcionamento.

### 10. Riscos e o que não foi checado

- Não checado: repositórios/funcionalidades fora do corpus selecionado; menor opção seria investigar só `opencode-code-review` e `shannon` que têm fonte própria.
- Risco: cobertura `1/53` impede recomendar conjunto de cinco; qualquer escolha além da combinação `shannon` + `oh-my-opencode` opcional seria inferência sem evidência.

## 2. Escopo, critérios, método e configuração efetiva

- **Pergunta:** Descubra e compare cinco plugins para melhorar planejamento, implementação, testes e revisão de código no OpenCode. Considere a versão instalada neste computador. Investigue compatibilidade, funcionalidades demonstradas, dependências, custos, manutenção e limitações. Justifique quais combinam entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie funcionalidades documentadas de inferências.
- **Data:** 2026-11-01T09:16:34Z (gerado em 2026-11-01T09:26:56Z)
- **Perfil:** medium
- **Amplitude:** 3 | **Profundidade:** 2
- **Rodadas:** 3 (Rodadas concluídas: 3)
- **Concorrência:** 4
- **Orçamento:** limites={'time_s': 1800, 'queries': 30, 'unique_sources': 150, 'extractions': 120, 'yt_live_fetches': 8}; consumido=unknown; tokens=unknown; custo=unknown
- **Critérios:** 15 | **Entidades:** 12
- **Coleta por canal:** web: 8 ok / 5 falha(s)


## 3. Achados por critério

### identificar cinco plugins candidatos para planejamento, implementação, testes e revisão no OpenCode — parcial
Material nomeia candidatos pertinentes (suite @bandonker/opencode-*, oh-my-opencode, ranger-testing/opencode-plugin, opencode-code-review, opencode-browser-plugin, shannon-plugin) em diretorios e repos, mas excertos estão truncados e sem qualificação sistemática dos cinco nos eixos exigidos.
Referências: [2], [6], [8], [1], [9], [10]
Alcance examinado: excertos de 25/25 docs únicos das entidades (49949 chars de 3217551 coletados); global: excertos examinados (25/25 docs)

### melhora planejamento — insuficiente
Escopo documentado é code review automatizado de PRs (port do /code-review do Claude Code, com git history/blame); nenhum trecho trata planejamento, que está fora do escopo declarado.
Referências: [1]

| Entidade | Estado |
|---|---|
| opencode-code-review | não aplicável |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)
- **N/A** opencode-code-review: Escopo documentado é code review automatizado de PRs (port do /code-review do Claude Code, com git history/blame); nenhum trecho trata planejamento, que está fora do escopo declarado.

### melhora implementação — parcial
Review automatizado com custom_rules e análise de git history incide sobre código implementado e pode melhorar implementação via achados; sem geração de código documentada.
Referências: [1], [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### melhora testes — insuficiente
Escopo documentado é review de PRs/diff (max_diff_lines, trigger, custom_rules); nenhum trecho trata geração ou execução de testes.
Referências: [3], [1]

| Entidade | Estado |
|---|---|
| opencode-code-review | não aplicável |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)
- **N/A** opencode-code-review: Escopo documentado é review de PRs/diff (max_diff_lines, trigger, custom_rules); nenhum trecho trata geração ou execução de testes.

### melhora revisão de código — parcial
Documenta diretamente review automatizado de PRs (port do plugin de review do Claude Code) com git history/blame, custom_rules e notificações.
Referências: [1], [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | coberto |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### compatibilidade com a versão instalada neste computador — insuficiente
LACUNA: nenhuma fonte selecionada menciona compatibilidade com 2.1.4; versao instalada sozinha nao sustenta compatibilidade funcional.
Referências: (não investigado: user://context/installed_opencode_version)

| Entidade | Estado |
|---|---|
| opencode-code-review | insuficiente |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### funcionalidades demonstradas — parcial
Documenta instalacao (agents/commands/plugin), review de PRs, blame/history, notificacoes macOS/Linux e threshold score.
Referências: [1]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | parcial |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### dependências — parcial
Exige Node.js 18+ e pnpm, 1 dependência; instalação em diretórios de plugin; plugins npm instalados via Bun no startup. Versões das dependências não detalhadas.
Referências: [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### custos — parcial
Licença MIT e distribuição npm documentadas (sem custo de licença); custos operacionais de modelo/API não tratados.
Referências: [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### manutenção — parcial
Versão 1.0.9 publicada há ~3 meses indica recência; sem histórico de commits, issues ou cadência no material.
Referências: [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### limitações — parcial
Limite documentado max_diff_lines 500 e trigger com cooldown 120s; demais limitações e falhas não tratadas.
Referências: [3]

| Entidade | Estado |
|---|---|
| opencode-code-review | parcial |
| opencode-shannon-plugin | insuficiente |
| opencode-plugin | insuficiente |
| oh-my-opencode | insuficiente |
| oh-my-opencode-slim | insuficiente |
Alcance examinado: excertos de 18/18 docs únicos das entidades (49949 chars de 3217551 coletados); opencode-code-review: excerto examinado (4/4 docs); opencode-shannon-plugin: excerto examinado (1/1 docs); opencode-browser-plugin (heimoshuiyu): desconhecido-legítimo (nada no corpus sobre a entidade); opencode-plugin: excerto examinado (11/11 docs); oh-my-opencode: excerto examinado (6/6 docs); opencode-code-review (@bandonker): excerto examinado (1/1 docs); oh-my-opencode-slim: excerto examinado (3/3 docs); opencode-notify: excerto examinado (2/2 docs); opencode-code-review: excerto examinado (4/4 docs); Context7: excerto examinado (4/4 docs); oh-my-openagent: excerto examinado (5/5 docs)

### justificar quais plugins combinam entre si — parcial
Apenas par shannon+oh-my-opencode tem combinacao documentada ('Installation with Oh-My-OpenCode', 'Combined Configuration'); justificativa geral de quais combinam entre os cinco ausente.
Referências: [9]
Alcance examinado: excertos de 25/25 docs únicos das entidades (49949 chars de 3217551 coletados); global: excertos examinados (25/25 docs)

### justificar quais plugins têm funções sobrepostas — insuficiente
Nenhuma fonte compara sobreposicao de funcoes entre os cinco; listagens lado a lado em diretorios nao sao analise de sobreposicao.
Referências: [6], [8]
Alcance examinado: excertos de 25/25 docs únicos das entidades (49949 chars de 3217551 coletados); global: excertos examinados (25/25 docs)

### usar fontes atuais — parcial
Fontes incluem diretorio com V 2.3.2 e 146 plugins, paginas opendock com datas 2026-04-11 e 2026-09-21, docs oficial e repos com status usable; currency sistematica por celula nao demonstrada nos excertos.
Referências: [6], [10], [2], [5]
Alcance examinado: excertos de 25/25 docs únicos das entidades (49949 chars de 3217551 coletados); global: excertos examinados (25/25 docs)

### diferenciar funcionalidades documentadas de inferências na síntese — parcial
Síntese entregue separa material (3 marcadores: documentado, inferência, lacuna; 5 fonte(s) do corpus citadas).
Referências: [4], [1], [9], [3], [6]
Alcance examinado: excertos de 25/25 docs únicos das entidades (49949 chars de 3217551 coletados); global: excertos examinados (25/25 docs)

## 5. Limitações, contradições, incertezas e não investigados

### Lacunas obrigatórias pendentes
- **identificar cinco plugins candidatos para planejamento, implementação, testes e revisão no OpenCode** (parcial): Material nomeia candidatos pertinentes (suite @bandonker/opencode-*, oh-my-opencode, ranger-testing/opencode-plugin, opencode-code-review, opencode-browser-plugin, shannon-plugin) em diretorios e repos, mas excertos estão truncados e sem qualificação sistemática dos cinco nos eixos exigidos.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **melhora planejamento** (insuficiente): Escopo documentado é code review automatizado de PRs (port do /code-review do Claude Code, com git history/blame); nenhum trecho trata planejamento, que está fora do escopo declarado.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **melhora implementação** (parcial): Review automatizado com custom_rules e análise de git history incide sobre código implementado e pode melhorar implementação via achados; sem geração de código documentada.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **melhora testes** (insuficiente): Escopo documentado é review de PRs/diff (max_diff_lines, trigger, custom_rules); nenhum trecho trata geração ou execução de testes.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **melhora revisão de código** (parcial): Documenta diretamente review automatizado de PRs (port do plugin de review do Claude Code) com git history/blame, custom_rules e notificações.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **compatibilidade com a versão instalada neste computador** (insuficiente): LACUNA: nenhuma fonte selecionada menciona compatibilidade com 2.1.4; versao instalada sozinha nao sustenta compatibilidade funcional.
  - Próximo passo: ler a fonte própria de opencode-code-review (https://github.com/erskingardner/opencode-code-review) nas seções da dimensão; ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão
- **funcionalidades demonstradas** (parcial): Documenta instalacao (agents/commands/plugin), review de PRs, blame/history, notificacoes macOS/Linux e threshold score.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão
- **dependências** (parcial): Exige Node.js 18+ e pnpm, 1 dependência; instalação em diretórios de plugin; plugins npm instalados via Bun no startup. Versões das dependências não detalhadas.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **custos** (parcial): Licença MIT e distribuição npm documentadas (sem custo de licença); custos operacionais de modelo/API não tratados.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **manutenção** (parcial): Versão 1.0.9 publicada há ~3 meses indica recência; sem histórico de commits, issues ou cadência no material.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **limitações** (parcial): Limite documentado max_diff_lines 500 e trigger com cooldown 120s; demais limitações e falhas não tratadas.
  - Próximo passo: ler a fonte própria de opencode-shannon-plugin (https://github.com/vichhka-git/opencode-shannon-plugin) nas seções da dimensão; ler a fonte própria de opencode-plugin (https://www.opendock.net/categories/testing/) nas seções da dimensão; ler a fonte própria de oh-my-opencode (https://opencode.im/) nas seções da dimensão; ler a fonte própria de oh-my-opencode-slim (https://opencode.im/) nas seções da dimensão
- **justificar quais plugins combinam entre si** (parcial): Apenas par shannon+oh-my-opencode tem combinacao documentada ('Installation with Oh-My-OpenCode', 'Combined Configuration'); justificativa geral de quais combinam entre os cinco ausente.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **justificar quais plugins têm funções sobrepostas** (insuficiente): Nenhuma fonte compara sobreposicao de funcoes entre os cinco; listagens lado a lado em diretorios nao sao analise de sobreposicao.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **usar fontes atuais** (parcial): Fontes incluem diretorio com V 2.3.2 e 146 plugins, paginas opendock com datas 2026-04-11 e 2026-09-21, docs oficial e repos com status usable; currency sistematica por celula nao demonstrada nos excertos.
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima
- **diferenciar funcionalidades documentadas de inferências na síntese** (parcial): Síntese entregue separa material (3 marcadores: documentado, inferência, lacuna; 5 fonte(s) do corpus citadas).
  - Próximo passo: investigar critério obrigatório; tentativas anteriores preservadas acima

### Incertezas e material não verificado
- melhora planejamento: insuficiente — Escopo documentado é code review automatizado de PRs (port do /code-review do Claude Code, com git history/blame); nenhum trecho trata planejamento, que está fora do escopo declarado.
- melhora testes: insuficiente — Escopo documentado é review de PRs/diff (max_diff_lines, trigger, custom_rules); nenhum trecho trata geração ou execução de testes.
- compatibilidade com a versão instalada neste computador: insuficiente — LACUNA: nenhuma fonte selecionada menciona compatibilidade com 2.1.4; versao instalada sozinha nao sustenta compatibilidade funcional.
- justificar quais plugins têm funções sobrepostas: insuficiente — Nenhuma fonte compara sobreposicao de funcoes entre os cinco; listagens lado a lado em diretorios nao sao analise de sobreposicao.

### Notas da execução
- downgrade without new evidence rejected for ('c5', 'cand-review-erskingardner'): kept covered (assessor said partial)
- downgrade without new evidence rejected for ('c8', 'cand-review-erskingardner'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c9', 'cand-review-erskingardner'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c10', 'cand-review-erskingardner'): kept partial (assessor said insufficient)
- downgrade without new evidence rejected for ('c11', 'cand-review-erskingardner'): kept partial (assessor said insufficient)

## 6. Conclusão e próximos passos

A investigação é **parcial**: há critérios obrigatórios sem cobertura suficiente (ver seção 5). A conclusão não pode ser apresentada como completa.

**Próximo passo:** ver detalhes por lacuna na seção 5 (15 pendente(s)); priorizar células com fonte própria indicada.

## 7. Fontes

Numeração estável do corpus obtido; nenhuma fonte é inventada pelo modelo.

| # | URL | Título | Obtida em | Tipo | Alcance lido |
|---|---|---|---|---|---|
| [1] | https://github.com/erskingardner/opencode-code-review | erskingardner/opencode-code-review | 2026-11-01T09:17:31Z | repository | 4044/4044 chars (usable) |
| [2] | https://www.opendock.net/plugins/bandonker--opencode-code-review/ | não registrado | 2026-11-01T09:17:31Z | page | 173851/173851 chars (usable) |
| [3] | https://npm.io/package/opencode-code-review | não registrado | 2026-11-01T09:17:31Z | page | 120318/120318 chars (usable) |
| [4] | https://composio.dev/content/best-opencode-plugins | não registrado | 2026-11-01T09:21:40Z | page | 306911/306911 chars (usable) |
| [5] | https://opencode.ai/docs/plugins/ | não registrado | 2026-11-01T09:17:31Z | page | 102552/102552 chars (usable) |
| [6] | https://opencode.im/ | não registrado | 2026-11-01T09:21:40Z | page | 235419/235419 chars (usable) |
| [7] | https://github.com/michaljach/opencode-browser | michaljach/opencode-browser | 2026-11-01T09:17:31Z | repository | 13711/13711 chars (usable) |
| [8] | https://www.opendock.net/categories/testing/ | não registrado | 2026-11-01T09:17:31Z | page | 126457/126457 chars (usable) |
| [9] | https://github.com/vichhka-git/opencode-shannon-plugin | vichhka-git/opencode-shannon-plugin | 2026-11-01T09:17:31Z | repository | 12043/12043 chars (usable) |
| [10] | https://www.opendock.net/plugins/opencode-browser-plugin/ | não registrado | 2026-11-01T09:17:31Z | page | 91585/91585 chars (usable) |
| [11] | https://opencodeguide.com/en/opencode-mcp-playwright/ | não registrado | 2026-11-01T09:17:32Z | page | 41061/41061 chars (usable) |
| [12] | https://www.opencode.asia/recipes/browser-automation/ | não registrado | 2026-11-01T09:17:32Z | page | 73212/73212 chars (usable) |
| [13] | https://github.com/opencode-ai/opencode | opencode-ai/opencode | 2026-11-01T09:19:38Z | repository | 24434/24434 chars (usable) |
| [14] | https://opencode.ai/docs/pt-br/plugins/ | não registrado | 2026-11-01T09:21:40Z | page | 104167/104167 chars (usable) |
| [15] | https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR | não registrado | 2026-11-01T09:22:52Z | page | 49724/49724 chars (usable) |
| [16] | https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb | não registrado | 2026-11-01T09:21:40Z | page | 187490/187490 chars (usable) |
| [17] | https://web-tutorial.com/pt-br/opencode/custom-tools.html | não registrado | 2026-11-01T09:21:40Z | page | 50853/50853 chars (usable) |
| [18] | https://github.com/rianprei/opencode-engineering | rianprei/opencode-engineering | 2026-11-01T09:21:40Z | repository | 3665/3665 chars (usable) |
| [19] | https://opencode.ai/docs/pt-br/tools/ | não registrado | 2026-11-01T09:21:40Z | page | 85700/85700 chars (usable) |
| [20] | https://github.com/MetalbolicX/opencode-code-review | MetalbolicX/opencode-code-review | 2026-11-01T09:21:40Z | repository | 14187/14187 chars (usable) |
| [21] | https://opencode.im/plugins?category=integration | não registrado | 2026-11-01T09:21:40Z | page | 179920/179920 chars (usable) |
| [22] | https://github.com/awesome-opencode/awesome-opencode | awesome-opencode/awesome-opencode | 2026-11-01T09:21:40Z | repository | 121721/121721 chars (usable) |
| [23] | https://www.opencode.asia/plugins/ | não registrado | 2026-11-01T09:21:40Z | page | 118899/118899 chars (usable) |
| [24] | https://forums.basehub.com/anomalyco/opencode/22 | não registrado | 2026-11-01T09:21:40Z | page | 110676/110676 chars (usable) |
| [25] | https://www.kdnuggets.com/7-opencode-plugins-that-make-ai-coding-more-powerful | não registrado | 2026-11-01T09:22:52Z | page | 272870/272870 chars (usable) |

## 8. Anexo: verificações e contadores

### Verificações independentes
| Dimensão | Estado | Evidência |
|---|---|---|
| execution | ok | 10 campo(s) |
| question | partial | 7 campo(s) |
| review | partial | 11 campo(s) |
| support | partial | 17 campo(s) |
- execution: 5 falha(s) registradas por motivo
- question: 15 critério(s) obrigatório(s) pendente(s)
- support: support: 29/46 frase(s) citada(s) sustentada(s); 48 sem citação; 2 declaração(ões) de lacuna sustentada(s); 29 inferência(s) declarada(s) (nunca supported por âncora); 2 partial(is) declarada(s) (premissas em fontes distintas, limites explícitos)

### Contadores de seis estágios
| Estágio | Documentos |
|---|---:|
| discovered | 27 |
| obtained | 25 |
| usable | 25 |
| analyzed | 25 |
| used_in_synthesis | 6 |
| cited | 9 |

| Relação | Documentos | Tipo |
|---|---|---|
| version | https://composio.dev/content/best-opencode-plugins ↔ https://composio.dev/content/best-opencode-plugins | trecho distinto da mesma URL (1 anterior(es)) |
| version | https://opencode.im/ ↔ https://opencode.im/ | trecho distinto da mesma URL (1 anterior(es)) |
| version | https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR ↔ https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR | trecho distinto da mesma URL (1 anterior(es)) |

**Leitura:** 1.6% dos caracteres do corpus incluídos em excertos avaliados (49949/3217551 chars; 39 batches de excerto em 25 docs únicos de 25 coletados; avaliados únicos pelo assessor: 25)
saturação de URLs novas ≠ análise esgotada; batches contam repetições entre chamadas, únicos não

### Notas técnicas (diagnóstico interno)
- semantic boost: 12 docs ranqueados (13 vetorizados, 0 do cache); top: https://opencode.im/, https://www.opendock.net/categories/testing/, https://www.opendock.net/plugins/bandonker--opencode-code-review/
- discovery: critério c2 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c3 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c4 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c5 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c6 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c7 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c8 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c9 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c10 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c11 estendido a cand-review-erskingardner (per_candidate)
- discovery: critério c2 estendido a cand-shannon (per_candidate)
- discovery: critério c3 estendido a cand-shannon (per_candidate)
- discovery: critério c4 estendido a cand-shannon (per_candidate)
- discovery: critério c5 estendido a cand-shannon (per_candidate)
- discovery: critério c6 estendido a cand-shannon (per_candidate)
- discovery: critério c7 estendido a cand-shannon (per_candidate)
- discovery: critério c8 estendido a cand-shannon (per_candidate)
- discovery: critério c9 estendido a cand-shannon (per_candidate)
- discovery: critério c10 estendido a cand-shannon (per_candidate)
- discovery: critério c11 estendido a cand-shannon (per_candidate)
- discovery: cand-browser-playwright fora da cobertura (sem menção na fonte própria; rastreado)
- discovery: critério c2 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c3 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c4 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c5 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c6 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c7 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c8 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c9 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c10 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c11 estendido a cand-browser-playwright (per_candidate)
- discovery: critério c2 estendido a cand-ranger (per_candidate)
- discovery: critério c3 estendido a cand-ranger (per_candidate)
- discovery: critério c4 estendido a cand-ranger (per_candidate)
- discovery: critério c5 estendido a cand-ranger (per_candidate)
- discovery: critério c6 estendido a cand-ranger (per_candidate)
- discovery: critério c7 estendido a cand-ranger (per_candidate)
- discovery: critério c8 estendido a cand-ranger (per_candidate)
- discovery: critério c9 estendido a cand-ranger (per_candidate)
- discovery: critério c10 estendido a cand-ranger (per_candidate)
- discovery: critério c11 estendido a cand-ranger (per_candidate)
- discovery: critério c2 estendido a cand-ohmy (per_candidate)
- discovery: critério c3 estendido a cand-ohmy (per_candidate)
- discovery: critério c4 estendido a cand-ohmy (per_candidate)
- discovery: critério c5 estendido a cand-ohmy (per_candidate)
- discovery: critério c6 estendido a cand-ohmy (per_candidate)
- discovery: critério c7 estendido a cand-ohmy (per_candidate)
- discovery: critério c8 estendido a cand-ohmy (per_candidate)
- discovery: critério c9 estendido a cand-ohmy (per_candidate)
- discovery: critério c10 estendido a cand-ohmy (per_candidate)
- discovery: critério c11 estendido a cand-ohmy (per_candidate)
- semantic boost: seleção ['https://github.com/erskingardner/opencode-code-review', 'https://github.com/michaljach/opencode-browser', 'https://github.com/vichhka-git/opencode-shannon-plugin', 'https://opencode.ai/docs/plugins/', 'https://opencode.im/', 'https://www.opendock.net/categories/testing/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/', 'https://www.opendock.net/plugins/opencode-browser-plugin/'] sob ordem ['https://opencode.im/', 'https://www.opendock.net/categories/testing/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/', 'https://opencode.ai/docs/plugins/', 'https://github.com/erskingardner/opencode-code-review', 'https://www.opendock.net/plugins/opencode-browser-plugin/'] (gates de identidade/seleção intactos)
- semantic boost: 13 docs ranqueados (2 vetorizados, 12 do cache); top: https://opencode.im/, https://www.opendock.net/categories/testing/, https://www.opendock.net/plugins/bandonker--opencode-code-review/
- discovery: critério c2 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c3 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c4 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c5 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c6 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c7 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c8 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c9 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c10 estendido a prop-bandonker-review (per_candidate)
- discovery: critério c11 estendido a prop-bandonker-review (per_candidate)
- discovery: prop-ohmy-slim fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c3 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c4 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c5 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c6 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c7 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c8 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c9 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c10 estendido a prop-ohmy-slim (per_candidate)
- discovery: critério c11 estendido a prop-ohmy-slim (per_candidate)
- discovery: prop-opencode-notify fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c3 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c4 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c5 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c6 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c7 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c8 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c9 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c10 estendido a prop-opencode-notify (per_candidate)
- discovery: critério c11 estendido a prop-opencode-notify (per_candidate)
- semantic boost: seleção ['https://composio.dev/content/best-opencode-plugins', 'https://github.com/erskingardner/opencode-code-review', 'https://github.com/opencode-ai/opencode', 'https://npm.io/package/opencode-code-review', 'https://opencode.ai/docs/plugins/', 'https://opencode.im/', 'https://opencodeguide.com/en/opencode-mcp-playwright/', 'https://www.opencode.asia/recipes/browser-automation/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/'] sob ordem ['https://opencode.im/', 'https://www.opendock.net/categories/testing/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/', 'https://opencode.ai/docs/plugins/', 'https://www.opendock.net/plugins/opencode-browser-plugin/', 'https://github.com/erskingardner/opencode-code-review'] (gates de identidade/seleção intactos)
- substitution: prop-bandonker-review -> prop-ohmy-slim (prop-bandonker-review sem evidência referenciada após 2 rounds; prop-ohmy-slim com fonte própria coletada e mencionada)
- semantic boost: 24 docs ranqueados (12 vetorizados, 13 do cache); top: https://opencode.ai/docs/pt-br/plugins/, https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://opencode.im/
- semantic boost: seleção ['https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://github.com/awesome-opencode/awesome-opencode', 'https://github.com/rianprei/opencode-engineering', 'https://opencode.ai/docs/pt-br/plugins/', 'https://opencode.ai/docs/pt-br/tools/', 'https://opencode.im/plugins?category=integration', 'https://www.opencode.asia/plugins/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR'] sob ordem ['https://opencode.ai/docs/pt-br/plugins/', 'https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://www.opendock.net/categories/testing/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/'] (gates de identidade/seleção intactos)
- discovery cheio (64): https://github.com/supermemoryai/opencode-supermemory ignorado
- semantic boost: 25 docs ranqueados (2 vetorizados, 24 do cache); top: https://opencode.ai/docs/pt-br/plugins/, https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb, https://opencode.im/
- discovery: prop-metalbolic-review fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c3 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c4 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c5 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c6 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c7 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c8 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c9 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c10 estendido a prop-metalbolic-review (per_candidate)
- discovery: critério c11 estendido a prop-metalbolic-review (per_candidate)
- discovery: prop-context7 fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a prop-context7 (per_candidate)
- discovery: critério c3 estendido a prop-context7 (per_candidate)
- discovery: critério c4 estendido a prop-context7 (per_candidate)
- discovery: critério c5 estendido a prop-context7 (per_candidate)
- discovery: critério c6 estendido a prop-context7 (per_candidate)
- discovery: critério c7 estendido a prop-context7 (per_candidate)
- discovery: critério c8 estendido a prop-context7 (per_candidate)
- discovery: critério c9 estendido a prop-context7 (per_candidate)
- discovery: critério c10 estendido a prop-context7 (per_candidate)
- discovery: critério c11 estendido a prop-context7 (per_candidate)
- discovery: prop-oh-my-openagent fora da cobertura (além do teto de 5 candidatos; rastreado)
- discovery: critério c2 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c3 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c4 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c5 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c6 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c7 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c8 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c9 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c10 estendido a prop-oh-my-openagent (per_candidate)
- discovery: critério c11 estendido a prop-oh-my-openagent (per_candidate)
- evaluation revised for ('c7', 'prop-ohmy-slim'): insufficient -> partial (origin=web)
- unexplored reconciliado: 1 registro(s) com covered/partial posterior removido(s)
- semantic boost: seleção ['https://composio.dev/content/best-opencode-plugins', 'https://forums.basehub.com/anomalyco/opencode/22', 'https://github.com/MetalbolicX/opencode-code-review', 'https://github.com/erskingardner/opencode-code-review', 'https://npm.io/package/opencode-code-review', 'https://web-tutorial.com/pt-br/opencode/custom-tools.html', 'https://www.kdnuggets.com/7-opencode-plugins-that-make-ai-coding-more-powerful', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/'] sob ordem ['https://opencode.ai/docs/pt-br/plugins/', 'https://dev.to/he4rt/sistema-de-planejamento-estruturado-no-opencode-16pb', 'https://opencode.im/', 'https://www.yodev.dev/t/tu-opencode-esta-vacio-10-plugins-y-agentes-que-vale-la-pena-instalar/3369?tl=pt_BR', 'https://www.opendock.net/categories/testing/', 'https://www.opendock.net/plugins/bandonker--opencode-code-review/'] (gates de identidade/seleção intactos)
- synthesis criterion c15 -> partial (markers=3, cited=5)

## 9. Encerramento e rodadas

- **Motivo de parada:** rounds — max_rounds=3 consumed (source=default; queries 10/30; unique_sources 0/150; extractions 40/120; yt_live_fetches 0/8; model_calls 5/16; model_remaining 11; elapsed=409.9s/1800s; reserva de finalização preservada); teto de rounds foi o único vinculante com 15 lacuna(s) aberta(s) e folga nos demais tetos — parada não-justificada por comparabilidade; ampliar max_rounds ou deixar budget/saturação decidir
- **Rodadas concluídas:** 3
- **Parcial:** True
