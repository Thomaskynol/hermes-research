"""Attempt4 lane-mecanismos: INFERÊNCIA de complementaridade delimitada com
2 premissas em fontes distintas + alcance examinado inclui seleção do writer.

Genérico, sem literais de produto. Offline (rede proibida inclusive 8082).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verification_report as vr


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("attempt4 tests forbid network, including 8082")


sys.addaudithook(offline)

A = "https://example.org/river-install"
B = "https://example.org/river-review"


def make_plan():
    return {"plan_id": "p", "version": 1,
            "entities": [{"id": "a", "label": "River Install",
                          "source_url": A, "required": True},
                         {"id": "b", "label": "River Review",
                          "source_url": B, "required": True}],
            "criteria": [{"id": "c0", "label": "compatibilidade",
                          "required": True, "description": "Eixo."}]}


CORPUS = {
    A: ("River Install tool. Install and update and list plugins via CLI. "
        "No planning records."),
    B: ("River Review tool. Review the plan and code with diff and "
        "feedback to the agent. No integration records."),
}


def numbers():
    return {1: A, 2: B}


GROUNDED = ("- INFERÊNCIA: River Install complementa River Review porque um "
            "trata de instalar e listar plugins e o outro de revisar plano "
            "e codigo com diff, sem sobreposição evidente nos excertos; "
            "limites: inferência de complementaridade a partir de premissas "
            "separadas, sem prova de integração testada ([1]) ([2])")


class GroundedPairComplementarity(unittest.TestCase):
    """Complementaridade delimitada com premissas nas 2 fontes não é
    unsupported: cai em partial declarada (nunca integração testada)."""

    def test_grounded_pair_is_not_unsupported(self):
        res = vr.check_support(GROUNDED, numbers(), CORPUS, make_plan())
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == GROUNDED]
        self.assertEqual(bad, [], res.get("unsupported"))
        partial = [d for d in (res.get("partial_declared") or [])
                   if d.get("sentence") == GROUNDED]
        self.assertEqual(len(partial), 1, res)
        self.assertIn("nunca integração testada",
                      str(partial[0].get("scope")), res)

    def test_fabricated_premise_stays_unsupported(self):
        """Controle preservado: premissa sem base nos docs segue rejeitada."""
        sent = ("- INFERÊNCIA: River Install complementa River Review porque "
                "um trata de teletransporte quantico e o outro de fusao "
                "nuclear, sem sobreposição evidente nos excertos; limites: "
                "sem prova de integração testada ([1]) ([2])")
        res = vr.check_support(sent, numbers(), CORPUS, make_plan())
        bad = [u for u in (res.get("unsupported") or [])
               if u.get("sentence") == sent]
        self.assertTrue(bad, res)
        self.assertIn("interoperabilidade", bad[0].get("reason", ""), res)
        partial = [d for d in (res.get("partial_declared") or [])
                   if d.get("sentence") == sent]
        self.assertEqual(partial, [], res)


class WriterSelectionCountsAsExamined(unittest.TestCase):
    """Alcance examinado soma a seleção do writer (excertos entregues)."""

    def test_writer_included_doc_is_examined(self):
        import adaptive_coordinator as ac
        import adaptive_state as ast
        st = ast.new_state("Compare River tools.")
        st["plan"] = {
            "plan_id": "r", "version": 1,
            "entities": [
                {"id": "a", "label": "AlphaWidget",
                 "source_url": A, "required": True},
                {"id": "b", "label": "BetaGadget",
                 "source_url": B, "required": True}],
            "criteria": [{"id": "c0", "label": "Revisão",
                           "required": True, "description": "Eixo.",
                           "applies_to": ["a", "b"]}],
        }
        st["evidence"] = {A: "AlphaWidget docs about install.",
                           B: "BetaGadget docs about review."}
        st["qualification"] = {u: {"status": "usable", "excluded": False,
                                   "usable_text": t}
                               for u, t in st["evidence"].items()}
        st["assessments"] = []
        st["reading"] = {"collected_chars": 1000, "excerpted_chars": 500}
        st["report"] = {"selection": {"included_urls": [A]}}
        scope = ac._criterion_scope(st, st["plan"]["criteria"][0])
        self.assertIn("AlphaWidget: excerto examinado (1/1", scope, scope)
        self.assertIn("BetaGadget: não examinado por orçamento", scope, scope)


if __name__ == "__main__":
    unittest.main()
