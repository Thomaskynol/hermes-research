# Modelagem do produto — Agent Reach e Deep Researcher para Hermes

**Versão:** 1.1 — 18 de outubro de 2026  
**Finalidade:** definir o produto que queremos alcançar e servir como referência comum para implementação, testes e revisão.  
**Natureza:** especificação do estado desejado. Este documento não afirma que todas as capacidades descritas já estão implementadas ou validadas.

## 1. Visão do produto

O Hermes deve oferecer um sistema de pesquisa capaz de investigar assuntos de forma ampla, profunda, atualizada e verificável. O usuário apresenta uma pergunta e escolhe o nível de investigação; o sistema identifica o que precisa descobrir, procura informações em diferentes lugares, lê o material relevante, compara evidências, investiga lacunas e entrega um relatório que responda à pergunta e ajude a tomar decisões.

A pesquisa deve descobrir informações e alternativas que o usuário não conhecia. Precisa combinar amplitude de descoberta com aprofundamento dos pontos importantes, incluindo limitações, contradições e informações que possam mudar a conclusão.

O produto é geral: deve atender comparações de ferramentas, investigações técnicas, estudos acadêmicos e outros assuntos compatíveis com as fontes disponíveis. Os casos de plugins do OpenCode usados no desenvolvimento são testes de referência, não o limite do produto nem uma lista fixa de assuntos reconhecidos.

## 2. Duas ferramentas, uma mesma base de acesso

### Agent Reach: operações individuais

O Agent Reach fornece ao Hermes acesso direto às operações de pesquisa e leitura. Deve permitir, conforme os conectores disponíveis:

- Fazer uma busca e devolver resultados identificados.
- Abrir e extrair o conteúdo de uma página ou documento.
- Obter título, descrição e transcrição disponível de um vídeo do YouTube.
- Consultar um repositório do GitHub e seus documentos relevantes.
- Localizar trabalhos acadêmicos, consultar seus dados e obter o texto quando acessível.

Um pedido como “leia esta página”, “resuma este vídeo” ou “examine este repositório” deve funcionar diretamente, sem iniciar uma investigação extensa. A operação devolve conteúdo, origem, limitações e estado de obtenção, permitindo ao Hermes responder proporcionalmente ao pedido.

### Deep Researcher: investigação coordenada

O Deep Researcher usa as capacidades do Agent Reach para executar pesquisas completas. Ele organiza o plano, acompanha o que foi coberto, decide os próximos caminhos, compara as descobertas e produz o relatório final.

As duas ferramentas compartilham conectores, contratos de retorno e tratamento de evidências. Uma correção na obtenção de transcrições ou na leitura de páginas deve beneficiar ambas.

**Reaproveitamento obrigatório:** a stack existente é o ponto de partida. Integrações que já funcionam no Agent Reach devem ser identificadas, verificadas e reutilizadas. Não se presume que precisam ser instaladas novamente. Também não se presume funcionamento apenas porque existe uma configuração ou dependência instalada.

## 3. Princípios e limites da infraestrutura

“Local” ou “offline”, neste projeto, significa infraestrutura autohospedada e processamento sob controle do usuário. Os sites continuam sendo acessados pela internet.

As regras são:

1. Busca web por infraestrutura própria, como a instância existente do SearXNG, aproveitando os motores efetivamente disponíveis.
2. Coleta, extração, armazenamento, organização de evidências e cálculos executados na infraestrutura controlada pelo usuário.
3. Uso permitido de modelo de IA hospedado na nuvem. O provedor e o modelo devem ser configuráveis; a pesquisa deve registrar o que efetivamente utilizou.
4. Não usar APIs comerciais terceirizadas de pesquisa, como Exa, Tavily ou serviços equivalentes, como dependência ou fallback silencioso.
5. Permitir APIs oficiais gratuitas de fontes pertinentes, incluindo GitHub e bases acadêmicas, respeitando suas condições e franquias. O esgotamento de uma franquia não autoriza contratar ou consumir uma modalidade paga.
6. Não integrar a API de catálogo do OpenRouter nesta etapa. Quando esse site for objeto de uma pesquisa, suas páginas web podem ser consultadas. Isso não impede usar o OpenRouter como provedor das chamadas ao modelo de IA.
7. Não introduzir serviços externos pagos de extração, transcrição, embeddings ou processamento de documentos.
8. Manter as operações de pesquisa como consultas. Produzir arquivos e registros locais faz parte do produto; publicar conteúdo ou interagir com terceiros não faz parte do fluxo de pesquisa.

