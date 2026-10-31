# Matriz de requisitos — primeira versão completa (modelagem v1.1)

Fonte normativa: `docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` (SHA-256
`3487df6f...`). Esta matriz orienta a execução e a revisão final. Estados:

- **IMPL** — implementado e coberto por teste offline no caminho integrado.
- **REAL** — validado com rede/modelo reais em ambiente isolado.
- **PARCIAL** — implementado com limitação declarada (ver coluna Evidência).
- **PENDENTE** — requisito obrigatório ainda não atendido.
- **BLOQUEADO** — impedido por ambiente externo (registrado, não fingido).

Atualizada em 2026-10-31 (accept22; RA8 segue PENDENTE; produto
congelado, só docs + 1 teste estrito desde o run). Evidências apontam para teste/comando/doc; nenhum
estado REAL é atribuído sem execução registrada. Promoções IMPL→REAL pela
validação RAG_001 estão em "Validação real RAG_001 — promoções"; as da
reabertura do aceite estão em "Reabertura do aceite — 2026-10-29"; a
entrega atual (accept21/accept22) está em "Entrega atual — 2026-10-31".

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
| R6.5 | Concorrência efetiva (não só registrada) | `_execute_ops_parallel` (3 fases, teto no thread principal) | `test_product_core.ConcurrencyTest` (4x mais rápido, teto respeitado, ordem preservada) | IMPL |
| R6.6 | Limites independentes: consultas, docs, modelo, tokens, tempo, tentativas | `run_budget` + `max_model_calls` | testes | PARCIAL (tokens não medidos) |
| R6.7 | Reserva para síntese/auditoria/entrega | `_finalize` + reserva | `test_review_85dac79` S01 | IMPL |
| R6.8 | Config efetiva registrada; níveis altos não comprovam alcance | `resolved` no estado + relatório | teste | IMPL |

## §7 Contadores

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R7.1 | Descobertas | `research_counters.record_discovered` (dedupe por URL normalizada) | `test_product_core.CountersTest` (6 estágios distinguíveis) | IMPL |
| R7.2 | Obtidas | `record_obtained` (só texto real; metadado/vídeo sem fala excluídos) | idem | IMPL |
| R7.3 | Utilizáveis (pós-qualificação) | `record_usable` (usable/partial + usable_text) | idem | IMPL |
| R7.4 | Analisadas (com trecho/alcance) | `record_analyzed` via `assess.last_selection` (só docs obtidos) | idem | IMPL |
| R7.5 | Utilizadas na síntese | `record_used_in_synthesis` via `included_urls` do writer | idem | IMPL |
| R7.6 | Citadas | `record_cited_urls` via `render_report.last_cited_urls` (só corpo entregue) | idem | IMPL |
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
| R8.7 | Cálculos locais reproduzíveis | `quantitative.py` (fórmulas fechadas, entradas/unidades/hipóteses registradas) | `test_product_core.QuantitativeTest` | IMPL |
| R8.8 | Verificação antes da entrega | `verification_report.py` (4 dimensões + agregado; falha honesta, nunca aprovação forçada) | `test_product_core` + `verification.json` no run | IMPL |

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
| R11.7 | Não verificado permanece desconhecido | relatório `uncertainties` + suporte rejeita citação fora do corpus | `test_product_core.ReportTest` | IMPL |

## §12 Auditoria

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R12.1 | Verificação de execução | `verification_report.verify_execution` (orçamento, falhas por motivo) | `test_product_core` | IMPL |
| R12.2 | Verificação de cobertura da pergunta | `verification_report.verify_question` (semântica nunca promove cobertura) | `test_product_core` | IMPL |
| R12.3 | Verificação de cobertura da revisão | `verification_report.verify_review` (extração vs auditoria, omissões explícitas) | `test_product_core` | IMPL |
| R12.4 | Verificação de sustentação das conclusões | `verification_report.verify_support` (citação fora do corpus reprova) | `test_product_core` | IMPL |
| R12.5 | Quórum/empates/inválidas/falhas/limites preservados | `semantic_review` | S01/S02/S08 | IMPL |
| R12.6 | Lotes com parte não revisada explícita | `semantic_review` + relatório | S01 | IMPL |
| R12.7 | Sem lista fixa de nomes de pacotes | planner/assessor genéricos | teste | IMPL |

