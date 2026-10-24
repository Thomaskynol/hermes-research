# Matriz de requisitos — primeira versão completa (modelagem v1.1)

Fonte normativa: `docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` (SHA-256
`3487df6f...`). Esta matriz orienta a execução e a revisão final. Estados:

- **IMPL** — implementado e coberto por teste offline no caminho integrado.
- **REAL** — validado com rede/modelo reais em ambiente isolado.
- **PARCIAL** — implementado com limitação declarada (ver coluna Evidência).
- **PENDENTE** — requisito obrigatório ainda não atendido.
- **BLOQUEADO** — impedido por ambiente externo (registrado, não fingido).

Atualizada em 2026-10-24. Evidências apontam para teste/comando/doc; nenhum
estado REAL é atribuído sem execução registrada.

## §2 Duas ferramentas, uma base

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R2.1 | Agent Reach: busca com resultados identificados | `agent_reach.py:search` | `tests/test_agent_reach.py` | IMPL |
| R2.2 | Agent Reach: abrir/extrair página ou documento | `agent_reach.py:read_page` (reusa `vast_local_retriever` cascade) | idem | IMPL |
| R2.3 | Agent Reach: vídeo — título/descrição/transcrição disponível | `agent_reach.py:read_video` (reusa `youtube_transcript`) | idem | IMPL |
| R2.4 | Agent Reach: repositório e documentos relevantes | `agent_reach.py:read_repo` (reusa `repo_readme` + API GitHub) | idem | IMPL |
| R2.5 | Agent Reach: trabalhos acadêmicos (metadados/resumo/texto) | `academic_search.py` (OpenAlex + arXiv) | idem | IMPL |
| R2.6 | Operação individual não inicia pesquisa extensa | `agent_reach.py` não importa coordenador/planner | teste de import/efeito | IMPL |
| R2.7 | Retorno com conteúdo, origem, limitações e estado | contrato `ReachResult` | teste de contrato | IMPL |
| R2.8 | Base compartilhada entre Agent Reach e Deep Researcher | conectores reusados; `fetch_transport` aceita `ReachResult` | teste de integração | IMPL |

## §3 Princípios e limites

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R3.1 | Busca web por infraestrutura própria (SearXNG) | `vast_local_retriever` | serviços locais fora nesta sessão | BLOQUEADO |
| R3.2 | Extração/armazenamento/cálculo locais | `vast_local_retriever`, `quantitative.py` | testes offline | IMPL |
| R3.3 | Modelo em nuvem configurável + registro do usado | `build_adaptive_transports`, `_validate_runtime_config` | `docs/LIBRARY_CONTRACTS_85dac79.md` | IMPL |
| R3.4 | Sem APIs comerciais de pesquisa / fallback pago | nenhum cliente Exa/Tavily; canais declarados | grep + teste de canais | IMPL |
| R3.5 | APIs oficiais gratuitas permitidas (GitHub, acadêmicas) | `academic_search.py`, GitHub REST | teste + validação real | IMPL |
| R3.6 | Não integrar catálogo OpenRouter | nenhuma chamada a `/models` no código de produto | grep | IMPL |
| R3.7 | Sem serviços pagos de extração/transcrição/embedding | apenas cascata local + legendas YouTube | grep | IMPL |
| R3.8 | Embeddings locais preservados | config existente intocada | `_validate_runtime_config` | IMPL |

## §4 Fontes e alcance

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R4.1 | Web/Google: descobrir e ler; motores identificados | canal `web` + `search` com `engine` | teste de canal | IMPL |
| R4.2 | YouTube: descobrir + transcrição autor/automática | `youtube_transcript` + `read_video` | teste + `fixtures/transcript_replay.json` | IMPL |
| R4.3 | GitHub: README, licença, releases, arquivos | `read_repo` + `repo_files` | teste | IMPL |
| R4.4 | Acadêmico: descobrir, metadados, resumo, texto quando acessível | `academic_search.py` | teste | IMPL |
| R4.5 | Honestidade de alcance: canal que falhou aparece no registro | `state["channels"]`, `notes` | teste de canal indisponível | IMPL |

## §5 YouTube

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R5.1 | Legendas autor e automáticas | `youtube_transcript.fetch_transcript` | replay fixture | IMPL |
| R5.2 | Registrar idioma, origem, data, timestamps | `TranscriptResult` + `read_video` | teste | IMPL |
| R5.3 | Classificar completo/parcial/insuficiente | `transcript_status` | teste | IMPL |
| R5.4 | Só material obtido sustenta fala | prompt de evidência + qualificação | teste | IMPL |
| R5.5 | Sem transcrição: fora das evidências de fala, motivo registrado | `read_video` retorna `unavailable` | teste | IMPL |
| R5.6 | Distinguir ausente de falha de acesso | `reason` (`absent` vs `blocked`) | teste | IMPL |
| R5.7 | Sem ASR nem análise visual | nenhuma dependência de áudio/visão | grep | IMPL |

