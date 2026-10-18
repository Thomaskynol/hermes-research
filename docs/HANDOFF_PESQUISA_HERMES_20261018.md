# Handoff — Pesquisa no Hermes: produto aprovado e próxima etapa de desenvolvimento

**Data:** 18 de outubro de 2026.  
**Destinatário:** nova conversa de acompanhamento técnico e agente de programação que trabalhará no projeto.  
**Usuário:** Thomaskyn / Thomas.  
**Idioma:** português brasileiro.

## 1. Leia primeiro: objetivo e ponto de continuidade

Estamos desenvolvendo a pesquisa do Hermes, com Agent Reach e GPT Researcher na stack atual. Uma rodada de correções da extração de afirmações, qualificação de evidências e auditoria foi concluída e validada. Depois disso, o usuário definiu e aprovou a modelagem do produto final.

O segundo anexo, **`MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.md`**, é a referência normativa do produto. A versão atual do texto é **1.1**. A modelagem anterior, 1.0, foi aprovada pelo usuário; a revisão 1.1 apenas registra sua confirmação de que embeddings já são locais e que nuvem pode ser avaliada futuramente, sem trocar a configuração agora.

SHA-256 da modelagem 1.1: `3487df6f2073a75b78047d60a384c92de2e0c41cde42ab0753f48c13e4f54be0`.

**A próxima fase é de desenvolvimento com código, testes e avaliação real da pesquisa.** O usuário propôs usar GitHub e operar o OpenCode diretamente na pasta do projeto, reduzindo a intermediação do Hermes para alterar arquivos. Essa direção foi recomendada, mas ainda não foi executada nesta conversa.

Não recomece a investigação do zero nem trate as capacidades da modelagem como já implementadas. Continue a partir da base validada, identificando a diferença entre o estado atual e o produto desejado.

## 2. Produto desejado: resumo das decisões

Leia a modelagem completa; este resumo é apenas orientação de continuidade.

- **Agent Reach:** operações individuais de busca e leitura. Ler uma página, um repositório ou um vídeo não deve iniciar uma pesquisa completa.
- **Deep Researcher:** planejamento, descoberta, coleta, análise, ciclos de lacunas, síntese e verificação, usando os acessos do Agent Reach.
- Produto de pesquisa geral, sem ficar restrito a plugins do OpenCode ou a regras sobre licenças e gratuidade.
- Prioridade a infraestrutura autohospedada. Sites e APIs oficiais continuam sendo acessados pela internet; “offline” não significa rede desconectada.
- Sem APIs comerciais de pesquisa como Exa/Tavily ou equivalentes, inclusive como fallback silencioso.
- APIs oficiais gratuitas de fontes pertinentes, GitHub e bases acadêmicas são permitidas, respeitando franquias e limites. Não contratar modalidades pagas automaticamente.
- Não integrar API de catálogo do OpenRouter nesta etapa. Isso é diferente da API usada para chamar o modelo de IA, que permanece permitida.
- O modelo de IA pode ser remoto. **Embeddings são locais atualmente**, segundo confirmação do usuário; nome e configuração exatos ainda precisam ser inventariados. Uma migração futura para nuvem é uma possibilidade, não trabalho autorizado para esta etapa.
- O usuário acredita que quase todas as integrações já existem no Agent Reach. Inventariar e reutilizar; não reinstalar tudo ou presumir funcionamento apenas pela configuração.
- Primeira versão completa: web/Google, YouTube, GitHub e pesquisa acadêmica. Reddit, Bilibili, V2EX e Twitter/X são ampliações posteriores.
- YouTube: usar legendas do autor ou automáticas do YouTube. Sem transcrição utilizável, retirar o vídeo das evidências sobre a fala e manter somente registro de descoberta/limitação. Diferenciar ausência de legenda de falha ao obtê-la. Não incluir ASR local ou remoto nesta etapa.
- Relatório final útil, em português por padrão, com resposta ao pedido, referências, comparações, cálculos reproduzíveis quando pertinentes, incertezas e lacunas.
- Reconhecer explicitamente pesquisas parciais. Aprovação semântica de um texto não comprova cobertura da pergunta inteira.

### Profundidade e orçamento

Os números são referências configuráveis, não cotas rígidas:

| Perfil | Fontes úteis como referência | Tempo aceitável |
|---|---:|---:|
| Light | 10–20 | 5–10 minutos |
| Medium | Cerca de 50 | Até 30 minutos |
| Hard | 100–200 | Até 2 horas |
| Deep | 200–600 | Até 10 horas |
| Extensivo ou personalizado, opcional | Conforme o problema | 16–24 horas |

