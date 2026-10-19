# Contratos da biblioteca instalada — revisão 85dac79

Inspeção no venv do container `hermes-gateway` (`/opt/data/home/.agent-reach-venv`),
sem chamadas reais de rede/modelo (só `importlib.metadata`, `__file__` e
`inspect.signature`). Produção nunca escrita; snapshot dev usa estes contratos
com transportes externos substituídos/bloqueados.

## Distribuição

- `importlib.metadata.version("gpt-researcher")` → `0.16.0`
- `distribution("gpt-researcher").locate_file("")` →
  `/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages`
- `gpt_researcher.__file__` →
  `/opt/data/home/.agent-reach-venv/lib/python3.13/site-packages/gpt_researcher/__init__.py`
- Versão via metadata (não `__version__`, que não existe como fonte).

## Assinaturas reais (container, Python 3.13.5)

- `GPTResearcher.__init__(self, query: str, report_type: str = 'research_report',
  report_format: str = 'markdown', report_source: str = 'web',
  tone: Tone = Objective(...), source_urls: list[str] | None = None,
  document_urls: list[str] | None = None, complement_source_urls: bool = False,
  query_domains: list[str] | None = None, documents=None, vector_store=None,
  vector_store_filter=None, config_path=None, websocket=None, agent=None,
  role=None, parent_query: str = '', subtopics: list | None = None,
  visited_urls: set | None = None, verbose: bool = True, context=None,
  headers: dict | None = None, max_subtopics: int = 5,
  prompt_family: str | None = None, mcp_configs: list[dict] | None = None,
  mcp_max_iterations: int | None = None, mcp_strategy: str | None = None,
  **kwargs)`
- `GPTResearcher.conduct_research(self, on_progress=None)`
- `GPTResearcher.quick_search(self, query: str,
  query_domains: list[str] | None = None, aggregated_summary: bool = False,
  all_retrievers: bool = False) -> list | str`
- `GPTResearcher.write_report(self, existing_headers: list = [],
  relevant_written_contents: list = [], ext_context=None, custom_prompt='') -> str`
- `GPTResearcher.get_source_urls(self) -> list`
- `gpt_researcher.actions.web_scraping.scrape_urls(urls,
  cfg: gpt_researcher.config.config.Config,
  worker_pool: gpt_researcher.utils.workers.WorkerPool)
  -> tuple[list[dict], list[dict]]`
- `gpt_researcher.config.config.Config.__init__(self, config_path: str | None = None)`
- `Config` efetivo em produção: `/opt/data/deep_research_outputs/gpt_researcher/config.json`
  (`SMART_LLM=openrouter:nvidia/nemotron-3.5-super-vl:free`, verificado via `cat`).

## Uso encapsulado (fiação real)

- `build_adaptive_transports(researcher)` em `gpt_researcher_integration.py`:
  varredura inicial = no máximo UM `conduct_research()`; rodadas de lacuna =
  `quick_search()` direcionadas (nunca repetem a pergunta original).
- Canal altera o acesso efetivo: `github` → `quick_search("site:github.com ...")`,
  `arxiv` → `site:arxiv.org`, `youtube` → `site:youtube.com`, `web` → contexto da
  varredura + `quick_search` direto. Identificado como busca web restrita a site,
  sem alegar API/conector próprio. Canais fora de
  `("web","github","arxiv","youtube")` → `TransportError` (registrado).
- Leitura: `scrape_urls([url], researcher.cfg, None)`; sucesso só quando
  `status == "success"`, senão `TransportError`. YouTube textual preservado via
  qualificação compartilhada (`[description]` utilizável, `[spoken n/M]` parcial);
  sem ASR, sem conectores duplicados (ver `youtube_transcript.fetch_transcript`).
- Modelo: `litellm.completion(model=os.environ["SMART_LLM"], ...)`; sem
  `SMART_LLM` → `TransportError`. Coerência config JSON × env validada em
  `_validate_runtime_config` (runtime instalado).

## Testes de contrato

- `tests/test_library_contracts_85dac79.py`: versão/location/assinaturas +
  canal `site:` via stub researcher (sem rede). Pula no host sem a biblioteca;
  passa no snapshot do container (`PYTHONPATH=/tmp/adaptive_snapshot`,
  `importlib.metadata` da venv instalada, transportes bloqueados).
- `tests/test_entry_single_run_85dac79.py`: UMA execução fim-a-fim com
  assessor/writer reais (modelo só no transporte) + canal no adaptador real.
- `tests/test_resume_orphan_85dac79.py`: ramo órfão de `_reconcile_resume`,
  run_id/consumo preservados.

Limite explícito: 1 invocação de fronteira = 1 unidade de orçamento de modelo;
um voto do auditor (`_review_pass`) = 1 unidade; lotes (chunks `batch_size=12`)
autorizados individualmente via `_AUDIT_BUDGET_CHECK` (sem saldo = sem chamada).
Requests internos da biblioteca (ex.: múltiplos chunks/requests por
`quick_search`/`conduct_research`) não têm atribuição fina — não apresentados
como teto global de requests (ver `docs/OFFLINE_VALIDATION.md`).