## §13 Relatório

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R13.1 | Português, Markdown, resposta direta | `report_renderer.py` (9 seções PT-BR) | `test_product_core.ReportTest` | IMPL |
| R13.2 | Data/escopo/critérios/método | idem §2 | idem | IMPL |
| R13.3 | Achados por critério | idem §3 (estado por par + refs) | idem | IMPL |
| R13.4 | Comparações/cálculos/recomendações | idem §4 + bloco reproduzível | idem | IMPL |
| R13.5 | Referências próximas das afirmações | idem (só corpus; fora removida e registrada) | idem | IMPL |
| R13.6 | Limitações/contradições/incertezas/não investigado | idem §5 | idem | IMPL |
| R13.7 | Conclusão + próximos passos | idem §6 | idem | IMPL |
| R13.8 | Fontes/anexos rastreáveis | idem §7–§8 + report.md/result.json/state.json | idem | IMPL |
| R13.9 | Tamanho proporcional à complexidade | idem (light < deep) | `test_light_is_shorter_than_deep` | IMPL |

## §14 Execuções longas e controle

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| R14.1 | run_id + estado persistente | `adaptive_state` | teste | IMPL |
| R14.2 | Progresso observável | `run_control.status.json` (fase/rodada/contadores/elapsed) | `test_run_control` + `test_control_integration` + status.json ao vivo (hermdemo5/6/7, `run_id` real) | REAL |
| R14.3 | Pausa/retomada/cancelamento | `run_control` + hooks no coordenador + `--resume` | `test_control_integration` + demo ao vivo hermdemo6 (paused→resume→rounds) e hermdemo7 (cancelled), guarda runs-never-mix (exit 2) | REAL |
| R14.4 | Registro de config/código/entradas/modelos/artefatos | `run_manifest.write_manifest` (hashes, artefatos, modelos sem chave) | `test_control_integration.ManifestTest` | IMPL |
| R14.5 | Simulado ≠ real identificado | `simulated: bool` obrigatório (erro se ausente) | idem | IMPL |
| R14.6 | Interrupção preserva obtido; retomada não duplica | `_reconcile_resume` | R08/S06 + resume hermdemo6 (0→4 rounds, sem re-obtenção) | REAL |
| R14.7 | Tentativas limitadas com espera | retry policy | teste | IMPL |
| R14.8 | Consumo não medido = desconhecido | `unknown` explícito | teste | PARCIAL |

## Validação real RAG_001 — promoções IMPL→REAL

Execução registrada em `docs/VALIDACAO_REAL_RAG_001.md` (artefatos em
`/tmp/hermes-real-run/run/`, fora do Git). Linhas promovidas:

