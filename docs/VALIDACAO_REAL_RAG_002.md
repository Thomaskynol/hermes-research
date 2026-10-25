# Validação real RAG_002 — continuação c-trat (runs 2–7)

Data: 2026-10-24/25. Mesmo ambiente e transporte da RAG_001, modelo
`opencode-go/muse-spark-1.3-contributor` (instrução do usuário; OpenRouter
segue 401 mesmo para `nvidia/nemotron-3.5-super-vl:free`, então o modelo
indicado para OpenRouter continua inutilizável — registrado, não contornado).

Pergunta: "Como o projeto gpt-researcher trata limitações de RAG adaptativo
(routing, iteração, filtragem de evidências, recursos)?" Plano `real-rag-003`
(2 critérios obrigatórios), `max_rounds=2`, `max_model_calls=14`.

## O que cada run revelou (todas honestas, nenhuma maquiadada)

- run2: `blocked` com 0 evidências — query github longa demais retornou 0 hits;
  plano corrigido para queries curtas (`gpt-researcher`, `adaptive retrieval
  augmented generation`).
- run3: bug real de integração — `native_transport` passava `token=` para
  `agent_reach.read_repo`, que não aceita o parâmetro; todas as leituras de
  repo falhavam. Corrigido em `native_transport.py` + teste de contrato
  atualizado (comportamento correto, não invariante enfraquecido).
- run4: sem o bug, mas host sem `httpx` — `read_repo` caía para erro.
  Instalado `httpx` no host via pip `--user` (nota de ambiente, não do produto).
- run5: 10 evidências (4 repos + 6 arXiv), mas assessor marcou `insufficient`:
  o excerto head-only de 1200 chars pegava só badges do README. Melhoria de
  produto: `_substantive_excerpt` ignora linhas de boilerplate
  (badges/imagens/tags/headers vazios) antes do corte, com registro em `cuts`
  + 3 testes novos.
- run6/run7 (reproduzível): c-trat `partial` com substância (planner/execution,
  deep research recursivo, smart context filtering, runs paralelos — tudo do
  README oficial, refs verificáveis); c-evid `insufficient` honesto (README é
  marketing/arquitetura, sem código/config 0.16.0). Contadores 16/10/10/10/6/7.
  Verificação overall `partial`. STOP rounds, parcial identificável.

## Melhoria adicional validada

- `agent_reach._direct_read`: fallback stdlib (urllib, 300 KB, HTTP observado)
  quando a cascata local está indisponível. `read_page` em
  `docs.gptr.dev/.../deep_research` real: obtained/usable, 45.161 chars,
  HTTP 200. Sem dependência nova, sem serviço pago. +2 testes offline.

## Pendente (exige o que não existe no ambiente)

- c-evid `covered`: precisaria de código/config versionado do projeto
  (leitura de arquivos do repo além do README) ou busca web funcional
  (SearXNG/vast seguem fora do ar). Declarado como lacuna, não fingido.

Artefatos: `/tmp/hermes-real-run/run{2,3,4,5,6,7}/` (o run7 é o estado final
estável). Reprodução: mesmo comando da RAG_001 com `--coverage-plan
/tmp/plan_rag003.json --max-rounds 2` e
`DEPTH_OVERRIDES_JSON='{"max_model_calls":14}'`.