A escolha de bibliotecas, processos e armazenamento deve aproveitar a stack atual e os recursos reais do servidor. Esta modelagem define responsabilidades e comportamentos, sem impor uma reconstrução geral ou um framework novo.

**Embeddings:** o usuário confirmou que a stack atual usa um modelo local. Essa configuração deve ser preservada durante esta etapa; a identidade e a configuração exatas precisam ser verificadas no ambiente, sem presumir outro modelo. Uma possível migração futura para embeddings em nuvem pode ser avaliada como decisão separada de qualidade, custo e operação. Essa possibilidade não é uma mudança já aprovada para execução, não autoriza fallback remoto silencioso e não altera a proibição de APIs pagas de pesquisa.

## 4. Fontes e alcance

### Alcance da primeira versão completa

| Família | Capacidade esperada |
|---|---|
| Web e Google | Descobrir e ler páginas, documentação, blogs, comparações, notícias e outras fontes públicas pertinentes. Identificar os motores realmente utilizados. |
| YouTube | Descobrir vídeos e obter a transcrição disponibilizada pelo autor ou gerada automaticamente pelo YouTube. |
| GitHub | Descobrir projetos e consultar README, licença, documentação, versões, releases, manifests e outros arquivos ou registros relevantes para a pergunta. |
| Pesquisa acadêmica | Descobrir trabalhos, explorar referências e citações, conferir identificação bibliográfica e ler resumos ou textos completos conforme a disponibilidade. |

APIs acadêmicas como Semantic Scholar, arXiv, OpenAlex e Crossref são opções de integração ou reaproveitamento. A escolha inicial deve considerar o que já existe na stack, a utilidade de cada operação e o acesso gratuito disponível. Não é obrigatório integrar todos os serviços para considerar a capacidade acadêmica inicialmente funcional.

Nem toda investigação exige todas as famílias de fontes. A seleção depende do assunto. Uma comparação de plugins pode exigir documentação, código e relatos de uso; uma pergunta científica pode exigir artigos e referências acadêmicas.

### Ampliação posterior

A arquitetura deve aceitar conectores para Reddit, Bilibili, V2EX, Twitter/X e outras fontes. Eles não são requisitos para fechar a primeira versão completa. Cada integração futura deve declarar quais operações oferece e quais limitações possui.

### Regra de honestidade do alcance

Uma fonte só é considerada acessada quando a operação tiver sido executada com resultado verificável. Estar habilitada em uma configuração não comprova acesso. Se Google ou outro canal falhar, isso deve aparecer no registro e na avaliação do alcance da pesquisa.

O acesso pode aproveitar requisições diretas, APIs oficiais permitidas e navegação autohospedada, conforme a necessidade da página e as capacidades existentes. O resultado deve identificar qual caminho funcionou, sem apresentar uma tentativa de acesso como leitura concluída.

## 5. Política específica do YouTube

O conteúdo necessário nesta etapa é textual; não há exigência de assistir ou analisar os quadros do vídeo.

O fluxo deve:

1. Buscar legendas disponibilizadas pelo autor e legendas automáticas do YouTube.
2. Registrar o vídeo, o idioma, a origem da transcrição, a data de obtenção e os intervalos disponíveis quando houver timestamps.
3. Identificar se o texto obtido é completo, parcial ou insuficiente.
4. Usar apenas o material efetivamente obtido para sustentar afirmações sobre o conteúdo falado.
5. Quando não houver transcrição utilizável, retirar o vídeo do conjunto de evidências sobre sua fala. Manter URL e motivo no registro de descoberta para evitar tentativas repetidas e explicar a limitação.
6. Distinguir “legendas ausentes” de “falha ou bloqueio ao obter legendas”. Uma falha de acesso não comprova inexistência da transcrição.

Título e descrição podem ajudar a descobrir e selecionar candidatos. Não substituem uma transcrição nem contam como leitura do conteúdo falado. Não haverá geração local ou terceirizada de transcrição a partir do áudio nesta etapa.

## 6. Modos, abrangência, profundidade e rodadas

O usuário deve poder configurar separadamente o orçamento da execução, a abrangência, a profundidade e os ciclos de pesquisa. Esses controles não são sinônimos nem devem ser reduzidos a uma única quantidade de fontes.

### Controles independentes

