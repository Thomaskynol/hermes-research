#!/usr/bin/env python3
"""CustomRetriever with a configurable HTTP timeout. No site-packages edits.

gpt_researcher/retrievers/custom/custom.py:50 hardcodes ``timeout=20`` and offers
no env var or config to change it. Our endpoint fetches real transcripts at
browser level, so it legitimately runs longer: 5 measured queries gave 9.0s,
17.0s, 18.4s, 20.8s, 22.7s -- 2 of 5 over the wall, and a re-measurement of
"kubernetes deployment" landed at 19.5s, i.e. the 20s limit is not a
reproducible failure, it is a coin flip. That is a misconfigured timeout, not a
slow server, so the timeout is what gets changed.

Why rebinding one attribute is enough
-------------------------------------
``gpt_researcher.actions.retriever.get_retriever`` resolves ``"custom"`` with a
*deferred* import executed at call time::

    case "custom":
        from gpt_researcher.retrievers import CustomRetriever
        return CustomRetriever

(actions/retriever.py:104). ``CustomRetriever`` is re-exported from
``gpt_researcher/retrievers/__init__.py:4`` and imported by that full path
nowhere else in the package, so the single package attribute is the only hop.
Rebinding it at process start is therefore complete, touches one name, and is
reversible -- unlike patching ``requests.get``, which would leak into every
HTTP call in the process and race across GPT Researcher's retriever threads.

The one thing a subclass cannot avoid: ``CustomRetriever.search`` inlines
``requests.get`` with no seam to override, so ``search`` is reproduced below
rather than delegated. The single behavioural difference is the timeout; the
rest matches upstream so error handling and payload validation stay identical.
"""
import os

import requests

import gpt_researcher.retrievers
from gpt_researcher.actions.retriever import get_retriever
from gpt_researcher.retrievers import CustomRetriever

# 20.8s was the worst of the 5 measured queries and the budget is 20s, so a
# cold run with 3 uncached transcripts can exceed it. 60s is headroom without
# being able to hang indefinitely. A bad value raises at import, which is
# intended: a silent fallback would put the 20s wall back without telling us.
TIMEOUT_S = int(os.getenv("VAST_RETRIEVER_TIMEOUT_S", "60"))


class VastCustomRetriever(CustomRetriever):
    """CustomRetriever with a raised, configurable timeout."""

    def search(self, max_results: int = 5) -> list[dict]:
        try:
            response = requests.get(
                self.endpoint,
                params={**self.params, "query": self.query},
                timeout=self.TIMEOUT_S,  # upstream: timeout=20
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Failed to retrieve search results: {e}")
            return []

        if payload is None:
            return []
        if not isinstance(payload, list):
            print(
                "Custom retriever response must be a JSON list of "
                "{url, raw_content} objects; got "
                f"{type(payload).__name__}"
            )
            return []
        return payload


# Read by the verification command and by callers that log the effective value.
VastCustomRetriever.TIMEOUT_S = TIMEOUT_S


def install():
    """Point GPT Researcher's "custom" retriever at the subclass, then assert it took.

    The assert asks GPT Researcher's own factory what it resolves, rather than
    trusting the assignment. A no-op here would leave the 20s wall in place and
    the only symptom would be a timeout, so it must fail at startup instead.
    """
    gpt_researcher.retrievers.CustomRetriever = VastCustomRetriever
    in_use = get_retriever("custom")
    if in_use is not VastCustomRetriever:
        raise RuntimeError(
            "retriever injection failed: get_retriever('custom') resolved to "
            f"{in_use!r}, not VastCustomRetriever. The 20s timeout is still in "
            "effect; fix the wiring before running research."
        )
    if getattr(in_use, "TIMEOUT_S", None) != TIMEOUT_S:
        raise RuntimeError(
            f"retriever injection failed: in-use class has "
            f"TIMEOUT_S={getattr(in_use, 'TIMEOUT_S', None)!r}, expected {TIMEOUT_S!r}."
        )
    return in_use


install()
