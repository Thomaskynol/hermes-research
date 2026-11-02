#!/usr/bin/env python3
"""Calibração do validador de suporte (accept15, mecanismos gerais).

Casos lidos DIRETAMENTE das fontes do corpus congelado
(``tools/calibration_sample.json``): cada teste abaixo fixa o comportamento
demonstrado pelos casos — falha no HEAD (sem ponte PT-EN, sem trava de
versão, sem menção integral de entidade) e passa depois.

Tipos: (a) paráfrase PT×EN; (b) palavras coincidentes sem sustentação;
(c) versão diferente; (d) evidência de outra entidade; (e) ausência;
(f) truncamento (prova de erro de contexto, estável antes/depois).

Integração (``CalibrationIntegration``) roda os 25 casos no state
congelado; pula com SkipTest fora deste ambiente (sem o state em disco).
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("calibration test is offline")


sys.addaudithook(offline_guard)

import verification_report as verify  # noqa: E402
import diagnose_run as diag  # noqa: E402

STATE_DEFAULT = Path("/tmp/hermes-real-run/accept15/adaptive_accept15/"
                     "state.json")

URL = "https://example.org/docs/one"


def plan_for(eid="cand-planner", label="opencode-planner"):
    return {"plan_id": "p", "version": 1,
            "entities": ([{"id": eid, "label": label}] if eid else []),
            "criteria": []}


def check(claim, doc, eid="cand-planner", label="opencode-planner"):
    return verify.check_support(claim + " [1]", {1: URL}, {URL: doc},
                                plan_for(eid, label))


class SupportBridgeTest(unittest.TestCase):
    """Ponte PT-EN (a) + trava de versão (c) + menção de entidade (d)."""

    def test_parafrase_pt_en_sustenta(self):
        doc = ("Features: Zero-config convention-based discovery. "
               "Content-hash based change detection.")
        res = check("A descoberta por convenção dispensa configuração",
                    doc, "cand-marketplace", "opencode-marketplace")
        self.assertEqual(res["supported"], 1, res)

    def test_licenca_pt_sustenta_via_ponte(self):
        doc = "Install with npm. ## License\n\nMIT"
        res = check("A licença do projeto é MIT", doc)
        self.assertEqual(res["supported"], 1, res)

    def test_versao_divergente_nao_sustenta(self):
        doc = ("The current release is 0.6.0. The same npm package "
               "supports OpenCode V1 and OpenCode V2.")
        res = check("The same npm package version 2.1.4 supports "
                    "OpenCode V1 and V2", doc)
        self.assertEqual(res["supported"], 0, res)

    def test_versao_coincidente_sustenta_controle(self):
        doc = ("opencode-planner: the current release is 0.6.0. The same "
               "npm package supports OpenCode V1 and OpenCode V2.")
        res = check("The same npm package version 0.6.0 supports "
                    "OpenCode V1 and V2", doc)
        self.assertEqual(res["supported"], 1, res)

    def test_entidade_de_outro_candidato_nao_sustenta(self):
        doc = ("Do not add the plural plugins field: OpenCode V1 rejects "
               "that unknown field instead of ignoring it. "
               "opencode-planner adds a plan agent.")
        res = check("opencode-agents rejects that unknown field instead "
                    "of ignoring it", doc, "cand-agents", "opencode-agents")
        self.assertEqual(res["supported"], 0, res)
        self.assertEqual(res["unsupported"][0]["reason"],
                         "entidade não mencionada no doc")

    def test_entidade_propria_sustenta_controle(self):
        doc = ("Do not add the plural plugins field: OpenCode V1 rejects "
               "that unknown field instead of ignoring it. "
               "opencode-planner adds a plan agent.")
        res = check("opencode-planner rejects that unknown field instead "
                    "of ignoring it", doc)
        self.assertEqual(res["supported"], 1, res)

    def test_coincidencia_minoritaria_nao_sustenta(self):
        doc = ("opencode-marketplace ## Development\n\nbun install\n"
               "bun test  # Run tests\nLicense MIT.")
        claim = ("O bun test do desenvolvimento interno prova testes ao "
                 "usuário final e garante qualidade contínua da entrega")
        res = check(claim, doc, "cand-marketplace", "opencode-marketplace")
        self.assertEqual(res["supported"], 0, res)

    def test_ausencia_nao_sustenta(self):
        doc = ("CLI for installing plugins. ## Development: bun test. "
               "## License MIT.")
        res = check("O marketplace cobra assinatura mensal de 20 dólares",
                    doc, "cand-marketplace", "opencode-marketplace")
        self.assertEqual(res["supported"], 0, res)

    def test_limite_de_sentido_documentado(self):
        # (b2) canônico: claim curta onde `testes`→test atinge 0.50.
        # Limitação conhecida e assumida (ponte léxica não distingue
        # sentido dev-vs-usuário); o teste fixa o comportamento atual.
        doc = ("opencode-marketplace ## Development\n\nbun install\n"
               "bun test  # Run tests\nLicense MIT.")
        res = check("O marketplace prova testes ao usuário com bun test",
                    doc, "cand-marketplace", "opencode-marketplace")
        self.assertEqual(res["supported"], 1, res)


class DiagnoseMirrorTest(unittest.TestCase):
    """diagnose_run espelha o validador (import único compartilhado)."""

    def _state(self, line, doc, label="Widget Alpha", eid="e1", cid="c1"):
        url = "https://alpha.example/docs"
        return {
            "plan": {"entities": [{"id": eid, "label": label,
                                   "required": True, "description": "Eixo eixo: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
                     "criteria": [{"id": cid, "label": "Compat",
                                   "required": True,
                                   "applies_to": [eid], "description": "Eixo Compat: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}]},
            "evidence": {url: doc},
            "report": {"markdown": f"{line} [1]",
                       "numbers": {"1": url}},
        }

    def test_diagnose_pt_en_sustenta(self):
        doc = ("Install with npm. ## License\n\nMIT")
        st = self._state("A licença do projeto é MIT", doc)
        out = diag.synthesis_audit(st)
        self.assertEqual(out["supported"], 1, out)

    def test_diagnose_versao_divergente(self):
        # gate separado tag exata vs familia: 2.0.0 ausente vira exata
        doc = "The current release is 0.6.0."
        st = self._state("Release 2.0.0 is current", doc)
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("versão exata ausente",
                      out["unsupported_items"][0]["reason"])

    def test_diagnose_outra_entidade(self):
        doc = "opencode-planner adds a plan agent. License MIT."
        st = self._state("opencode-agents adds a plan agent", doc,
                         label="opencode-agents", eid="cand-agents")
        out = diag.synthesis_audit(st)
        self.assertEqual(out["unsupported"], 1, out)
        self.assertIn("entidade ausente",
                      out["unsupported_items"][0]["reason"])

    def test_diagnose_import_unico_compartilhado(self):
        self.assertIs(diag.is_lacuna_declaration,
                      verify.is_lacuna_declaration)
        self.assertIs(diag._expand_support_tokens,
                      verify._expand_support_tokens)
        self.assertIs(diag._entity_mentioned, verify._entity_mentioned)
        self.assertIs(diag._text_versions, verify._text_versions)


def load_frozen():
    if not STATE_DEFAULT.exists():
        raise unittest.SkipTest(f"state congelado ausente: {STATE_DEFAULT}")
    state = json.loads(STATE_DEFAULT.read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "tools" / "calibration_sample.json")
                        .read_text(encoding="utf-8"))
    return state, {c["id"]: c for c in sample["cases"]}


class CalibrationIntegrationTest(unittest.TestCase):
    """Os 25 casos no corpus congelado (pipeline real, sem modelo)."""

    @classmethod
    def setUpClass(cls):
        from run_calibration import assessor_terms  # noqa: E402
        cls.state, cls.cases = load_frozen()
        terms, groups = assessor_terms(cls.state)
        cls.terms, cls.groups = terms, groups

    def _row(self, cid):
        from run_calibration import run_case  # noqa: E402
        return run_case(self.cases[cid], self.state,
                        self.state.get("evidence") or {},
                        self.terms, self.groups)

    def test_tipos_a_sustentados_apos_ponte(self):
        for cid in ("a1", "a2", "a3", "a4", "a5"):
            with self.subTest(cid=cid):
                self.assertTrue(self._row(cid)["check_supported"], cid)

    def test_tipos_c_d_negados_apos_trava_e_mencao(self):
        for cid in ("c1", "c2", "c3", "c4", "d1", "d2", "d3", "d4"):
            with self.subTest(cid=cid):
                self.assertFalse(self._row(cid)["check_supported"], cid)

    def test_tipos_b_e_negados_controles(self):
        for cid in ("b1", "b3", "b4", "e1", "e2", "e3", "e4"):
            with self.subTest(cid=cid):
                self.assertFalse(self._row(cid)["check_supported"], cid)

    def test_limitacao_b2_fixa(self):
        self.assertTrue(self._row("b2")["check_supported"])

    def test_excerpt_flags_conferem_com_amostra(self):
        for cid, case in self.cases.items():
            with self.subTest(cid=cid):
                row = self._row(cid)
                self.assertEqual(row["in_current_excerpt"],
                                 case["in_current_excerpt"], cid)

    def test_fontes_de_erro_finais(self):
        from run_calibration import attribute  # noqa: E402
        want = {"a1": "ok", "a2": "ok", "a3": "ok", "a4": "ok",
                "a5": "julgamento_modelo",
                "b1": "ok", "b2": "validacao", "b3": "ok", "b4": "ok",
                "c1": "ok", "c2": "ok", "c3": "ok", "c4": "ok",
                "d1": "ok", "d2": "ok", "d3": "ok", "d4": "ok",
                "e1": "julgamento_modelo", "e2": "ok", "e3": "ok",
                "e4": "ok",
                "f1": "contexto", "f2": "contexto", "f3": "contexto",
                "f4": "contexto"}
        for cid, source in want.items():
            with self.subTest(cid=cid):
                row = self._row(cid)
                self.assertEqual(attribute(self.cases[cid],
                                           row["check_supported"],
                                           row["in_current_excerpt"],
                                           row["recorded"]), source, cid)


if __name__ == "__main__":
    unittest.main()