## §6 Modos e controles independentes

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R6.1 | Perfil de esforço altera orçamentos | `depth_profiles.PROFILES` + `run_budget` | teste de perfis | IMPL |
| R6.2 | Amplitude independente (candidatos/perspectivas) | `DEEP_RESEARCH_BREADTH` + `max_ops_per_round` | teste de estratégia | IMPL |
| R6.3 | Profundidade independente (aprofundamento) | `DEEP_RESEARCH_DEPTH` + gap policy | teste de estratégia | IMPL |
| R6.4 | Rodadas independentes e com motivo | `max_rounds`, `stop.reason` | `test_adaptive_research` | IMPL |
| R6.5 | Concorrência efetiva (não só registrada) | `_execute_ops` com pool e orçamento compartilhado | teste de concorrência | PENDENTE |
| R6.6 | Limites independentes: consultas, docs, modelo, tokens, tempo, tentativas | `run_budget` + `max_model_calls` | testes | PARCIAL (tokens não medidos) |
| R6.7 | Reserva para síntese/auditoria/entrega | `_finalize` + reserva | `test_review_85dac79` S01 | IMPL |
| R6.8 | Config efetiva registrada; níveis altos não comprovam alcance | `resolved` no estado + relatório | teste | IMPL |

## §7 Contadores

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R7.1 | Descobertas | `state["counters"]["discovered"]` | teste | PENDENTE |
| R7.2 | Obtidas | idem `obtained` | teste | PENDENTE |
| R7.3 | Utilizáveis (pós-qualificação) | idem `usable` | teste | PENDENTE |
| R7.4 | Analisadas (com trecho/alcance) | idem `analyzed` | teste | PENDENTE |
| R7.5 | Utilizadas na síntese | idem `used_in_synthesis` | teste | PENDENTE |
| R7.6 | Citadas | idem `cited` | teste | PENDENTE |
| R7.7 | Metadados/vídeo sem transcrição não inflam lidos | qualificação por tipo | teste | IMPL |
| R7.8 | Duplicatas/republicações reconhecidas; versões identificadas | `_content_hash`, `versions` | testes R08/R10 | IMPL |
| R7.9 | URL ≠ independência | `classify_hit` (`confirmed` vs `duplicate`) | R10 | IMPL |

## §8 Fluxo

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R8.1 | Compreender pedido (pergunta, critérios, alvos, restrições) | `adaptive_planner.generate_plan` | teste | IMPL |
| R8.2 | Plano verificável por entidade e critério | `coverage_ledger` | 29 testes | IMPL |
| R8.3 | Descoberta não limitada às sementes | `discovery.open` + `propose_entity` | S03 | IMPL |
| R8.4 | Explorar amplamente (variações, idiomas, fontes primárias) | `select_ops` + planner | teste | IMPL |
| R8.5 | Obter/ler com qualificação e procedência | `_coerce_payload` + `incorporate` | S04/S05 | IMPL |
| R8.6 | Lacunas orientam novas operações | `prioritize_gaps` + `select_ops` | teste | IMPL |
| R8.7 | Cálculos locais reproduzíveis | `quantitative.py` | teste | PENDENTE |
| R8.8 | Verificação antes da entrega | `verification_report.py` | teste | PENDENTE |

## §9 Ciclo adaptativo

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R9.1 | Estados separados de cobertura | `coverage_ledger` (6 estados) | teste | IMPL |
| R9.2 | Revisão do material a cada rodada (não só no fim) | `_assess_round` | teste | IMPL |
| R9.3 | Lacuna com pergunta/importância/material/tentativas/próxima ação | `state["gaps"]` | teste | IMPL |
| R9.4 | Distinguir dado novo, confirmação, duplicata, repetição | `classify_hit` | R08/R10 | IMPL |
| R9.5 | Não repetir consulta idêntica sem resolução | `queries_tried` | teste | IMPL |
| R9.6 | Encerramento com motivo explícito | `stop.reason` + `rounds` | teste | IMPL |
| R9.7 | Saturação não declara completude com alvo pendente | `decide_stop` + required | R02 | IMPL |
| R9.8 | Parcial identificável (ex.: 6 plugins, só Daytona) | `partial` + relatório | R02 | IMPL |

## §10 Evidências e rastreabilidade

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R10.1 | Origem, ID, URL, data, versão, bruto e utilizável | `state["evidence"]` | teste | IMPL |
| R10.2 | Hashes de integridade | `_content_hash` | teste | IMPL |
| R10.3 | Trechos distintos da mesma URL preservados | `versions`/`excerpts` | teste | IMPL |
| R10.4 | Cache não substitui corpus silenciosamente | reconciliação | R08 | IMPL |
| R10.5 | Material efetivamente fornecido à escrita/auditoria | `last_selection` + `included_urls` | S05/S07 | IMPL |
| R10.6 | Conteúdo externo é evidência, não instrução | prompt de evidência | teste | IMPL |