| Controle | O que significa | O que deve modificar |
|---|---|---|
| Perfil de esforço | Quanto trabalho e tempo a execução pode consumir. | Orçamentos de tempo, consultas, documentos, análise, escrita e verificação. |
| Abrangência ou amplitude | Quantos candidatos, perspectivas, subtemas e caminhos distintos serão explorados. | Diversidade e quantidade de caminhos de descoberta; cobertura de categorias e alternativas. |
| Profundidade | Até onde se investiga cada questão relevante. | Detalhamento, acompanhamento de referências, explicações, condições, contraprovas e verificação das conclusões. |
| Rodadas de pesquisa | Quantas vezes o sistema pode reavaliar o que sabe e buscar o que falta. | Limites dos ciclos de avaliação de lacunas e novas operações direcionadas. |
| Concorrência | Quantas operações podem acontecer ao mesmo tempo. | Velocidade e consumo simultâneo de recursos, respeitando os limites das fontes. |

Abrangência e profundidade podem ser apresentadas como níveis compreensíveis, como baixa, média, alta e muito alta, com opção automática. A implementação deve resolver cada nível em limites e comportamentos observáveis, registrar esses valores e permitir ajustes avançados. Escolher um nível alto não comprova que ele foi alcançado: o registro final deve mostrar a exploração e o aprofundamento efetivamente realizados.

### Perfis de esforço

Os perfis abaixo são atalhos de orçamento. O nome do perfil Deep não obriga a mesma combinação de abrangência e profundidade para todas as perguntas.

| Perfil | Referência de fontes úteis | Tempo de referência | Intenção |
|---|---:|---:|---|
| Light | Aproximadamente 10–20 | 5–10 minutos | Cobrir o essencial com verificação proporcional. |
| Medium | Cerca de 50 | Até 30 minutos | Ampliar candidatos e comparar os principais critérios. |
| Hard | Aproximadamente 100–200 | Até 2 horas | Investigar mais alternativas, detalhes, divergências e limitações. |
| Deep | Aproximadamente 200–600 | Até 10 horas | Explorar muitos caminhos e aprofundar os subtemas relevantes. |
| Extensivo, opcional ou personalizado | Conforme o problema e os recursos | 16–24 horas | Investigações excepcionalmente amplas ou trabalhosas. |

Esses números são referências iniciais, não cotas obrigatórias nem garantias de quantidade. Encontrar material irrelevante para preencher um contador não melhora uma pesquisa. Uma investigação deve poder encerrar antes do teto quando os critérios estiverem satisfeitos; também pode terminar parcial quando as evidências disponíveis forem insuficientes.

Devem existir limites independentes para consultas, documentos, chamadas ao modelo, tokens, tempo, concorrência e tentativas. A execução deve reservar capacidade para síntese, auditoria e entrega, em vez de gastar todo o orçamento na coleta.

O usuário pode ajustar o perfil por pesquisa e restringir ou priorizar fontes. A configuração efetivamente aplicada deve ser registrada; ajustes de profundidade não podem ultrapassar as restrições globais de serviços e custos permitidos.

O tempo informado deve abranger as fases da execução, incluindo escrita e auditoria. Tempos de requisições individuais e tolerância a falhas são controles separados da duração total da pesquisa.

### Configuração de rodadas

Deve ser possível definir um máximo de rodadas globais e, quando necessário, limites de aprofundamento por ramo. Uma rodada global considera o estado acumulado da investigação; o aprofundamento de um ramo acompanha uma subpergunta específica. Esses números precisam ter significado explícito, sem confusão com tentativas de transporte, quantidade de chamadas ao modelo ou votos do auditor.

O funcionamento padrão é adaptativo: continuar enquanto houver lacunas relevantes e orçamento, até o limite configurado. O usuário pode exigir revisões intermediárias adicionais ou ajustar o mínimo de rodadas, sem ultrapassar os limites globais. Se uma rodada obrigatória não trouxer caminhos pertinentes, ela deve registrar a revisão e o motivo, sem fabricar buscas para preencher o contador.

Aumentar abrangência, profundidade e rodadas simultaneamente pode multiplicar o trabalho. Os limites globais de tempo, chamadas e documentos têm precedência sobre a expansão de qualquer ramo. O sistema deve preservar uma finalização útil quando algum limite for atingido.

### Exemplos de intenção

