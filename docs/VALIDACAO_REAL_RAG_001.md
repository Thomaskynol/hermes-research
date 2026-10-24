# Validação real RAG_001 — pesquisa ponta a ponta com rede e modelo reais

Data: 2026-10-24. Ambiente: host (Python 3.14.6), transporte nativo
(`--transport native --model-transport opencode`), modelo
`opencode/glm-5.3-flash-free` via CLI `opencode run --standalone --format json`
(7 chamadas, 2 retries, `max_calls=8`). Simulado: não
(`manifest.json: simulated=false`).

Pergunta: "Quais limitações de RAG adaptativo aparecem na literatura recente
e como o projeto gpt-researcher as trata?" Perfil light, `max_rounds=1`,
canais academic + github + web.

## O que funcionou de verdade

- Busca acadêmica real: OpenAlex + arXiv retornaram 8 trabalhos descobertos.
- Leitura real de 6 arXiv (resumo + fatia de texto integral obtida via HTTP).
- `read_repo` real do `assafelovic/gpt-researcher` (README parcial/metadata,
  stars, licença, release citados no relatório com honestidade de alcance).
- Contadores observados 8/6/6/6/6/6 (descobertas/obtidas/utilizáveis/
  analisadas/usadas-na-síntese/citadas), todos dedupados por URL normalizada.
- Assessor e escritor reais via modelo: 3 critérios avaliados, relatório
  `report.md` (14,9 KB, PT-BR, 9 seções) com refs próximas às afirmações,
  limitações declaradas e conclusão proporcional (`partial`, proporção 0,25).
- Quatro verificações executadas: execution=ok, question=partial,
  review e support registradas em `verification.json` (overall partial).
- Manifesto com config, hashes de artefatos, modelo (sem chave),
  `simulated=false`.

## Limites honestos observados

- Canal github para a pergunta: `nogain` (busca sem retorno útil); canal web:
  `failed` (`retriever_unavailable` — SearXNG/vast fora do ar), registrado no
  relatório, nunca fingido.
- c-trat (como o gpt-researcher trata cada limitação): `blocked` — sem
  evidência no corpus; relatório declara a lacuna em vez de inventar.
- Excertos arXiv predominantemente títulos/índices; relatório qualifica as
  afirmações como inferência estrutural, não limitação citável.
- Modelo: apenas `glm-5.3-flash-free` respondeu (quota free esgotada p/
  lightning/beam/flint/mimo/deepseek — 429); OpenRouter 401, Zen HTTP
  bloqueado/sem fundos. Segunda rodada não executada (`max_rounds=1`).
- Tokens/custos do modelo: desconhecidos (`unknown`), nunca zero.

## Artefatos (fora do Git; caminhos absolutos)

`/tmp/hermes-real-run/run/`: `report.md`, `result.json`, `state.json`,
`counters.json`, `verification.json`, `manifest.json`, `checkpoint.jsonl`.
Reprodução: `python3 gpt_researcher_integration.py "<pergunta>" light
--mode adaptive --transport native --model-transport opencode
--model opencode/glm-5.3-flash-free --coverage-plan plan.json
--max-rounds 1 --output-dir /tmp/hermes-real-run/run`
(requer quota disponível no modelo free e rede para OpenAlex/arXiv/GitHub).

Skipped: segunda pesquisa de continuação (c-trat) — sem quota free
disponível no momento; registrada como pendência, não executada.
