# Checkpoint de desenvolvimento — 2026-10-24

Objetivo: primeira versão completa do produto da modelagem v1.1.
Matriz: `docs/REQUIREMENTS_MATRIX.md`.

## Estado de partida (verificado)

- Branch `fix/review-85dac79`, HEAD `364497c`, árvore limpa.
- 8 testes `tests/test_review_85dac79.py`, 14 `test_review_regressions.py`,
  29 adaptativos/cobertura, 8 de entrada e 83 casos históricos verdes.
- Host: Python 3.14.6, sem `gpt_researcher`.
- Container `hermes-gateway`: Python 3.13.5 no venv
  `/opt/data/home/.agent-reach-venv`, gpt-researcher 0.16.0.
- Serviços locais fora: vast `:8001`, SearXNG `:8888`, embeddings
  `172.17.0.1:8082` respondem `000` do container.
- Rede externa OK: OpenAlex 200, GitHub 200, OpenRouter 200, arXiv 301
  (usar `https://export.arxiv.org`).
- Credenciais de modelo existem em `~/.hermes/.env` (não copiadas para o repo;
  usadas só em execução real isolada).

## Frentes

- A: Agent Reach (`agent_reach.py`, `academic_search.py`) + testes + doc.
- B: contadores de seis estágios, `quantitative.py`, relatório PT,
  `verification_report.py`, concorrência efetiva (dono de
  `adaptive_coordinator.py`/`adaptive_state.py`).
- C (após B): `run_control.py` (progresso/pausa/retomada/cancelamento) +
  fiação CLI (`gpt_researcher_integration.py`) + doc de ativação no Hermes.
- D: validação real (OpenAlex/arXiv/GitHub/página/YouTube + uma execução
  limitada com OpenRouter) e revisão final contra a matriz.

## Regras

- Produção intocada; sem push/PR/deploy.
- Um escritor por arquivo; integração explícita.
- Não enfraquecer testes; mudanças de contrato documentadas.
- Estado real ≠ simulado sempre identificado nos artefatos.