**Controles independentes:** perfil de esforço, abrangência, profundidade, máximo de rodadas e concorrência. Podem existir limites por ramo e ajustes de revisões mínimas, sempre subordinados ao orçamento global.

O exemplo “50 melhores skills para OpenCode e Claude Code” exige principalmente amplitude, com análise suficiente dos finalistas. Uma investigação explicativa sobre crise de RAM e cenários exige principalmente profundidade, mas ainda precisa cobrir os fatores relevantes. A comparação ampla de modelos de IA pode exigir ambas em nível alto.

### Ciclo adaptativo obrigatório

Durante a pesquisa, o sistema deve examinar o material acumulado, identificar lacunas e contradições, priorizar sua importância, buscar evidências direcionadas, atualizar o estado e decidir a próxima rodada. Não basta revisar o relatório quando ele estiver pronto.

Rodadas continuam a mesma investigação e preservam achados. Devem ter registro do que acrescentaram, do que tentaram resolver e de seu motivo de encerramento. Repetição sem informação nova não demonstra aprofundamento. Lacunas essenciais remanescentes impedem declarar completude, mesmo quando se atingiu saturação nos caminhos já visitados.

## 3. Ambiente de produção conhecido

| Item | Referência conhecida |
|---|---|
| Pasta do projeto no ambiente Hermes | `/opt/data/deep_research_outputs/gpt_researcher` |
| Python usado nas validações | `/opt/data/home/.agent-reach-venv/bin/python` |
| HERMES_HOME | `/opt/data` |
| Hermes | v0.21.6, conforme contexto informado; conferir se necessário |
| Modelo da pesquisa/auditoria na última rodada | `nvidia/nemotron-3.5-super-vl:free`, via OpenRouter |
| Embeddings | Locais; identidade e configuração a verificar |
| Hardware do servidor | Não inventariado nesta conversa |
| Estado do Git / remoto GitHub | Não inventariado nesta conversa |

A troca para esse Nemotron foi solicitada pelo usuário e foi legítima. Não trate a escolha como um defeito nem altere o modelo incidentalmente. O modelo do agente de programação OpenCode pode ser diferente do modelo executado pelo produto; são decisões separadas.

O ChatGPT desta conversa revisou arquivos exportados, rodou testes offline e produziu patches/documentos. **Não possui acesso comprovado ao servidor de produção.** Os caminhos `/workspace/scratch/...` mencionados adiante são do ambiente transitório de revisão, não do Hermes. A nova conversa não deve presumir que esse scratch estará disponível.

## 4. Última base de produção validada

### Pacote recebido e conferido

**Arquivo:** `coverage_delivery_184601_qualificacao_execucao_replay_daytona.zip`  
**Tamanho:** 156.351 bytes.  
**SHA-256:** `7095bab8f89bfe8f966858a65d4f34380275d77d94d0367dc89309b97ac076a7`.

Todos os **34 registros do manifesto** foram conferidos. O resumo do Hermes mencionou 28, mas isso foi uma imprecisão de contagem, não falha de integridade.

| Arquivo | SHA-256 esperado da última base |
|---|---|
| `semantic_review.py` | `93087dc82f8fbadb9802146195473458c6d1ab7d36aeed4c110caa6a5557f57a` |
| `gpt_researcher_integration.py` | `972f5d95b7fdbe6815058e7fc52b5da3c49bd3fa41d1ceadee24d71c3a7816b7` |
| `fixtures/relatorio_daytona_original.md` | `4952cc655ef2c636d79eac25d26df6450bfed502515a717d8aae8c37a2783d27` |
| `fixtures/corpus_context_original.json` | `309880552fadcd7b71b500549b2d9dda84f9e0128953eeb4bf5c934168de3892` |

O pacote inclui os dois arquivos de produção, dois fixtures Daytona, manifesto, scripts, saídas de testes, backups e replay. **Não é uma exportação completa do projeto.** Não contém toda a implementação dos serviços e dos módulos auxiliares da instalação. O desenvolvimento deve partir da árvore real ou de uma exportação completa do código relevante.

### Testes aprovados independentemente

| Suíte em `scripts/` | Quantidade |
|---|---:|
| `test_semantic_evidence_selection.py` | 9 |
| `test_semantic_failure_guard.py` | 8 |
| `test_semantic_coverage.py` | 11 |
| `test_semantic_coverage_review.py` | 11 |
| `test_semantic_coverage_structure.py` | 16 |
| `test_semantic_scope_boundary.py` | 1 |
| `test_semantic_corpus_qualification_review.py` | 7 |
| `test_semantic_qualification_final_cases.py` | 6 |
| `test_semantic_e2e_integration_review.py` | 4 |
| `test_semantic_e2e_replay_regressions.py` | 3 |
| `test_semantic_replay_closure.py` | 7 |
| **Total** | **83** |

