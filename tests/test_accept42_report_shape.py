"""Accept42 report shape — itens 1-5 (veto idempotente + reconciliação +
template do writer + separação principal/anexo + pares de combinação).

Offline, sem rede/run real. Genérico, sem literais de produto.
"principal" = saída antes de "\\n## 8." (mesma definição de
test_accept40_user_facing.body_of); "anexo" = render_technical_annex().
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import report_renderer as rr


def _with_counters(st, urls, outside=()):
    import research_counters as rc
    rc.ensure(st)
    norms = [rr._norm(u) for u in urls if rr._norm(u)]
    st["counters"]["documents"]["obtained"] = list(norms)
    st["counters"]["documents"]["usable"] = list(norms)
    st["counters"]["counts"]["obtained"] = len(norms)
    st["counters"]["counts"]["usable"] = len(norms)
    st["counters"]["outside_corpus_citations"] = list(outside)
    return st


def _rich_state():
    A = "https://alfa.example/doc"
    B = "https://beta.example/doc"
    C = "https://gama.example/doc"
    bodies = {
        A: "Alfa gerencia fases e conclusão no corpus.",
        B: "Beta planeja antes de implementar no corpus.",
        C: "Gama explora alternativas no corpus.",
    }
    entities = [
        {"id": "e1", "label": "Alfa", "source_url": A,
         "discovered": True, "required": True},
        {"id": "e2", "label": "Beta", "source_url": B,
         "discovered": True, "required": True},
        {"id": "e3", "label": "Gama", "source_url": C,
         "discovered": True, "required": False},
    ]
    criteria = [
        {"id": "c1", "label": "Planejamento", "state": "partial",
         "justification": "Alfa e Beta com evidência parcial de planejamento.",
         "references": [{"url": A}], "examined_scope": "alcance examinado: t",
         "entity_states": {"e1": "covered", "e2": "partial",
                           "e3": "insufficient"}},
        {"id": "c2", "label": "Testes", "state": "partial",
         "justification": "Beta com evidência de testes.",
         "references": [{"url": B}], "examined_scope": "alcance examinado: t",
         "entity_states": {"e1": "partial", "e2": "covered"}},
    ]
    st = {
        "question": "q rica",
        "profile": "light",
        "plan": {"entities": entities,
                 "criteria": [{"id": "c1", "label": "Planejamento"},
                              {"id": "c2", "label": "Testes"}]},
        "question_coverage": {"status": "partial", "proportion": 0.2,
                              "criteria": criteria, "gaps": []},
        "evidence": dict(bodies),
        "qualification": {u: {"usable_text": t} for u, t in bodies.items()},
        "report": {"selection": {"included_urls": [A, B]}},
        "notes": [],
        "rounds": [],
        "stop": {},
    }
    return _with_counters(st, [A, B, C]), (A, B, C)


class TemplateWriterTest(unittest.TestCase):
    def test_principal_tem_matriz_entidade_x_criterio_e_recomendacao(self):
        st, (A, B, C) = _rich_state()
        synth = ("Alfa gerencia fases. Beta planeja antes. "
                 "INFERÊNCIA: complementaridade prudente entre Alfa e Beta, "
                 f"com limite declarado. Ver {A} e {B}.")
        out = rr.render_report(st, synthesis_text=synth, verifications=None)
        principal = out.split("\n## 8.")[0]
        self.assertIn("Matriz", principal,
                      "template sem matriz entidade×critério")
        for token in ("Alfa", "Beta", "Planejamento", "Testes"):
            self.assertIn(token, principal,
                          f"rótulo exigido fora da matriz: {token}")
        header = [ln for ln in principal.split("\n")
                  if ln.startswith("|") and "Alfa" in ln]
        self.assertTrue(header, "cabeçalho da matriz ausente")
        self.assertNotIn("Gama", "\n".join(header),
                         "não-exigido virou coluna da matriz")
        explorados = [ln for ln in principal.split("\n")
                      if "Explorados fora da seleção" in ln]
        self.assertTrue(explorados and "Gama" in explorados[0],
                        "não-exigido fora da matriz sem rótulo")
        self.assertIn("### Resposta direta", principal)
        bloco = principal.split("### Resposta direta")[1]
        bloco = bloco.split("\n### ")[0].split("\n## ")[0]
        linhas = [ln for ln in bloco.strip().split("\n") if ln.strip()]
        self.assertLessEqual(len(linhas), 15,
                             f"resposta direta com {len(linhas)} linhas")
        self.assertIn("### Recomendação", principal)
        rec = principal.split("### Recomendação")[1]
        rec = rec.split("\n### ")[0].split("\n## ")[0]
        self.assertTrue(any(ln.strip().lstrip("-•* ").strip()
                            for ln in rec.strip().split("\n") if ln.strip()),
                        "seção recomendação vazia")


class SeparacaoPrincipalAnexoTest(unittest.TestCase):
    MARKERS = [
        "proporcional: células 3→7 (last=5)",
        "link-following: https://example.org/c (de https://example.org/b)",
        "repo minerado: https://example.org/a (de https://example.org/b)",
        "semantic boost: 21 docs ranqueados",
        "discovery: 5 candidatos",
        "evaluation revised c1xe1: partial -> insufficient",
        "downgrade without new evidence rejected for ('c1', 'e1')",
        "reenvio de quarentena (_sent): 1 doc(s) em 1 célula(s)",
        "lote _sent aguardando reenvio",
        "teto de seleção: 12k atingido",
    ]
    OUT_URL = "https://fora.example/detalhe"

    def test_principal_sem_marcadores_e_anexo_com_marcadores(self):
        st = _base_state()
        st["profile"] = "deep"
        st["notes"] = list(self.MARKERS)
        st["rounds"] = [{"round": 1, "kind": "busca",
                         "target_gaps": ["c-alfa"], "new_evidence": True,
                         "delta": "+1", "decision": "aprofundar"}]
        _with_counters(st, ["https://alfa.example/doc"],
                       outside=[self.OUT_URL])
        out = rr.render_report(st, synthesis_text="texto simples.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        for marker in self.MARKERS:
            self.assertNotIn(marker, principal,
                              f"jargão interno no principal: {marker[:40]}")
        self.assertNotIn("| Rodada |", principal,
                         "tabela de rodadas no principal")
        tech = rr.render_technical_annex(st, verifications=None,
                                         verbose=True)
        for marker in self.MARKERS:
            self.assertIn(marker, tech,
                          f"marcador fora do anexo: {marker[:40]}")
        self.assertIn("| Rodada |", tech)
        self.assertIn(self.OUT_URL, tech,
                      "outside detalhado fora do anexo")
        self.assertNotIn(self.OUT_URL, principal,
                         "outside detalhado no principal")

    def test_limites_nao_duplica_justificativa_dos_achados(self):
        justification = ("Justificativa específica ZZ-9988 sobre Alfa que "
                         "deve ficar só nos achados. Segunda frase de detalhe.")
        st = _base_state(estate="insufficient", justification=justification)
        st["question_coverage"]["criteria"][0]["state"] = "insufficient"
        out = rr.render_report(st, synthesis_text="Alfa sem material novo.",
                               verifications=None)
        sec3 = out.split("## 3.")[1].split("## 5.")[0]
        sec5 = out.split("## 5.")[1].split("## 6.")[0]
        self.assertIn("Alfa", sec3)
        self.assertIn("seção 3", sec5)
        self.assertNotIn(justification, sec5,
                         "§5 duplicou a justificativa da §3")


def _coverage_state():
    A = "https://alfa.example/doc"
    B = "https://beta.example/doc"
    bodies = {A: "Alfa gerencia fases no corpus.",
              B: "Beta planeja antes no corpus."}
    entities = [
        {"id": "e1", "label": "Alfa", "source_url": A,
         "discovered": True, "required": True},
        {"id": "e2", "label": "Beta", "source_url": B,
         "discovered": True, "required": True},
    ]
    criteria = [
        {"id": "c0", "label": "Fontes", "state": "partial",
         "justification": "Catálogo e repositório sustentam fontes.",
         "references": [{"url": A}],
         "examined_scope": "alcance examinado: t"},
        {"id": "c1", "label": "Planejamento", "state": "partial",
         "justification": "Alfa e Beta com evidência parcial.",
         "references": [{"url": A}],
         "examined_scope": "alcance examinado: t",
         "entity_states": {"e1": "covered", "e2": "partial"}},
        {"id": "c2", "label": "Testes", "state": "partial",
         "justification": "Só Alfa cobre testes.",
         "references": [{"url": A}],
         "examined_scope": "alcance examinado: t",
         "entity_states": {"e1": "covered", "e2": "insufficient"}},
    ]
    st = {
        "question": "q matriz",
        "profile": "light",
        "plan": {"entities": entities,
                 "criteria": [{"id": "c0", "label": "Fontes"},
                              {"id": "c1", "label": "Planejamento"},
                              {"id": "c2", "label": "Testes"}]},
        "question_coverage": {"status": "partial", "proportion": 0.3,
                              "criteria": criteria, "gaps": []},
        "evidence": dict(bodies),
        "qualification": {u: {"usable_text": t}
                          for u, t in bodies.items()},
        "report": {"selection": {"included_urls": [A]}},
        "notes": [],
        "rounds": [],
        "stop": {},
    }
    return _with_counters(st, [A, B]), (A, B)

class MatrizDeterministicaTest(unittest.TestCase):
    def test_global_sem_entity_states_usa_estado_do_criterio(self):
        st, (A, B) = _coverage_state()
        out = rr.render_report(st, synthesis_text="Alfa e Beta no corpus.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        self.assertIn("| Fontes | parcial | parcial |", principal,
                      "matriz divergiu do §3 no critério global")
        rows = [ln for ln in principal.split("\n")
                if ln.startswith("| Fontes |")]
        self.assertTrue(rows and "não avaliado" not in rows[0],
                        "fantasma 'não avaliado' na matriz")

    def test_celulas_refletem_covered_partial_dos_states(self):
        st, (A, B) = _coverage_state()
        out = rr.render_report(st, synthesis_text="Alfa e Beta no corpus.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        self.assertIn("| Planejamento | coberto | parcial |", principal)
        self.assertIn("| Testes | coberto | insuficiente |", principal)


class RecomendacaoDeterministicaTest(unittest.TestCase):
    def test_fallback_dispara_quando_sintese_sem_recomendacao(self):
        st, (A, B, C) = _rich_state()
        out = rr.render_report(st, synthesis_text="Alfa gerencia fases. "
                               "Beta planeja antes.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        rec = principal.split("### Recomendação")[1].split("\n## ")[0]
        self.assertIn("a partir dos achados", rec,
                      "fallback não disparou sem recomendação na síntese")
        self.assertIn("Alfa", rec)
        self.assertIn("Beta", rec)
        self.assertIn("[1]", rec,
                      "fallback sem refs auditadas")

    def test_fallback_dispara_quando_generica_sem_entidades(self):
        st, (A, B, C) = _rich_state()
        out = rr.render_report(st, synthesis_text="Recomendo revisar tudo "
                               "com calma.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        rec = principal.split("### Recomendação")[1].split("\n## ")[0]
        self.assertIn("a partir dos achados", rec,
                      "genérica sem entidades não ganhou fallback")

    def test_fallback_nao_dispara_quando_sintese_ja_recomenda(self):
        st, (A, B, C) = _rich_state()
        out = rr.render_report(st, synthesis_text="Recomendo Alfa para "
                               "planejar. Recomendo Beta para testar.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        rec = principal.split("### Recomendação")[1].split("\n## ")[0]
        self.assertNotIn("a partir dos achados", rec,
                         "fallback indevido com recomendação válida")

    def test_fallback_ranqueia_por_covered_partial_refs(self):
        st, (A, B) = _coverage_state()
        out = rr.render_report(st, synthesis_text="Alfa e Beta no corpus.",
                               verifications=None)
        principal = out.split("\n## 8.")[0]
        rec = principal.split("### Recomendação")[1].split("\n## ")[0]
        self.assertIn("a partir dos achados", rec,
                      "fallback não disparou para ranquear")
        self.assertLess(rec.index("Alfa"), rec.index("Beta"),
                        "ranking covered>partial não respeitado")


class ParesCombinacaoTest(unittest.TestCase):
    def test_par_sintese_fora_dos_achados_vira_reconciliacao(self):
        st, (A, B, C) = _rich_state()
        synth = ("INFERÊNCIA: complementaridade prudente entre Alfa e Gama, "
                 f"com limite declarado. Ver {A} e {C}.")
        out = rr.render_report(st, synthesis_text=synth, verifications=None)
        principal = out.split("\n## 8.")[0].lower()
        self.assertIn("achados", principal,
                      "par fora dos achados sem nota explícita")
        self.assertIn("texto integral", principal,
                      "nota sem alcance do texto integral")
        self.assertIn("excertos avaliados", principal,
                      "nota sem alcance dos excertos")
        self.assertIn("seleção analisada", principal,
                      "nota sem alcance da seleção analisada")
        self.assertNotIn("pares×síntese", principal,
                         "jargão interno no principal")
        self.assertNotIn("janela do writer", principal,
                         "jargão interno no principal")
        self.assertNotIn("full-text", principal,
                         "jargão interno no principal")

    def test_par_coeso_nos_achados_nao_gera_nota_de_par(self):
        st, (A, B, C) = _rich_state()
        synth = ("INFERÊNCIA: complementaridade prudente entre Alfa e Beta, "
                 f"com limite declarado. Ver {A} e {B}.")
        out = rr.render_report(st, synthesis_text=synth, verifications=None)
        self.assertNotIn("cobertura conjunta", out.lower(),
                         "par coeso gerou nota indevida")

    def test_coberto_com_lacuna_para_mesma_entidade_tem_nota(self):
        st, (A, B, C) = _rich_state()
        synth = (f"LACUNA: sem base para afirmar testes de Alfa. Ver {A}. "
                 "Alfa gerencia fases.")
        out = rr.render_report(st, synthesis_text=synth, verifications=None)
        principal = out.split("\n## 8.")[0].lower()
        self.assertIn("achados", principal,
                      "coberto×LACUNA sem nota explícita")
        self.assertIn("texto integral", principal,
                      "nota sem alcance do texto integral")
        self.assertIn("excertos avaliados", principal,
                      "nota sem alcance dos excertos")
        self.assertNotIn("findings", principal,
                         "jargão interno no principal")
        self.assertNotIn("janela do writer", principal,
                         "jargão interno no principal")
        self.assertNotIn("full-text", principal,
                         "jargão interno no principal")


def _base_state(entity_id="e-alfa", label="Alfa", src="https://alfa.example/doc",
                body="Alfa faz planejamento com fases e revisão.",
                included=None, refs=None, estate="covered",
                crit_id="c-alfa", crit_label="Planejamento",
                justification="justificativa"):
    evidence = {src: body}
    qualification = {src: {"usable_text": body}}
    entities = [{"id": entity_id, "label": label, "source_url": src,
                 "discovered": True, "required": True}]
    references = [{"url": r} for r in (refs if refs is not None else [src])]
    criteria = [{"id": crit_id, "label": crit_label, "state": "partial",
                 "justification": justification,
                 "references": references,
                 "entity_states": {entity_id: estate}}]
    inc = included if included is not None else []
    return {
        "question": "q",
        "profile": "light",
        "plan": {"entities": entities,
                 "criteria": [{"id": crit_id, "label": crit_label}]},
        "question_coverage": {"status": "partial", "proportion": 0.1,
                              "criteria": criteria, "gaps": []},
        "evidence": evidence,
        "qualification": qualification,
        "report": {"selection": {"included_urls": list(inc)}},
        "notes": [],
        "rounds": [],
        "stop": {},
    }


class VetoIdempotenteTest(unittest.TestCase):
    def test_marcador_preexistente_nao_duplica(self):
        # Linha 21 do accept42: marcador já presente + "fora do corpus"
        # na mesma frase virou 2 ocorrências. Idempotente => 1.
        src = "https://alfa.example/doc"
        st = _base_state(
            src=src,
            body="Alfa faz planejamento com fases e revisão.",
            included=[src],
            refs=[src],
        )
        synth = (
            "URL citada na cobertura para detalhes de Alfa "
            "fora da seleção do writer (LACUNA de análise; ler a seguir: "
            f"{src}) está fora do corpus e não foi usada como fonte lida."
        )
        out = rr._veto_outside_corpus(st, synth)
        self.assertEqual(
            out.lower().count("fora da seleção"), 1,
            f"veto duplicou marcador: {out!r}")

    def test_f3_so_rotula_fora_da_selecao_se_src_fora_do_included(self):
        # Caso [11]: src EM included_urls reais nunca é "fora da seleção".
        src = "https://alfa.example/doc"
        st = _base_state(
            src=src,
            body="Alfa faz planejamento com fases e revisão.",
            included=[src],
            refs=[src],
        )
        synth = "Detalhe de Alfa está fora do corpus e sem prova."
        out = rr._veto_outside_corpus(st, synth)
        self.assertNotIn(
            "fora da seleção", out.lower(),
            f"F3 rotulou URL incluída como fora da seleção: {out!r}")


class ReconciliacaoFindingsSinteseTest(unittest.TestCase):
    def test_covered_com_refs_vs_lacuna_global_vira_nota_com_alcance(self):
        src = "https://alfa.example/doc"
        st = _base_state(
            src=src,
            body="Alfa faz planejamento com fases e revisão.",
            included=[src],
            refs=[src],
            estate="covered",
        )
        synth = ("LACUNA: sem base para afirmar planejamento de Alfa. "
                 "Alfa gerencia fases e conclusão.")
        out = rr.render_report(st, synthesis_text=synth, verifications=None)
        principal = out.split("\n## 8.")[0].lower()
        self.assertIn("achados", principal,
                      "divergência covered×LACUNA sem nota explícita")
        self.assertIn("texto integral", principal,
                      "nota sem alcance do texto integral")
        self.assertIn("excertos avaliados", principal,
                      "nota sem alcance dos excertos")
        self.assertIn("seleção analisada", principal,
                      "nota sem alcance da seleção analisada")
        self.assertNotIn("findings", principal,
                         "jargão interno no principal")
        self.assertNotIn("janela do writer", principal,
                         "jargão interno no principal")
        self.assertNotIn("full-text", principal,
                         "jargão interno no principal")


if __name__ == "__main__":
    unittest.main()
