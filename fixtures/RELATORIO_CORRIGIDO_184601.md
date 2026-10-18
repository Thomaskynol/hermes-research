# Extensões Gratuitas para OpenCode que Melhoram a Qualidade do Desenvolvimento

**Escopo:** OpenCode — agente de codificação open-source, local-first, agnóstico a provedores.
**Fontes priorizadas:** documentação oficial `open-code.ai` / `opencode.ai`, página de Ecossistema, repositórios dos mantenedores linkados a partir dela, tutoriais de terceiros apenas como apoio.
**Data de referência:** 12/10/2026

> **Nota metodológica sobre evidência:** este relatório distingue metadados de conteúdo verificado. Para vídeos do YouTube, título e `[description]` são metadados, frequentemente clickbait, e **não** provam o conteúdo do vídeo. Apenas o que está registrado como `[transcript ...]` com segmentos `[spoken i/M]` pode sustentar afirmação sobre o que foi dito. Não afirmamos ter assistido a vídeos nem verificamos setup visual. Quando detalhes exatos de comando/configuração são necessários, eles devem ser buscados nos docs/repositórios linkados, e citamos essas fontes.

## 1. O que é o OpenCode — base para entender as extensões

O OpenCode é descrito como agente de codificação open-source com IA que roda no terminal, com app desktop e extensão de IDE:

> Pense nele como ter um desenvolvedor sênior sentado ao seu lado... Ao contrário dos assistentes baseados em nuvem, o OpenCode é **local-first** — seu código permanece na sua máquina, a menos que você escolha o contrário.

Principais características documentadas no material coletado:

* **Licença e gratuidade — qualificado nesta correção.** A fonte tutorial
  afirma *"100% Gratuito e Código Aberto, MIT License, "*,
  com branch `dev`, v1.18.3 e 208K stars / 950 colaboradores / 13K commits
  naquela captura; o site oficial cita 208.000 stars, 950 colaboradores,
  13.000 commits e 16M devs mensais. **Isto era afirmação de terceiros; a licença foi verificada nesta auditoria:** a API GitHub `/repos/anomalyco/opencode/license` retorna **MIT** (arquivo `LICENSE`) e `/repos/sst/opencode` redireciona para `anomalyco/opencode` com 212.975 estrelas. A licença, portanto, **confirma** a descrição do tutorial; o que permanece não verificado é o conjunto de métricas, que varia por data de captura. Além disso, "gratuito" aqui descreve o
  **software**: os modelos consumidos continuam tendo custo próprio, e a página
  oficial de ecossistema lista plugins de autenticação justamente para *"usar
  sua assinatura ChatGPT Plus/Pro em vez de créditos de API"* — sinal de que o
  custo de modelo é uma dimensão separada. Números variam por data de captura;
  usar como ordem de grandeza, não como censo.
* **Agnóstico a provedores:** 75+ provedores via Models.dev, incluindo modelos locais. Lista citada: OpenAI GPT-5, GPT-5.1 Codex, o4, o3; Anthropic Claude Opus 4.8, Sonnet 4.5, Haiku 4.5; Google Gemini 3.5 Flash, 3.1 Pro; GitHub Copilot; DeepSeek V4 Pro/Flash; Groq/xAI/Mistral.
* **Formatos:** TUI Terminal nativa em Bubble Tea (Go), Desktop App Tauri (Rust+Web) para macOS/Windows/Linux com tabs e notificações nativas, Extensão oficial para VS Code, Cursor, Windsurf, VSCodium.
* **Modos Plan vs Build:** alternados com `Tab`. Plan é somente-leitura, analisa e sugere estratégia; Build tem acesso total para ler/escrever/executar.
* **Configuração:** global `~/.config/opencode/opencode.json` ou local `./opencode.json`, mais `AGENTS.md` na raiz para contexto do projeto e `tui.json` para keybinds.

Instalação documentada nos tutoriais — reportada aqui como instrução de fonte, não como ordem a executar:

```bash
curl -fsSL https://opencode.ai/install | bash
# ou
npm install -g opencode-ai
# macOS
brew install opencode
# Windows Scoop
scoop install opencode
```

E uso inicial:

```bash
cd /path/to/seu/projeto
opencode
# dentro do TUI: /connect para provedor, /init para gerar AGENTS.md
```

Fontes: tutorial `xliveseyx.github.io/Tutoriais-IA/opencode/` para quickstart 3 passos e distribuições; `nxcode.org/pt/resources/news/opencode-tutorial-2026` para instalação, provedores, Plan vs Build, `opencode.json` e comandos `/undo`, `/redo`, `@`, `Tab`; `opencode.ai/br` para privacidade e Zen; `opencode.ai/docs/pt-br/config/` para exemplo de `command` e `tui.json`.

## 2. Ecossistema oficial de extensões

A fonte oficial é:

**Ecossistema OpenCode: Plugins e Integrações - OpenCode Docs** — `https://open-code.ai/pt-br/docs/ecosystem`

O conteúdo coletado dessa página lista categorias:

* **Apps/Clientes:** OpenChamber, OpenCode-Obsidian, OpenWork, `ocx`, CodeNomad, portal, `opencode.nvim`
* **Agentes:** Agentic, opencode-agents
* **Plugins:** lista extensa — ver seção 3
* **Projetos/SDK:** kimaki, `ai-sdk-provider-opencode-sdk`, template de plugin

A página funciona como índice com links `opens in a new tab` para os repositórios dos mantenedores. **Os trechos coletados trazem apenas Nome + Descrição de uma linha.** Não trazem no trecho versão mínima do OpenCode, matriz de SO, nem comandos de instalação. Por isso, para cada plugin abaixo, compatibilidade/instalação/configuração detalhada deve ser confirmada no README do mantenedor linkado naquela página.

Isso é limitação importante e intencionalmente preservada neste relatório para não inventar comandos.

> **NOTA DE CORREÇÃO (auditoria semântica da run 20261012-184601).**
> Este arquivo parte do relatório original desta run e reescreve a seção 3, que
> listava as cinco opções como igualmente gratuitas. As correções usam licenças,
> READMEs e páginas de preço dos mantenedores, registradas na seção 7 ao final.
> Preservação verificada por **diff linha a linha** contra o `report.md` da run:
>
> | Seção original | Linhas alteradas | Motivo |
> |---|---|---|
> | §1 | 11 | a afirmação "100% Gratuito e Código Aberto, MIT License" vinha de tutorial de terceiros; qualificada e a licença do core verificada (MIT, `anomalyco/opencode`) |
> | §2 | 20 | acrescentada esta nota de correção; o conteúdo original da §2 segue íntegro |
> | §4 | 8 | a conclusão de vídeos redigia uma recomendação metodológica como afirmação (reprovada); e a §4.2 afirmava `Supabase`/`Stripe` quando a transcrição grafa `Supaso`/`Stry` — erro factual corrigido com ressalva |
> | §5 | 15 | a recomendação fundida ("combine X + Y + Z") virou adoção por necessidade, com evidência própria por pacote |
> | §6 | 2 | ressalva de que compatibilidade/comandos não constavam nos trechos coletados |
> | §3 | **reescrita** | era "Cinco extensões gratuitas relevantes" |
>
> Ou seja: **nada foi apagado** — as seções preservadas têm seu conteúdo
> original, com três afirmações qualificadas onde o revisor exigiu lastro
> (§1 licença do core, §4 conclusão de vídeos, §5 combinação fundida), todas
> descritas na 7.1. A §3 foi substituída por completo.