| Pedido | Ênfase esperada | Comportamento |
|---|---|---|
| Encontrar as 50 melhores skills para OpenCode e Claude Code | Abrangência muito alta; profundidade suficiente para comparar. | Descobrir um conjunto maior que a seleção final, reconhecer duplicatas e verificar critérios relevantes de cada finalista. |
| Explicar uma crise no mercado de RAM e avaliar possíveis desdobramentos | Profundidade alta; abrangência dirigida aos fatores necessários. | Investigar mecanismos, atores, dados ao longo do tempo, explicações concorrentes, hipóteses e cenários com incertezas explícitas. |
| Comparar amplamente modelos de IA, rotas, preços, cache e capacidades | Abrangência e profundidade altas. | Descobrir muitos candidatos e investigar em detalhe versões, condições, evidências e contas dos finalistas. |
| Ler uma página ou um vídeo específico | Operação individual do Agent Reach. | Recuperar e analisar o material solicitado, com alcance proporcional ao pedido. |

As 50 skills representam o tamanho desejado da seleção final, não 50 URLs ou 50 consultas. Profundidade menor não dispensa verificação dos critérios essenciais. Uma pergunta focada, por sua vez, pode exigir vários fatores e perspectivas para ser explicada adequadamente.

O usuário não precisa preencher todos os controles em cada solicitação. O sistema pode propor uma combinação a partir da pergunta e do perfil, respeitando os valores definidos explicitamente pelo usuário e registrando as escolhas automáticas.

## 7. O significado de “fonte” e os contadores obrigatórios

A pesquisa deve distinguir:

- **Descobertas:** resultados e endereços encontrados.
- **Obtidas:** documentos cujo conteúdo foi recuperado.
- **Utilizáveis:** documentos com conteúdo pertinente após a qualificação.
- **Analisadas:** material efetivamente processado na investigação, com indicação do trecho ou alcance lido.
- **Utilizadas na síntese:** material levado para a construção das conclusões.
- **Citadas:** fontes referenciadas no relatório final.

Resultados de busca, registros bibliográficos e vídeos sem transcrição não podem inflar o contador de documentos lidos. Páginas duplicadas ou republicações do mesmo material devem ter sua relação reconhecida. Versões diferentes de um documento podem ser relevantes, mas devem continuar identificadas como versões.

Quantidade de URLs e independência das evidências são medidas distintas. Muitas páginas reproduzindo a mesma afirmação não constituem, por si só, múltiplas confirmações independentes.

## 8. Fluxo esperado de uma investigação

### Compreender o pedido

Identificar a pergunta principal, a finalidade da resposta, os critérios de comparação, os alvos obrigatórios, o período relevante e as restrições. Pedir esclarecimento somente quando uma informação ausente mudar materialmente o trabalho; nas demais situações, declarar premissas razoáveis e avançar.

### Construir um plano verificável

Dividir a pergunta em subperguntas e critérios que possam ser acompanhados. Em comparações com entidades nomeadas, manter cobertura por entidade e por critério. Em buscas abertas, manter também o conjunto de candidatos descobertos e os caminhos ainda não explorados.

O plano não pode limitar a descoberta às alternativas mencionadas inicialmente pelo usuário. Deve poder ser atualizado quando a investigação revelar novas alternativas ou perguntas relevantes.

### Explorar amplamente

Usar variações de consulta, termos relacionados e outros idiomas quando pertinentes. Procurar fontes primárias, alternativas menos óbvias, análises e experiências relevantes. Evitar que o primeiro candidato encontrado monopolize o orçamento.

### Obter e ler o material

Selecionar resultados pertinentes, recuperar o conteúdo, qualificar a captura, reconhecer duplicatas e registrar procedência. Usar o texto efetivamente obtido, com contexto suficiente para a afirmação avaliada.

### Aprofundar lacunas e divergências

As descobertas devem orientar novas operações. Uma dependência obrigatória pode exigir investigar preço; uma divergência sobre versão pode exigir consultar releases; um artigo importante pode levar às referências e aos trabalhos que o citam.

Priorizar caminhos pelo impacto na resposta, pelas lacunas de cobertura, pelas contradições e pelo ganho provável de informação. O aprofundamento deve ser limitado pelo orçamento e pela relevância para o pedido.

### Comparar, calcular e sintetizar

Organizar os fatos por critério, confrontar fontes e produzir conclusões proporcionais às evidências. Quando houver cálculos, executá-los com ferramentas locais e conservar fórmulas, entradas, unidades e hipóteses para reprodução.

### Verificar e entregar