As onze suítes passaram em processos offline separados, com transporte de rede proibido. Isso valida seus casos, não a qualidade geral de toda pesquisa.

Comando usado no servidor:

```bash
/opt/data/home/.agent-reach-venv/bin/python scripts/run_replay_offline_validation.py
```

O runner também depende dos fixtures congelados antigos existentes no ambiente:

- `output/RELATORIO_CORRIGIDO_184601.md`: SHA `55b658951b2bc67d18a0ac78b81b5ad42e374f826350564cdf28c477b968ff9d`.
- `runs/replay_corrigido_evidence.json`: SHA `c58dae0e6a6fa6104c13c9f0736ccd0d6ff51f7aa3b2d96247169ef16410668c`.

Esses fixtures antigos não são o par Daytona. Na revisão local, seus caminhos foram redirecionados para cópias verificadas, sem alterar os testes. Para GitHub/CI, será necessário tornar a localização dos fixtures portátil e preservá-los adequadamente; não basta subir somente o último ZIP.

### Replay real da versão final

- Run ID: `20261018-025746-499364-replay-daytona-reviewed`.
- Script: `scripts/replay_daytona_reviewed.py`.
- Entradas: o par Daytona acima, com hashes de código e entradas registrados antes/depois.
- Três passagens, `max_claims=10000`, duração de aproximadamente 340,19 segundos.
- **23 claims**, incluindo as cinco linhas antes omitidas da tabela `1.2 Core Value Proposition`.
- Seis tentativas de requisição: cinco respostas válidas e uma falha 502 do provedor.
- **57 votos válidos e 12 votos falhos**, reconciliados com o material bruto. A falha de uma requisição afetou um lote de 12 claims.
- Todas as claims atingiram quórum mínimo. Resultado: 20 sustained, dois disputed_tie e uma partial.
- `coverage_complete=True`, `dropped_incomplete=0`, `accepted=False`, `verdict_state="revisão incompleta"`.
- Os dois empates foram corretamente bloqueantes. Não é necessário repetir o replay até obter aprovação.

As entradas de revisão extraídas pelo código final corresponderam às do replay. Código, fixtures e script conferiram com os hashes registrados durante a execução.

**Esta rodada de correções está encerrada para os casos acordados. A ferramenta inteira não foi declarada concluída.**

## 5. O que foi corrigido e deve ser preservado

- Trechos distintos da mesma URL são acumulados, sem sobrescrever evidência anterior.
- Qualificação distingue conteúdo útil, erros, HTML insuficiente, metadados e transcrições parciais, preservando fatos utilizáveis.
- Metadados úteis de GitHub mantêm relações como tag/commit e branch/HEAD.
- Extração dos formatos acordados: metadados, tabelas, títulos factuais e parágrafos longos.
- Tabelas herdam sujeito dos headings ancestrais, respeitando seções irmãs e ambiguidades.
- Itens descartados com estado incompleto bloqueiam cobertura; o contador é explícito.
- IDs, origem, duplicatas, limite de claims e estados de revisão são rastreáveis.
- Quórum, empates e falhas técnicas não são convertidos em aprovação artificial.
- Há contador de falhas por voto, além dos resultados agregados por claim.
- Metadados de chamadas pertencem à revisão atual e são serializáveis; dicionários de uso não viram strings repr.
- O registro normal `depth.semantic` preserva o resultado completo, incluindo veredictos, votos, cobertura e chamadas.
- O tempo total registrado inclui revisão semântica.

Evite restaurar versões anteriores V2/V3/V4 ou aceitar um nome de arquivo como prova de identidade. Houve entregas antigas com hashes e resultados diferentes sob nomes parecidos. A referência desta transição é a base identificada acima.

## 6. Principais pendências do produto

