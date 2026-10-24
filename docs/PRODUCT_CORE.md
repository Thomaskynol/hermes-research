# Product core — contadores, concorrência, cálculos, relatório, verificações e manifesto

Implementação do núcleo de produto da pesquisa adaptativa (modelagem v1.1,
§§6–14). Tudo abaixo é stdlib, offline e determinístico nas fronteiras: os
transportes (busca, fetch, modelo) são injetados; o coordenador, o ledger, o
assessor/escritor e a persistência são o código real.

Arquivos deste incremento:

| Arquivo | Papel |
|---|---|
| `research_counters.py` | contadores de seis estágios (unidade = documento/URL) |
| `adaptive_state.py` | defaults retrocompatíveis (`counters`, `gaps`, `quantitative`, `verification`, `manifest`) |
| `adaptive_coordinator.py` | incremento dos contadores, pool de concorrência, render + verificações no `_finalize` |
| `quantitative.py` | cálculos locais reproduzíveis (conjunto fechado de operações) |
| `report_renderer.py` | entrega em Markdown PT-BR estruturado |
| `verification_report.py` | quatro verificações independentes + `verification.json` |
| `run_manifest.py` | manifesto da execução (config/código/modelos/artefatos) |
| `tests/test_product_core.py` | 17 testes offline do núcleo |

## 1. Contadores de seis estágios

Estrutura em `state["counters"]`:

```json
{
  "counts": {"discovered": 0, "obtained": 0, "usable": 0,
             "analyzed": 0, "used_in_synthesis": 0, "cited": 0},
  "documents": {"<estágio>": ["url-normalizada", ...]},
  "meta": {"<url>": {"obtained_at": "...", "raw_chars": 0,
                     "usable_chars": 0, "status": "...", "type": "...",
                     "title": null}},
  "relations": [{"url": "...", "related_to": "...", "kind": "version|duplicate",
                 "detail": "...", "at": "..."}],
  "outside_corpus_citations": []
}
```

Unidade é **documento/URL normalizada** (`scripts.citation_audit.normalize_url`),
nunca chunk. Cada estágio só cresce quando o evento correspondente foi
observado; nada é inferido.

| Estágio | Incrementa em | Regra de exclusão |
|---|---|---|
| `discovered` | `record_discovered` com os hits reais de cada busca (caminho sequencial e paralelo) | dedupe por URL normalizada; hit sem URL não conta |
| `obtained` | `incorporate` → `record_obtained` quando o payload trouxe texto real | metadado puro (`metadata_only`, `bibliographic`, …), vídeo sem `[spoken`, erro/vazio/timeout **não** contam; página excluída por insuficiência/relevância **conta** (o texto foi obtido) |
| `usable` | `incorporate` → `record_usable` após qualificação | exige `obtained` + `excluded=false` + status `usable`/`partial` + `usable_text` não vazio |
| `analyzed` | `_assess_round` → `record_analyzed` com `assess_fn.last_selection["urls"]` da chamada real | só documentos `obtained`; referência fora da seleção nunca justifica cobertura |
| `used_in_synthesis` | `_finalize` → `record_used_in_synthesis` com `selection["included_urls"]` do escritor | só `obtained`; fallback determinístico (sem prompt de escritor) conta zero, registrado como fallback |
| `cited` | `_finalize` → `record_cited_urls` com `report_renderer.render_report.last_cited_urls` | só URLs do corpus efetivamente referenciadas no corpo entregue; a tabela de fontes não infla o contador |

Relações:

- **version**: trechos distintos da mesma URL (uma URL, várias versões) — a URL
  continua sendo um documento para `obtained`.
- **duplicate**: bytes idênticos em outra URL (republicação; independência
  desconhecida). URL diferente não prova confirmação independente.

O ledger mantém seus nomes (`qualified`, `used`); `_update_ledger_counts` mapeia
`usable → qualified` e `used_in_synthesis → used` quando há contadores
observados. Estados antigos sem `counters` caem no caminho legado
(evidência/avaliações), sem regressão.

## 2. Concorrência real

`resolve_adaptive` expõe `concurrency` (default do perfil = 4). `_execute_ops`
despacha:

- `concurrency <= 1` **ou** `len(ops) <= 1` → `_execute_ops_sequential`
  (comportamento anterior, sem pool);
- caso contrário → `_execute_ops_parallel`, em três fases:

1. **Fase 1 (sequencial)** — checagem de tempo, decisões de reuso/duplicata e
   autorização de orçamento **antes** de qualquer transporte: `queries` para
   buscas e `extractions` para `read_source`.
