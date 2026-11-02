"""Higiene do gerador de relatório (G1/G2).

G1: notas internas (inglês ou jargão de estabilização/transporte/
semântica) não vazam no corpo visível (§5 "Notas da execução");
preservadas na máquina (state["notes"]) e roteadas ao anexo (§8).
G2: alcance examinado idêntico não se repete por critério: escopo
comum 1× no bloco de método + por critério só o delta.
Genérico: sem literais de produto/entidade.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("hygiene test is offline")


sys.addaudithook(offline_guard)

import report_renderer as rr


INTERNAL_NOTES = [
    "downgrade without new evidence rejected for ('c3', 'e2'): "
    "kept partial (assessor said insufficient)",
    "identity mismatch: c1xe1 sem doc da entidade (atribuicao rejeitada, "
    "kept as insufficiency)",
    "op r6-c3-0 transport failure (canal web): web search unavailable: "
    "gateway failed (retriever_unavailable)",
    "assessor transient failure, retrying once (budget counted): "
    "assessor must return a JSON list",
    "evaluation revised for c4xe2: partial -> insufficient",
    "synthesis criterion c16 -> partial",
    "unexplored reconciliado: 2 alternativa(s) fora da cobertura",
    "pool reserve: https://example.org/candidate "
    "(candidato minerado ligado a e2)",
    "reenvio de quarentena (_sent): 1 doc(s) em 1 celula(s) sustentam "
    "celulas abertas sem refs",
    "semantic boost: 21 docs ranqueados (22 vetorizados, 0 do cache)",
    "repo minerado: https://example.org/a (de https://example.org/b)",
    "link-following: https://example.org/c (de https://example.org/b)",
    "rodizio gap_query: alvo e3 apos - (entidades com gaps: e2,e3)",
    "op r1-c3-0: hit ignorado por identidade (sem mencao a entidade e3) "
    "https://example.org/x",
    "op r1-c3-0 fetch failure for https://example.org/x: fetch failed: casc",
    "op init-2 fetch failure for https://example.org/y: fetch failed: "
    "html_without_content",
    # Limite: detalhe por fonte (ex. timeout) vai ao anexo; a falha de
    # capacidade segue visível no corpo via "Coleta por canal" (§2).
    "fonte https://example.org/z com timeout; mantido como lacuna",
]

USER_NOTES = [
    "contexto do usuario registrado: 1 fato(s) (nao evidencia coletada)",
    "sem substituto no plano; alternativas descobertas nao exploradas: "
    "BetaGadget: https://example.org/beta",
]


def make_state(notes, criteria=None):
    return {
        "question": "q higiene",
        "profile": "medium",
        "plan": {"plan_id": "p", "entities": [], "criteria": []},
        "question_coverage": {"status": "partial", "proportion": 0.0,
                              "criteria": criteria or [], "gaps": []},
        "report": {"numbers": {}, "selection": {}},
        "evidence": {}, "notes": list(notes),
        "rounds": [], "stop": {},
    }


def crit(cid, label, scope):
    return {"id": cid, "label": label, "state": "partial",
            "justification": f"justificativa {label}",
            "references": [], "examined_scope": scope}


def section(out, start_marker, end_marker):
    self_start = out.index(start_marker)
    try:
        self_end = out.index(end_marker, self_start)
    except ValueError:
        self_end = len(out)
    return out[self_start:self_end]


class BodyHygieneTest(unittest.TestCase):
    def test_internal_notes_absent_from_body(self):
        st = make_state(INTERNAL_NOTES + USER_NOTES)
        out = rr.render_report(st, synthesis_text="texto",
                               verifications=None)
        body = section(out, "## 5.", "## 6.")
        for note in INTERNAL_NOTES:
            self.assertNotIn(note, body,
                             f"nota interna vazou no corpo (§5): {note[:80]}")

    def test_user_pt_notes_stay_in_body(self):
        st = make_state(INTERNAL_NOTES + USER_NOTES)
        out = rr.render_report(st, synthesis_text="texto",
                               verifications=None)
        body = section(out, "## 5.", "## 6.")
        for note in USER_NOTES:
            self.assertIn(note, body,
                          f"nota PT util sumiu do corpo (§5): {note[:60]}")

    def test_internal_notes_preserved_on_machine_and_annex(self):
        st = make_state(INTERNAL_NOTES + USER_NOTES)
        out = rr.render_report(st, synthesis_text="texto",
                               verifications=None)
        annex = out[out.index("## 8."):]
        for note in INTERNAL_NOTES:
            self.assertIn(note, st["notes"],
                          f"nota apagada da maquina: {note[:60]}")
            self.assertIn(note, annex,
                          f"nota interna fora do anexo (§8): {note[:60]}")


class ScopeCollapseTest(unittest.TestCase):
    SCOPE_A = ("alcance examinado: excertos de 9/10 docs unicos "
               "(100 chars de 1000 coletados); global: excertos "
               "examinados (9/10 docs)")
    SCOPE_B = ("alcance examinado: excertos de 2/3 docs unicos "
               "(50 chars de 900 coletados); BetaGadget: excerto "
               "examinado (2/3 docs)")

    def test_identical_scope_collapses_to_single_common_block(self):
        criteria = [crit(f"c{i}", f"Eixo {i}", self.SCOPE_A)
                    for i in range(3)]
        st = make_state(list(USER_NOTES), criteria)
        out = rr.render_report(st, synthesis_text="texto",
                               verifications=None)
        self.assertEqual(out.count("Alcance examinado"), 1,
                         "escopo identico repetido no relatorio")
        method = section(out, "## 2.", "## 3.")
        self.assertIn("9/10", method, "escopo comum fora do metodo")

    def test_distinct_scope_shown_once_as_delta(self):
        criteria = [crit("c0", "Eixo 0", self.SCOPE_A),
                    crit("c1", "Eixo 1", self.SCOPE_A),
                    crit("c2", "Eixo 2", self.SCOPE_B)]
        st = make_state(list(USER_NOTES), criteria)
        out = rr.render_report(st, synthesis_text="texto",
                               verifications=None)
        findings = section(out, "## 3.", "## 5.")
        self.assertEqual(out.lower().count("excertos de 9/10"), 1,
                         "escopo comum duplicado fora do bloco unico")
        self.assertEqual(findings.count("excertos de 2/3"), 1,
                         "delta distinto ausente ou duplicado")
        self.assertIn("Eixo 2", findings)


if __name__ == "__main__":
    unittest.main()