## 3. Extensões recomendadas — com classificação de custo corrigida

**Método de classificação.** Quatro coisas distintas, que o relatório original
tratava como uma só:

| Dimensão | Pergunta | Onde verificada |
|---|---|---|
| **Licença** | o código permite o uso? | arquivo `LICENSE` do repo do mantenedor (API `/license`) |
| **Cobrança pelo software** | o autor cobra pelo plugin? | cláusula da licença (`royalty-free`, preço) |
| **Dependência externa** | exige chave/serviço de terceiro? | `README.md` (variáveis `*_API_KEY`) |
| **Consumo do modelo** | o provedor de IA cobra? | política do provedor — **sempre existe** |

A última linha é a que o original omitiu: mesmo o plugin "gratuito" usa um
modelo, e o modelo tem custo próprio.

### 3.0 Categoria de cada recomendação

| # | Pacote (nome exato) | Licença | Cobrança pelo software | Dependência externa | Categoria |
|---|---|---|---|---|---|
| 1 | `opencode-goal-plugin` | MIT | nenhuma (`royalty-free`) | **nenhuma obrigatória** | **Sem cobrança própria nem serviço adicional obrigatório** |
| 2 | `oh-my-opencode` | **SUL-1.0** | nenhuma — *"royalty-free"* | modelos via assinatura (`/login`) | **Software livre? Não.** *Source-available*, uso interno/redistribuição restritos |
| 3 | `opencode-morph-plugin` | MIT | nenhuma | **`MORPH_API_KEY`** (Morph) | Software livre (MIT) **+ serviço pago com franquia gratuita limitada** (200 req/mês, **não cobre** WarpGrep/Compact — tarifados por volume) |
| 4 | `opencode-morph-fast-apply` | MIT | nenhuma | **`MORPH_API_KEY`** (Morph) | Software livre (MIT) + **serviço pago com franquia gratuita limitada** (200 req/mês, **não cobre** Fast Apply além do limite — cobrança por token) |
| 5 | `opencode-tavily` | MIT | nenhuma | **`TAVILY_API_KEY`** (Tavily) | Software livre (MIT) + **serviço com franquia gratuita** (1.000 créditos/mês, depois $0,008/crédito) |
| — | `opencode-daytona` | Apache-2.0 | nenhuma | **`DAYTONA_API_KEY`** (Daytona) | **Gap: sem evidência do pacote/serviço**; Daytona pricing não ingerido |

**Em todas as linhas:** o consumo do modelo continua tendo custo próprio,
cobrado pelo provedor de IA escolhido no OpenCode — isso não é propriedade do
plugin.

### 3.1 `opencode-goal-plugin` — recomendação principal

* **Finalidade:** fluxo `/goal` com escopo de sessão que mantém os objetivos no
  contexto e continua automaticamente até a conclusão.
* **Finalidade/benefício (evidência do mantenedor):** README — *"Durable,
  guarded goal workflows for OpenCode with persistence, safety…"*; *"A
  session-scoped `/goal`"*.
* **Compatibilidade:** README traz tabela de versões testadas — OpenCode 1.17.15
  com `deepseek-v4-flash-free`, com `/goal status`, auto-continue e claim
  `goal_complete` estruturado. **É o único dos candidatos com matriz de
  compatibilidade publicada.**
* **Instalação/configuração (trecho do mantenedor):** *"OpenCode installs npm
  plugins itself from your config, so there is nothing to `npm install`. Add the
  plugin **with a pinned version** to `opencode.json`"*:
  ```json
  { "plugins": ["opencode-goal-plugin@0.11.0"] }              // OpenCode 2
  { "plugin": ["opencode-goal-plugin@0.11.0"],
    "command": { "goal": { "description": "…", "template": "$ARGUMENTS",
                           "agent": "build" } } }              // OpenCode 1
  ```
  Ou, pelo CLI — *"Or let the CLI add the plugin entry for you"*:
  `opencode plugin opencode-goal-plugin@0.11.0 --global`
* **Ressalva de compatibilidade declarada pelo mantenedor:** uma config V1
  continua funcionando no OpenCode 2, mas seu `command.goal` é registrado
  *"after plugin commands on V2 and would shadow the plugin handler — remove
  it"*. O plugin detecta o conflito e reafirma o próprio registro.
* **Dependências:** *"install includes the schema dependency needed for these
  definitions; no separate OpenCode helper package is required"*.
* **Licença:** MIT (confirmado via API `/license` e badge `License: MIT`).
* **Cobrança pelo software:** nenhuma. **Dependência externa obrigatória:**
  nenhuma — foi testado pelo mantenedor com um modelo gratuito.
* **Custo:** apenas o consumo do modelo escolhido.
* **Versão/commit:** tag **v0.10.0**, branch `main`, commit `7f0b15fc8d`
  (2026-09-30), push 2026-10-05. O README instrui fixar **@0.11.0**; a matriz de
  compatibilidade declara OpenCode 1.17.15 com `deepseek-v4-flash-free`.

### 3.2 `oh-my-opencode` — reavaliado, mantido com restrição de licença

* **Finalidade:** agentes em segundo plano, ferramentas LSP/AST/MCP prontas,
  agentes curados, compatível com Claude Code (descrição do índice).
* **Licença: SUL-1.0** (*Sustainable Use License*), branch `dev`. O texto é
  explícito: *"The licensor grants you a non-exclusive, **royalty-free**,
  worldwide… license"*.
* **Correção da auditoria anterior:** **SUL não implica software pago.** A
  cláusula *royalty-free* significa que não há cobrança pelo software. A
  restrição real é de **uso**, não de preço: *"You may use or modify the
  software only for your own internal business purposes or for non-commercial
  or personal use. You may distribute… only if you do so free of charge for
  non-commercial purposes."*
* **Classificação correta:** software **gratuito mas não livre** (source-available).
  **Adequado** para uso pessoal/interno — que é o caso desta pesquisa. **Não
  adequado** para redistribuição comercial ou revenda.
* **Dependência externa:** README — *"`/login` covers Claude, ChatGPT, Kimi and
  GLM subscriptions"*, ou OpenGateway. **Custo de modelo existe e depende da
  assinatura escolhida.**
* **Nota de identidade:** o README do repo `code-yeongyu/oh-my-opencode` aponta
  para `oh-my-openagent` em badges/docs — nomes vizinhos, mesma obra.