Conferir se a resposta atende ao pedido, se as referências sustentam as afirmações e se existem partes importantes não investigadas. Uma revisão pode gerar correções ou buscas adicionais delimitadas; isso não autoriza um ciclo indefinido de tentativas até obter aprovação.

## 9. Ciclo adaptativo, cobertura e condições de parada

O sistema deve acompanhar separadamente os critérios cobertos, parcialmente cobertos, contraditórios, sem evidência, bloqueados e ainda não investigados. A presença de uma URL não é suficiente para marcar um critério como coberto.

### Revisão do material durante a pesquisa

O sistema deve examinar o material em mãos durante a execução, ao final de cada rodada e antes de decisões importantes de expansão ou encerramento. Essa revisão não pode ficar restrita à auditoria do relatório pronto.

Cada ciclo deve:

1. Recuperar o plano, as evidências, os achados e as pendências acumuladas.
2. Avaliar quais perguntas já podem ser respondidas e com que sustentação.
3. Identificar critérios ausentes, evidência insuficiente, divergências, possíveis vieses de descoberta e novas questões relevantes.
4. Priorizar as lacunas pelo impacto na conclusão, pela importância para o usuário e pelo ganho provável de informação.
5. Escolher operações específicas para resolvê-las: reformular buscas, explorar outro canal, abrir uma fonte primária, acompanhar referências ou obter um documento que faltou.
6. Executar a coleta e a análise selecionadas, respeitando o orçamento.
7. Atualizar a cobertura, as conclusões provisórias e o estado de cada lacuna.
8. Salvar o progresso e decidir entre outra rodada, aprofundamento de um ramo ou encerramento fundamentado.

As rodadas continuam a mesma investigação. Elas não devem reiniciar a pesquisa original nem descartar o conhecimento acumulado.

### Registro de lacunas e ganho de informação

Cada lacuna deve conter a pergunta ainda não resolvida, sua importância, o material já disponível, o motivo da insuficiência, as tentativas realizadas, a próxima ação pretendida e seu estado atual. A conclusão de uma tarefa só resolve a lacuna quando seu resultado fornece a evidência necessária.

O sistema deve distinguir novos dados úteis, novas confirmações independentes, duplicatas e repetição sem ganho relevante. Resultados repetidos não justificam considerar a pesquisa mais profunda.

Se uma lacuna essencial permanecer, novas tentativas devem variar o caminho de investigação quando isso fizer sentido. Quando os caminhos disponíveis se esgotarem ou estiverem bloqueados, o sistema registra a limitação. Não deve repetir indefinidamente a mesma consulta nem preencher o que falta com uma hipótese apresentada como fato.

A revisão de lacunas usa critérios e evidências inspecionáveis. Uma nota de qualidade atribuída pelo próprio modelo, isoladamente, não comprova cobertura nem autoriza declarar a pesquisa completa.

### Decisão de encerramento

Uma investigação pode encerrar quando:

- Os critérios importantes tiverem evidência suficiente para responder, com as ressalvas pertinentes.
- Novas rodadas deixarem de acrescentar informação relevante após uma verificação de saturação.
- Um limite de orçamento ou uma interrupção determinar o encerramento.
- Um bloqueio externo impedir a continuação de caminhos importantes.

O motivo de encerramento deve ser explícito, incluindo a possibilidade de atingir o limite de rodadas. A execução deve registrar o número de ciclos concluídos e o que cada um acrescentou ou tentou resolver.

Saturação não pode ser usada para declarar completude se alvos ou critérios essenciais ainda não foram investigados. Nos encerramentos por limite ou bloqueio, a ferramenta entrega o que conseguiu e identifica precisamente o que falta.

O exemplo de uma pergunta sobre seis plugins respondida quase inteiramente com material sobre Daytona deve ser reconhecido como pesquisa parcial, mesmo que o texto produzido sobre Daytona esteja bem sustentado.

## 10. Organização das evidências e rastreabilidade

Cada documento deve preservar sua origem, identificação, URL ou identificador estável, data de obtenção, versão quando disponível, conteúdo bruto e conteúdo utilizável. Identificadores e hashes devem permitir conferir a integridade e reconhecer o material ao longo do processamento. Informações técnicas, como status HTTP, só podem ser registradas como conhecidas quando tiverem sido realmente observadas.

Trechos diferentes da mesma URL precisam ser preservados. Conteúdo de uma execução anterior não pode substituir silenciosamente o corpus atual. Reutilização de cache deve manter a procedência e considerar a necessidade de atualização da informação.