| ID | Evidência real |
|---|---|
| R2.2, R2.5 | `read_page`/`academic_search` reais (arXiv texto integral via HTTP) |
| R2.3 | `read_video` com estado `blocked` honesto (sem cookies; sem fala inventada) |
| R2.4 | `read_repo` real (README parcial, stars, licença, release) |
| R2.7 | contrato `ReachResult` com origem/limites/estado no caminho real |
| R3.5 | OpenAlex + arXiv + GitHub oficiais gratuitos, sem chave |
| R4.3, R4.4, R4.5 | idem R2.4/R2.5; canal web falho registrado (`retriever_unavailable`) |
| R6.4 | `stop.reason=rounds`, parcial identificável, 2 rodadas registradas |
| R7.1–R7.6 | contadores observados 8/6/6/6/6/6 em `counters.json` |
| R8.5, R8.6, R9.2, R9.6, R9.8 | coleta→avaliação→parada parcial honesta (`result.json:rounds`) |
| R10.1, R10.2 | `state.json` com evidências, hashes, datas de obtenção |
| R11.6, R11.7 | `read_level` por trabalho; incertezas declaradas no relatório |
| R12.1–R12.4 | `verification.json` (execution=ok, question=partial, review+support) |
| R13.1–R13.3, R13.5–R13.8 | `report.md` PT-BR 9 seções, refs do corpus, lacunas explícitas |
| R14.1, R14.4, R14.5 | `state.json` + `manifest.json` (`simulated=false`, modelo sem chave) |
| R9.6 (ext.) | sem regressão de cobertura sem evidência nova (ledger reflete o merge) | uvrun6 (0.2 mantido no round sem ganho) + `test_monotonic_coverage` | REAL |
| R8.5, R8.6, R9.2 | coleta→avaliação→nova coleta por lacuna no caminho real | acadrun5 (10 ev, 1 round certeiro) | REAL |
| R9.6, R9.8 | STOP `criteria_ok` 1.0 + parcial identificável quando há lacuna | acadrun5 (`stop.reason=criteria_ok`); hermdemo6/7 (`paused`/`cancelled`) | REAL |
| R12.1–R12.4 | 4 dimensões ao vivo: review ACCEPTED (3 claims, 9 blocos), support estrito | acadrun5 `verification.json` (overall=failed por rigor do support, dimensões inspecionáveis) | REAL |
| R13.1–R13.3, R13.5–R13.8 | relatório responde critérios com substância + declara o não-respondido | acadrun5 `report.md` (c-fail com números; gpt-researcher em GAP-1 honesto) | REAL |
| R14.2, R14.3, R14.6 | acompanhamento/pausa/retomada/cancel ao vivo via arquivos | `docs/HERMES_E2E_DEMO.md` (hermdemo5/6/7) | REAL |
| §16 | pesquisa acadêmica REAL; bloqueio/erro/limite→parcial honesto REAL |

Seguem IMPL (offline): R2.1 (gateway local fora do ar), R6.5, R8.7, R10.3–R10.6,
R12.5–R12.7, R13.4/R13.9 (parcialmente exercidos), R14.2/R14.3/R14.6/R14.7.
Seguem BLOQUEADO: R3.1. Seguem PARCIAL: R6.6, R14.8 (tokens unknown).

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
| Pesquisa acadêmica | `academic_search` + real RAG_001 | REAL |
| Relatório quantitativo (fórmulas/entradas/unidades) | `quantitative.py` + §4 do relatório | IMPL |
| Mudança de profundidade observável | teste de perfis | IMPL |
| Amplitude × profundidade independentes | teste de estratégia | IMPL |
| Lacuna → ação direcionada | demo S03/entry | IMPL |
| Controle de rodadas | teste | IMPL |
| Execução longa interrompida | resume + pausa/cancel via controle | IMPL |
| Bloqueio/erro/limite → parcial honesto | R11/R12 + real RAG_001 | REAL |
| Entrega final verificável | report.md + verification.json + manifest.json | IMPL |

## Reabertura do aceite — 2026-10-29

Pergunta de aceite e histórico completo: `docs/ACEITE_V1_RESULTADO.md`.
Run final analisado: `accept11` (`/tmp/hermes-real-run/accept11/adaptive_accept11/`).

