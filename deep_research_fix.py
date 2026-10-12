#!/usr/bin/env python3
"""Guard the upstream deep-researcher zero-query branch. No site-packages edits.

Upstream bug (installed
``gpt_researcher/skills/deep_research.py``, ``DeepResearchSkill.deep_research``):
when ``generate_search_queries`` returns zero queries at some recursion depth,
the early return references ``all_learnings`` / ``all_visited_urls`` /
``all_citations`` / ``all_context`` / ``all_sources`` BEFORE their first
assignment (they are initialised after that block on the normal path).
Result: ``UnboundLocalError: 'all_learnings'`` -- observed killing a ~10h
deep run during final descent, with all in-memory learnings lost.

The intended behaviour is obvious from the return shape: stop the descent and
hand back empty collections. This adapter wraps the method (opt-in, via
``install()`` called by the entry point, same pattern as
``reasoning_effort.py``) and, ONLY for that specific ``UnboundLocalError``,
returns the intended empty shape with a log line. Any other exception
propagates untouched, so no other bug can hide behind this guard.
"""
import asyncio
import functools
import logging

logger = logging.getLogger("deep_fix")

_EMPTY = {
    "learnings": [],
    "visited_urls": set(),
    "citations": {},
    "context": [],
    "sources": [],
}

_installed = False


def install() -> bool:
    """Wrap DeepResearchSkill.deep_research with the zero-query guard."""
    global _installed
    if _installed:
        return True
    try:
        from gpt_researcher.skills.deep_research import DeepResearchSkill
    except ImportError as exc:
        logger.warning("deep_fix: DeepResearchSkill unavailable: %s", exc)
        return False
    original = DeepResearchSkill.deep_research

    @functools.wraps(original)
    async def guarded(self, *args, **kwargs):
        try:
            return await original(self, *args, **kwargs)
        except UnboundLocalError as exc:
            if "all_learnings" not in str(exc):
                raise
            # Preserve what was already accumulated instead of throwing the
            # run's work away: the caller passes learnings/citations/urls in,
            # and they are still valid even though the descent stopped early.
            learnings = list(kwargs.get("learnings") or [])
            citations = dict(kwargs.get("citations") or {})
            visited = set(kwargs.get("visited_urls") or ())
            logger.warning(
                "deep_fix: zero-query descent hit the unbound branch; "
                "returning carried-over state (learnings=%d citations=%d urls=%d) "
                "instead of crashing",
                len(learnings), len(citations), len(visited))
            return {
                "learnings": learnings,
                "visited_urls": visited,
                "citations": citations,
                "context": [],
                "sources": [],
                # Explicit: this branch found no NEW evidence, so any caller
                # must not read it as coverage.
                "insufficient_evidence": True,
            }

    DeepResearchSkill.deep_research = guarded
    _installed = True
    return True