As notas e sínteses intermediárias devem continuar ligadas às fontes e aos trechos que as sustentam. Para centenas de documentos, o sistema deve trabalhar com registros por fonte e sínteses por subtema, preservando esse vínculo durante toda a investigação.

Também deve ser possível identificar o material efetivamente fornecido à escrita e à auditoria, incluindo cortes, seleções e limitações de contexto. Ter um documento no armazenamento não comprova que ele participou de determinada análise.

O conteúdo externo é material de pesquisa, não uma instrução para mudar as regras ou executar ações do agente.

## 11. Qualidade da evidência e tratamento de incertezas

A ferramenta deve:

- Priorizar fontes adequadas ao tipo de afirmação: documentação, código e dados oficiais para características verificáveis; estudos e análises para questões que exigem investigação adicional.
- Diferenciar afirmação do fabricante, avaliação independente, relato de usuário, inferência do pesquisador e desconhecimento.
- Identificar versões, datas e condições que tornem duas afirmações aparentemente contraditórias compatíveis.
- Tratar captura parcial, HTML sem conteúdo, erros, metadados e texto integral de forma distinta.
- Reconhecer divergências relevantes e explicar como elas afetam a conclusão.
- Distinguir, em trabalhos acadêmicos, leitura de metadados, resumo e texto completo. Classificar tipo e situação do trabalho apenas quando houver base para isso.

Uma informação importante não verificada deve permanecer desconhecida ou qualificada. A ausência de documentação não pode ser preenchida com uma suposição apresentada como fato.

## 12. Auditoria e significado de aprovação

A qualidade final exige quatro verificações distintas:

| Dimensão | Pergunta que precisa ser respondida |
|---|---|
| Execução | As operações foram executadas e as falhas foram registradas? |
| Cobertura da pergunta | Os alvos, critérios e caminhos importantes foram investigados? |
| Cobertura da revisão | As afirmações selecionadas para verificação foram extraídas e revisadas, sem omissões silenciosas? |
| Sustentação das conclusões | O material obtido sustenta o que o relatório afirma? |

A aprovação semântica de um texto não comprova que a pergunta inteira foi investigada. Da mesma forma, extração completa de claims não equivale a aprovação de suas conclusões.

Devem ser preservadas as proteções já validadas para quórum, empates, respostas inválidas, falhas técnicas, limites de claims e extração incompleta. Falhas não podem contar como votos favoráveis. Relatórios maiores precisam de revisão por lotes e orçamento compatível, com indicação explícita de qualquer parte não revisada.

O planejamento e a extração de afirmações precisam se adaptar ao assunto. Seu funcionamento geral não pode depender de uma lista fixa de nomes de pacotes, licenças ou expressões específicas dos testes de software.

Os julgamentos do modelo não substituem evidências ou verificações reproduzíveis. O sistema deve permitir inspecionar votos, chamadas, fontes e correções propostas. Não se deve alterar evidências ou eliminar afirmações problemáticas para produzir artificialmente um resultado aprovado.

## 13. Relatório e entregáveis

O resultado principal deve ser um relatório em português, salvo outro idioma solicitado, entregue em formato legível e reutilizável, inicialmente Markdown.

A estrutura se adapta ao assunto, mas deve conter:

1. Resposta direta ou resumo executivo.
2. Data, escopo, critérios e método da pesquisa.
3. Achados organizados pelas perguntas ou critérios relevantes.
4. Comparações, cálculos e recomendações quando fizerem sentido.
5. Referências próximas das afirmações importantes, permitindo consultar a origem.
6. Limitações, contradições, incertezas e itens não investigados suficientemente.
7. Conclusão objetiva e próximos passos úteis.
8. Fontes e anexos necessários à rastreabilidade.

O relatório deve reunir o que for útil para o pedido, incluindo achados negativos ou limitações que alterem uma decisão. O corpo principal precisa ser compreensível; detalhes extensos, corpus e registros podem ser entregues em anexos próprios.

Seu tamanho deve acompanhar a complexidade. Um perfil profundo não pode ficar artificialmente reduzido a um texto curto que omita critérios, enquanto um pedido simples não precisa gerar um documento enorme.

Rankings precisam declarar critérios e justificar inclusões e exclusões. Em uma pesquisa aberta de plugins do OpenCode, oh-my-opencode-slim é um candidato esperado no teste de descoberta. A ferramenta deve encontrá-lo e avaliá-lo; a posição final precisa decorrer da comparação. Nomes conhecidos não podem ser codificados como vencedores permanentes.

