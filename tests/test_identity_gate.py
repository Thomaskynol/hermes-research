"""Identity/aboutness gate (accept17 residuals): foreign material sharing
generic vocabulary (health PDFs, scribd, instagram mirrors, uptodown,
open-code.ai vs opencode.ai, generic blogs) must not become usable
evidence for an entity-led op.

Controlled cases: the legacy vocabulary gate fetches anything sharing a
word with the question/target; the identity rule additionally requires an
entity-led hit to mention the entity's distinctive name part.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("identity gate test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac


def state_with_entity():
    return {
        "question": "Descubra e compare cinco plugins para planejamento "
                    "no OpenCode",
        "notes": [],
        "plan": {
            "entities": [
                {"id": "e1", "label": "opencode-planner",
                 "source_url": "https://github.com/x/opencode-planner"},
            ],
            "criteria": [{"id": "c1", "label": "planejamento",
                           "required": True, "applies_to": ["e1"]}],
        },
    }


def entity_op(eid="e1"):
    return {"op_id": "op-1", "kind": "gap_query", "channel": "web",
            "target": "opencode-planner planejamento",
            "criterion_id": "c1", "entity_id": eid}


class IdentityGateTest(unittest.TestCase):
    def test_generic_blog_sharing_vocab_is_gated_for_entity_op(self):
        st = state_with_entity()
        hit = {"url": "https://blog.example/top-plugins",
               "title": "Top 10 OpenCode plugins",
               "snippet": "review and testing workflow plugins for "
                          "opencode productivity"}
        # Legacy vocabulary gate alone would fetch (opencode/plugins/
        # review/testing all match the question/target terms).
        self.assertTrue(ac._hit_gated_by_snippet(st, entity_op(), hit),
                        "blog genérico sem menção a 'planner' não pode "
                        "virar evidência do candidato")
        self.assertTrue(any("entidade" in n for n in st["notes"]))

    def test_entity_doc_is_fetched(self):
        st = state_with_entity()
        hit = {"url": "https://github.com/x/opencode-planner",
               "title": "x/opencode-planner: planning workflows",
               "snippet": "planner plugin for opencode with todo "
                          "tracking"}
        self.assertFalse(ac._hit_gated_by_snippet(st, entity_op(), hit))

    def test_homonym_domain_without_entity_mention_is_gated(self):
        st = state_with_entity()
        hit = {"url": "https://open-code.ai/docs",
               "title": "Open-Code AI",
               "snippet": "OpenCode AI coding assistant plans and pricing"}
        self.assertTrue(ac._hit_gated_by_snippet(st, entity_op(), hit),
                        "homônimo open-code.ai sem 'planner' não é o candidato")

    def test_mirror_without_entity_mention_is_gated(self):
        st = state_with_entity()
        hit = {"url": "https://opencode.en.uptodown.com/android",
               "title": "OpenCode for Android download",
               "snippet": "download opencode apk mirror latest version"}
        self.assertTrue(ac._hit_gated_by_snippet(st, entity_op(), hit))

    def test_non_entity_op_keeps_legacy_behaviour(self):
        st = state_with_entity()
        op = {"op_id": "op-9", "kind": "gap_query", "channel": "web",
              "target": "planejamento", "criterion_id": "c1"}
        hit = {"url": "https://blog.example/top-plugins",
               "title": "Top 10 OpenCode plugins",
               "snippet": "review and testing workflow plugins for "
                          "opencode productivity"}
        self.assertFalse(ac._hit_gated_by_snippet(st, op, hit))

    def test_entity_without_distinctive_tokens_keeps_legacy(self):
        st = state_with_entity()
        st["plan"]["entities"].append(
            {"id": "e2", "label": "OpenCode Marketplace"})
        op = dict(entity_op("e2"))
        hit = {"url": "https://blog.example/top-plugins",
               "title": "Top 10 OpenCode plugins",
               "snippet": "review and testing workflow plugins for "
                          "opencode productivity"}
        self.assertFalse(ac._hit_gated_by_snippet(st, op, hit))


class DistinctiveTokensTest(unittest.TestCase):
    def test_planner_is_distinctive(self):
        toks = ac._entity_distinctive_tokens(
            {"id": "e1", "label": "opencode-planner"})
        self.assertIn("planner", toks)
        self.assertNotIn("opencode", toks)
        self.assertNotIn("plugin", toks)

    def test_fully_generic_label_has_no_distinctive(self):
        self.assertEqual(ac._entity_distinctive_tokens(
            {"id": "e2", "label": "OpenCode Marketplace Plugin"}), [])


if __name__ == "__main__":
    unittest.main()