## §11 Qualidade da evidência

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R11.1 | Fonte adequada ao tipo de afirmação | qualificação + assessor | teste | IMPL |
| R11.2 | Fabricante vs independente vs usuário vs inferência | `origin` nas avaliações | teste | IMPL |
| R11.3 | Versões/datas reconciliam contradição aparente | assessor + relatório | teste | IMPL |
| R11.4 | Parcial/HTML vazio/erro/metadado/texto distintos | `_coerce_payload` | S04 | IMPL |
| R11.5 | Divergências explicadas e com efeito na conclusão | `contradictory` + relatório | teste | IMPL |
| R11.6 | Acadêmico: metadados vs resumo vs texto completo | `academic_search.read_level` | teste | IMPL |
| R11.7 | Não verificado permanece desconhecido | relatório `uncertainties` | teste | PENDENTE |

## §12 Auditoria

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R12.1 | Verificação de execução | `verification_report.execution` | teste | PENDENTE |
| R12.2 | Verificação de cobertura da pergunta | `verification_report.question` | teste | PENDENTE |
| R12.3 | Verificação de cobertura da revisão | `verification_report.review` | teste | PENDENTE |
| R12.4 | Verificação de sustentação das conclusões | `verification_report.support` | teste | PENDENTE |
| R12.5 | Quórum/empates/inválidas/falhas/limites preservados | `semantic_review` | S01/S02/S08 | IMPL |
| R12.6 | Lotes com parte não revisada explícita | `semantic_review` + relatório | S01 | IMPL |
| R12.7 | Sem lista fixa de nomes de pacotes | planner/assessor genéricos | teste | IMPL |

## §13 Relatório

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R13.1 | Português, Markdown, resposta direta | `report_renderer.py` | teste | PENDENTE |
| R13.2 | Data/escopo/critérios/método | idem | teste | PENDENTE |
| R13.3 | Achados por critério | idem | teste | PENDENTE |
| R13.4 | Comparações/cálculos/recomendações | idem + `quantitative.py` | teste | PENDENTE |
| R13.5 | Referências próximas das afirmações | idem | teste | PENDENTE |
| R13.6 | Limitações/contradições/incertezas/não investigado | idem | teste | PENDENTE |
| R13.7 | Conclusão + próximos passos | idem | teste | PENDENTE |
| R13.8 | Fontes/anexos rastreáveis | idem + artefatos | teste | PENDENTE |
| R13.9 | Tamanho proporcional à complexidade | idem | teste | PENDENTE |

## §14 Execuções longas e controle

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R14.1 | run_id + estado persistente | `adaptive_state` | teste | IMPL |
| R14.2 | Progresso observável | `run_control.status` | teste | PENDENTE |
| R14.3 | Pausa/retomada/cancelamento | `run_control` + CLI | teste | PENDENTE |
| R14.4 | Registro de config/código/entradas/modelos/artefatos | `run_manifest` | teste | PENDENTE |
| R14.5 | Simulado ≠ real identificado | `environment` no manifesto | teste | PENDENTE |
| R14.6 | Interrupção preserva obtido; retomada não duplica | `_reconcile_resume` | R08/S06 | IMPL |
| R14.7 | Tentativas limitadas com espera | retry policy | teste | IMPL |
| R14.8 | Consumo não medido = desconhecido | `unknown` explícito | teste | PARCIAL |

## §15 Arquitetura

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R15.1 | Conectores / planejador / coordenador / evidências / cálculo / síntese / verificação separados | módulos próprios | inspeção + testes | IMPL |
| R15.2 | GPT Researcher encapsulado e avaliado pelo que a versão oferece | `build_adaptive_transports` | `LIBRARY_CONTRACTS` | IMPL |

## §16 Aceitação

| Cenário | Evidência | Estado |
|---|---|---|
| Página/repo/vídeo individual sem pesquisa extensa | `test_agent_reach` | IMPL |
| YouTube com legendas (origem/alcance) | replay + real | IMPL |
| YouTube sem transcrição/falha | teste de estado | IMPL |
| Vários alvos explícitos | cobertura por par | IMPL |
| Descoberta aberta | S03 + real | IMPL |
| Divergência entre fontes | teste de contradição | IMPL |
| Pesquisa acadêmica | `academic_search` + real | IMPL |
| Relatório quantitativo | `quantitative.py` | PENDENTE |
| Mudança de profundidade observável | teste de perfis | IMPL |
| Amplitude × profundidade independentes | teste de estratégia | IMPL |
| Lacuna → ação direcionada | demo S03/entry | IMPL |
| Controle de rodadas | teste | IMPL |
| Execução longa interrompida | resume + control | PARCIAL |
| Bloqueio/erro/limite → parcial honesto | R11/R12 | IMPL |
| Entrega final verificável | relatório + verificação | PENDENTE |