O prompt e o relatório de modelos de IA fornecidos pelo usuário são uma referência de abrangência, estrutura e utilidade: candidatos, versões, preços, fontes, fórmulas, comparações e ressalvas. Seus valores e recomendações não constituem uma base fixa de verdade; pesquisas futuras precisam obter evidências atuais.

## 14. Execuções longas e controle pelo usuário

Cada pesquisa deve ter identificação própria e estado persistente, com plano, resultados obtidos, pendências, consumo conhecido e próximos trabalhos. A interface do Hermes deve permitir acompanhar progresso e solicitar pausa, retomada ou cancelamento.

O registro deve vincular a execução à configuração aplicada, ao código, às entradas, aos modelos utilizados e aos artefatos produzidos. As chamadas ao modelo devem conservar metadados suficientes para distinguir solicitações, respostas válidas e falhas. Resultados simulados ou testes offline devem ser identificados separadamente das operações reais.

Uma interrupção deve preservar o que já foi obtido. Retomar uma pesquisa não pode repetir toda a coleta nem misturar versões sem registro. A expiração de uma sessão de interface ou de uma chamada não deve criar outra execução silenciosamente.

O sistema precisa tolerar falhas pontuais com tentativas limitadas e espera adequada, respeitando os limites de cada fonte. Quando uma integração estiver indisponível, deve avaliar alternativas pertinentes e registrar o impacto na cobertura.

Progresso deve ser medido por trabalho observado: fontes obtidas, critérios investigados, pendências e fases concluídas. Estimativas de tempo devem ser identificadas como estimativas. Consumo não medido deve aparecer como desconhecido, não como zero.

O orçamento deve evitar gasto sem ganho de informação e reservar uma finalização utilizável. Cancelamentos ou limites devem produzir um resultado parcial identificável quando houver material suficiente para isso.

## 15. Arquitetura conceitual

As responsabilidades devem ficar organizadas em componentes reaproveitáveis:

| Componente | Responsabilidade |
|---|---|
| Conectores do Agent Reach | Executar acesso individual e devolver resultados com conteúdo, procedência e limitações. |
| Planejador | Interpretar o pedido, definir critérios, descobrir caminhos e acompanhar cobertura. |
| Coordenador da execução | Distribuir tarefas, controlar concorrência e orçamento, persistir progresso e retomar trabalhos. |
| Repositório de evidências | Preservar documentos, versões, trechos, estados de qualidade e relações entre fontes e achados. |
| Análise e cálculo | Comparar informações, examinar divergências e executar contas reproduzíveis. |
| Síntese e relatório | Construir a resposta a partir do material disponível, respeitando os critérios do pedido. |
| Verificação | Conferir cobertura, referências, afirmações e limitações antes da entrega. |

Esses componentes podem aproveitar módulos e serviços existentes. A separação é de responsabilidade; não exige novos servidores, microsserviços ou infraestrutura distribuída.

### Papel do GPT Researcher e eventual coordenação própria

O produto deve ser definido por seus comportamentos, não pela obrigação de permanecer em um framework específico. O GPT Researcher é uma dependência atual a avaliar e reaproveitar conforme sua utilidade; não é o produto final em si.