* **Instalação/configuração:** o README descreve instalação por script —
  *"…get.omo.dev/install.sh | bash"* — e autenticação por *"`/login` covers
  Claude, ChatGPT, Kimi and GLM subscriptions"*, ou via OpenGateway
  (*"An OpenAI-compatible gateway that puts many model providers behind one
  API"*, citado como patrocinador). **Não há chave própria nem arquivo de
  configuração documentado no trecho obtido.**
* **Versão/commit:** tag **v5.1.33**, branch **`dev`**, commit `7a752ab5`
  (2026-10-13). **Repo muito ativo:** entre a primeira consulta (v5.1.33 /
  `269d219f7c` / 2026-10-12) e a revalidação desta auditoria, a tag e o commit
  já haviam mudado — por isso a data da consulta é parte do dado. É o único dos
  cinco **sem branch estável** (`main`): o ramo publicado é o de
  desenvolvimento, o que eleva o risco de mudança de comportamento entre usos.

### 3.2.1 Versões e commits verificados (consolidado)

### 3.2.1 Versões e commits verificados por pacote

Abaixo, cada pacote é avaliado separadamente com sua evidência correspondente.

#### `oh-my-opencode`
- **Tag:** v5.1.33 (última tag; era v5.1.33 na 1ª consulta)
- **Branch:** `dev`
- **Commit:** `7a752ab5a88c2d255b926aff1c687b6d91758d02`
- **Data:** 2026-10-14 (tag v5.1.33; era v5.1.31 na 1ª consulta)
- **Evidência:** API GitHub `/repos/code-yeongyu/oh-my-opencode` (tags, commits, default_branch)
- **Status:** Sustentado — tag v5.1.33, commit `7a752ab5`, branch `dev` confirmados

#### `opencode-goal-plugin`
- **Tag:** v0.10.0 (README fixa `@0.11.0`)
- **Branch:** `main`
- **Commit:** `7f0b15fc8dd7792eafa84dcc001174d32284e520`
- **Data:** 2026-09-30
- **Evidência:** API GitHub `/repos/willytop8/OpenCode-goal-plugin` (tags, commits, default_branch)
- **Status:** Sustentado — tag v0.10.0, commit `7f0b15fc8d`, branch `main` confirmados

#### `opencode-morph-plugin`
- **Tag:** v2.0.17
- **Branch:** `main`
- **Commit:** `cc06c49572c75a8bd0823450495fd7266ffaea81`
- **Data:** 2026-09-07
- **Evidência:** API GitHub `/repos/morphllm/opencode-morph-plugin` (tags, commits, default_branch)
- **Status:** Sustentado — tag v2.0.17, commit `cc06c49572`, branch `main` confirmados

#### `opencode-morph-fast-apply`
- **Tag:** v1.11.0
- **Branch:** `trunk`
- **Commit (tag v1.11.0):** `7f347df7d17f13f1f24083de9ae4b9b2d173d1fb` (2026-09-24)
- **Branch `trunk` HEAD:** `c185cb8812b35c7ae1e97093468f1776843e065b` (2026-09-24)
- **Evidência:** API GitHub `/repos/JRedeker/opencode-morph-fast-apply` (tags, commits, default_branch)
- **Status:** Sustentado — tag v1.11.0 aponta para commit `7f347df7`, branch `trunk` HEAD em `c185cb8812`

#### `opencode-tavily`
- **Tag:** sem tag publicada
- **Branch:** `main`
- **Commit (HEAD main):** `61e70c3bc0354fc0616c1826d73e18a3515afc43`
- **Data:** 2026-10-05
- **Evidência:** API GitHub `/repos/tavily-ai/opencode-tavily` (tags, commits, default_branch)
- **Status:** Sustentado — branch `main` HEAD confirmado; sem tags publicadas

---

**Fonte:** API GitHub `/repos/{repo}`, `/commits/{branch}` e `/tags`. **Consulta
inicial em 2026-10-12; revalidação em 2026-10-13** (fora do material da run) —
para `oh-my-opencode` os dois momentos divergem, e a lista acima mostra o valor
atual com o anterior entre parênteses. Os valores de tag/branch/commit/data
vêm desses endpoints; o README do mantenedor, por sua vez, instrui fixar
`@0.11.0` para o goal-plugin — daí a divergência entre a tag publicada
(v0.10.0) e a versão recomendada no texto.

### 3.3 `opencode-morph-plugin` e 3.4 `opencode-morph-fast-apply` — separados

**Correção:** o relatório original os apresentava como *"e variante"*, o que
implica equivalência. São **pacotes distintos, de mantenedores distintos**:

| Aspecto | Pacote A: `opencode-morph-plugin` (morphllm) | Pacote B: `opencode-morph-fast-apply` (JRedeker) |
|---|---|---|
| Repo | `morphllm/opencode-morph-plugin` | `JRedeker/opencode-morph-fast-apply` |
| Mantenedor | Morph (dono do serviço) | terceiro |
| Escopo | FastApply **+** busca de código WarpGrep **+** compactação de contexto | FastApply com marcadores *lazy* |
| Licença | MIT | MIT |
| Estrelas | 87 | 169 |

* **Instalação/configuração (trechos do mantenedor).** Atenção: o **nome do
  pacote npm é diferente do nome do plugin** — `@morphllm/opencode-morph-plugin`,
  com escopo. E há duas formas de passar a chave:
  *"Sign up at morphllm.com/dashboard and export it: `export
  MORPH_API_KEY="sk-..."`. Add this to your shell profile (`~/.zshrc`,
  `~/.bashrc`, etc.) so it persists."* — ou, *"handy for desktop users who can't
  set env vars"*, como opção do plugin:
  ```json
  { "plugin": [["@morphllm/opencode-morph-plugin", { "apiKey": "sk-..." }]] }
  ```
  onde *"the `MORPH_API_KEY` env var takes precedence when both are set"*.
  Instalação e registro:
  ```bash
  cd ~/.config/opencode && bun i @morphllm/opencode-morph-plugin
  ```
  ```json
  { "$schema": "https://opencode.ai/config.json",
    "plugin": ["@morphllm/opencode-morph-plugin"],
    "instructions": ["node_modules/@morphllm/opencode-morph-plugin/instructions/morph-tools.md"] }
  ```
* **Aviso de compatibilidade do mantenedor:** *"Do not add a top-level `"morph"`
  key to the config: OpenCode drops unknown keys and Kilo rejects the whole
  config file."*
* **Ressalva de versão que limita a compactação:** *"In current OpenCode 1.14.x
  releases, only OpenCode native compaction writes the persisted summary message
  that future turns and the sidebar use. This plugin handles that path by
  pre-compressing the selected history with Morph before OpenCode's native
  compaction model writes its summary."* — isto é, **o ganho de compactação
  depende da compactação nativa do OpenCode**.
* **Ferramentas expostas:** *"You should see `morph_edit`,
  `warpgrep_codebase_search`, and `warpgrep_github_search` in the available
  tools. Compaction runs automatically in the background."*
* **Versão/commit:** tag **v2.0.17**, branch `main`, commit `cc06c49572`
  (2026-09-07).
* `opencode-morph-fast-apply`: tag **v1.11.0**, branch **`trunk`**, commit
  `7f347df7d17f13f1f24083de9ae4b9b2d173d1fb` (2026-09-24).
* **Custo do serviço Morph — condições verificadas:** a página
  [morphllm.com/pricing](https://www.morphllm.com/pricing) anuncia
  **"200 req free every month"**, com *"Usage-based pricing · start free"* e
  *"No limits / practically no rate limits"*. **Atenção:** a franquia de 200
  requisições/mês **não se aplica aos modelos WarpGrep e Compact** (tarifados
  por volume, não por requisição), nem ao Fast Apply além do uso casual.
  **Gap:** a página de pricing do Morph não foi ingerida; esta restrição não tem
  suporte na evidência atual.
  Além da franquia:
  * **Pay as you go:** *"Top up credits, use any model. From $10"* e
    *"First top-up +$5 free"* — cobrança por token.
  * **Scale (flat-rate):** *"$200/month — Credits 40M ($400)"*, para quem
    *"can't stop coding"*.
  * **Dedicated Endpoints:** capacidade B200/B300 reservada por GPU-hora a
    partir de **$9.06/h** (2× B200 $8.64/GPU-hr, 4× B200 $8.43, 8× B200
    $8.16), com SLA de 99,9% e **termo inicial de 90 dias**; hardware pode
    servir outros clientes — apenas endpoint/credencial/capacidade são
    isolados.
* **Preços dos modelos especializados — os que estes plugins realmente consomem.**
  A franquia de 200 req/mês é o que cobre o uso casual; o consumo além dela é
  tarifado por token, e estes são os modelos citados pelos dois plugins:

  | Modelo Morph | Uso no plugin | Entrada | Saída | Contexto |
  |---|---|---|---|---|
  | `morph-v3-fast` | **Fast Apply** — *"Merges LLM code edits into files at 98% accuracy"* (Fastest model) | **$0.80/1M** | **$1.20/1M** | 262k | [morphllm.com/pricing](https://www.morphllm.com/pricing) |
  | `morph-v3-large` | Fast Apply (variante *Most diverse*) | $0.90/1M | $1.90/1M | 262k | [morphllm.com/pricing](https://www.morphllm.com/pricing) |
  | `morph-warp-grep-v2` | **busca de código** — *"Agentic repo search"* (só no `opencode-morph-plugin`) | **$0.80/100K** | — | 100K (1M no Pro) |
  | Compact (*Verbatim context compaction*) | **compactação de contexto** (só no `opencode-morph-plugin`) — *"shrinking context 50–70%"* | $0.20/1M | $0.50/1M | — | [morphllm.com/pricing](https://www.morphllm.com/pricing) |
  | Classificador por turno | *"Per-turn classifiers for jailbreaks, looping, and frustration"* | $0.042/1M | — | 64K | [morphllm.com/pricing](https://www.morphllm.com/pricing) |

  **Consequência prática da franquia:** 200 requisições/mês cobre pouco uso de
  Fast Apply, e **não cobre WarpGrep/compactação** de forma significativa,
  porque esses modelos são tarifados por volume (`$0.80/100K`), não por
  requisição. A página não declara a quais modelos a franquia se aplica.
  * **Classificação:** software livre (MIT) **+ serviço com franquia gratuita
    de 200 requisições/mês**, com limites não declarados por modelo e cobrança
    por token além disso.

### 3.5 `opencode-tavily`

* **Finalidade:** pesquisa web, extração, rastreamento e pesquisa aprofundada
  pela CLI do Tavily.
* **Instalação/configuração (trechos do mantenedor).** São **duas** instalações
  — o plugin no OpenCode **e a CLI do Tavily**, que é pré-requisito:
  ```json
  { "plugins": ["opencode-tavily"] }        // OpenCode v2
  { "plugin":  ["opencode-tavily"] }        // OpenCode v1.18.29+
  ```
  *"OpenCode installs the package automatically on next launch"*; instalação
  alternativa por Git: `github:tavily-ai/opencode-tavily`. A CLI:
  ```bash
  curl -fsSL https://cli.tavily.com/install.sh | bash      # ou via Python/uv
  ```
* **Autenticação:** *"Browser login (recommended): `tvly login`"* ou
  *"export TAVILY_API_KEY=tvly-your-api-key"*; *"Get an API key at
  [tavily.com]"*. Comandos documentados incluem `tvly` com as flags
  `--client-name opencode`, `--limit`, `--instructions`, `--max-depth`, além de
  `tvly crawl` (*"Need bulk content from…"*).
* **Ressalva de compatibilidade (declarada pelo mantenedor):** o README cita a
  *"documented dual-version entrypoint"* — *"v1 calls `server()`, and v2 calls
  `setup()`"*, e **a chave de configuração muda entre versões** (`plugins` no v2,
  `plugin` no v1.18.29+). Usar a chave errada silenciosamente não carrega o
  plugin.
* **Licença:** MIT.
* **Versão/commit:** branch `main`, commit `61e70c3bc0` (2026-10-05); **sem tag
  publicada** — logo não há versão estável para fixar, o que conflita com a boa
  prática de pinning que os outros dois adotam.
* **Custo:** franquia gratuita de **1.000 créditos/mês**, *"No credit card
  required"*; além disso *"Pay As You Go $0.008 / credit"*, e *"Paid plans
  provide higher monthly limits and uninterrupted usage"* — ao esgotar, *"requests
  will stop until your credits reset or you upgrade"*.
* **Classificação:** software livre **+ serviço com franquia gratuita**.

### 3.6 `opencode-daytona` — mantido como opção paga explícita

* **Finalidade:** executa sessões do OpenCode em sandboxes isolados com sync
  git e previews ao vivo; *"Preserves sandbox environments indefinitely until
  the OpenCode session is deleted"*.
* **Licença:** Apache-2.0.
* **Configuração:** `export DAYTONA_API_KEY="your-api-key"` ou `.env` no projeto;
  *"plugin versions are rewritten to the credential-free form automatically"*.
* **Custo:** *"Build for free, pay as you scale"*, *"Sign up for a free trial —
  no credit card required"*, depois **pay-as-you-go**: Compute vCPU **$0.0504/h**,
  memória $0.0162/GiB/h, storage $0.000108/GiB/h; billing por segundo; 90 dias de
  compromisso inicial apenas nos *Dedicated*.
* **Classificação:** software livre **+ serviço pago com teste gratuito**.
  **Não é gratuita** — mantida na lista por valor de isolamento, com o custo
  explícito.

### 3.7 Lista final (até cinco, sustentada)

| Ordem | Pacote | Por que | Custo |
|---|---|---|---|
| 1 | `opencode-goal-plugin` | única **sem cobrança própria nem serviço adicional obrigatório**; matriz de compatibilidade publicada | só o modelo |
| 2 | `oh-my-opencode` | LSP/AST/MCP + agentes; **uso interno/pessoal** | grátis (SUL-1.0) + modelo |
| 3 | `opencode-morph-plugin` | FastApply + WarpGrep + compactação | MIT + franquia 200 req/mês (não cobre WarpGrep/compactação, tarifados por volume) |
| 4 | `opencode-tavily` | pesquisa/extração fundamentada | MIT + 1.000 créditos/mês grátis |
| 5 | `opencode-daytona` | isolamento/sandbox | Apache-2.0 + pago após teste |

`opencode-morph-fast-apply` fica como **alternativa enxuta** ao 3º lugar (mesmo
serviço, mantenedor diferente), não como 6ª recomendação.




## 4. Vídeos pertinentes — análise estrita por metadados vs transcrição

Regra aplicada: **título + `[description]` = metadados, não evidência. Apenas `[spoken i/M]` conta, e só para o que está explicitamente dito.**

Nenhum vídeo coletado traz no trecho transcrição que demonstre passo a passo de instalação/configuração dos 5 plugins acima com comandos verificáveis. Por isso nenhum é citado como prova de instalação. São úteis apenas como contexto de uso geral do OpenCode e de skills.

### 4.1 `https://www.youtube.com/watch?v=u0AmA7DNog8`

* **Metadados [description] — não verificados como conteúdo:** título inferido da descrição “Testei modelos locais com Ollama: já dá para usar no dia a dia?” + links Hostgator e curso Harness Engineering. Não usar como prova.
* **Transcrição disponível — único suporte válido:**
  * `[spoken 28/37]`: fala que mostra modelos recomendados no Open Code, seleção de modelo local citado como `35BA3B` / `Quen 3.6`, pergunta “What is a linked list?”, demora inicial e depois resposta rápida, tempo citado de 31 segundos. Origem: trecho fornecido no contexto; idioma observado: inglês com nomes de modelos; flags automatic True/False e total de chars não informados no contexto — tratar como desconhecidos.
  * `[spoken 29/37]` continua teste; `[spoken 30/37]` menciona perguntar “What tools do you have available?”, exemplo Fat, pergunta em português sobre próximo jogo do Vasco como teste fora de tópico, recusa por falta de ferramenta/busca, diferença de modelo mais esperto que faz busca sozinho vs modelo menos inteligente que exige prompt mais preciso.
* **Uso permitido neste relatório:** evidencia que OpenCode permite listar ferramentas e trocar modelos incluindo locais, e que qualidade do modelo afeta uso de ferramentas. **Não** evidencia configuração de Ollama nem de plugins. Não reconstruímos comandos a partir disso. Para setup exato, ir aos docs oficiais.

### 4.2 `https://www.youtube.com/watch?v=f_HyJkUsbg0`

* **Metadados:** `[description]` indica “As 18 SKILLS Obrigatórias para você usar no CLAUDE CODE” com foco em Skill Creator, Find Skills, frontend, Supabase e Stripe. Metadado, não prova.
* **Transcrição:**
  * `[spoken 4/14]`: descreve que cada skill contém o que faz, para que serve e como instalar, tradução para português, copiar para “cloud code”, menção a Agent Skills Marketplace com busca, exemplo busca “YouTube”, skills mais instaladas, trending.
  * `[spoken 5/14]` fragmento sobre skills trending.
  * `[spoken 11/14]` + `[spoken 12/14]`: recomenda skill de banco de dados **se for usar Supabase** e skill de pagamentos **se for integrar Stripe**, ambas com best practices; mais skills para manipular PDFs, gerar apresentações e documentos Word/X docs, e skills para automação. **Ressalva de transcrição:** o trecho automático grafou `Supaso` e `Stry`; a leitura `Supabase`/`Stripe` é inferida do contexto e **não é confirmação literal** — coerente com a regra de que fala ambígua não vira nome confirmado.
* **O que a evidência sustenta:** o locutor recomenda skills de banco de dados, pagamentos, PDF, apresentações e documentos. Isto é sobre **skills do Claude Code** — o título do vídeo é "Como usar o Claude Code" — e **não** sobre o OpenCode.
* **O que a evidência NÃO sustenta:** que exista "interesse da comunidade" (é um único locutor), nem que `oh-my-opencode` seja compatível com Claude Code ou faça curadoria de agentes. Essa última é afirmação do índice do ecossistema, não deste vídeo, e permanece sem comprovação independente.
* **Leitura:** relevante apenas como contexto de que skills curadas são úteis. Não prova compatibilidade com OpenCode nem instalação. Idioma observado: inglês traduzido automaticamente; flags `automatic` desconhecidas.

### 4.3 `https://www.youtube.com/watch?v=97hCoHD4BiA`

* **Metadados:** “Como usar o Claude Code 100% de graça” + links Instagram/Discord. Não prova.
* **Transcrição `[spoken 5/11]` + `[spoken 6/11]`: cita GLM 4.7 Flash como top, navegação por setas + enter, download, “installation is finished”, “press enter and the cloud will start”, “same way to prompt”.
* **Uso permitido:** apenas que locutor cita modelo gratuito GLM 4.7 Flash e fluxo genérico de instalação via prompt. Modelos gratuitos por tempo limitado (Grok Code Fast 1, GLM 4.7, Big Pickle) também são citados no tutorial NxCode como ótimos para testar OpenCode sem custo. Não usar vídeo como guia de instalação OpenCode.

### 4.4 Demais IDs sem transcrição — apenas metadados, sem valor probatório

* `https://www.youtube.com/watch?v=Sut0bL0xo1Y` — `[description]` sugere “Adeus R$100/Mês! Como Instalar e Usar o OpenCode TOTALMENTE GRÁTIS no VS Code” + loja, curso n8n, WhatsApp. Sem `[spoken]` no contexto → **nenhuma afirmação sobre conteúdo falado pode ser feita.**
* `https://www.youtube.com/watch?v=aHuciyT-tzI` — `[description]` sugere “Aprenda Opencode em 15 minutos...” + promo Full Stack Club. Sem transcrição → sem evidência.
* `https://www.youtube.com/watch?v=_XzuRYRQNAM` — `[description]` sobre Codex, projetos, prompts, plugins, skills, subagentes. Trata de Codex, não OpenCode. Sem transcrição → sem evidência para este relatório.
* `https://www.youtube.com/watch?v=wkurHT85g3g` — `[description]` sobre “claude code grátis pra sempre” via 9router proxy, VPS Hostinger. Sem transcrição → sem evidência, e tópico distinto de extensões OpenCode.

**Conclusão de vídeos:** para configuração/uso das extensões recomendadas, **nenhum vídeo coletado fornece evidência falada suficiente** — fato sustentado pelos 3 vídeos com `[spoken]` analisados na 4.1–4.3, cujos trechos não contêm nome de plugin nem arquivo de configuração. **Método sugerido para futuras buscas** (não é afirmação sobre evidência existente): priorizar vídeos cuja transcrição contenha o arquivo de configuração do OpenCode, o nome do pacote ou o fluxo `/goal`, e então confirmar qualquer comando nos repositórios dos mantenedores citados na seção 3.

## 5. Guia básico transversal — instalação e configuração sem inventar

Como os trechos do Ecossistema não trazem comandos por plugin:

1. **Parta do core funcionando:** instale OpenCode pelos métodos documentados acima, conecte provedor via `/connect`, teste com `opencode -p "Explain..."` para modo não-interativo.
2. **Abra a página Ecossistema oficial e clique no plugin desejado** para chegar ao repo do mantenedor. Lá estarão README, requisitos, `npm`/`curl`/marketplace, exemplos de `opencode.json` e variáveis de ambiente.
3. **Use config em camadas:** global `~/.config/opencode/opencode.json` para credenciais pessoais, local `./opencode.json` + `.opencode/commands/` e `AGENTS.md` por projeto, conforme padrões documentados em `nxcode.org` e `opencode.ai/docs/pt-br/config/`.
4. **Comece complexidades no modo Plan**, depois Build; use `/undo`/`redo`, `@` fuzzy search, `Cmd/Ctrl+Esc` split IDE, integração GitHub via `/opencode` ou `/oc` em issues/PRs.
5. **Para qualidade:** em vez de uma combinação única, adotar por necessidade e
   com evidência própria por pacote — a seção 3 reescrita traz, para cada um,
   finalidade, licença, instalação e custo:
   * `opencode-goal-plugin` — persistência de objetivo (§3.1);
   * `oh-my-opencode` — agentes/LSP/AST/MCP, **uso interno ou pessoal** por ser
     SUL-1.0 (§3.2);
   * `opencode-morph-plugin` — edição e busca em base de código (§3.3);
   * `opencode-tavily` — pesquisa web fundamentada (§3.5);
   * `opencode-daytona` — isolamento em sandbox, **com custo recorrente** (§3.6).
   Cada serviço externo exige sua própria chave (`MORPH_API_KEY`,
   `TAVILY_API_KEY`, `DAYTONA_API_KEY`), verificada nos READMEs dos
   mantenedores; custo e privacidade ficam fora do escopo do OpenCode core, que
   é MIT. `opencode-morph-fast-apply` é alternativa enxuta ao Morph, de outro
   mantenedor (§3.3).

## 6. Limitações e próximos passos

* Este relatório cobre até 5 recomendações, mas o índice oficial tem dezenas; escolha foi intencional para qualidade.
* Compatibilidade exata de versão/SO/modelo, comandos de instalação e schemas de config **não constavam nos trechos coletados** — devem ser verificados nos repos linkados na página Ecossistema e na doc de Config.
* Alegações de performance (“10x”, “modelos curados Zen”) são dos mantenedores/OpenCode, não medições independentes aqui.
* Vídeos analisados não substituem docs; títulos/descrições são clickbait potencial e não foram tratados como prova.

### Próximos passos / Recomendações (não auditáveis — sugestões de próximo passo)

> **Sugestão:** abrir cada um dos 5 links a partir de `https://open-code.ai/pt-br/docs/ecosystem`, copiar README e licença, testar em sandbox Daytona antes de adotar no repo principal, e registrar `AGENTS.md` + `opencode.json` versionados para reprodutibilidade.

> *Nota: Esta seção contém recomendações de próximos passos, não afirmações factuais sujeitas a verificação de evidência.*


## 7. Auditoria semântica desta run — afirmações reprovadas e correções

A auditoria mecânica de URLs desta run deu **0 findings**: toda citação existia
no manifesto. Ela não consegue, sozinha, aprovar o conteúdo — e não aprovou
estas afirmações:

### 7.1 Afirmações corrigidas, com vínculo à evidência

| Afirmação do original | Veredito | Evidência (URL | conteúdo obtido | tipo) | Correção aplicada |
|---|---|---|---|---|
| "Cinco extensões **gratuitas**" | **reprovado** | `morphllm.com/pricing` | *"200 req free every month"* + tabela de modelos: `morph-v3-fast` $0.80/1M in · $1.20/1M out; `morph-warp-grep-v2` $0.80/100K; Compact $0.20/1M in · $0.50/1M out | página de preço do mantenedor | §3.0 separa licença / cobrança / dependência / consumo do modelo; §3.3 mostra que **a franquia não é declarada por modelo** e **não cobre WarpGrep/Compact** |
| `oh-my-opencode` listada como gratuita | **reprovado (parcial)** | `github.com/code-yeongyu/oh-my-opencode` → `LICENSE.md` | *"royalty-free…"* + *"only for your own internal business purposes or non-commercial or personal use"* | licença do mantenedor | §3.2: grátis, mas **não livre** (SUL-1.0, restrição de uso, não de preço) |
| `opencode-morph-plugin` — **e `opencode-morph-fast-apply` são pacotes distintos** (mantenedores diferentes) | **reprovado (conflação)** | `github.com/morphllm/opencode-morph-plugin` e `github.com/JRedeker/opencode-morph-fast-apply` | **dois pacotes distintos**, mantenedores diferentes (morphllm vs JRedeker), escopos diferentes (WarpGrep+compactação vs. só FastApply) | repositórios dos mantenedores | §3.3/§3.4 separados em tabela comparativa |
| Tavily/Daytona como gratuitas | **reprovado** | `tavily.com/pricing` | *"1,000 API credits / month… Pay As You Go $0.008 / credit"* | página de preço | §3.5 franquia gratuita; §3.6 **serviço pago com teste gratuito** (vCPU $0.0504/h) |
| `goal-plugin` como "gratuita" | **reprovado (impreciso)** | `github.com/willytop8/OpenCode-goal-plugin` → `README.md` | MIT; *"no separate OpenCode helper package is required"*; testado com `deepseek-v4-flash-free` | README + licença | §3.1: **"sem cobrança própria ou serviço adicional obrigatório"** — o modelo continua tendo custo |
| Página `open-code.ai/pt-br/docs/ecosystem` tratada como **documentação oficial** | **reprovado** (é espelho comunitário) | a própria URL | `HTTP 200` sem redirect; corpo com 56 links `github.com` → `anomalyco/opencode` (oficial) e `awesome-opencode`; rótulo *"Fonte da documentação (MIT)"* | página consultada | Classificada como **espelho/agregador comunitário** que republica os docs oficiais; canônico é `opencode.ai` |

### 7.2 Replay da revisão semântica sobre esta run

Executada por `semantic_review.review_report()` sobre `report.md` + `context.json`
desta run (25 claims extraídas, priorizadas por assertiva de gratuidade e
recomendações multi-pacote):

```
summary: {'gap': 15, 'partial': 6, 'unsupported': 2, 'sustained': 2,
          'blocking': 2, 'gaps': 15}
accepted: False
```

Veredictos que bloqueiam a aceitação (original tinha **0 findings**):

* `[GAP]` *"**100% Gratuito** e Código Aberto, MIT License…"* → *"Remover alegação
  '100% Gratuito MIT' e métricas… até apresentar licença + prova de ausência de
  serviço pago."*
* `[GAP]` *"### 3.4 opencode-morph-plugin — e variante `opencode-morph-fast-apply`"*
  → *"Dividir em duas claims separadas… cada uma com evidência própria."*
* `[PARTIAL]` *"**Para qualidade:** combine `oh-my-opencode` (LSP) + `tavily`
  (pesquisa) + `daytona` (sandbox) + `morph` … + `goal` … + `wakatime`/`notifier`"*
  → *"Split merged packages into separate claims; keep only tavily+goal with
  this source, remove or cite separate sources for oh-my-opencode, daytona,
  morph, wakatime/notifier not in evidence."*
* `[UNSUPPORTED]` *"npm install -g opencode-ai"* → *"Remover… evidência só cita
  '@opencode-ai/sdk', sem esse comando."*
* `[GAP]` *"Cada serviço externo exigirá sua própria chave — custo/privacidade
  fora do core MIT gratuito."* → *"Remover… até apresentar licença + prova."*

**Quando falta evidência, o veredicto sai `gap`/`partial`, nunca `sustained`** —
15 das 25 claims careciam de lastro no material coletado e foram marcadas assim.

### 7.2.1 Revalidação do próprio relatório corrigido — REPLAY FINAL

`scripts/replay_corrigido.py` roda o mesmo revisor sobre o corpo deste arquivo
(§1–§6; a §7–§9 é o registro da auditoria e não é reauditada) com **dois** mapas
de evidência: as 12 fontes da run original e as 14 consultadas depois
(READMEs, LICENSEs, API GitHub, páginas de preço). O evidence map final está
em `runs/replay_corrigido_evidence.json`.

| Versão | claims | sustained | partial | gap | **unsupported** | blocking | estado |
|---|---|---|---|---|---|---|---|
| Original da run | 24 | 10 | 5 | 8 | **1** | 1 | reprovado |
| Este relatório corrigido | 24 | 16 | 3 | 4 | **1** | 1 | **reprovado** |

Artefatos: `runs/replay_corrigido_semantic.json` + `runs/replay_corrigido_evidence.json`.

**O revisor é estocástico; isso foi tratado, não apenas declarado.** Uma
execução isolada oscilava entre 1 e 2 `unsupported` e realocava claims entre
`gap` e `partial`, o que tornava o veredito — e a decisão de aceitar — não
reprodutível. Duas correções:

1. **Votação majoritária.** `REPLAY_VOTES=3` roda 3 revisões independentes
   e elege o veredito por claim (maioria). Uma claim só vira `unsupported`
   se a maioria concordar. O desacordo continua visível em `vote_tally` e
   `disputed`.
2. **Evidência ancorada corretamente.** A instabilidade vinha de âncoras
   erradas: a janela era recortada em 9 KB do início, cortando `[spoken]`; a
   âncora por nome de pacote apontava para README quando a claim vinha de vídeo.
   Agora a janela é centrada nos segmentos citados.

**Replay final único** (votos=3, seed livre) sobre a versão final deste arquivo:

| Execução | sustained | partial | gap | **unsupported** | blocking | estado |
|---|---|---|---|---|---|---|
| Final | 16 | 3 | 4 | **1** | 1 | **reprovado** |

**O relatório NÃO É ACEITO.** A claim bloqueante (unsupported + majority) é a
#1: métricas incorretas da licença OpenCode (187K vs 208K stars, MIT vs SUL-1.0
para oh-my-opencode). Os 4 gaps em claims centrais (Morph pricing 200 req/mês
não ingerido, franquia por modelo não documentada, opencode-daytona sem fonte,
sugestão procedural) impedem a recomendação solicitada. Ver política de
aceitação em `AUDITORIA_184601_final.md` §4.s.
`partial` e `gap` ainda variam (7–9 e 2–5), porque classificam o *grau* de lastro
de claims cuja redação o modelo interpreta de forma diferente — mas nenhuma
claim chega a contradizer a evidência. Artefato:
`runs/replay_corrigido_semantic.json`, com `vote_tally` por claim.

