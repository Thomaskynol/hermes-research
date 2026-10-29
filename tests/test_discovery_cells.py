"""Discovery cells: versioned entities get investigated and evaluated.

Regression from accept6: propose_entity fired 3x and entities were
versioned (remap+inheritance), but rounds kept emitting generic ops and the
assessor evaluated only the blob/None cells — new entities were never
investigated nor evaluated per cell. General mechanisms (no question names):

- G1a: proposal entity.url validated against corpus/candidates becomes
  entity source_url; invented URLs are ignored with a note.
- G1b: ledger emits an actionable per-cell gap (criterion, entity,
  source_url) for uncovered cells with their own source.
- G1c: select_ops turns a cell gap into a direct read_source (one shot).
- G2: the assessor prompt enumerates required (criterion x entity) cells.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("discovery cells test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

URL_REPO = "https://github.com/o/r"
URL_OTHER = "https://github.com/o/other"


def cell_plan():
    return {
        "plan_id": "cell-1", "version": 1,
        "entities": [{"id": "e0", "label": "Alvo", "required": True},
                     {"id": "e1", "label": "Repo X", "required": True,
                      "source_url": URL_REPO}],
        "criteria": [{"id": "c0", "label": "funciona", "required": True,
                      "applies_to": ["e0", "e1"]}],
        "initial_paths": ["q"],
    }


class LedgerCellGapsTest(unittest.TestCase):
    def test_g1b_cell_gap_para_fonte_propria_nao_coletada(self):
        b = cl.Ledger(cell_plan()).compute()
        cells = [(g.get("criterion_id"), g.get("entity_id"),
                  g.get("source_url")) for g in b["gaps"]]
        self.assertIn(("c0", None, None), cells)  # gap por critério mantido
        self.assertIn(("c0", "e1", URL_REPO), cells)

    def test_g1b_sem_cell_gap_quando_fonte_ja_coletada(self):
        led = cl.Ledger(cell_plan())
        led.set_corpus({URL_REPO: "texto"}, {URL_REPO: {"status": "usable",
                      "usable_text": "texto", "excluded": False}})
        cells = [(g.get("criterion_id"), g.get("entity_id"))
                 for g in led.compute()["gaps"]]
        self.assertNotIn(("c0", "e1"), cells)

    def test_g1b_sem_cell_gap_quando_celula_coberta(self):
        led = cl.Ledger(cell_plan())
        led.set_corpus({URL_REPO: "texto"}, {URL_REPO: {"status": "usable",
                      "usable_text": "texto", "excluded": False}})
        led.evaluate("c0", "covered", "j", "o",
                     [{"url": URL_REPO}], "e1")
        cells = [(g.get("criterion_id"), g.get("entity_id"))
                 for g in led.compute()["gaps"]]
        self.assertNotIn(("c0", "e1"), cells)


class DiscoverySourceUrlTest(unittest.TestCase):
    def _state(self):
        st = state_api.new_state("cells")
        st["plan"] = {
            "plan_id": "d1", "version": 1,
            "entities": [{"id": "e0", "label": "Alvo", "required": True}],
            "criteria": [{"id": "c0", "label": "x", "required": True,
                          "applies_to": ["e0"]}],
            "initial_paths": ["q"]}
        st["evidence"] = {URL_REPO: "corpo do repo"}
        st["discovery"] = {"candidates": [], "open": True}
        return st

    def test_g1a_url_do_corpus_vira_source_url(self):
        st = self._state()
        led = cl.Ledger(st["plan"])
        ac._apply_discovery(
            st, led, {"entity": {"id": "e9", "label": "Repo Novo",
                                 "url": URL_REPO}}, {"criterion_id": "c0"})
        ents = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertEqual(ents["e9"].get("source_url"), URL_REPO)

    def test_g1a_url_inventada_descartada_com_nota(self):
        st = self._state()
        led = cl.Ledger(st["plan"])
        ac._apply_discovery(
            st, led, {"entity": {"id": "e9", "label": "Repo Novo",
                                 "url": "https://github.com/o/inventado"}},
            {"criterion_id": "c0"})
        ents = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertNotIn("source_url", ents["e9"])
        self.assertTrue(any("fora do corpus" in str(n)
                            for n in st["notes"]))


class SelectCellReadSourceTest(unittest.TestCase):
    def test_g1c_gap_de_celula_vira_read_source_direto(self):
        st = state_api.new_state("cells")
        st["plan"] = cell_plan()
        st["discovery"] = {"candidates": [], "open": True}
        st["attempts"] = {}
        ops = ac.select_ops(st, [{
            "criterion_id": "c0", "entity_id": "e1",
            "entity_label": "Repo X", "source_url": URL_REPO,
            "label": "funciona", "state": "insufficient"}], 1)
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["kind"], "read_source")
        self.assertEqual(ops[0]["target"], URL_REPO)
        self.assertEqual(ops[0].get("entity_id"), "e1")

    def test_g1c_fonte_com_falha_nao_reabre(self):
        st = state_api.new_state("cells")
        st["plan"] = cell_plan()
        st["discovery"] = {"candidates": [], "open": True}
        st["attempts"] = {"c0": [{"channel": "web", "outcome": "failed",
                                  "target": URL_REPO}]}
        ops = ac.select_ops(st, [{
            "criterion_id": "c0", "entity_id": "e1",
            "source_url": URL_REPO, "label": "funciona",
            "state": "insufficient"}], 1)
        kinds_targets = [(o["kind"], o.get("target", "")) for o in ops]
        self.assertTrue(all(URL_REPO not in t for _, t in kinds_targets))


class AssessorCellsPromptTest(unittest.TestCase):
    def test_g2_prompt_enumera_celulas_obrigatorias(self):
        seen = {}

        def model(prompt):
            seen["prompt"] = prompt
            return "[]"

        assess = ac.make_model_assessor(model)
        plan = cell_plan()
        assess(plan, {"https://example.org/a": "texto sobre repos"},
               {"https://example.org/a": {"status": "usable",
                "usable_text": "texto", "excluded": False}}, {})
        p = seen.get("prompt", "")
        self.assertIn("Células obrigatórias", p)
        self.assertIn("c0×e0", p)
        self.assertIn("c0×e1", p)


if __name__ == "__main__":
    unittest.main()


class PerCandidateExtensionTest(unittest.TestCase):
    """G3: criteria marked per_candidate cover every discovered candidate."""

    def _state(self, criteria):
        st = state_api.new_state("cells")
        st["plan"] = {
            "plan_id": "g3", "version": 1,
            "entities": [{"id": "e0", "label": "Alvo", "required": True}],
            "criteria": criteria,
            "initial_paths": ["q"]}
        st["evidence"] = {URL_REPO: "corpo do repo"}
        st["discovery"] = {"candidates": [URL_OTHER], "open": True}
        return st

    def test_g3_per_candidate_estendido_ao_novo_candidato(self):
        st = self._state([
            {"id": "c0", "label": "funcionalidades", "required": True,
             "per_candidate": True},
            {"id": "c9", "label": "sintese", "required": True},
        ])
        led = cl.Ledger(st["plan"])
        ac._apply_discovery(
            st, led, {"entity": {"id": "e9", "label": "Repo Novo",
                                 "url": URL_OTHER}}, {"criterion_id": "c0"})
        crit = {c["id"]: c for c in st["plan"]["criteria"]}
        self.assertEqual(crit["c0"].get("applies_to"), ["e9"])
        self.assertNotIn("applies_to", crit["c9"])
        cells = [(g.get("criterion_id"), g.get("entity_id"))
                 for g in led.compute()["gaps"]]
        self.assertIn(("c0", "e9"), cells)

    def test_g3_fallback_criterio_de_origem_sem_marcacao(self):
        st = self._state([
            {"id": "c1", "label": "identificar candidatos", "required": True},
            {"id": "c9", "label": "sintese", "required": True},
        ])
        led = cl.Ledger(st["plan"])
        ac._apply_discovery(
            st, led, {"entity": {"id": "e9", "label": "Repo Novo",
                                 "url": URL_REPO}}, {"criterion_id": "c1"})
        crit = {c["id"]: c for c in st["plan"]["criteria"]}
        self.assertEqual(crit["c1"].get("applies_to"), ["e9"])
        self.assertNotIn("applies_to", crit["c9"])
        self.assertTrue(any("origem da proposta" in str(n)
                            for n in st["notes"]))

    def test_g3_prompt_do_planner_marca_per_candidate(self):
        import adaptive_planner as ap
        p = ap.build_plan_prompt("compare cinco plugins", "")
        self.assertIn("per_candidate", p)


class WriterCitedFirstTest(unittest.TestCase):
    """G4: the writer prompt shows the material the coverage cites.

    accept8: c3 was covered citing refs that the writer cut (alphabetical
    fill + char budget), so the delivered report could not show what the
    coverage claimed. Cited documents come first; the rest stays stable.
    """

    def test_documento_citado_pela_cobertura_vem_primeiro(self):
        cited = "https://z.example/cited-source"
        other = "https://a.example/other-source"
        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "# Relatorio\n\nTexto [1]."

        write = ac.make_model_writer(fake_client, max_chars=2400)
        view = {
            "question": "comparar",
            "plan": {"criteria": [{"id": "c0", "label": "comparar"}],
                     "entities": []},
            "evidence": {other: "texto " * 400, cited: "texto " * 400},
            "question_coverage": {
                "criteria": [{"id": "c0", "references": [{"url": cited}]}]},
        }
        _, selection = write(view)
        self.assertEqual(selection.get("included_urls", [])[:1], [cited])
        self.assertIn(cited, seen.get("prompt", ""))