2. **Fase 2a** — buscas no pool limitado por `concurrency`.
   **Fase 2b (sequencial, ordem das ops)** — autorização de `extractions` para
   os hits e agendamento dos fetches; URLs idênticas no mesmo lote são
   buscadas uma vez (`claim_owner`, dedupe declarado).
   **Fase 2c** — fetches no pool limitado.
3. **Fase 3 (sequencial, ordem das ops)** — `incorporate`, qualificação,
   persistência, contadores e desfechos. O estado final não depende da ordem de
   conclusão dos threads.

Garantias:

- **Teto de orçamento**: todo `spend()` é autorizado na thread principal
  (fases 1 e 2b). O pool só transporta. O teto agregado não é furado.
- **Determinismo**: a aplicação é feita na ordem original das ops; evidência,
  `attempts` e `pending_ops` ficam estáveis.
- **Falha de transporte** vira resultado por op (`failed`), o pool sobrevive.
  `KeyboardInterrupt` (BaseException) propaga.
- **Tempo esgotado**: ops não concluídas recebem `outcome="time"`; fetches já
  agendados podem concluir, mas a op sem resultado vira `time`.
- `read_source` continua lendo o alvo direto, sem busca.

Limitação declarada: `concurrency` limita **nossos** transportes de op. Tetos
internos de requests por fonte (bibliotecas de busca/fetch) continuam sendo
responsabilidade do transporte — não há teto global fictício.

## 3. Cálculos reproduzíveis

`quantitative.compute(spec)` aceita um conjunto fechado — `sum`, `mean`,
`median`, `min`, `max`, `percent_change`, `ratio`, `weighted_mean`,
`compound_growth`, `unit_convert` — sem `eval`. Cada resultado preserva:

`formula_id`, `op`, `inputs`, `units`, `assumptions`, `result`, `computed_at`,
`source_urls`.

Regras: NaN/Inf e divisão por zero levantam `ValueError`; conversão de moeda é
recusada (taxa varia por data); `unit_convert` só converte grandezas
declaradas. `to_markdown_block` renderiza o bloco da seção 4.

`run_adaptive(..., quantitative=[spec, ...])` calcula os specs no `_finalize`,
guarda `state["quantitative"]`, inclui a seção **4. Comparações e cálculos** no
relatório e devolve `result["quantitative"]`. Spec inválido não derruba a
execução: vira nota (`quantitative spec rejected: ...`) e não entra no
resultado. Os cálculos são **declarados pelo chamador**; o coordenador não
inventa fórmulas a partir do corpus.

## 4. Relatório PT-BR

`report_renderer.render_report(state, synthesis_text=..., verifications=...,
quantitative=...)` produz a entrega. O texto do modelo é a **síntese**; o
renderer é a **entrega**. Seções:

1. Resposta direta / resumo executivo (síntese)
2. Escopo, critérios, método e configuração efetiva
3. Achados por critério (estado, justificativa, referências)
4. Comparações e cálculos (quando declarados)
5. Limitações, contradições, incertezas e não investigados (+ notas)
6. Conclusão e próximos passos
7. Fontes (numeradas a partir do corpus **obtido**)
8. Anexo: verificações independentes + contadores de seis estágios + relações
9. Encerramento e rodadas (motivo de parada, rodadas, parcial)

URLs fora do corpus citadas pela síntese são **removidas do corpo** (viram
`[fora do corpus]`), registradas em `state["notes"]` e nunca entram na tabela
de fontes. `report.md` contém o Markdown do renderer; `state["report"]["text"]`
continua sendo a síntese do modelo. Perfis `hard`/`deep` renderizam método,
rodadas e notas completos; `light` é conciso sem esconder incertezas.

## 5. Quatro verificações independentes

`verification_report.verify_all` agrega, sem promoção cruzada:

| Dimensão | Pergunta | `ok` exige |
|---|---|---|
| `execution` | as ops foram executadas e as falhas registradas? | todas as ops com desfecho `done`/`failed` e motivo; nenhuma pendente |
| `question` | os critérios obrigatórios foram investigados? | `block.complete` e nenhum par obrigatório pendente |
| `review` | as afirmações foram extraídas/revisadas sem omissão silenciosa? | revisão habilitada, `claims_reviewed == claims`, sem falha técnica, aceita |
| `support` | o corpus real sustenta o que o relatório diz? | toda citação resolve no corpus, nenhuma claim `unsupported`, revisão integral |

