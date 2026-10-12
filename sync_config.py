#!/usr/bin/env python3
"""GPT Researcher auto-sync — reads Hermes config.yaml, sets env vars."""
import json
import os
from pathlib import Path

CONFIG_YAML = Path("/opt/data/config.yaml")
GPT_CONFIG = Path("/opt/data/deep_research_outputs/gpt_researcher/config.json")
ENV_FILE = Path("/opt/data/.env")
STATE_DB = Path("/opt/data/state.db")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Hermes: provider do config/session -> prefixo de provider do GPT Researcher
PROVIDER_MAP = {
    "custom": "openai",
    "ollama": "openai",
    "ollama-cloud": "openai",
    "openrouter": "openrouter",
}


def _is_local_url(url: str) -> bool:
    return bool(url) and any(h in url for h in ("172.17.0.1", "localhost", "127.0.0.1"))


def get_chat_model():
    """Detecta o modelo ativo DO CHAT atual (Hermes state.db -> sessions).

    Usa HERMES_SESSION_ID (disponível no ambiente do agente).
    Returns dict {model, provider, base_url, session_id} ou None se não detectar.
    """
    sid = os.environ.get("HERMES_SESSION_ID", "").strip()
    if not sid or not STATE_DB.exists():
        return None
    try:
        import sqlite3
        con = sqlite3.connect(str(STATE_DB), timeout=2)
        try:
            row = con.execute(
                "SELECT model, model_config FROM sessions WHERE id = ?", (sid,)
            ).fetchone()
        finally:
            con.close()
        if not row or not row[0]:
            return None
        chat_model = str(row[0]).strip()
        provider, chat_base = "", ""
        if row[1]:
            try:
                mc = json.loads(row[1])
                provider = str(mc.get("provider") or "").strip()
                chat_base = str(mc.get("base_url") or "").strip()
            except Exception:
                pass
        if not chat_model or not provider:
            return None
        return {
            "model": chat_model,
            "provider": provider,
            "base_url": chat_base,
            "session_id": sid,
        }
    except Exception:
        return None


def get_hermes_model():
    """Read model.* from config.yaml. Returns (model_string, base_url, api_key)."""
    text = CONFIG_YAML.read_text()
    in_model = False
    model = ""
    provider = "openrouter"
    base_url = ""
    api_key = ""
    for line in text.split("\n"):
        if line.startswith("model:"):
            in_model = True
            continue
        if in_model and line.startswith("  provider:"):
            provider = line.split(":", 1)[1].strip()
            continue
        if in_model and line.startswith("  default:"):
            model = line.split(":", 1)[1].strip()
            continue
        if in_model and line.startswith("  base_url:"):
            base_url = line.split(":", 1)[1].strip().strip('"').strip("'")
            # handle http:// case where split(':') broke it
            if base_url.startswith("//"):
                base_url = "http:" + base_url
            elif base_url == "http":
                # value was http://... split on first colon lost it
                raw = line.split(":", 1)[1].strip().strip('"').strip("'")
                base_url = raw
            continue
        if in_model and line.startswith("  api_key:"):
            api_key = line.split(":", 1)[1].strip().strip('"').strip("'")
            continue
        if in_model and not line.startswith("  ") and line.strip() and not line.startswith("#"):
            break
    # Re-read base_url properly (handle http://)
    for line in text.split("\n"):
        if "base_url:" in line and in_model:
            # extract everything after base_url:
            idx = line.index("base_url:")
            base_url = line[idx + len("base_url:"):].strip().strip('"').strip("'")
            break
    # GPT Researcher uses OpenAI-compatible provider names; map Hermes 'custom'/'ollama' -> 'openai'
    gr_provider = provider
    if provider in ("custom", "ollama", "ollama-cloud"):
        gr_provider = "openai"
    if "/" in model and ":" not in model.split("/")[0]:
        model_str = f"{gr_provider}:{model}"
    else:
        model_str = model or f"{gr_provider}:inclusionai/ling-3.0-flash-vl:free"
    # bare gguf filename without provider prefix — prefix it
    if ".gguf" in model_str and ":" not in model_str:
        model_str = f"{gr_provider}:{model_str}"
    # If gr_provider is openai and model already bare, ensure prefix
    if gr_provider == "openai" and ":" not in model_str:
        model_str = f"openai:{model}"
    return model_str, base_url, api_key


def load_api_keys():
    """Load API keys from .env and map to what GPT Researcher needs."""
    keys = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not value or value == "sk-or-...ebe2":
                continue
            keys[key] = value
    
    # Map OPENROUTER_API_KEY → OPENAI_API_KEY (OpenRouter uses OpenAI-compatible auth)
    if "OPENROUTER_API_KEY" in keys and "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = keys["OPENROUTER_API_KEY"]
    
    if "OPENAI_API_KEY" in keys and "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = keys["OPENAI_API_KEY"]
    
    if "OPENROUTER_API_KEY" in keys and "OPENROUTER_API_KEY" not in os.environ:
        os.environ["OPENROUTER_API_KEY"] = keys["OPENROUTER_API_KEY"]
    
    return keys


