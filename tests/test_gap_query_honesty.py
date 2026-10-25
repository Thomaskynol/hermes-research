"""D1/D2 (accept1): short gap queries, no re-fetch of failed URLs, channel
failures visible in the user-facing report.

accept1 formulated every gap_query with the full NL question and repeated
a failing fetch 6x; transport failures lived only in verification.json.
"""
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("gap query tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import report_renderer as rr
import run_budget as rb


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
        # accept3: a pergunta traz o nome próprio distintivo (OpenCode);
        # a query curta o preserva como âncora (antes derivava p/ genérico).
        # stopwords: scaffolding interrogativo ('descubra') é filtrado.
        self.assertEqual(q, "Candidato 1 Melhoria de planejamento "
                            "opencode")
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
                         "Candidato 1 Melhoria de planejamento "
                         "opencode")

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


def gate_state(question, target):
    st = state_api.new_state(question)
    st["discovery"] = {"candidates": [], "open": True}
    op = {"op_id": "op-1", "kind": "gap_query", "channel": "web",
          "target": target, "criterion_id": "c1", "status": "in-progress"}
    st["pending_ops"].append(dict(op))
    return st, [op]


def gate_run(st, ops, hits, fetched, concurrency=1):
    def search(target, channel="web"):
        return hits

    def fetch(url):
        fetched.append(url)
        return "COVER substance about " + url + " (injected corpus text)"

    resolved = ac.resolve_adaptive("light", {"concurrency": concurrency,
                                             "time_s": 60})
    budget = rb.Budget({"queries": 20, "extractions": 20, "time_s": 60},
                       profile="light")
    t_start = time.monotonic()
    ac._execute_ops(st, ops, search, fetch, budget, resolved,
                    time.monotonic, t_start, None, 0)
    return budget


class QuestionAnchorTest(unittest.TestCase):
    def test_anchor_appended_when_missing(self):
        st = state()
        st["plan"] = {
            "entities": [{"id": "e1", "label": "Plugin Alfa"}],
            "criteria": [{"id": "c1", "label": "Suporte a atalhos",
                          "required": True, "applies_to": ["e1"]}],
        }
        q = ac._short_gap_query(
            st, {"criterion_id": "c1", "label": "Suporte a atalhos"})
        # 'OpenCode' (nome próprio da pergunta) ausente nos labels.
        self.assertIn("opencode", q)

    def test_anchor_not_duplicated_when_present(self):
        st = state()
        st["plan"] = {
            "entities": [{"id": "e1", "label": "OpenCode CLI"}],
            "criteria": [{"id": "c1", "label": "atalhos",
                          "required": True, "applies_to": ["e1"]}],
        }
        q = ac._short_gap_query(st, {"criterion_id": "c1", "label": "atalhos"})
        self.assertEqual(q.lower().count("opencode"), 1)


class SnippetGateTest(unittest.TestCase):
    QUESTION = "Como avaliar plugins de planejamento no OpenCode?"
    TARGET = "Candidato 1 Melhoria de planejamento opencode"
    JUNK = {"url": "https://saude.example/plano-familia",
            "title": "Plano de Saúde Familiar",
            "snippet": "cobertura completa para toda a família, "
                       "planos a partir de R$99"}

    def test_irrelevant_hit_skipped_without_spend(self):
        st, ops = gate_state(self.QUESTION, self.TARGET)
        hits = [{"url": "https://docs.example/opencode-plugins",
                 "title": "OpenCode plugin guide",
                 "snippet": "planning workflow plugins for OpenCode "
                            "with shortcuts"},
                dict(self.JUNK)]
        fetched = []
        budget = gate_run(st, ops, hits, fetched)
        self.assertEqual(fetched, ["https://docs.example/opencode-plugins"])
        self.assertEqual(budget.snapshot()["used"]["extractions"], 1)
        self.assertEqual(st["consumption"]["fetches"], 1)
        self.assertTrue(any("irrelevância" in n and "plano-familia" in n
                            for n in st["notes"]),
                        st["notes"])
        self.assertEqual(ops[0]["outcome"], "new_useful")

    def test_absent_or_empty_snippet_fetches_normally(self):
        st, ops = gate_state(self.QUESTION, self.TARGET)
        hits = [{"url": "https://docs.example/sem-snippet"},
                {"url": "https://docs.example/vazio",
                 "title": "", "snippet": "   "}]
        fetched = []
        budget = gate_run(st, ops, hits, fetched)
        self.assertEqual(fetched, ["https://docs.example/sem-snippet",
                                   "https://docs.example/vazio"])
        self.assertEqual(budget.snapshot()["used"]["extractions"], 2)

    def test_english_snippet_matches_via_bilingual_expansion(self):
        st, ops = gate_state("como lidar com erro em produção?",
                             "Candidato 1 Modos de falha")
        hit = {"url": "https://example.org/eng",
               "title": "Production guide",
               "snippet": "failure modes in production systems and "
                          "recovery steps"}
        self.assertNotIn("falha", hit["snippet"].lower())
        self.assertIn("failure", ac._expand_terms_en(["falha"]))
        fetched = []
        gate_run(st, ops, [hit], fetched)
        self.assertEqual(fetched, ["https://example.org/eng"])

    def test_all_gated_means_nogain_never_failed(self):
        st, ops = gate_state(self.QUESTION, self.TARGET)
        hits = [dict(self.JUNK),
                {"url": "https://bank.example/consorcio",
                 "title": "Consórcio de veículos",
                 "snippet": "parcelas que cabem no bolso, contemple "
                            "sua carta de crédito"}]
        fetched = []
        budget = gate_run(st, ops, hits, fetched, concurrency=2)
        self.assertEqual(fetched, [])
        self.assertEqual(budget.snapshot()["used"]["extractions"], 0)
        self.assertEqual(st["consumption"]["fetches"], 0)
        self.assertEqual(ops[0]["outcome"], "nogain")
        self.assertEqual(ops[0]["status"], "done")
        self.assertEqual(sum("irrelevância" in n for n in st["notes"]), 2)


if __name__ == "__main__":
    unittest.main()
