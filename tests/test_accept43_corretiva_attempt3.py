"""Attempt3 — vr:1569 adjacência + propagação fora-dos-excertos (TDD RED primeiro).

Genérico, sem literais de produto. Offline (rede proibida inclusive 8082).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import report_renderer as rr
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("attempt3 tests forbid network, including 8082")


sys.addaudithook(offline)

URL = "https://github.com/team/river-plan"


def make_plan():
    return {"plan_id": "p", "version": 1,
            "entities": [{"id": "e1", "label": "River Plan",
                          "source_url": URL, "required": True}],
            "criteria": [{"id": "c0", "label": "compatibilidade",
                          "required": True, "description": "Eixo."}]}


CORPUS = {URL: ("River Plan requires RiverHost V2 2.1.2+. "
                "Documented plan review.")}


class Vr1569Adjacency(unittest.TestCase):
    """Isenção mesma-oração alcançava versão inventada vizinha.

    Causa: _premise_ok marcava qualquer versão na mesma oração com
    marcador+comparação, sem exigir adjacência (≤40 chars) ao marcador.
    """

    def test_neighbor_invented_same_clause_far_from_marker_rejected(self):
        plan = make_plan()
        # Mesma oração (sem ';'), marcador+numérico presentes, válida
        # adjacente (≤40), inventada distante (>40 com enchimento).
        sent = ("O River Plan declara mínimo 2.1.2 com mínimo atendido e "
                "instalada 2.1.4 (premissa controlada) com detalhamento "
                "extenso sobre compatibilidade funcional verificada e ainda "
                "9.9.9 sem fonte (LACUNA de integração [1]).")
        res = vr.check_support(sent, {1: URL}, CORPUS, plan)
        self.assertTrue(res.get("unsupported"), res)
        self.assertIn("versão exata",
                      str((res.get("unsupported") or [{}])[0].get("reason")),
                      res)

    def test_t2a_valid_multi_version_stays_supported(self):
        plan = make_plan()
        sent = ("O River Plan declara Requires RiverHost V2 2.1.2+; contra a versão "
                "instalada 2.1.4 do contexto controlado há INFERÊNCIA numérica de mínimo "
                "atendido, sem fonte de compatibilidade funcional com 2.1.4 "
                "(LACUNA de integração [1]).")
        res = vr.check_support(sent, {1: URL}, CORPUS, plan)
        self.assertEqual(res.get("unsupported"), [], res)
        self.assertEqual(res.get("supported"), 1, res)

    def test_inference_marker_alone_does_not_exempt(self):
        plan = make_plan()
        # INFERÊNCIA perto da versão, sem marcador de premissa controlada
        # por perto: não isenta.
        sent = ("O River Plan declara compatibilidade funcional com 9.9.9 "
                "por INFERÊNCIA numérica de mínimo atendido [1].")
        res = vr.check_support(sent, {1: URL}, CORPUS, plan)
        self.assertTrue(res.get("unsupported"), res)

    def test_negation_does_not_exempt(self):
        plan = make_plan()
        # Negação sem linguagem de lacuna não isenta versão inventada
        # funcional: segue exigindo a tag no doc.
        sent = ("O River Plan não oferece compatibilidade funcional com 9.9.9 "
                "e integração testada [1].")
        res = vr.check_support(sent, {1: URL}, CORPUS, plan)
        self.assertTrue(res.get("unsupported"), res)


class PropagationOutsideExcerpts(unittest.TestCase):
    """Refs fora de included_urls devem renderizar '[N] (fora dos excertos)'
    em TODAS superfícies (matriz, Achados, recomendação)."""

    OUT = "https://github.com/shreyanshrana/opencode-jira"
    IN = "https://github.com/erskingardner/opencode-code-review"

    def test_recommendation_fallback_marks_outside(self):
        import adaptive_state as ast
        import coverage_ledger as cl
        st = ast.new_state("Compare RiverHost.")
        st["plan"] = {
            "plan_id": "r", "version": 1,
            "entities": [
                {"id": "a", "label": "River Review",
                 "source_url": self.IN, "required": True},
                {"id": "b", "label": "River Plan",
                 "source_url": self.OUT, "required": True}],
            "criteria": [{"id": "review", "label": "Revisão",
                           "required": True, "description": "Eixo.",
                           "per_candidate": True,
                           "applies_to": ["a", "b"]}],
        }
        st["evidence"] = {self.IN: "River Review docs.",
                           self.OUT: "River Plan docs."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                    "usable_text": t}
                                for u, t in st["evidence"].items()}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("review", "partial", "River Plan parcial.",
                     "corpus", [{"url": self.OUT}], "b")
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [self.IN]},
                        "numbers": {"1": self.IN, "2": self.OUT}}
        numbers = {rr._norm(self.IN): 1, rr._norm(self.OUT): 2}
        labels = {"not_investigated": "não investigado"}
        lines = rr._recommendation_fallback(st, labels, numbers)
        text = "\n".join(lines)
        # [2] fora dos excertos nunca nu
        self.assertIn("[2] (fora dos excertos)", text, lines)
        bare = [l for l in text.split("[2]") if True]
        # garante que não há ocorrência nua de [2] sem qualificador
        import re as _re
        nus = _re.findall(r"\[2\](?!\s*\(fora dos excertos\))", text)
        self.assertEqual(nus, [], text)

    def test_findings_marks_outside(self):
        import adaptive_state as ast
        import coverage_ledger as cl
        st = ast.new_state("Compare RiverHost.")
        st["plan"] = {
            "plan_id": "r", "version": 1,
            "entities": [
                {"id": "a", "label": "River Review",
                 "source_url": self.IN, "required": True},
                {"id": "b", "label": "River Plan",
                 "source_url": self.OUT, "required": True}],
            "criteria": [{"id": "review", "label": "Revisão",
                           "required": True, "description": "Eixo.",
                           "per_candidate": True,
                           "applies_to": ["a", "b"]}],
        }
        st["evidence"] = {self.IN: "River Review docs.",
                           self.OUT: "River Plan docs."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                    "usable_text": t}
                                for u, t in st["evidence"].items()}
        led = cl.Ledger(st["plan"], run_id=st["run_id"])
        led.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        led.evaluate("review", "covered", "River Review ok.",
                     "corpus", [{"url": self.IN}], "a")
        led.evaluate("review", "partial", "River Plan parcial.",
                     "corpus", [{"url": self.OUT}], "b")
        st["question_coverage"] = led.compute()
        st["report"] = {"selection": {"included_urls": [self.IN]},
                        "numbers": {"1": self.IN, "2": self.OUT}}
        # força corpus via evidence (sem filtro de contadores vazios)
        st.pop("counters", None)
        out = rr.render_report(st, synthesis_text="Ver síntese.",
                               verifications=None)
        # Achados §3 e matriz devem qualificar [2]
        self.assertIn("[2] (fora dos excertos)", out, out[-2000:])
        import re as _re
        nus = _re.findall(r"\[2\](?!\s*\(fora dos excertos\))", out)
        self.assertEqual(nus, [], out[-3000:])

    def test_recommendation_fallback_rf_marks_outside_when_details_empty(self):
        """Fallback `_rf` sem justifications rendia refs nuas; deve
        qualificar fora-dos-excertos como o ramo details."""
        import adaptive_state as ast
        st = ast.new_state("Compare RiverHost.")
        st["plan"] = {
            "plan_id": "r", "version": 1,
            "entities": [
                {"id": "a", "label": "River Review",
                 "source_url": self.IN, "required": True},
                {"id": "b", "label": "River Plan",
                 "source_url": self.OUT, "required": True}],
            "criteria": [
                {"id": "review", "label": "Revisão",
                 "required": True, "description": "Eixo.",
                 "per_candidate": True,
                 "applies_to": ["a", "b"],
                 "entity_states": {"b": "partial"},
                 "references": [{"url": self.OUT}]},
            ],
        }
        st["evidence"] = {self.IN: "River Review docs.",
                           self.OUT: "River Plan docs."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                    "usable_text": t}
                                for u, t in st["evidence"].items()}
        st["question_coverage"] = {
            "criteria": st["plan"]["criteria"],
            "status": "partial",
        }
        st["report"] = {"selection": {"included_urls": [self.IN]},
                        "numbers": {"1": self.IN, "2": self.OUT}}
        numbers = {rr._norm(self.IN): 1, rr._norm(self.OUT): 2}
        labels = {"not_investigated": "não investigado"}
        lines = rr._recommendation_fallback(st, labels, numbers)
        text = "\n".join(lines)
        # ramo sem details usa _rf: fora deve qualificar
        self.assertIn("[2] (fora dos excertos)", text, lines)
        import re as _re
        nus = _re.findall(r"\[2\](?!\s*\(fora dos excertos\))", text)
        self.assertEqual(nus, [], text)
        # dentro da seleção permanece nu: monta variante com ref interna
        st2 = dict(st)
        import copy as _copy
        st2 = _copy.deepcopy(st)
        st2["plan"]["criteria"][0]["references"] = [{"url": self.IN}]
        st2["plan"]["criteria"][0]["entity_states"] = {"a": "partial"}
        st2["plan"]["entities"] = [
            {"id": "a", "label": "River Review",
             "source_url": self.IN, "required": True}]
        st2["report"] = {"selection": {"included_urls": [self.IN]},
                         "numbers": {"1": self.IN}}
        numbers2 = {rr._norm(self.IN): 1}
        lines2 = rr._recommendation_fallback(st2, labels, numbers2)
        text2 = "\n".join(lines2)
        self.assertIn("[1]", text2, lines2)
        self.assertNotIn("(fora dos excertos)", text2, lines2)


if __name__ == "__main__":
    unittest.main()