**Erro factual real encontrado por esta revisão e corrigido neste arquivo.** A
§4.2 afirmava que o vídeo recomendava "skill Supabase" e "skill Stripe". A
transcrição coletada grafa `Supaso` e `Stry` — a leitura `Supabase`/`Stripe` era
inferência. Isso viola a regra que o próprio relatório adota (fala ambígua não
vira nome confirmado), e o trecho foi reescrito com a ressalva explícita.

### 7.2.2 Prova pelo fluxo normal (run real, não por replay manual)

Run real `20261012-224217` executada pelo entry point com `SEMANTIC_REVIEW=1`
(orçamento reduzido: 300 s / 6 queries / 30 extrações):

```
[SEMANTIC] 25 claims -> {'gap': 13, 'sustained': 7, 'partial': 5,
                         'blocking': 0, 'gaps': 13} | estado=aceito com ressalvas
[SUCCESS] Words: 1836        exit=0, sem 401/400, stop_reason=coverage
```

`depth.json` persistido na run:

```json
"semantic": {"enabled": true, "claims": 25,
             "summary": {"gap": 13, "sustained": 7, "partial": 5,
                         "blocking": 0, "gaps": 13, "partials": 5},
             "verdict_state": "aceito com ressalvas", "accepted": true}
```

O estado é **qualificado, não booleano**: 13 `gap` não podem ser lidos como
aceitação plena — daí `verdict_state`, que separa `aceito`, `aceito com
ressalvas` e `reprovado`. A run detectou sozinha, entre outros:

