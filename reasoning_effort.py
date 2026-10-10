#!/usr/bin/env python3
"""Force reasoning_effort=high for our reasoning model. No site-packages edits.

Why this exists
---------------
`stealth/space-bunny-alpha` is absent from
``gpt_researcher/llm_provider/generic/base.py:77``
``SUPPORT_REASONING_EFFORT_MODELS``, so ``gpt_researcher/utils/llm.py:89`` never
forwards the parameter at all::

    if model in SUPPORT_REASONING_EFFORT_MODELS:
        provider_kwargs['reasoning_effort'] = reasoning_effort

Unreasoned, the model spends the entire 12k-token budget on thinking, finishes
with ``finish_reason=length`` and ``content=""``; the run then reports
"LLM returned empty response" and the report comes out blank. Measured on the
exact report prompt (5,880 tokens, ``max_tokens=12000``):

    payload            content                              reasoning   finish
    nothing (today)    0                                    53,356      length
    reasoning_effort=high   32,344 / 40,314 / 36,307      2k-11k      stop x3
    reasoning_effort=max    18,467 / 537 / 0               38k-54k     length

`high` failed 0 of 4 runs. `max` still fails a third of the time, so `high` is
the value we ask for -- it is not a guess.

Two seams, both outside the package
-----------------------------------
1. The allow-list is a plain Python list, so it is opened with an **in-place
   append**. It must be ``append`` and not a rebind: ``utils/llm.py`` does
   ``from ...base import SUPPORT_REASONING_EFFORT_MODELS`` and therefore holds a
   second reference to the same object. Only in-place mutation reaches that
   reference; rebinding the name on ``base`` would leave ``llm.py`` looking at
   the original list and the parameter would still never be sent.

2. The *value* is harder, because it is not configuration. There are three
   independent copies, and the two that matter are hardcoded:

   * ``actions/query_processing.py:124`` (the sub-query / planning call) passes
     ``reasoning_effort=ReasoningEfforts.Medium.value`` literally.
   * every call in ``actions/report_generation.py`` omits the argument, so the
     report inherits the ``ReasoningEfforts.Medium.value`` default declared on
     ``utils/llm.py:51``.
   * ``Config.reasoning_effort`` (config.py:96, read from ``$REASONING_EFFORT``)
     is the third copy, used by ``skills/deep_research.py:285``.

   Raising the first two means changing a caller argument and a function default.
   With the package off-limits the only remaining seam is the function itself, so
   this module wraps ``create_chat_completion`` and rebinds the wrapper in the two
   modules that call it. That is the same shape as ``retriever_timeout.py``:
   rebind one name from our own code, reversible, nothing installed is touched.

Why it is conditional
---------------------
The wrapper only rewrites the effort for models in ``REASONING_MODELS`` below,
and the allow-list is only opened for those same models. A model we have not
declared as a reasoning model is left completely alone, so we never hand
``reasoning_effort`` to something that would reject it. Swapping the chat model
for a non-reasoning one therefore needs no code change here: it is simply not in
the set, and the gate stays shut.

Env overrides: ``REASONING_MODELS`` (comma-separated bare model names) and
``REASONING_EFFORT`` (one of low/medium/high). Both default to the authorised
values. A bad ``REASONING_EFFORT`` raises at install rather than silently
reverting to a default that we know produces empty reports.
"""
import functools
import inspect
import json
import os
from pathlib import Path

from gpt_researcher.actions import query_processing, report_generation
from gpt_researcher.llm_provider.generic import base
from gpt_researcher.utils import llm as llm_utils

CONFIG_JSON = Path("/opt/data/deep_research_outputs/gpt_researcher/config.json")

# Bare model names (provider prefix already stripped) that we treat as reasoning
# models. Overridable so a future chat model can be excluded without a code edit.
REASONING_MODELS = tuple(
    m.strip() for m in os.environ.get(
        "REASONING_MODELS", "stealth/space-bunny-alpha"
    ).split(",") if m.strip()
)

# Set at install() time; the wrapper reads it as a module global on every call.
EFFORT = os.environ.get("REASONING_EFFORT", "high").strip() or "high"

