#!/usr/bin/env python3
"""Accept38 frozen-artifact fixes (offline, generic, no product literals).

Three defects reproduced from the frozen accept38 artifacts (report.md §1
with ~53 `[(fonte)][N]` placeholders; false §0×§7 contradiction note about
a short label caused by a hyphen-compound line; self-contradiction where a
trailing-slash citation variant rendered `(fora do corpus)` while the same
entity holds `[N]` elsewhere).

Each test asserts the FIXED behavior; they must FAIL before the fix (RED,
for the expected reason) and PASS after (GREEN). Audithook blocks network
incl. 8082.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept38 test is offline (inclusive 8082)")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state
import coverage_ledger as cl
import report_renderer as rr
import verification_report as vr


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def desc_for(label):
    return (f"Eixo {label}: o que conta como evidencia operacional para este "
            f"eixo, com exemplos de trechos e condicoes de aceite.")


URL_A = "https://example.org/alpha-repo"


def tiny_state(label="Alpha-Beta", url=URL_A):
    st = adaptive_state.new_state("q tiny")
    st["plan"] = {
        "plan_id": "t38", "version": 1, "question": "q",
        "entities": [{"id": "e1", "label": label, "required": True,
                      "source_url": url}],
        "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                      "description": desc_for("um")}],
    }
    body = f"{label} detalhes do eixo um " * 40
    st["evidence"] = {url: body}
    st["qualification"] = {url: qual(body)}
    st["question_coverage"] = {"status": "partial", "proportion": 0.0,
                               "criteria": [], "gaps": []}
    try:
        st["counters"]["documents"]["obtained"] = [rr._norm(url)]
        st["counters"]["documents"]["usable"] = [rr._norm(url)]
        st["counters"]["counts"]["obtained"] = 1
        st["counters"]["counts"]["usable"] = 1
    except Exception:
        pass
    return st


class FontePlaceholderTest(unittest.TestCase):
    """Defect 1: `[(fonte)]` placeholder never emitted, stripped if residual."""

    def _writer_prompt(self):
        st = tiny_state("AlphaWidget", "https://example.org/w")
        body = "AlphaWidget detalhes " * 10
        st["evidence"] = {"https://example.org/w": body}
        st["qualification"] = {"https://example.org/w": qual(body)}
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio"

        write = ac.make_model_writer(fake_client, max_chars=2400)
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        block = led.compute()
        view = {"question": st["question"], "plan": st["plan"],
                "evidence": dict(st["evidence"]), "user_context": {},
                "question_coverage": block, "stop": {}, "rounds": [],
                "evaluations": [], "unexplored_alternatives": [],
                "substitutions": [], "semantic_rank": []}
        write(view)
        return seen.get("prompt", "")

    def test_writer_prompt_bans_fonte_placeholder(self):
        prompt = self._writer_prompt()
        self.assertIn("[(fonte)]", prompt,
                      "prohibition must name the banned token literally")
        self.assertIn("nunca emita", prompt.lower(),
                      f"prompt must prohibit the placeholder: {prompt[:800]}")

    def test_render_strips_fonte_placeholder_keeping_number(self):
        st = tiny_state()
        syn = ("Alpha-Beta instala itens [(fonte)](https://example.org/alpha-repo)"
               " e nada mais.")
        md = rr.render_report(st, synthesis_text=syn)
        self.assertNotIn("[(fonte)]", md, f"residual token: {md[:600]}")
        self.assertRegex(md, r"\[1\]",
                         f"real citation number must survive: {md[:600]}")

    def test_rewrite_refs_keeps_number_without_placeholder(self):
        out, outside = rr._rewrite_refs(
            "veja [(fonte)](https://example.org/alpha-repo) fim",
            {rr._norm("https://example.org/alpha-repo"): 3}, set())
        self.assertNotIn("[(fonte)]", out)
        self.assertIn("[3]", out)
        self.assertEqual(outside, [])


class HyphenIdentityTest(unittest.TestCase):
    """Defect 2: short label is not mentioned by a hyphen-compound line."""

    LINE = ("Alpha-Beta foca em instalar itens [(fonte)] (fora do corpus), "
            "enquanto AlphaWidget foca em revisao.")

    def test_short_label_not_mentioned_in_hyphen_compound(self):
        self.assertFalse(
            vr._entity_mentioned("Alpha", "e1", self.LINE),
            "hyphen-joined compound must not count as the short entity")

    def test_full_hyphen_label_is_mentioned(self):
        self.assertTrue(
            vr._entity_mentioned("Alpha-Beta", "e6", self.LINE),
            "full hyphen form must still match separator-insensitively")

    def test_short_token_hyphen_form_matches(self):
        self.assertTrue(
            vr._entity_mentioned("EC2 instance", "e8",
                                 "Use EC2-instance para implantar."),
            "hyphenated full form with short token must match "
            "(token fallback needs 2x len>=4)")

    def test_contradictory_absence_ignores_hyphen_prefix(self):
        src = "https://example.org/alpha-source"
        body = "Alpha detalhes do eixo um " * 60
        st = adaptive_state.new_state("q identidade audit")
        st["plan"] = {
            "plan_id": "hx", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "Alpha", "required": True,
                          "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["report"] = {"numbers": {"1": src}}
        report = ("Alpha-Beta instala itens (fora do corpus). "
                  "Nenhum documento trata [1].")
        self.assertEqual(vr._contradictory_absence(report, st), "",
                         "compound line must not indict the short entity")

    def test_contradictory_absence_keeps_real_contradiction(self):
        src = "https://example.org/alpha-source"
        body = "Alpha detalhes do eixo um " * 60
        st = adaptive_state.new_state("q identidade audit")
        st["plan"] = {
            "plan_id": "hx2", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "Alpha", "required": True,
                          "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["report"] = {"numbers": {"1": src}}
        report = ("Alpha instala itens (fora do corpus). "
                  "Nenhum documento trata [1].")
        self.assertTrue(vr._contradictory_absence(report, st),
                        "genuine absence-vs-usable contradiction must stay")


class SlashVariantRefTest(unittest.TestCase):
    """Defect 3: trailing-slash citation variant resolves to the corpus doc."""

    def test_markdown_slash_variant_resolves(self):
        out, outside = rr._rewrite_refs(
            "veja [(fonte)](https://example.org/alpha-repo/) fim",
            {rr._norm("https://example.org/alpha-repo"): 3}, set())
        self.assertIn("[3]", out, f"slash variant must resolve: {out}")
        self.assertNotIn("fora do corpus", out)
        self.assertEqual(outside, [])

    def test_bare_slash_variant_resolves(self):
        cited = set()
        out, outside = rr._rewrite_refs(
            "veja https://example.org/alpha-repo/ fim.",
            {rr._norm("https://example.org/alpha-repo"): 3}, cited)
        self.assertIn("[3]", out, f"bare slash variant: {out}")
        self.assertEqual(outside, [])

    def test_bare_url_keeps_trailing_period(self):
        out, _ = rr._rewrite_refs(
            "Veja https://exemplo.com. Segue.",
            {"https://exemplo.com": 3}, set())
        self.assertIn("[3]. Segue", out)

    def test_genuinely_outside_url_still_flagged(self):
        out, outside = rr._rewrite_refs(
            "veja https://fora.example/ausente fim.",
            {rr._norm("https://example.org/alpha-repo"): 3}, set())
        self.assertIn("fora do corpus", out)
        self.assertEqual(outside, ["https://fora.example/ausente"])

    def test_render_resolves_slash_variant_without_contradiction(self):
        st = tiny_state()
        syn = ("Alpha-Beta instala itens [(fonte)](https://example.org/alpha-repo/) "
               "e nada mais.")
        md = rr.render_report(st, synthesis_text=syn)
        self.assertNotIn("fora do corpus", md.split("## 2.")[0],
                         f"slash variant must not read as outside: {md[:600]}")
        self.assertRegex(md, r"\[1\]")


if __name__ == "__main__":
    unittest.main()