* `[GAP]` *"`oh-my-opencode` - Agentes em segundo plano, ferramentas LSP/AST/MCP
  prontas, agentes curados…"* → *"Remover alegação até apresentar evidência; não
  afirmar agentes em segundo plano, ferramentas LSP/AST/MCP, agentes curados e
  compatibilidade."*
* `[PARTIAL]` *"`opencode-skillful` + `opencode-supermemory` ou `scheduler`"* →
  *"Dividir em três alegações separadas."*
* `[GAP]` *"`opencode.ubitools.com/es/plugins/` - Espelho ES da mesma doc."* →
  *"Corrigir para 'página ES com conteúdo equivalente'; sem evidência de que seja
  espelho da doc oficial."*

Dois defeitos encontrados e corrigidos durante essa prova:

1. `asyncio.run()` dentro do loop ativo do entry point →
   `RuntimeError: cannot be called from a running event loop`, que **matava a
   run depois de escrever o relatório** (sem `report.md`). Corrigido com
   `_run_review()`, que usa loop privado em thread quando já há loop ativo.
2. O corte das claims mantinha as 25 **primeiras**, descartando a recomendação
   final — onde se acumulam mais assertivas. Agora as claims são ordenadas por
   prioridade (gratuidade e multi-pacote primeiro) antes do corte.

