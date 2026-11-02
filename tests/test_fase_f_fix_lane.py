#!/usr/bin/env python3
"""Fase F fix-lane RED tests (offline, generic, no product literals).

Each test asserts the FIXED behavior from the review lane; they must FAIL
before the fix (RED, reason checked) and PASS after (GREEN).
Audithook blocks network incl. 8082.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("fix-lane test is offline (inclusive 8082)")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_planner as planner
import adaptive_state
import coverage_ledger as cl


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def desc_for(label):
    return (f"Eixo {label}: o que conta como evidencia operacional para este "
            f"eixo, com exemplos de trechos e condicoes de aceite.")


A = "https://example.org/na/a"
C = "https://example.org/na/c"


def qual_map(urls):
    return {u: {"status": "usable", "usable_text": "texto util " * 20,
                "excluded": False} for u in urls}


class Fix1NoDominanceNoSwapTest(unittest.TestCase):
    """Contrato 3: troca só com dominância estrita em _comparative_pairs."""

    def _state(self):
        p = {
            "plan_id": "fix1", "version": 1,
            "question": "Comparar dois candidatos",
            "entities": [
                {"id": "e1", "label": "cand um", "required": True,
                 "discovered": True, "source_url": A},
                {"id": "e2", "label": "cand dois", "required": True,
                 "discovered": True, "source_url": A},
                {"id": "e3", "label": "cand tres", "required": False,
                 "discovered": True, "source_url": C},
            ],
            "criteria": [
                {"id": "c1", "label": "eixo um", "required": True,
                 "per_candidate": True, "applies_to": ["e1", "e2", "e3"],
                 "description": desc_for("eixo um")},
            ],
            "initial_paths": ["consulta"],
        }
        st = adaptive_state.new_state("Comparar dois candidatos")
        st["plan"] = p
        st["evidence"] = {A: "nada util aqui " * 50,
                          C: "cand tres detalhes do eixo um " * 50}
        st["qualification"] = qual_map([A, C])
        st["qualification"][C] = {
            "status": "usable",
            "usable_text": "cand tres detalhes do eixo um " * 50,
            "excluded": False}
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "e1",
             "state": "insufficient", "justification": "tentativa",
             "origin": "assessor", "references": [{"url": A}]},
            {"criterion_id": "c1", "entity_id": "e2",
             "state": "insufficient", "justification": "sem evidencia",
             "origin": "assessor", "references": []},
        ]
        st["rounds"] = [{"round": 0}, {"round": 1}]
        return st

    def test_supported_without_dominance_does_not_swap(self):
        st = self._state()
        lg = cl.Ledger(st["plan"], run_id=st["run_id"])
        lg.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        for ev in st["evaluations"]:
            lg.evaluate(ev["criterion_id"], ev["state"],
                        ev["justification"], ev["origin"],
                        ev["references"], ev["entity_id"])
        # e3 é suportado (fonte própria coletada+mencionada) mas sem nenhuma
        # avaliação covered/partial com ref própria => sem dominância.
        self.assertFalse(ac._maybe_substitute(st, lg),
                         f"sem dominância não há troca: {st.get('notes')}")
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(emap["e2"].get("required", True))
        self.assertFalse(emap["e3"].get("required", True))
        recs = st.get("unexplored_alternatives") or []
        self.assertTrue(recs, "sem troca deve registrar unexplored")


class Fix2PromotePrefersGlobalTest(unittest.TestCase):
    def test_multi_premise_never_lands_on_per_candidate(self):
        st = adaptive_state.new_state("q promo global")
        st["plan"] = {
            "plan_id": "fix2", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            # c4 per_candidate primeiro de propósito: o bug cai nele.
            "criteria": [
                {"id": "c4", "label": "eixo quatro", "required": True,
                 "per_candidate": True, "applies_to": ["eA"],
                 "description": desc_for("quatro")},
                {"id": "c12", "label": "combinacao doze", "required": True,
                 "description": desc_for("doze")},
                {"id": "c13", "label": "combinacao treze", "required": True,
                 "description": desc_for("treze")},
            ],
        }
        ua, ub = "https://example.org/a", "https://example.org/b"
        doc_a = "AlphaWidget premissa um com detalhes " * 40
        doc_b = "BetaGadget premissa dois com detalhes " * 40
        st["evidence"] = {ua: doc_a, ub: doc_b}
        st["qualification"] = {ua: qual(doc_a), ub: qual(doc_b)}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        decl = {"sentence": ("INFERÊNCIA: complementaridade plausível entre "
                             "premissas [1][2] com limites explícitos."),
                "citations": [1, 2], "anchor_ok": True,
                "relation_ok": False,
                "scope": "limites explícitos",
                "premise_docs": [ua, ub]}
        ok = ac._promote_partial_declared(st, led, [decl], {1: ua, 2: ub})
        self.assertTrue(ok, f"promoção esperada: {st.get('notes')}")
        promoted_ids = [e.get("criterion_id")
                        for e in (st.get("evaluations") or [])
                        if isinstance(e, dict)]
        self.assertTrue(promoted_ids, st.get("notes"))
        for pid in promoted_ids:
            self.assertIn(pid, ("c12", "c13"),
                          f"inferência multi-premissa nunca em per_candidate "
                          f"(c4): {promoted_ids}")


class Fix3ExplicitPlanQualityTest(unittest.TestCase):
    def test_explicit_weak_description_rejected(self):
        p = {
            "plan_id": "fix3", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "applies_to": ["eA"], "description": "curto"}],
        }
        with self.assertRaises(planner.PlanError):
            planner.plan_from_explicit(dict(p))


class Fix4VetoScopedTest(unittest.TestCase):
    def test_only_triggering_sentence_rewritten(self):
        import report_renderer as renderer
        src_a = "https://example.org/alpha-source"
        body_a = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q veto escopo")
        st["plan"] = {
            "plan_id": "fix4", "version": 1, "question": "q",
            "entities": [
                {"id": "eA", "label": "AlphaWidget", "required": True,
                 "source_url": src_a},
                {"id": "eB", "label": "BetaGadget", "required": True,
                 "source_url": "https://example.org/beta-source"},
            ],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {src_a: body_a}
        st["qualification"] = {src_a: qual(body_a)}
        st["question_coverage"] = {"status": "partial", "proportion": 0.0,
                                   "criteria": [], "gaps": []}
        synth = ("AlphaWidget com fonte propria está fora do corpus. "
                 "BetaGadget legitimamente ausente está fora do corpus.")
        out = renderer._veto_outside_corpus(st, synth)
        low = out.lower()
        # Sentença de AlphaWidget (com doc) reescrita...
        self.assertNotIn("alphawidget com fonte propria está fora do corpus",
                         low, f"sentença com doc deve ser reescrita: {out}")
        # ...mas a de BetaGadget (sem doc) preservada.
        self.assertIn("betagadget legitimamente ausente está fora do corpus",
                      low, f"sentença sem doc deve ser preservada: {out}")


class Fix5AnalisadaRequiresEntityDocTest(unittest.TestCase):
    def test_listing_ref_is_not_cell_analysis(self):
        src = "https://example.org/alpha-source"
        listing = "https://example.org/catalog-listing"
        ent = {"id": "eA", "label": "AlphaWidget", "source_url": src}
        body_src = "AlphaWidget detalhes do eixo um " * 60
        body_list = "texto generico de catalogo sem o nome " * 60
        st = adaptive_state.new_state("q analisada")
        st["evidence"] = {src: body_src, listing: body_list}
        st["qualification"] = {src: qual(body_src),
                               listing: qual(body_list)}
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "eA", "state": "partial",
             "justification": "mencao em lista", "origin": "assessor",
             "references": [{"url": listing}]}]
        status = ac._candidate_selection_status(st, ent, [])
        self.assertFalse(status["analisada_celula"],
                         f"ref de lista não é análise da célula: {status}")

    def test_own_doc_ref_is_cell_analysis(self):
        src = "https://example.org/alpha-source"
        ent = {"id": "eA", "label": "AlphaWidget", "source_url": src}
        body_src = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q analisada ok")
        st["evidence"] = {src: body_src}
        st["qualification"] = {src: qual(body_src)}
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "eA", "state": "partial",
             "justification": "fonte propria", "origin": "assessor",
             "references": [{"url": src}]}]
        status = ac._candidate_selection_status(st, ent, [src])
        self.assertTrue(status["analisada_celula"],
                        f"ref própria deve contar: {status}")


class Fix6HysteresisFingerprintTest(unittest.TestCase):
    def test_changed_fingerprint_releases_block(self):
        st = adaptive_state.new_state("q histerese")
        A2 = "https://example.org/h1"
        B2 = "https://example.org/h2"
        st["plan"] = {
            "plan_id": "fix6", "version": 1, "question": "q",
            "candidate_target": 1,
            "entities": [
                {"id": "eOld", "label": "AlphaWidget", "required": True,
                 "discovered": True, "source_url": A2},
                {"id": "eNew", "label": "BetaGadget", "required": False,
                 "discovered": True, "source_url": B2},
            ],
            "criteria": [
                {"id": "c1", "label": "eixo um", "required": True,
                 "per_candidate": True, "applies_to": ["eOld", "eNew"],
                 "description": desc_for("eixo um")},
                {"id": "c2", "label": "eixo dois", "required": True,
                 "per_candidate": True, "applies_to": ["eOld", "eNew"],
                 "description": desc_for("eixo dois")},
            ],
        }
        st["evidence"] = {A2: "AlphaWidget eixo um parcial " * 40,
                          B2: ("BetaGadget eixo um coberto com detalhes. "
                               "BetaGadget eixo dois coberto com detalhes. "
                               * 40)}
        st["qualification"] = {u: qual(t)
                               for u, t in st["evidence"].items()}
        st["rounds"] = [{"round": 0}, {"round": 1}]
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("c1", "partial", "AlphaWidget parcial fraco",
                     "assessor", [{"url": A2}], "eOld")
        led.evaluate("c1", "covered", "BetaGadget cobre eixo um",
                     "assessor", [{"url": B2}], "eNew")
        led.evaluate("c2", "covered", "BetaGadget cobre eixo dois",
                     "assessor", [{"url": B2}], "eNew")
        # Estado sem refs para eOld (histerese atual vetaria o reverso);
        # so eNew tem refs proprias (dominancia vale).
        st["evaluations"] = [
            {"criterion_id": "c1", "entity_id": "eNew",
             "state": "covered", "justification": "j",
             "origin": "assessor", "references": [{"url": B2}]},
            {"criterion_id": "c2", "entity_id": "eNew",
             "state": "covered", "justification": "j",
             "origin": "assessor", "references": [{"url": B2}]},
        ]
        # Historico reverso (eNew->eOld) com fingerprint obsoleto: a
        # evidencia atual difere da registrada => nao pode bloquear.
        st["_substitution_history"] = [
            {"old": "eNew", "new": "eOld", "round": 1,
             "fingerprint": "0/0->9/9"}]
        self.assertTrue(ac._maybe_substitute(st, led),
                        f"fingerprint mudou: histerese nao bloqueia: "
                        f"{st.get('notes')}")


class Fix7CutAtSpaceTest(unittest.TestCase):
    def test_early_space_cut_never_mid_word(self):
        import report_renderer as renderer
        text = ("ab " * 100) + ("c" * 400 + " fim.")
        cut = renderer._cut_at_sentence(text, 600)
        self.assertIn("[…]", cut, cut[:200])
        import re as _re
        self.assertNotRegex(cut, r"c{20}",
                            f"corte mid-word antes de 2/3: {cut[:300]}")

    def test_no_space_hard_cut_marks_truncation(self):
        import report_renderer as renderer
        text = "z" * 900
        cut = renderer._cut_at_sentence(text, 600)
        self.assertTrue(cut.rstrip().endswith("[…]") or "truncado" in cut,
                        f"corte duro deve marcar: {cut[:120]}")
        self.assertLessEqual(len(cut), 640, cut[:120])


class Fix8DedupTest(unittest.TestCase):
    def test_unexplored_same_entity_collapses_in_prompt(self):
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "texto"

        write = ac.make_model_writer(fake_client, max_chars=6000)
        plan = {
            "plan_id": "fix8", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        recs = [{"entity": "BetaGadget", "entity_id": "eB",
                 "urls": [f"https://example.org/{i}"]} for i in range(5)]
        view = {"question": "q", "plan": plan,
                "evidence": {"https://example.org/x": "AlphaWidget x " * 50},
                "user_context": {},
                "question_coverage": {"criteria": []}, "stop": {},
                "rounds": [], "evaluations": [],
                "unexplored_alternatives": recs,
                "substitutions": [], "semantic_rank": []}
        write(view)
        prompt = seen.get("prompt", "")
        self.assertEqual(prompt.count("BetaGadget"), 1,
                         f"5× mesma entidade deve colapsar: {prompt[:800]}")

    def test_record_unexplored_no_duplicate_on_repeat(self):
        st = adaptive_state.new_state("q dedup")
        st["plan"] = {
            "plan_id": "fix8b", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "AlphaWidget",
                          "required": True, "discovered": True}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "per_candidate": True, "applies_to": ["eA"],
                          "description": desc_for("eixo um")}],
        }
        st["discovery"] = {"candidates": ["https://example.org/alpha-x"]}
        st["evidence"] = {}
        st["qualification"] = {}
        ac._record_unexplored(st, ["eA"])
        n1 = len(st.get("unexplored_alternatives") or [])
        ac._record_unexplored(st, ["eA"])
        n2 = len(st.get("unexplored_alternatives") or [])
        self.assertEqual(n1, n2, f"repeat não duplica: {n1} vs {n2}")


class Fix9StrictIdentityTest(unittest.TestCase):
    def test_veto_ignores_substring_entity(self):
        import report_renderer as renderer
        # Entidade "Alpha"; doc/sentença falam de "AlphaWidget" (outra
        # entidade): substring "alpha" casa, identidade estrita não.
        src = "https://example.org/other-source"
        body = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q identidade")
        st["plan"] = {
            "plan_id": "fix9", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "Alpha", "required": True,
                          "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["question_coverage"] = {"status": "partial", "proportion": 0.0,
                                   "criteria": [], "gaps": []}
        synth = ("Alpha está fora do corpus: nenhum documento trata dele. "
                 "AlphaWidget tem fonte e foi analisado.")
        out = renderer._veto_outside_corpus(st, synth)
        self.assertIn("Alpha está fora do corpus", out,
                      f"substring não pode vetar outra entidade: {out}")

    def test_contradictory_absence_ignores_substring_doc(self):
        import verification_report as vr
        src = "https://example.org/other-source"
        body = "AlphaWidget detalhes do eixo um " * 60
        st = adaptive_state.new_state("q identidade audit")
        st["plan"] = {
            "plan_id": "fix9b", "version": 1, "question": "q",
            "entities": [{"id": "eA", "label": "Alpha", "required": True,
                          "source_url": src}],
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "description": desc_for("eixo um")}],
        }
        st["evidence"] = {src: body}
        st["qualification"] = {src: qual(body)}
        st["report"] = {"numbers": {"1": src}}
        report = "Alpha está fora do corpus. Nenhum documento trata [1]."
        note = vr._contradictory_absence(report, st)
        self.assertEqual(note, "",
                         f"doc de outra entidade não contradiz: {note}")


if __name__ == "__main__":
    unittest.main()