| ID | Requisito | Implementação | Evidência | Estado |
|---|---|---|---|---|
| RA1 | Planejamento separa alvos de investigação de obrigações metodológicas | `per_candidate` no planner; entidades-placeholder proibidas; `initial_paths` são queries web, nunca caminhos locais | `tests/test_plan_placeholders.py`, `tests/test_discovery_cells.py`, plano do accept11 (12 critérios, 5 per_candidate) | REAL |
| RA2 | Nome encontrado em lista vira candidato real com fonte própria | `propose_entity` + remap de id + `source_url` validada + `candidate_target` + gate de menção na fonte | accept11: 5 exigidos, todos com fonte no corpus ([2],[6],[4],[5],[3]) | REAL |
| RA3 | Qualificação de contexto: lixo, espelhos, duplicatas, captura vs análise | snippet gate, dedupe por URL normalizada, alcance lido por fonte no relatório | accept15: 55 docs obtidos, contadores obtained/usable/analyzed/cited separados; lixo analisado não citado. Residual 2026-10-30: lixo com vocabulário compartilhado passa; hits sem snippet lidos às cegas | REAL |
| RA4 | Consistência entre relatório e registros (citações, fontes, escopo lido, rodadas, consumo) | writer prioriza fontes citadas; tabela `cited` usa o próprio render; numeração `[n]→URL` persistida no artefato (E2); 5ª dimensão `support` audita cada frase citada (S2) | accept15: `verification.json` support `failed` honesto com 5 `unsupported` reais sinalizados; diagnose 28/5/57. Residual 2026-10-30 (accept16): 44/2/57 — 2 unsupported são cites fracos de menção em lista (overlap 0,12–0,20) | REAL |
| RA5 | Entrada Hermes isolada demonstrada ponta a ponta | CLI única + `--control-dir` + `run_control.py status` + pause/resume | accept11 status ao vivo + accept12: pause limpo entre rodadas e `--resume` com contadores preservados (§10) | REAL |
| RA6 | Generalização em outro assunto | mesmos mecanismos, outra pergunta | genus1 (httpx×requests×aiohttp): 10/16=0.625 partial, SATURATION, support `ok` 37/37 + acadrun5 FAIR-RAG (§5) | REAL |
| RA7 | Relatório responde à pergunta: 5 plugins, comparação, combinações/sobreposições, documentado vs inferência | `report_renderer.py` + writer sobre corpus real | `accept11/report.md` §1, §3 e "Combinações e sobreposições" | REAL |
| RA8 | Cobertura completa da pergunta de aceite | denominador estável (células obrigatórias do plano final, §M6); sem redução de requisitos | accept16 (2026-10-30): 11/51 parcial; accept22 (2026-10-31): 11/54 = 0.2037 parcial, verification overall `failed` honesto (5 URLs nuas + 3 inferências de combinação + 17 LACUNA sem overlap), denominador nunca reduzido | PENDENTE (cobertura parcial persistente, retrieval-bound; mecanismos validados, denominador nunca reduzido) |

Pendências declaradas: gate de citação literal por avaliação (justificativa do
assessor não é verificada contra o excerto); conector de inspeção local;
tokens/custos desconhecidos; canal web primário (gateway vast) fora.

## Reabertura do aceite — resultado final 2026-10-30

Run final: `accept16` (mecanismos até `d0ba933` + M7/M8/M9, `34c760c`).
Série outro assunto genus2–genus8 (Django×FastAPI×Flask, medium,
max-rounds 3). Calibração Lane B (corpus congelado accept15,
`tools/run_calibration.py`, 25 casos a–f). Detalhes em
`docs/ACEITE_V1_RESULTADO.md` §§11–15. HEAD `c83b892`; 411 testes OK
(9 skipped).

| ID | Requisito / mecanismo | Evidência | Estado |
|---|---|---|---|
| M7 | N/A por célula só vale p/ per_candidate de entidade discovered+required (excluído do denominador, com `na_cells`) | `34c760c`; accept16: na=4 com escopo (ex.: marketplace N/A p/ planejamento — instalador) | REAL |
| M8 | Substituição só p/ MAIS evidência, registrada em `plan_versions`, velha mantida no relatório | `34c760c`; accept16: zero substituições disparadas | REAL |
| M9 | Métrica de leitura (excerptado vs coletado; saturação ≠ análise exaurida) | accept16: 51.707/5.927.450 chars (~0,9%) | REAL |
| CAL | Calibração Lane B do validador | 25 casos a–f: erros de validador 12→1, ok 8→18, modelo-julgamento 1→2, contexto 4→4 | REAL (residuais: gap lexical PT/EN, b2 `known_limitation`, taxa sem-citação) |
| FIXE | Gaps de critério per_candidate expandem em sub-gaps por entidade (`select_ops`) | `5304231` (completa `1c68e3c`, no-op isolado); genus7: queries Flask-led + docs oficiais Flask no corpus | REAL |
| RR | Round-robin interleave entre critérios nos slots de op | `c83b892`; genus8: spread intra-round [c1,c2,c3], total 4/26 idêntico | REAL (gargalo vinculante é retrieval, não alocação — stop) |
| GEN | Série genus2–8; variância single-run dominada por retrieval | genus2 1/10 (expôs bug per_candidate, fix `b861763`) → genus3–8: 7,7,3,7,4,4 /26 | REAL (±0,1 cobertura entre configs idênticas) |

