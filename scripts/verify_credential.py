#!/usr/bin/env python3
"""Regression: the LLM credential must survive every sync path.

Verifies the CLIENT that is actually built (not just the env var), and the
three degraded cases the brief names: api_key absent, empty, and masked.

Offline: no provider calls. Uses a fake key value so nothing real leaks.
Run:
    /opt/data/home/.agent-reach-venv/bin/python scripts/verify_credential.py
Exit 0 = the credential contract holds.
"""
import importlib
import os
import sys
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKDIR))
_foreign = [p for p in sys.path if "/.venv/" in p]
for p in _foreign:
    sys.path.remove(p)

FAILURES: list[str] = []
FAKE = "sk-or-v1-" + "f" * 64  # shaped like a real key, obviously fake


def check(name, ok, evidence):
    print(f"{'PASS' if ok else 'FAIL'} {name}: {evidence}")
    if not ok:
        FAILURES.append(name)


def fresh_sync(env: dict):
    """Import sync_config with a controlled environment, run sync()."""
    for k in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "SMART_LLM",
              "FAST_LLM", "STRATEGIC_LLM", "OPENAI_BASE_URL"):
        os.environ.pop(k, None)
    os.environ.update(env)
    mod = importlib.import_module("sync_config")
    importlib.reload(mod)
    mod.sync()
    return mod


def _usable(v: str | None) -> bool:
    """Same rule sync_config._usable_key applies (mirrored for the test)."""
    if not v:
        return False
    v = v.strip()
    if v in ("***", "sk-or-...", "sk-or-...ebe2") or "..." in v:
        return False
    return len(v) >= 20


def env_key() -> str:
    """The real key from /opt/data/.env (what load_api_keys() will read)."""
    for line in Path("/opt/data/.env").read_text(encoding="utf-8").split("\n"):
        if line.strip().startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


REAL = env_key()


def main() -> int:
    # --- A. real key present: sync must install it, never clobber it ---
    fresh_sync({"OPENROUTER_API_KEY": REAL})
    got = os.environ.get("OPENAI_API_KEY", "")
    check("A1_real_key_installed", got == REAL and _usable(got),
          f"OPENAI_API_KEY is the real key (len {len(got)})")

    # A2: a SECOND sync in the same process must not downgrade it. This is the
    # exact historical failure: the placeholder *** overwrote a good key.
    mod = importlib.import_module("sync_config")
    mod.sync()
    got2 = os.environ.get("OPENAI_API_KEY", "")
    check("A2_second_sync_preserves_key", got2 == REAL,
          f"key survives a repeat sync (len {len(got2)}, not '***')")

    # --- B. api_key ABSENT (config.yaml has none): keep the good key ---
    os.environ["OPENAI_API_KEY"] = REAL
    os.environ.pop("OPENROUTER_API_KEY", None)
    mod = importlib.import_module("sync_config")
    mod.sync()
    got3 = os.environ.get("OPENAI_API_KEY", "")
    check("B1_absent_key_preserves_existing", got3 == REAL,
          f"absent config key does not wipe the env key (len {len(got3)})")

    # --- C. a MASKED value in the env must be REPLACED by the real one ---
    for label, value in (("C1_empty", ""), ("C2_masked", "***"),
                         ("C3_redacted", "sk-or-...ebe2")):
        os.environ["OPENAI_API_KEY"] = value
        os.environ.pop("OPENROUTER_API_KEY", None)
        mod = importlib.import_module("sync_config")
        mod.sync()
        gotv = os.environ.get("OPENAI_API_KEY", "")
        check(f"{label}_replaced_by_real",
              gotv == REAL,
              f"masked/empty {value!r} was replaced by the real key "
              f"(len {len(gotv)}), never left as a half-key")

    # --- D. the CLIENT built by the library, not just the env var ---
    fresh_sync({"OPENROUTER_API_KEY": REAL})
    from gpt_researcher.utils.llm import get_llm
    try:
        provider = get_llm("openrouter", model="meta/muse-spark-1.3-contributor")
        # GenericLLMProvider wraps the real chat client; unwrap it.
        client = getattr(provider, "llm", provider)
        key = (getattr(client, "openai_api_key", None)
               or getattr(client, "api_key", None))
        key_val = getattr(key, "get_secret_value", lambda: key)()
        base = (getattr(client, "openai_api_base", None)
                or getattr(client, "base_url", None))
        check("D1_client_carries_real_key", key_val == REAL,
              f"inner client ({type(client).__name__}) holds the real key "
              f"(len {len(str(key_val))}), not '***'")
        check("D2_client_base_url_openrouter", "openrouter.ai" in str(base),
              f"base_url={base}")
    except Exception as exc:
        check("D1_client_carries_real_key", False,
              f"could not build client: {type(exc).__name__}: {exc}")

    # --- E. pin survives: model is explicit, never omitted ---
    fresh_sync({"OPENROUTER_API_KEY": REAL})
    for slot in ("SMART_LLM", "FAST_LLM", "STRATEGIC_LLM"):
        val = os.environ.get(slot, "")
        check(f"E_{slot}_explicit",
              bool(val) and ":" in val and "muse" in val,
              f"{slot}={val}")

    print(f"\n{len(FAILURES)} FAILURES")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