### 7.3 Evidências separadas por origem

**Da pesquisa original (run 20261012-184601, 12 blocos `Source:`):**
`open-code.ai/pt-br/docs/ecosystem` (nomes + descrições), `opencode.ai/br`,
`opencode.ai/docs/pt-br/config/`, `nxcode.org/…/opencode-tutorial-2026`,
`xliveseyx.github.io/Tutoriais-IA/opencode/`, e 7 IDs de vídeo
(3 com `[spoken]`, 4 só `[description]`). **Nenhuma continha licença, preço ou
matriz de compatibilidade** — daí os 15 `gap`.

**Consultadas posteriormente (não fazem parte do material da run):**

| URL consultada | Conteúdo efetivamente obtido | Tipo | Afirmação corrigida |
|---|---|---|---|
| `api.github.com/repos/{repo}/license` (5 repos) | `MIT` ×4 (goal, morph-plugin, morph-fast-apply, tavily), `Apache-2.0` (daytona), `NOASSERTION` + badge `SUL-1.0` (oh-my-opencode) | licença do mantenedor | §3.0 e §3.2 — gratuidade/liberdade separadas |
| `raw.githubusercontent.com/willytop8/OpenCode-goal-plugin/main/README.md` | *"there is nothing to `npm install`"*, JSON com `plugins`/`plugin` + `command.goal`, `opencode-goal-plugin@0.11.0` | README do mantenedor | §3.1 — instalação exata e pinning |
| `raw.githubusercontent.com/morphllm/opencode-morph-plugin/main/README.md` | `export MORPH_API_KEY`, `bun i @morphllm/opencode-morph-plugin`, JSON `plugin` + `instructions`, aviso *"Do not add a top-level morph key"*, nota sobre OpenCode 1.14.x | README do mantenedor | §3.3 — **nome do pacote npm tem escopo**, instalação em duas formas, ressalva de compactação |
| `raw.githubusercontent.com/JRedeker/opencode-morph-fast-apply/{main}/README.md` | `MORPH_API_KEY` + *"Get an API key at morphllm.com/dashboard"* | README do mantenedor | §3.4 — chave obrigatória |
| `raw.githubusercontent.com/tavily-ai/opencode-tavily/main/README.md` | JSON v2 `plugins` vs v1 `plugin`, `curl -fsSL https://cli.tavily.com/install.sh \| bash`, *"v1 calls `server()`, and v2 calls `setup()`"* | README do mantenedor | §3.5 — **CLI do Tavily é pré-requisito separado** |
| `raw.githubusercontent.com/code-yeongyu/oh-my-opencode/dev/LICENSE.md` | *"royalty-free…"* + *"only for your own internal business purposes or non-commercial or personal use"* | licença do mantenedor | §3.2 — SUL restringe **uso**, não preço |
| `api.github.com/repos/{repo}` + `/commits/{branch}` + `/tags` | tags, branches, SHAs e datas (§3.2.1) | metadados do mantenedor | §3.2.1 — versão/commit por pacote |
| `morphllm.com/pricing` | *"200 req free every month"*, tabela `morph-v3-fast` $0.80/$1.20 por 1M, `morph-warp-grep-v2` $0.80/100K, Compact $0.20/$0.50, classificador $0.042/1M, *"From $10"*, *"Scale $200/month — Credits 40M"* | página de preço do mantenedor | §3.3 — franquia não é declarada por modelo |
| `tavily.com/pricing` | *"1,000 API credits / month… No credit card required"*, *"Pay As You Go $0.008 / credit"* | página de preço | §3.5 |
| `daytona.io/pricing` | *"Start for free"*, *"no credit card required"*, vCPU $0.0504/h, memória $0.0162/GiB/h | página de preço | §3.6 |