## Entrega atual — runs accept21/accept22 (2026-10-31)

HEAD de execução congelado: `776af89` (produto == `a704463`; hashes
pré/pós-run reconferidos, sem edição durante o run:
`adaptive_coordinator.py 9b3a577a…`, `verification_report.py a3ee1baa…`,
`native_transport.py 5c78c526…`). HEAD atual `534c946` = **só docs**
(+ 1 teste estrito); produto intacto — hashes conferem com
`hashes.frozen` do accept22.

| Run | Config | Cobertura | Verification | RA8 |
|---|---|---|---|---|
| accept21 | pergunta do aceite, medium/max-rounds-3, contexto 2.1.4, vast UP + SearXNG DOWN, EXIT=0, 343s | 0/15 + 0 N/A (funil YouTube sem transcrição, 0 entidades) | overall `partial` (15 frases LACUNA com citação fora do corpus ⇒ só `partial`; leniência residual vs accept19) | PENDENTE |
| accept22 | idem, vast DOWN + SearXNG DOWN, EXIT=0, 658s | 11/54 + 0 N/A (ok 10, partial_legit 11, missing 16, selection_context 16, synthesis_unsupported 1) | overall `failed` **honesto** (5 URLs nuas fora do corpus + 3 inferências de combinação reprovadas [12,13,14] + 17 LACUNA sem overlap; métodos de acordo) | PENDENTE |

Detalhes em `docs/CONTINUIDADE.md` (§§ Resultado accept21/accept22) e
evidências em `/home/thomaskyn/hermes-runs/accept21|22/` (fora do Git).

## Escopo: o que é REAL vs o que segue PENDENTE (limitações — sem fechar aceite)

REAL = validado em run real isolado (RAG_001/accept15, genus1/acadrun5,
hermdemo5–7, accept22 parcial). PENDENTE = sem validação em run real;
**não fechar o aceite sobre estes itens** (`docs/ACEITE_V1.md`, Limites):

1. Gateway vast local (`127.0.0.1:8001`) no ar durante run real
   (accept21 subiu on-demand e desligou; accept22 rodou DOWN confirmado).
2. Perfil deep 10h (só medium/max-rounds-3 exercitado).
3. `conduct_research` ponta a ponta da biblioteca (só CLI exercitada).
4. Pausa no meio de chamada ao modelo (limite conhecido: pausa só vale
   entre rounds; hermdemo6 validou pause/resume entre rounds).
5. Multiusuário.

Riscos amarelos (limitações registradas, **sem refatorar** — reavaliar
só se teste provar bug crítico; detalhe em `docs/CONTINUIDADE.md`):

- janela legado `u>start` (`adaptive_coordinator.py:473`, caminho sem
  grupos; caminho B4 usa dedupe estrito);
- ranking low (`_rank_unfetched`: contagem de substrings, empate mantém
  ordem original — sem ranking semântico);
- nota duplicada (`select_ops`: nota `pool reserve:` repetida por round
  p/ mesmo alvo — cosmético, sem efeito lógico);
- single-hit transcrição (`_needs_diversity`: 1 hit com marcador
  suprime a mistura por diversidade da página);
- versão major nua (`_text_versions`: regex só enxerga `x.y`/`Vn`;
  "versão 2" isolada é invisível ao gate);
- LACUNA overlap 0 (citação in-corpus sem overlap ⇒ unsupported;
  17 casos no accept22, rigor correto, volume residual);
- B5 convergência (ponderação `sentence_support` + `_selection_window`:
  convergência entre rounds provada só em unit, sem alvo em run real).
