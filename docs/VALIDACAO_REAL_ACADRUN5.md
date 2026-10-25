# Validação real acadrun5 — ponto 4 (pesquisa satisfatória)

Data: 2026-10-26. Pergunta FAIR-RAG (modos de falha + limitações declaradas),
plano `acad-fairrag-001`, light, max_rounds=2, native+spark
(`opencode-go/muse-spark-1.3-contributor`), SEARXNG autohospedado.
Saída: `/tmp/hermes-real-run/acadrun5` (fora do Git).

## Resultado

- STOP `criteria_ok` (primeiro da série), proporção **1.0**, 1 round, 10 ev.
- Contadores: 16/10/10/8/7/7
  (descobertas/obtidas/utilizáveis/analisadas/usadas-na-síntese/citadas).
- Verificações: execution=ok (0 falhas), question=ok (2/2, gaps vazios),
  review=ok (ACCEPTED: 3 claims genéricas extraídas e revisadas, 9 blocos,
  0 unreviewed, 0 falhas), support=failed **estrito e correto**: 1 URL MDPI
  fora do corpus + `cited_beyond_synthesis` (overall=failed por rigor, não
  por erro — as 4 dimensões ficam inspecionáveis no `verification.json`).
- Relatório responde c-fail com substância (falha de componente 63.5%,
  falha de retrieval 32.5%, knowledge-base gaps, SEA 28–32%, taxonomia de
  failure modes de outros papers) e c-lim para o FAIR-RAG; declara
  honestamente que o corpus não sustenta como o gpt-researcher trata cada
  limitação (§2.2 + GAP-1) — writer não inventa cobertura (mesma honestidade
  observada no RAG_002, onde o writer recusou o partial do ledger).

## O que destravou (cadeia causal auditável)

1. Excerto head-only escondia o corpo (131K chars com §5.2.4/§6.1) →
   janelas de relevância por offset (size 600/stride 300).
2. Desencontro PT×EN (plano em PT, corpo em EN) → ponte bilíngue
   `_PT_EN_RESEARCH` + termos das consultas emitidas.
3. Recorte por parágrafo colapsava em corpo single-line → reescrita por offset.
4. Sem esses três, o assessor via "sumário até §5" e marcava insufficient.

## Limites

- 1 round bastou (pergunta focada + corpus certeiro); não demonstra
  multi-round com ganho progressivo (uv cobre multi-round, sem cobertura).
- support=failed mostra que o modelo ainda cita 1 URL fora do corpus;
  verificação pega, relatório segue parcial-honesto nesse ponto.
- Reprodução exige quota do modelo free + rede (OpenAlex/arXiv/SearXNG).