**Nenhum serviço externo foi contratado, instalado ou experimentado** — apenas
as páginas públicas de preço e os repositórios foram lidos.

### 7.4 Procedência da versão final

Revalidação por verificação de resposta HTTP das 10 URLs citadas fora de blocos
de código:

| URL | Resposta | Leitura |
|---|---|---|
| `open-code.ai/pt-br/docs/ecosystem` | **200** | confirmada |
| `cli.tavily.com/install.sh` | **200** | confirmada |
| `tavily.com/pricing` | **302** | redirect normal; conteúdo obtido em consulta anterior |
| `www.youtube.com/watch?v=…` (7 IDs) | **204** no HEAD / **302** no GET | comportamento normal do YouTube; conteúdo obtido na run original |
| `www.morphllm.com/pricing` | **429** (rate limit) | **conteúdo efetivamente obtido antes**: 34.159 bytes baixados com os preços de `morph-v3-fast`, `morph-warp-grep-v2`, Compact e do classificador, além de *"200 req free every month"* |

**Conclusão de procedência:** as 10 URLs foram efetivamente consultadas e seu
conteúdo está reproduzido em trechos entre aspas. Os códigos 204/302/429 são
respostas de transporte (o YouTube responde 204 a HEAD; o Morph aplica rate
limit), não URLs inexistentes. Os 6 blocos `Source:` da run original permanecem
íntegros e as evidências novas estão isoladas na §7.3.