Estados: `ok`, `partial`, `failed`, `not_run`. Agregação: `failed` se qualquer
dimensão falhou; `ok` só se todas ok; `partial` caso contrário; `not_run` se
todas não executadas. Aprovação semântica **nunca** promove `question` a `ok`.
O `_finalize` roda `verify_all` sobre a síntese, renderiza a entrega e reexecuta
`support` sobre o Markdown entregue (referências renumeradas/removidas),
recalculando o `overall`. `verification.json` é persistido no run_dir.

## 6. Manifesto

`run_manifest.build_manifest(run_dir, state, resolved=..., model_info=...,
environment=..., artifacts=...)` registra:

- `run_id`, pergunta, modo, perfil, timestamps, config aplicada e `resolved`;
- `simulated` (topo) e `environment.simulated` — **obrigatório booleano**;
  ausência levanta `ValueError` (execução offline nunca é apresentada como real);
- modelos por nome declarado, com chaves sensíveis (`key`, `token`, `secret`,
  `password`, `authorization`, `credential`, `cookie`) redigidas;
- hashes sha256 dos módulos próprios presentes;
- artefatos com caminho, `sha256`, bytes e `exists`;
- consumo; `tokens`/`cost_usd` não medidos ficam `"unknown"`, nunca `0`;
- motivo de parada e contadores.

`write_manifest` grava `manifest.json` atomicamente. O manifesto é escrito pelo
chamador/integração que conhece `environment` e `model_info`; o estado reserva
`state["manifest"]` para esse registro. Rodar sem declaração de ambiente não
gera manifesto — ausência explícita, não um manifesto mentiroso.

## 7. Estado retrocompatível

`adaptive_state.ensure_defaults` preenche `gaps`, `quantitative_specs`,
`quantitative`, `verification`, `manifest` e a estrutura de contadores ao
carregar estados antigos, sem apagar nada. `load` continua verificando
`run_id` e marcando ops `in-progress` como `interrupted`. `new_state` já nasce
com todos os defaults. `run_adaptive` mantém `result["report"]` e adiciona
`report_markdown`, `report_path`, `verification`, `counters` e `quantitative`.

## 8. Validação executada

Host (Python 3.14.6, sem `httpx`):

```text
python3 -m unittest discover -s tests -p "test_product_core.py" -v
Ran 17 tests ... OK

python3 -m unittest discover -s tests -p "test_adaptive*.py"
Ran 26 tests ... OK

python3 -m unittest discover -s tests -p "test_*.py"
Ran 87 tests ... FAILED (errors=1, skipped=4)
```

O único erro é pré-existente e alheio a este incremento:
`test_yt_enrich_fix` não importa no host porque `vast_local_retriever` importa
`httpx` (módulo ausente no host). No container, com o venv real, o mesmo
`discover` passa.

Container `hermes-gateway` (Python 3.13.5,
`/opt/data/home/.agent-reach-venv/bin/python`), snapshot em `/tmp/core_snap`:

```text
docker cp <worktree>/. hermes-gateway:/tmp/core_snap/
docker exec hermes-gateway sh -c 'cd /tmp/core_snap &&
  PYTHONPATH=/tmp/core_snap /opt/data/home/.agent-reach-venv/bin/python \
  -m unittest discover -s tests -p "test_*.py"'
Ran 86 tests ... OK          # 86 = 87 do host - 1 import quebrado no host

docker exec hermes-gateway sh -c 'cd /tmp/core_snap &&
  PYTHONPATH=/tmp/core_snap /opt/data/home/.agent-reach-venv/bin/python \
  scripts/run_replay_offline_validation.py --output-dir /tmp/core_out'
11/11 suítes com exit=0 (rede proibida por audithook nos processos filhos)
```

## 9. Limitações reais

- `tokens`/`cost_usd` permanecem `"unknown"`: não há atribuição por chamada
  neste caminho (`run_budget` documenta a limitação).
- `concurrency` não limita requests internos das bibliotecas de transporte;
  limita as ops que o coordenador dispara.
- Cálculos são declarados pelo chamador; não há derivação automática de
  fórmulas a partir do corpus.
- O manifesto é escrito pela integração que declara ambiente/modelos; o
  coordenador não inventa `simulated` nem nomes de modelo.
- `outside_corpus_citations` é populado quando o chamador registra as URLs
  externas; o renderer garante a remoção do corpo e a nota, mas não duplica a
  contagem no contador.
- A data do relatório usa o instante de geração (`time.gmtime`), não um relógio
  injetado; os testes não dependem desse valor.