A documentação pública do projeto já descreve controles de abrangência, profundidade e concorrência. Também existe uma proposta pública de pesquisa adaptativa, identificada como proposta; isso não comprova que seu comportamento esteja disponível na versão instalada ou no caminho usado pela nossa integração. Referências: [configuração](https://docs.gptr.dev/docs/gpt-researcher/gptr/config), [Deep Research](https://docs.gptr.dev/docs/gpt-researcher/gptr/deep_research) e [proposta adaptativa](https://docs.gptr.dev/docs/proposals/adaptive-deep-research).

Uma avaliação da arquitetura precisa distinguir limitação do framework, limitação da versão instalada, configuração incorreta e problema na integração. O fato de uma execução ter falhado em cobertura não demonstra, sozinho, que a biblioteca inteira deva ser descartada.

Para o escopo deste produto, a direção recomendada é manter sob nosso controle o plano, o estado persistente, a matriz de cobertura, as rodadas adaptativas, o orçamento e a decisão de encerramento. Os conectores do Agent Reach, a qualificação das evidências, a auditoria e os testes existentes devem ser reaproveitados. A biblioteca pode continuar como componente encapsulado enquanto isso for útil e compatível com os contratos definidos.

Uma eventual migração deve ocorrer por etapas: identificar quais responsabilidades a biblioteca realmente executa na stack, avaliar sua adequação, substituir as partes que dificultam o produto e comparar a solução resultante com os mesmos casos de referência. A alternativa própria deve demonstrar cobertura, qualidade, rastreabilidade e controle operacional, incluindo regressões, tempo e consumo. A solução anterior deve permanecer disponível durante essa comparação.

Construir uma coordenação própria não exige reinventar motores de busca, navegadores, leitores de documentos ou APIs. Por outro lado, assumir essa camada cria responsabilidade por manutenção, recuperação de falhas, seleção de contexto, integração de provedores e testes. Não se presume que uma reescrita completa será automaticamente mais fácil ou melhor.

## 16. Critérios de aceitação do produto

| Cenário | Evidência de funcionamento esperada |
|---|---|
| Pedido de uma página, repositório ou vídeo | O Agent Reach resolve a operação individual, com origem e limites, sem iniciar uma pesquisa extensa. |
| YouTube com legendas do autor ou automáticas | Transcrição realmente obtida, com origem e alcance identificados; título não substitui fala. |
| YouTube sem transcrição ou com falha de acesso | Estado correto, limitação registrada e ausência de afirmações inventadas sobre a fala. |
| Consulta com vários alvos explícitos | Todos acompanhados; lacunas importantes impedem declarar cobertura total. |
| Descoberta aberta de alternativas | Novos candidatos encontrados; o conjunto não fica limitado às sementes iniciais ou a nomes codificados. |
| Divergência relevante entre fontes | Contradição investigada ou mantida como incerteza que afeta a conclusão. |
| Pesquisa acadêmica | Registro de qual conteúdo foi lido, identificação do trabalho e referências verificáveis. |
| Relatório quantitativo | Fórmulas e entradas preservadas; cálculos reproduzíveis e coerentes com as fontes. |
| Mudança de profundidade | Diferença observável de exploração, cobertura e aprofundamento, com limites registrados. |
| Amplitude e profundidade independentes | Uma pesquisa extensa de candidatos e uma investigação focada em mecanismos produzem estratégias diferentes, coerentes com os controles escolhidos. |
| Lacuna descoberta durante a pesquisa | A avaliação intermediária gera uma ação direcionada; o resultado resolve a lacuna com evidência ou mantém a insuficiência explícita. |
| Controle de rodadas | Limites respeitados, achados preservados entre ciclos e motivo de parada registrado sem confundir rodadas, tentativas e votos. |
| Execução longa interrompida | Retomada do trabalho preservado, sem perda geral nem duplicação silenciosa. |
| Bloqueio, erro de provedor ou limite de orçamento | Falha visível, impacto na cobertura e resultado final honesto. |
| Entrega final | Responde ao pedido, permite verificar as afirmações importantes e informa o que permanece incerto. |

A avaliação deve combinar testes offline, casos de regressão e pesquisas reais representativas. Os testes existentes, incluindo os 83 aprovados na rodada de auditoria, devem continuar preservados. Eles demonstram os casos que cobrem; não substituem a validação da qualidade geral de pesquisa.

## 17. Limites da promessa e fronteira do escopo

O objetivo é uma ferramenta confiável, abrangente e útil, com falhas detectáveis e tratadas. Não é possível garantir acesso permanente a qualquer site, ausência absoluta de erros ou uma classificação objetivamente definitiva dos “melhores” itens de todo o mundo.

O compromisso verificável é investigar de forma proporcional ao modo escolhido, justificar conclusões, reconhecer omissões importantes e permitir revisar as evidências. Uma investigação parcial pode ser útil, desde que seja apresentada como parcial.

Não fazem parte do escopo inicial: análise visual completa de vídeos, geração de transcrição a partir do áudio, integração obrigatória com todas as redes sociais, contratação de APIs pagas de pesquisa ou reconstrução da stack sem necessidade demonstrada.

O produto final será considerado alcançado quando Agent Reach e Deep Researcher cumprirem esses comportamentos em operações individuais e pesquisas reais variadas, dentro dos limites declarados. Qualquer mudança posterior nas restrições, fontes obrigatórias ou critérios de aceitação deve ser incorporada à modelagem, mantendo uma referência única para o trabalho.
