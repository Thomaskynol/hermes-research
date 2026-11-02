#!/usr/bin/env python3
"""Guarda deterministica anti-ausencia-falsa no verifier (TDD RED->GREEN).

Generica (AlphaWidget/BetaGadget ficticios, example.org, sem literais de
produto/entidades). Offline: audithook bloqueia rede, sem 8082. Nao toca
tetos/orcamento/thresholds do verifier.

Contrato: uma frase que afirma ausencia GLOBAL de funcionalidade/
documentacao atribuivel a uma entidade rotulada (padroes 'sem
funcionalidade/documentacao atribuivel', 'sem funcionalidade documentada
atribuivel', via _entity_mentioned estrito, nunca substring) contradiz
evaluations partial/covered dessa entidade com refs resolvidas (references
nao-vazias resolvendo p/ usable_text nao-excluido, gates do Ledger) e
reprova `support` com reason distinto ('ausencia contradiz evaluations
com refs'). NUNCA forca covered: LACUNA genuina (sem evaluations que
sustentem) continua passando.

Escopo decidido: a guarda mira o CLAIM (ausencia global de
funcionalidade atribuivel), nao a secao: dispara em qualquer linha de
afirmacao fora de tabela/nota propria. LACUNA window-scoped ('nenhum
excerto afirma X nos excertos examinados') nao casa os padroes e segue
legitima mesmo com evaluations parciais (caso d). Falsa-presenca inversa
proibida: partial_declared fraco (anchor_ok sem refs resolvidas) e refs
fora do corpus/excluidas/vazias NAO sustentam presenca (caso c).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("false-absence verifier test is offline")


sys.addaudithook(offline_guard)

import adaptive_state
import verification_report as vr


URL_A = "https://example.org/alpha-doc"
URL_B = "https://example.org/beta-doc"
DOC_A = ("AlphaWidget guia de orquestracao. AlphaWidget documenta "
         "orquestracao leve de agentes com exemplos. " * 20)
DOC_B = ("BetaGadget manual de instalacao. BetaGadget instala via "
         "linha de comando com exemplos. " * 20)


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def plan_two():
    return {
        "plan_id": "fa-v1", "version": 1, "question": "q",
        "entities": [
            {"id": "eA", "label": "AlphaWidget", "required": True},
            {"id": "eB", "label": "BetaGadget", "required": True},
        ],
        "criteria": [
            {"id": "cF", "label": "eixo funcional", "required": True,
             "applies_to": ["eA", "eB"],
             "description": ("Eixo funcional: o que conta como evidencia "
                             "operacional de funcionalidade documentada "
                             "para este eixo, com exemplos e condicoes.")},
        ],
    }


def state_with(evaluations, qualification=None):
    st = adaptive_state.new_state("q ausencia falsa")
    st["plan"] = plan_two()
    st["evidence"] = {URL_A: DOC_A, URL_B: DOC_B}
    st["qualification"] = (dict(qualification) if qualification is not None
                           else {URL_A: qual(DOC_A), URL_B: qual(DOC_B)})
    st["evaluations"] = list(evaluations)
    st["report"] = {"numbers": {"1": URL_A, "2": URL_B}}
    return st


def eval_partial(entity_id, url):
    return {"criterion_id": "cF", "entity_id": entity_id,
            "state": "partial",
            "justification": "funcionalidade documentada no corpus",
            "origin": "corpus", "references": [{"url": url}]}


ABSENCE_A = ("- INFERÊNCIA de lacuna para AlphaWidget: sem funcionalidade "
             "atribuível documentada [1], combinação ou sobreposição com "
             "os demais é LACUNA, limites: verificação restrita ao corpus "
             "examinado.")


class FalseAbsenceVerifierTest(unittest.TestCase):
    def test_a_partial_resolvida_mais_ausencia_falha(self):
        st = state_with([eval_partial("eA", URL_A)])
        flags = vr._false_absence_flags(ABSENCE_A, state=st)
        self.assertEqual(len(flags), 1,
                         f"1 flag esperada (AlphaWidget): {flags}")
        self.assertEqual(flags[0].get("entity_id"), "eA")
        self.assertIn("cF", str(flags[0].get("evaluations")),
                      f"flag deve citar evaluations que sustentam: {flags}")
        dim = vr.verify_support(st, ABSENCE_A, None)
        self.assertEqual(dim.get("status"), "failed",
                         f"support deve reprovar ausencia contraditoria: {dim}")
        ev = dim.get("evidence") or {}
        reasons = str(ev.get("sentence_unsupported")) + str(dim.get("notes"))
        self.assertIn("ausência contradiz evaluations com refs", reasons,
                      f"reason distinto esperado: {dim}")

    def test_b_sem_evaluations_lacuna_genuina_passa(self):
        st = state_with([])
        flags = vr._false_absence_flags(ABSENCE_A, state=st)
        self.assertEqual(flags, [],
                         "sem evaluations que sustentem, sem flag "
                         "(nunca forca covered)")
        dim = vr.verify_support(st, ABSENCE_A, None)
        self.assertNotEqual(dim.get("status"), "failed",
                            f"LACUNA genuina nao reprova: {dim}")

    def test_c_refs_nao_resolvidas_nao_sustentam_presenca(self):
        missing = "https://example.org/fora-do-corpus"
        st = state_with([eval_partial("eA", missing)])
        self.assertEqual(vr._false_absence_flags(ABSENCE_A, state=st), [],
                         "ref fora do corpus nao resolve: sem flag")
        # Excluida pela qualificacao tambem nao resolve (mesmo URL no
        # corpus): falsa-presenca inversa proibida.
        q_excl = {URL_A: {"status": "usable", "reason": "x",
                          "usable_text": DOC_A, "excluded": True},
                  URL_B: qual(DOC_B)}
        st2 = state_with([eval_partial("eA", URL_A)],
                         qualification=q_excl)
        self.assertEqual(vr._false_absence_flags(ABSENCE_A, state=st2), [],
                         "ref excluida nao resolve: sem flag")
        # partial_declared fraco: anchor_ok sem refs (references vazias)
        # NAO basta para sustentar presenca.
        weak = dict(eval_partial("eA", URL_A))
        weak["references"] = []
        st3 = state_with([weak])
        self.assertEqual(vr._false_absence_flags(ABSENCE_A, state=st3), [],
                         "references vazias nao sustentam: sem flag")
        dim = vr.verify_support(st, ABSENCE_A, None)
        self.assertNotEqual(dim.get("status"), "failed",
                            f"sem refs resolvidas, LACUNA passa: {dim}")

    def test_d_lacuna_window_scoped_fora_da_combinacao_passa(self):
        st = state_with([eval_partial("eA", URL_A)])
        scoped = ("- LACUNA: nenhum excerto afirma combinação entre "
                  "AlphaWidget e BetaGadget nos excertos examinados [1].")
        self.assertEqual(vr._false_absence_flags(scoped, state=st), [],
                         "claim de janela (excertos) nao e ausencia global "
                         "de funcionalidade: sem flag mesmo com partial")
        dim = vr.verify_support(st, scoped, None)
        self.assertNotEqual(dim.get("status"), "failed",
                            f"LACUNA window-scoped segue legitima: {dim}")


if __name__ == "__main__":
    unittest.main()