1. **Cobertura da pergunta e descoberta ampla.** A pesquisa original comparava seis plugins, mas coletou apenas material de Daytona. Isso precisa ser reconhecido como lacuna da execução, sem atribuir automaticamente tudo a limitações dos resultados de busca.
2. **Planejamento e ciclos adaptativos reais.** A coordenação precisa examinar o estado acumulado e buscar lacunas durante a pesquisa.
3. **Controles independentes de amplitude, profundidade, rodadas e orçamento.** Valores de configuração precisam afetar o caminho executado e aparecer nas medições.
4. **Operações individuais do Agent Reach comprovadas e reaproveitadas.** Inventário primeiro; não presumir ausência ou duplicar integrações existentes.
5. **Síntese que responda ao pedido.** A primeira pesquisa gerou um relatório técnico sobre Daytona em vez da comparação solicitada. O relatório deve organizar critérios, decisões e lacunas do pedido.
6. **Generalização da extração e verificação.** O auditor atual ainda contém regras específicas de pacotes, licenças e gratuidade. Não é prova de auditoria equivalente em qualquer assunto.
7. **Escala e execuções longas.** Retomada, preservação de evidências e orçamento para pesquisas de horas e centenas de documentos precisam de validação própria.
8. **Avaliação real representativa.** Além dos testes de regressão, medir cobertura, fontes, sustentação das conclusões, utilidade, tempo e consumo em diferentes tipos de pergunta.

Detalhe relevante do código recebido: a integração calcula parte do sinal de cobertura a partir da presença/ausência de `research_gaps`, com valores substitutos como 1,0 ou 0,5. Isso não é uma matriz observada de cobertura da pergunta. Também delega o fluxo principal a `conduct_research()` e `write_report()`. Esses são pontos a examinar na arquitetura; não demonstram, sozinhos, impossibilidade do framework.

## 7. GPT Researcher: orientação arquitetural, não reescrita já decidida

O usuário perguntou se seria mais fácil construir algo próprio. A recomendação foi assumir controle direto da coordenação: plano, estado, cobertura, ciclos de lacunas, orçamento e encerramento. Reaproveitar conectores, evidências, auditoria e testes.

Não foi afirmado que reescrever tudo será mais fácil. A documentação pública do GPT Researcher já descreve breadth, depth e concurrency, e há uma proposta pública de pesquisa adaptativa identificada como proposta. Não presumir que documentação atual corresponde à versão instalada.

Separar quatro causas possíveis: limitação da biblioteca, versão instalada, configuração e integração. Inspecionar primeiro a implementação efetivamente usada. Manter a biblioteca encapsulada enquanto útil; migrar componentes quando a alternativa demonstrar melhor adequação aos mesmos casos de referência.

Referências oficiais consultadas nesta conversa:

- https://docs.gptr.dev/docs/gpt-researcher/gptr/config
- https://docs.gptr.dev/docs/gpt-researcher/gptr/deep_research
- https://docs.gptr.dev/docs/proposals/adaptive-deep-research
- https://github.com/assafelovic/gpt-researcher

## 8. Fluxo de desenvolvimento proposto: GitHub + OpenCode

### Responsabilidades

- **Git/GitHub:** histórico, branches, diffs, revisão, documentação e checks reproduzíveis.
- **OpenCode:** ler a árvore real, implementar mudanças delimitadas e executar testes no ambiente correto.
- **Conversa de acompanhamento:** modelagem, decisões, definição de casos, revisão crítica dos resultados e próximos objetivos.
- **Hermes:** aplicação que utilizará as ferramentas e ambiente de validação da integração. Não precisa intermediar toda alteração de código.

O próximo trabalho será majoritariamente código e testes, mas o produto continua exigindo pesquisas reais para avaliar utilidade e sustentação das conclusões. Um total crescente de testes não basta.

### Condições práticas

Abrir o OpenCode na raiz correta da nossa integração, com acesso ao Python, às dependências e aos serviços usados na execução. Preferir o mesmo ambiente do servidor, por exemplo via terminal SSH e container quando aplicável, ou um ambiente de desenvolvimento realmente reproduzível. A mesma pasta nominal em outro computador não garante o mesmo ambiente.

Antes de preparar GitHub, descobrir se a pasta já é um repositório, qual sua raiz, quais mudanças estão pendentes e como ela se relaciona ao upstream. Não presumir que o diretório com nome `gpt_researcher` seja um projeto próprio completo. Não iniciar um repositório aninhado ou trocar remotes sem entender a estrutura.

A sugestão é usar um remoto privado inicialmente, com branch de trabalho e baseline identificável. A organização concreta — repositório da integração, dependência fixada ou customização de um upstream — depende desse inventário. Nenhum repositório GitHub foi criado nesta conversa; não há URL conhecida.

Versionar o código relevante, dependências, instruções de execução, modelagem e fixtures necessários aos testes. Manter credenciais, ambientes virtuais, sessões autenticadas e caches fora do Git. Usar configurações de exemplo sem segredos. Preservar fixtures públicos necessários à reprodução, com revisão do que efetivamente será enviado.

Trabalhar por entregas delimitadas: problema, comportamento esperado, critérios de aceitação, implementação, testes e diff. Os checks offline devem funcionar sem rede e sem credenciais; testes reais com rede/modelo ficam separados e limitados. Não habilitar chamadas reais a cada commit como efeito implícito do CI.

