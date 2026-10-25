"""D1/D2 (accept1): short gap queries, no re-fetch of failed URLs, channel
failures visible in the user-facing report.

accept1 formulated every gap_query with the full NL question and repeated
a failing fetch 6x; transport failures lived only in verification.json.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("gap query tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import report_renderer as rr


def state():
    return {
        "question": "Descubra e compare cinco plugins para melhorar "
                    "planejamento no OpenCode e avalie tudo em detalhe?",
        "plan": {
            "entities": [{"id": "e1", "label": "Candidato 1"}],
            "criteria": [{"id": "c1", "label": "Melhoria de planejamento",
                          "required": True, "applies_to": ["e1"]}],
        },
        "evidence": {},
        "attempts": {},
        "discovery": {"open": True, "candidates": []},
        "rounds": [],
    }


class ShortGapQueryTest(unittest.TestCase):
    def test_query_uses_entity_and_criterion_labels(self):
        st = state()
        q = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "Melhoria de planejamento"})
        self.assertEqual(q, "Candidato 1 Melhoria de planejamento")
        self.assertLess(len(q), len(st["question"]))

    def test_query_never_contains_full_question(self):
        st = state()
        q = ac._short_gap_query(st, {"criterion_id": "c1"})
        self.assertNotIn(st["question"][:60], q)

    def test_fallback_truncates_question_without_plan(self):
        st = state()
        st["plan"] = {}
        q = ac._short_gap_query(st, {"criterion_id": "cx"})
        self.assertLessEqual(len(q), 141)
        self.assertTrue(q)

    def test_select_ops_uses_short_target(self):
        st = state()
        ops = ac.select_ops(
            st, [{"criterion_id": "c1",
                  "label": "Melhoria de planejamento"}], 1)
        self.assertEqual(ops[0]["target"],
                         "Candidato 1 Melhoria de planejamento")

    def test_failed_fetch_target_never_reoffered(self):
        st = state()
        st["discovery"]["candidates"] = ["https://example.org/broken.pdf"]
        st["attempts"] = {"c1": [{"channel": "web", "outcome": "failed",
                                  "target": "https://example.org/broken.pdf"}]}
        ops = ac.select_ops(
            st, [{"criterion_id": "c1",
                  "label": "Melhoria de planejamento"}], 1)
        self.assertNotEqual(ops[0].get("kind"), "read_source")
        self.assertNotIn("broken.pdf", ops[0].get("target", ""))


class ChannelLineTest(unittest.TestCase):
    def test_failures_visible_per_channel(self):
        line = rr._channel_line(
            {"rounds": [{"ops": [{"channel": "web", "outcome": "failed"}] * 9
                         + [{"channel": "web", "outcome": "new_useful"}] * 3}]},
            {})
        self.assertIn("web", line)
        self.assertIn("9", line)
        self.assertIn("falha", line)

    def test_empty_rounds_honest(self):
        line = rr._channel_line({"rounds": []}, {})
        self.assertIn("desconhecida", line)


if __name__ == "__main__":
    unittest.main()