def _http_ok(url: str, timeout: float = 2) -> bool:
    """Health check GET; True se respondeu."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def get_model_pin() -> str | None:
    """Modelo fixo para o GPT Researcher, se o usuário tiver pinado.

    Lê ``GPT_MODEL_PIN`` do arquivo ``.env`` (formato: um modelo por linha,
    ex. ``openrouter:meta/muse-spark-1.3-contributor``). Quando presente, o
    ``sync()`` usa ESSE modelo nos 3 slots e ignora o auto-follow do chat —
    o pin só é trocado quando o usuário o editar explicitamente. Retorna
    ``None`` se não houver pin (comportamento auto-follow normal).
    """
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "GPT_MODEL_PIN":
            value = value.strip().strip('"').strip("'").strip()
            return value or None
    return None


def sync():
    model, base_url, api_key = get_hermes_model()
    keys = load_api_keys()

    # ── Pin explícito do usuário: vence o auto-follow do chat ──
    # Se o usuário fixou um modelo para o pesquisador, respeitamos e não
    # deixamos o sync reescrever para o modelo do chat a cada run.
    pin = get_model_pin()
    chat = None
    if pin:
        print(f"[SYNC] GPT_MODEL_PIN ativo: {pin} (auto-follow do chat desativado)")
    else:
        chat = get_chat_model()
        if chat:
            gr_provider = PROVIDER_MAP.get(chat["provider"], chat["provider"])
            model = f"{gr_provider}:{chat['model']}"
            chat_base = chat.get("base_url") or ""
            if chat_base and not _is_local_url(chat_base):
                base_url = chat_base
            elif gr_provider == "openrouter":
                base_url = OPENROUTER_BASE_URL
            print(f"[SYNC] Chat model: {model} (sessão {chat['session_id']})")
        else:
            print("[SYNC] Chat model não detectado — usando config.yaml")

    # ══ GATES: se falhar, a pesquisa NÃO pode rodar — usuário é quem subir ══
    errors = []
    EMBEDDING_SERVER_URL = "http://172.17.0.1:8082/v1"
    if not _http_ok(f"{EMBEDDING_SERVER_URL.replace('/v1', '')}/health"):
        errors.append(
            "[SYNC] ❌ EMBEDDING (172.17.0.1:8082) FORA DO AR — sem fallback. "
            "PARE e peça ao usuário pra subir o servidor de embedding."
        )
    if not pin:
        if chat:
            llm_is_local = chat["provider"] != "openrouter" and _is_local_url(
                chat.get("base_url") or base_url)
            llm_endpoint = chat.get("base_url") or base_url
        else:
            llm_is_local = _is_local_url(base_url)
            llm_endpoint = base_url
        if llm_is_local:
            health = (llm_endpoint or "").rstrip("/")
            if health.endswith("/v1"):
                health = health[:-3]
            if not _http_ok(f"{health}/health"):
                errors.append("[SYNC] ❌ ORNITH (LLM local) FORA DO AR.")
        else:
            print("[SYNC] LLM remoto — 8080 (Ornith) não precisa estar no ar")

    if errors:
        for e in errors:
            print(e)
        raise SystemExit(1)

    if pin:
        # provider do pin (antes do ':') decide o base_url quando OpenRouter
        base_url = OPENROUTER_BASE_URL

    cfg = json.loads(GPT_CONFIG.read_text())
    model = pin or model
    cfg["SMART_LLM"] = model
    cfg["FAST_LLM"] = model
    cfg["STRATEGIC_LLM"] = model

    # Embedding: SEMPRE o servidor local 8082 (harrier GGUF na GPU) — gates acima
    # garantiram que ele está no ar. Nenhum fallback.
    cfg["EMBEDDING"] = "custom:harrier-oss-v1-0.6b"
    os.environ["EMBEDDING"] = "custom:harrier-oss-v1-0.6b"
    os.environ["OPENAI_BASE_URL"] = base_url if base_url else OPENROUTER_BASE_URL  # LLM endpoint
    os.environ["OPENAI_EMBEDDING_BASE_URL"] = EMBEDDING_SERVER_URL  # embedding endpoint (lido pelo custom provider)

    # Write config to disk and set common env vars
    GPT_CONFIG.write_text(json.dumps(cfg, indent=4))
    if api_key is not None:
        os.environ["OPENAI_API_KEY"] = api_key if api_key else "***"
    os.environ["SMART_LLM"] = model
    os.environ["FAST_LLM"] = model
    os.environ["STRATEGIC_LLM"] = model
    os.environ["RETRIEVER_ENDPOINT"] = "http://127.0.0.1:8001/"
    os.environ["SEARX_URL"] = "http://127.0.0.1:8888/"

    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    print(f"[SYNC] Model: {model}")
    print(f"[SYNC] API Key: {'SET' if has_key else 'NOT SET'} (never printed)")
    print(f"[SYNC] Base URL: {os.environ['OPENAI_BASE_URL']}")
    print(f"[SYNC] Embedding: {os.environ.get('EMBEDDING', cfg.get('EMBEDDING'))}")


if __name__ == "__main__":
    sync()
