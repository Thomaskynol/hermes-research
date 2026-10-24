# Ativação no host vs container (v1)

Dois ambientes reais, dois caminhos explícitos. Nada é autodetectado: a CLI
falha ou registra o transporte escolhido, nunca troca de caminho em silêncio.

| Ambiente | `--transport` | `--model-transport` | Por quê |
|---|---|---|---|
| Host (`/home/thomaskyn/Projetos/hermes-research-dev`) | `native` | `opencode` | Python 3.14 sem `gpt_researcher`/`litellm`; único modelo real é o CLI `opencode` |
| Container (Python 3.13 + biblioteca) | `library` | `litellm` | `gpt_researcher` instalado; litellm com chave/config válidos |

Fatos do ambiente que motivam a matriz: a chave OpenRouter de produção está
inválida (401), o Zen HTTP direto bloqueia free tier e não tem fundos para
pago. O CLI do host (`opencode run --standalone --format json`) funciona em
~6–9s para prompts de ~3k chars; o container **não** tem esse binário.

## Host — nativo + CLI

```bash
cd /home/thomaskyn/Projetos/hermes-research-dev
python3 gpt_researcher_integration.py "pergunta" light \
  --mode adaptive \
  --transport native \
  --model-transport opencode \
  --coverage-plan plan.json \
  --output-dir /tmp/hermes-run \
  --control-dir /tmp/hermes-run/control
```

- `--transport native`: search/fetch vêm de `agent_reach` + `academic_search`
  (`native_transport.build_native_transports`). `gpt_researcher` não é
  importado — verificado por teste em subprocesso.
- `--model-transport opencode`: modelo via
  `opencode_client(model="opencode/nemotron-3.5-lightning-free")`. Use
  `--model <id>` para outro id. `max_calls`/timeout são do cliente, não da CLI.
- Web depende do gateway local (`RETRIEVER_ENDPOINT`); indisponível vira
  `TransportError` com o motivo, nunca resultado inventado.
- GitHub search usa `api.github.com`; `GITHUB_TOKEN` no ambiente evita o
  rate limit anônimo (403 é erro visível, não lista vazia).

## Container — biblioteca + litellm

```bash
python3 gpt_researcher_integration.py "pergunta" light \
  --mode adaptive \
  --transport library \
  --model-transport litellm \
  --coverage-plan plan.json
```

- `--transport library` mantém o caminho atual (`GPTResearcher` + sweep único
  + `quick_search` direcionado).
- Modelo resolvido por `model_transport.litellm_client`: `--model` >
  `researcher.cfg.smart_llm` > `SMART_LLM` > erro
  `model_not_configured`. Prefixos `openrouter:`, `openai:`, `anthropic:`,
  `google_genai:` são normalizados para `/`; provedor desconhecido é erro.
- O stdout registra `transport=`, `model_transport=`, `model=` e
  `control_dir=` (sem chave).

## Controle externo (status/pause/resume/cancel)

`run_control.RunControl(run_dir)` grava `status.json` (atômico: tmp+rename)
e consome `control.json` uma única vez (`control.taken.json`); JSON inválido
vira `control.invalid-*.json`, nunca é apagado em silêncio.

```bash
python3 run_control.py --run-dir /tmp/hermes-run/adaptive_<id> status
python3 run_control.py --run-dir /tmp/hermes-run/adaptive_<id> pause
python3 run_control.py --run-dir /tmp/hermes-run/adaptive_<id> resume
python3 run_control.py --run-dir /tmp/hermes-run/adaptive_<id> cancel
```

Exit 0 em sucesso; 2 em uso/arquivo ausente. `--control-dir` na CLI adaptive
é aceito e registrado, mas **a integração no coordenador ainda não existe**:
`poll()` deve ser chamado no início de cada rodada e entre operações;
`pause` -> persistir estado e encerrar com stop reason `"paused"`; `cancel` ->
`"cancelled"`; retomada via `--resume`. Fica para a próxima fase.

## Verificação offline

```bash
python3 -m unittest tests.test_model_transport tests.test_native_transport tests.test_run_control
python3 -m unittest discover -s tests
```

Rede e subprocesso são bloqueados/mockados. `test_yt_enrich_fix` pode falhar
no host por `httpx` ausente (pré-existente, não relacionado).
