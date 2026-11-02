#!/usr/bin/env python3
"""Review ses_e64568cabffebBauww18L5cPiN: 4 confirmed body-hygiene findings.

Offline, generic, no product literals. Each test asserts the FIXED behavior;
they must FAIL before the fix (RED) and PASS after (GREEN). No network
(incl. 8082).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("review-fix test is offline (incl 8082)")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl
import report_renderer as rr

URL_A = "https://example.org/alpha-doc"
URL_B = "https://example.org/beta-doc"


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def hygiene_state():
    st = state_api.new_state("q review")
    st["plan"] = {
        "plan_id": "hr", "version": 1, "question": "q",
        "entities": [
            {"id": "e1", "label": "AlphaWidget", "required": True,
             "source_url": URL_A},
            {"id": "e2", "label": "BetaGadget", "required": True,
             "source_url": URL_B},
            {"id": "e3", "label": "GammaTool", "required": False,
             "source_url": URL_B},
        ],
        "criteria": [
            {"id": "c1", "label": "eixo um", "required": True,
             "description": "Eixo um: o que conta como evidencia."},
        ],
    }
    body_a = "AlphaWidget detalhes do eixo um " * 40
    body_b = "BetaGadget detalhes do eixo um " * 40
    st["evidence"] = {URL_A: body_a, URL_B: body_b}
    st["qualification"] = {URL_A: qual(body_a), URL_B: qual(body_b)}
    try:
        st["counters"]["documents"]["obtained"] = [
            rr._norm(URL_A), rr._norm(URL_B)]
        st["counters"]["documents"]["usable"] = [
            rr._norm(URL_A), rr._norm(URL_B)]
        st["counters"]["counts"]["obtained"] = 2
        st["counters"]["counts"]["usable"] = 2
    except Exception:
        pass
    return st


def body_of(md):
    return md.split("\n## 8.")[0]


class AssessRoundUrlMaskTest(unittest.TestCase):
    """Finding 1: id->label rewrite must not corrupt URLs nor persist so."""

    def test_justification_url_and_unknown_token_survive(self):
        st = hygiene_state()
        st["rounds"] = [{"round": 0}]
        url = "https://example.org/itens/e1"
        just = ("e1 cumpre o eixo; detalhe em " + url +
                " para conferir; e9 segue sem rotulo no plano")

        def fake_assess(plan, evidence, qualification, attempts=None):
            return [{"criterion_id": "c1", "state": "insufficient",
                     "justification": just, "origin": "assessor",
                     "references": []}]

        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        applied, _block = ac._assess_round(st, fake_assess, lg, None)
        self.assertTrue(applied, "evaluation must be applied")
        kept = applied[0]["justification"]
        self.assertIn(url, kept,
                      f"URL corrupted by id rewrite: {kept[:300]}")
        self.assertIn("e9", kept,
                      f"unknown token rewritten: {kept[:300]}")
        self.assertIn("AlphaWidget", kept,
                      f"prose id must still map to label: {kept[:300]}")
        persisted = [e.get("justification", "")
                     for e in (st.get("evaluations") or [])]
        self.assertTrue(any(url in j for j in persisted),
                       "corrupted justification persisted to evaluations")


class SourceLegendMentionTest(unittest.TestCase):
    """Finding 2: only legend-like lines drop; mere mentions survive."""

    LEGEND = ("> Legenda de fontes do corpus \u2014 toda afirma\u00e7\u00e3o "
              "traz cita\u00e7\u00e3o: [1](https://example.org/alpha-doc) "
              "[2](https://example.org/beta-doc)")
    MENTION = ("A nota sobre legenda de fontes acima mostra que a "
               "cita\u00e7\u00e3o inline basta.")

    def test_legend_like_line_drops(self):
        out = rr._strip_source_legend(self.LEGEND + "\nCorpo real.")
        self.assertNotIn("Legenda de fontes", out)
        self.assertIn("Corpo real.", out)

    def test_mere_mention_survives(self):
        out = rr._strip_source_legend(self.MENTION)
        self.assertIn("legenda de fontes", out,
                      f"legitimate line dropped: {out[:300]}")

    def test_render_keeps_mention_drops_legend(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        syn = (self.LEGEND + "\n\n" + self.MENTION +
               " AlphaWidget faz algo [1](https://example.org/alpha-doc).")
        md = rr.render_report(st, synthesis_text=syn)
        body = body_of(md)
        self.assertIn("legenda de fontes", body,
                      f"mention dropped from body: {body[:600]}")
        self.assertRegex(body, r"\[1\]",
                         f"inline citation must survive: {body[:600]}")


class BodySanitizePointsTest(unittest.TestCase):
    """Finding 3: gap.next, raw notes and synthesis share body hygiene."""

    def test_gap_next_sanitized(self):
        st = hygiene_state()
        st["question_coverage"] = {
            "status": "partial", "proportion": 0.1, "criteria": [],
            "gaps": [{"criterion_id": "c1", "label": "eixo um",
                      "state": "insufficient", "justification": "Falta.",
                      "next": ("Skipped: checar e1 em campo "
                               "(trecho com desconhecido-leg\u00edtimo)")}],
        }
        body = body_of(rr.render_report(st, synthesis_text="s\u00edntese."))
        self.assertNotIn("Skipped:", body, f"EN prefix leaked: {body[:600]}")
        self.assertIn("N\u00e3o verificado:", body)
        self.assertIn("AlphaWidget", body)
        self.assertNotRegex(body, r"\be1\b")
        self.assertNotIn("desconhecido-leg\u00edtimo", body)
        self.assertIn("sem fonte no corpus", body)

    def test_raw_note_sanitized(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        st["notes"] = ["Skipped: revisar e2 "
                       "(ponto com desconhecido-leg\u00edtimo)"]
        body = body_of(rr.render_report(st, synthesis_text="s\u00edntese."))
        self.assertNotIn("Skipped:", body, f"EN prefix leaked: {body[:600]}")
        self.assertIn("N\u00e3o verificado:", body)
        self.assertIn("BetaGadget", body)
        self.assertNotRegex(body, r"\be2\b")
        self.assertNotIn("desconhecido-leg\u00edtimo", body)
        self.assertIn("sem fonte no corpus", body)

    def test_synthesis_scope_jargon_paraphrased(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        syn = ("Achado geral.\ndesconhecido-leg\u00edtimo aparece no "
               "trecho sobre e1.")
        body = body_of(rr.render_report(st, synthesis_text=syn))
        self.assertNotIn("desconhecido-leg\u00edtimo", body,
                         f"jargon leaked: {body[:600]}")
        self.assertIn("sem fonte no corpus", body)
        self.assertIn("AlphaWidget", body)


class SubstitutionBodyLineTest(unittest.TestCase):
    """Finding 4: curated substitution line in body; raw stays annex-only."""

    def test_curated_line_in_body_raw_in_annex(self):
        st = hygiene_state()
        st["question_coverage"] = {"status": "partial", "proportion": 0.1,
                                   "criteria": [], "gaps": []}
        st["substitutions"] = [
            {"old": "e2", "new": "e3",
             "reason": "e3 cobre o eixo com fonte pr\u00f3pria", "round": 1}]
        st["notes"] = ["substitution: e2 -> e3 "
                       "(e3 cobre o eixo com fonte pr\u00f3pria)"]
        md = rr.render_report(st, synthesis_text="s\u00edntese.")
        body = body_of(md)
        annex = md.split("\n## 8.")[1]
        self.assertIn("BetaGadget \u2192 GammaTool", body,
                      f"curated substitution line missing: {body[-1200:]}")
        self.assertNotIn("substitution: e2 -> e3", body,
                         "raw internal note leaked into body")
        self.assertNotRegex(body, r"\be[23]\b",
                            f"bare id leaked into body: {body[-1200:]}")
        self.assertIn("substitution: e2 -> e3", annex,
                      "raw note must stay in the technical annex")


if __name__ == "__main__":
    unittest.main()