## 9. Primeiro passo recomendado na nova conversa

Depois de ler os dois anexos, preparar uma primeira tarefa de inventário para o OpenCode no ambiente real. O objetivo é obter informação suficiente para organizar o desenvolvimento sem alterar a produção incidentalmente.

A tarefa deve levantar:

1. Raiz Git, estado de trabalho, remotes identificados sem divulgar credenciais, regras locais e relação com o upstream.
2. Arquivos de entrada, módulos próprios, alterações no GPT Researcher e serviços auxiliares efetivamente envolvidos.
3. Versões instaladas, importações reais, Python/venv e dependências reproduzíveis.
4. Conectores do Agent Reach existentes, operações expostas, evidência de funcionamento e lacunas de integração. Configuração e chamada bem-sucedida são evidências diferentes.
5. Modelo remoto configurado, modelo local de embeddings e caminhos de configuração sem mostrar chaves.
6. Recursos do servidor e limites operacionais pertinentes à concorrência e às execuções longas.
7. Estado dos testes, dos fixtures e dos hashes da baseline. Se houver divergência, documentar o diff antes de substituir qualquer arquivo.
8. Proposta de organização no GitHub, de ambiente de desenvolvimento e de marcos de implementação vinculados à modelagem.

Não há necessidade de outra pesquisa extensa ou replay caro para esse inventário. Se um teste de acesso for necessário para esclarecer uma integração, deve ser pequeno, identificado como real e com seu objetivo explícito.

O resultado do inventário deve permitir escolher a primeira entrega de código. O maior problema funcional observado é a cobertura por pergunta/entidade/critério, mas a ordem concreta depende do que a árvore atual já oferece.

## 10. Como continuar com os arquivos

O usuário pretende anexar nesta ordem:

1. Este handoff.
2. `MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.md`, versão textual 1.1.

Se for necessário revisar código fora do ambiente OpenCode, obter a árvore pelo futuro repositório ou pedir o pacote técnico adequado. Os dois anexos de texto não contêm o código completo. O último ZIP validado é uma referência de baseline, não substitui a árvore real.

Identificadores de arquivos já existentes nesta conversa, úteis apenas quando o acesso correspondente estiver disponível:

- Modelagem: Library ID `libfile_2b31871e2a048191b60555c6e50b374d`.
- Último ZIP validado: Library ID `libfile_b585234a435c819194be94e9ee960358`.
- Exemplo de relatório desejado: `modelos_openrouter_pesquisa_2026-10-18(1).md`, Library ID `libfile_9213ca6ca9e08191907495dc6dad4055`.
- Prompt desse exemplo: `prompt_pesquisa_modelos_IA_OpenRouter(2).md`, Library ID `libfile_178b5b5f2a80819194a8bb89a47977da`.

Os exemplos de modelos de IA definem o nível esperado de estrutura e rigor; seus preços e benchmarks não foram auditados nesta etapa de modelagem e não devem ser tratados como fatos confirmados por este handoff.

No ambiente anterior de revisão, a extração do último ZIP ficou em `/workspace/scratch/06d8e9e4931d/review_daytona_final_20261018`, com verificação independente em `review_daytona_final_20261018_offline`. Esses caminhos são conveniências temporárias e podem não existir na nova conversa.

## 11. Regras de continuidade

- Seja preciso e crítico. O usuário prefere limites e problemas concretos a declarações de conclusão prematuras.
- Use a modelagem como referência única do estado desejado; não acrescente requisitos grandes silenciosamente.
- Reutilize o que existe. Não confunda “não inspecionado” com “não implementado”.
- Diferencie execução real, simulação offline, resultado do modelo e conclusão da revisão independente.
- Não trate exit 0, corpus grande, muitas fontes ou `accepted=False` como demonstração suficiente de pesquisa boa.
- Preserve a rodada de auditoria encerrada. Reabra um ponto somente com uma mudança necessária ou uma falha concreta, sem perder o objetivo geral do produto.
- Não altere o modelo, embeddings, provedores ou serviços incidentalmente durante uma tarefa de código.
- Não restaure arquivos destrutivamente ou sobrescreva o corpus congelado para fazer um teste passar.
- Prefira evidência reproduzível em commits, diffs e resultados de testes. ZIPs continuam úteis para transferência, mas não precisam ser o mecanismo principal de desenvolvimento quando houver GitHub.
- Nenhuma nova funcionalidade de produção foi implementada depois da última base validada; o trabalho posterior foi de modelagem e preparação desta transição.