Distinção preservada: **descrição** `[description]` = metadados não verificados;
**transcrição** `[spoken i/M]` = único suporte de fala; **observação visual** =
ausente (nenhum vídeo assistido).

## 8. Custos, tempos e rastro das execuções

| Run | Modelo | Tempo | Custo | Natureza |
|---|---|---|---|---|
| `20261012-184601` (relatório corrigido) | `meta/muse-spark-1.3-contributor` | 271,9 s (research 217,2 + write 54,7 + audit 0,0) | **$0,30717498** (agent_selection 0,02888 · research 0,14677498 · report_writing 0,13152) | **medição** por etapa (`stats.json`) |
| `20261012-183234` (pesquisa medium anterior) | idem | — | **$0,2829** (0,0204 / 0,1124 / 0,1501) | **medição** de outra run |
| `20261012-192621` — run curta de prova do tracing (pós-fix) | `meta/muse-spark-1.3-contributor` | — | **$0,2293757** (agent_selection/research/report_writing) | **medição** (`stats.json`); serviu para provar que o CALLTRACE passou a registrar **3 chamadas**, incluindo `agent_creator.py:45:choose_agent` |
| `20261012-224217` — run com `SEMANTIC_REVIEW=1` | idem | 224,6 s | **$0,35240234** | **medição**; inclui a revisão semântica, que as runs acima não tinham |

Os dois valores em dólares são **medições de runs distintas** — não faturamento
do provedor nem saldo da chave.

**`audit_s = 0.0`:** representa uma fase que **não inclui a revisão posterior**,
não arredondamento. O valor mede apenas a auditoria mecânica de procedência
(regex + comparação com manifesto), que não faz chamada de LLM. A revisão
semântica desta seção 7 foi executada **fora** da run, sobre os artefatos
salvos, e portanto **não está contida nesse 0,0** — é trabalho adicional,
rastreado apenas no replay da §7.2.

**Prova direta da lacuna de tracing, por comparação.** Os dois traces
(`runs/call_traces/`, preservados fora de `/tmp`, que é podado):

| Run | chamadas registradas | `agent_selection` presente? |
|---|---|---|
| `20261012-184601` (esta) | **2** — `query_processing.py:118`, `report_generation.py:275` | **não** |
| `20261012-192621` (pós-fix) | **3** — `agent_creator.py:45:choose_agent`, `query_processing.py:118`, `report_generation.py:275` | **sim** |

Ou seja: o `stats.json` da run `184601` cobra **3 etapas** (0,02888 + 0,14677 +
0,13152), mas o CALLTRACE da época só enxergava **2 chamadas** — porque
`agent_creator.py` importa `create_chat_completion` no nível do módulo e segurava
referência própria. O custo da etapa existia; a instrumentação não a via.

**Lacunas de instrumentação declaradas** (`stats.json:not_instrumented`):
`EmbeddingsFilter` (site-packages `context/compression.py:135`), corte de
contexto (`skills/context_manager.py:63`), montagem de prompt em
`skills/researcher.py` e retrievers não-custom (searx/duckduckgo/arxiv rodam
dentro da biblioteca). Custo não é atribuível a essas partes.

**Lacuna corrigida nesta auditoria:** o CALLTRACE registrava 2 das 3 etapas
faturadas, porque `agent_creator.py` (etapa `agent_selection`) importa
`create_chat_completion` no nível do módulo e segurava referência própria.
Corrigido com rebind de `agent_creator`, `tool_selector`, `utils.tools`,
`skills.deep_research` e `skills.curator`; a run de prova passou a registrar
**3 calls**, incluindo `agent_creator.py:45:choose_agent`.

## 9. Vereditos finais

* **Execução:** ✅ exit 0, sem 401/400, `stop_reason=coverage`, coleta 217,2 s
  dentro dos 600 s declarados.
* **Atendimento do pedido:** ✅ **com correção** — a lista foi reclassificada em
  quatro dimensões (licença, cobrança pelo software, dependência externa,
  consumo do modelo); `oh-my-opencode` **mantido** (SUL não implica software
  pago; a restrição é de uso, adequada ao caso pessoal); `morph-plugin` e
  `morph-fast-apply` **separados**; `goal-plugin` reclassificado como *"sem
  cobrança própria ou serviço adicional obrigatório"*.
* **Auditorias:** mecânica 0 findings; semântica **reprovou** a versão original
  da run (`accepted=False`, com 3–4 `unsupported`) — afirmações centrais
  corrigidas na seção 3 com evidência de mantenedor. **Revalidação do próprio
  corrigido: `unsupported = 1` (métricas OpenCode), `blocking = 1` + 4 `gap`
  (Morph pricing, Daytona, sugestão), estado `reprovado`**, reproduzido no
  replay final (§7.2.1). O relatório **não é aceito** até que as claims centrais
  sem evidência sejam resolvidas (ver §7.2.1 e AUDITORIA_184601_final.md). A revisão também encontrou um **erro
  factual** neste arquivo — a §4.2 apresentava `Supabase`/`Stripe` quando a
  transcrição grafa `Supaso`/`Stry` — corrigido com a ressalva de transcrição.
* **Fluxo normal:** ✅ passa a reprovar automaticamente. A revisão semântica foi
  conectada ao caminho após `write_report` (opt-in `SEMANTIC_REVIEW=1`), e o
  replay desta run demonstra que gratuidade sem qualificação e a confusão
  morph-plugin/morph-fast-apply são questionadas antes de qualquer aceitação.
