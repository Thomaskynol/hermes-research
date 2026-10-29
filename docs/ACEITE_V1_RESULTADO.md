# Aceite da primeira versão — reabertura e resultado (2026-10-26 a 2026-10-29)

Pergunta de aceite (literal, usada em todas as execuções):

> Descubra e compare cinco plugins para melhorar planejamento, implementação,
> testes e revisão de código no OpenCode. Considere a versão instalada neste
> computador. Investigue compatibilidade, funcionalidades demonstradas,
> dependências, custos, manutenção e limitações. Justifique quais combinam
> entre si e quais têm funções sobrepostas. Use fontes atuais e diferencie
> funcionalidades documentadas de inferências.

Contexto explícito fornecido à entrada (nunca inspecionado pelo produto):
`--context installed_opencode_version=2.1.4`.

## 1. Entrada isolada (eixo 5)

Caminho único, sem tocar produção (`/home/thomaskyn/.hermes` intocado):

```bash
cd /home/thomaskyn/Projetos/hermes-research-dev
export SEARXNG_URL=http://172.18.0.2:8888
R=accept11
python3 gpt_researcher_integration.py "<pergunta>" medium \
  --mode adaptive --transport native --model-transport opencode \
  --model opencode-go/muse-spark-1.3-contributor \
  --auto-plan --max-rounds 3 \
  --control-dir /tmp/hermes-real-run/$R/control --run-id $R \
  --output-dir /tmp/hermes-real-run/$R --context installed_opencode_version=2.1.4
```

Controle em tempo real, na mesma run: `python3 run_control.py --run-dir
/tmp/hermes-real-run/accept11/control status` → exit 0, `phase: round`,
`round: 1`, `run_id: accept11`, contadores e documentos (verificado durante a
execução). Pausa/retomada/cancelamento já demonstrados em
`docs/HERMES_E2E_DEMO.md`.

## 2. O que falhava e o que foi corrigido (mecanismos gerais)

| Run | Sintoma observado | Causa raiz | Correção (commit) |
|---|---|---|---|
| accept1–3 | cobertura 0.0, consultas de lacuna genéricas | query de lacuna não usava o alvo; falhas de canal não apareciam no relatório | D1/D2 (`5976c06`) |
| accept3 | poluição por ambiguidade PT | termos da pergunta sem âncora | âncoras + snippet gate (`f9387a2`, `a83981f`) |
| accept4 | 41 candidatos, `propose_entity` disparava mas sumia | ids propostos colidiam com e1–e5 do plano | remap + herança (`3e8b628`) |
| accept5 | run morria com 54 avaliações e orçamento restante | 1 payload não-lista do assessor virava `TransportError` fatal | 1 retry limitado, contado no budget (`0cad02a`) |
| accept6 | entidades descobertas versionadas, nunca investigadas | gaps só por critério; fonte própria não virava alvo | gaps por célula + `read_source` + prompt enumera células (`54294f7`) |
| accept7 | cobertura 0.0 com lixo (npm/ripgrep) | plano com entidades-placeholder e caminhos locais como queries | proíbe placeholder, descarta caminho local, `_query_label` (`6b54fe7`) |
| accept8 | 6 candidatos reais, 1 avaliação cada, sem virar cobertura | critérios todos globais; writer cortava fontes citadas | `per_candidate` + writer prioriza citadas (`92361db`) |
| accept9 | denominador 83, 12 entidades | sem teto de candidatos | `candidate_target` + teto na cobertura (`7f79ac6`) |
| accept10 | 3 dos 5 exigidos sem excerto | candidato de lista virava exigido sem menção na fonte | gate de menção na fonte própria (`cd0c12b`) |
| accept11 | `cited: 0` na tabela com 7 citações no texto | snapshot lido antes de `record_cited` | tabela usa as citações do próprio render (`d96a114`) |

Correção adicional: URL dentro de literal citado (`"plugin": ["x@git+https://…"]`)
deixou de ser substituída por `[fora do corpus]` (`de7c979`).

## 3. Resultado do accept11 (run iniciado em `cd0c12b`; renderer corrigido depois em `de7c979`/`d96a114`)

- Artefatos: `/tmp/hermes-real-run/accept11/adaptive_accept11/`
  (`report.md`, `result.json`, `verification.json`, `counters.json`,
  `manifest.json`, `state.json`).
- Perfil medium; 3 rodadas + varredura inicial; 441 s; 42 documentos;
  53 fetches; 7 chamadas de modelo; 4 rodadas.
- Contadores: discovered 50, obtained 41, usable 41, analyzed 31,
  used_in_synthesis 7, cited 7 (após `d96a114`; antes a tabela dizia 0 —
  verificado por re-render do `state.json` real, sem nova chamada de modelo).
- Cobertura: **0.025 (1/40 células), parcial**; motivo de parada `rounds`.
- Verificações independentes: execution `ok`; question `partial` (11 critérios
  pendentes); review `partial`; support `failed` (2 falhas registradas por
  motivo, URL fora do corpus sinalizada).
- Cinco candidatos exigidos, sem substituição, todos com fonte no corpus:
  `opencode-planner` [2], `Plannotator` [6], `oh-my-opencode-slim` [4],
  `dzianisv plugin-testing` [5], `opencode-daytona` [3].
- O relatório entrega: comparação lado a lado, funcionalidades demonstradas
  com trecho literal, dependências, custos (lacuna explícita), manutenção,
  limitações, combinações/sobreposições classificadas em DOCUMENTADO /
  INFERÊNCIA / LACUNA, fontes numeradas com alcance lido e a contradição
  entre a justificativa da cobertura e os excertos disponíveis.

## 4. O que ainda não está resolvido (limitações reais)

1. **Cobertura baixa e não comparável entre runs.** O denominador mudou a cada
   correção (global → por célula → teto → gate). 0.025 significa 1 de 40
   células obrigatórias com evidência forte; o relatório responde à pergunta
   com lacunas explícitas, mas não pode ser declarado completo.
2. **Justificativa do assessor não é verificada contra o excerto.** No
   accept11 ele afirmou `V2 only` e `pin 0.6.0` sem esses trechos no corpus; o
   relatório detecta e declara a contradição, mas a célula `c2` ficou
   `partial` com base nessa justificativa. Gate de citação literal por
   avaliação é o próximo mecanismo (não implementado).
3. **Sem conector de inspeção local.** A versão instalada só entra como
   contexto informado; o produto não lê `~/.config/opencode` nem o binário.
4. **Tokens e custos desconhecidos** (nunca zero). `model_calls` conta
   chamadas de fronteira, não requisições internas do provedor.
5. **Canal web primário (gateway vast local :8001) segue fora**; SearXNG
   auto-hospedado (IP de bridge frágil) e ddgs cobriram a coleta, com `via`
   registrado.
6. **Snippet gate não filtra lixo que compartilha vocabulário**; hits sem
   snippet são lidos às cegas (e contam no orçamento).

## 5. Generalização (outro assunto)

`docs/VALIDACAO_REAL_ACADRUN5.md`: pergunta FAIR-RAG, perfil com orçamento
explícito, `criteria_ok = 1.0`, revisão ACCEPTED, contadores
16/10/10/8/7/7. Evidência de que os mecanismos não são específicos de
OpenCode.

## 6. Estado do repositório

Branch `feat/product-v1`; HEAD `d96a114`; árvore limpa; **322 testes OK
(9 skipped)** no host; sem push/deploy; produção intocada; nenhum pacote de
revisão gerado.