_orig_create_chat_completion = llm_utils.create_chat_completion
_sig = inspect.signature(_orig_create_chat_completion)
_installed = False


def active_model() -> str | None:
    """Bare (provider-stripped) name of the model the chat is actually using.

    ``sync_config.sync()`` exports ``SMART_LLM`` as ``<provider>:<model>`` and
    ``Config.parse_llm`` splits on the first colon, so the model the library
    compares against the allow-list is the part after it. Falls back to
    config.json only so this is importable before sync has run.
    """
    raw = os.environ.get("SMART_LLM", "").strip()
    if not raw and CONFIG_JSON.exists():
        try:
            raw = str(json.loads(CONFIG_JSON.read_text()).get("SMART_LLM", "")).strip()
        except (OSError, ValueError):
            raw = ""
    if not raw:
        return None
    return raw.split(":", 1)[1] if ":" in raw else raw


@functools.wraps(_orig_create_chat_completion)
async def create_chat_completion(*args, **kwargs):
    """``create_chat_completion`` with the effort forced for our reasoning models.

    Everything else is passed straight through, so callers that omit
    ``reasoning_effort`` keep the library default and only the declared reasoning
    models are rewritten.
    """
    model = _sig.bind_partial(*args, **kwargs).arguments.get("model")
    if model in REASONING_MODELS:
        kwargs["reasoning_effort"] = EFFORT
    return await _orig_create_chat_completion(*args, **kwargs)


def install() -> None:
    """Open the allow-list, force the effort at both call sites, then assert it took.

    Idempotent: safe to call from every entry point that runs research. The
    asserts ask GPT Researcher's own objects what they now hold rather than
    trusting the assignments -- a silent no-op here would put the 12k wall and
    the empty-response failure straight back, and the only symptom would be a
    blank report, so it must fail at startup instead.
    """
    global _installed, EFFORT

    EFFORT = os.environ.get("REASONING_EFFORT", "high").strip() or "high"
    if EFFORT not in {e.value for e in base.ReasoningEfforts}:
        raise ValueError(
            f"REASONING_EFFORT={EFFORT!r} is not one of "
            f"{sorted(e.value for e in base.ReasoningEfforts)}. 'max' is not a "
            "member of ReasoningEfforts; 'high' is the value that measured 0/4 "
            "empty responses."
        )

    if _installed:
        return

    for model in REASONING_MODELS:
        if model not in base.SUPPORT_REASONING_EFFORT_MODELS:
            base.SUPPORT_REASONING_EFFORT_MODELS.append(model)

    # utils/llm.py holds its own reference to the list; only in-place mutation
    # reaches it, so a passing check here is the only proof the gate is open.
    missing = [m for m in REASONING_MODELS
               if m not in llm_utils.SUPPORT_REASONING_EFFORT_MODELS]
    if missing:
        raise RuntimeError(
            "reasoning-effort injection failed: utils/llm.py still does not see "
            f"{missing} in SUPPORT_REASONING_EFFORT_MODELS, so llm.py:89 will "
            "not send reasoning_effort. The model will reason unrestrained and "
            "return empty content."
        )

    for module in (query_processing, report_generation):
        module.create_chat_completion = create_chat_completion

    for module, attr in ((query_processing, "create_chat_completion"),
                         (report_generation, "create_chat_completion")):
        if getattr(module, attr) is not create_chat_completion:
            raise RuntimeError(
                f"reasoning-effort injection failed: {module.__name__}.{attr} "
                f"is {getattr(module, attr)!r}, not the wrapper. The report and "
                "sub-query calls will still request 'medium'."
            )

    # Third copy: Config.reasoning_effort, used by skills/deep_research.py.
    # Must be in the environment before Config is constructed, hence this runs
    # at the top of research() rather than at import.
    os.environ.setdefault("REASONING_EFFORT", EFFORT)

    _installed = True
    model = active_model()
    print(
        f"[EFFORT] reasoning_effort={EFFORT} for {list(REASONING_MODELS)}"
        f"  active_model={model!r}"
        f"  sends_param={model in llm_utils.SUPPORT_REASONING_EFFORT_MODELS}"
    )
