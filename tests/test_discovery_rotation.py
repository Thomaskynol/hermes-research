#!/usr/bin/env python3
"""B+D+E+F (accept2): rotação de candidatos, mineração geral de repos,
elicitação de propose_entity e --context com teto parcial.

Offline: só transports injetados + audithook bloqueando rede.
Run: python3 -m unittest tests.test_discovery_rotation -v
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("discovery rotation tests are offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac  # noqa: E402
import adaptive_state as state_api  # noqa: E402
import gpt_researcher_integration as entry  # noqa: E402


A = "https://github.com/o/alpha-tool"
B = "https://github.com/o/beta-tool"


def plan2():
    return {
        "plan_id": "rot-1", "version": 1, "question": "Compare ferramentas",
        "entities": [{"id": "e1", "label": "Alpha", "required": True},
                     {"id": "e2", "label": "Beta", "required": True}],
        "criteria": [
            {"id": "c1", "label": "alpha", "required": True,
             "applies_to": ["e1"]},
            {"id": "c2", "label": "beta", "required": True,
             "applies_to": ["e2"]},
        ],
        "initial_paths": ["compare tools"],
    }


def rot_state(candidates, attempts):
    st = state_api.new_state("rotação")
    st["plan"] = plan2()
    st["discovery"] = {"candidates": list(candidates), "open": True}
    st["attempts"] = {k: list(v) for k, v in attempts.items()}
    return st


def failed(channel="web", target=""):
    att = {"channel": channel, "outcome": "failed"}
    if target:
        att["target"] = target
    return att


class RotationTest(unittest.TestCase):
    def test_b1_gaps_distintos_consomem_candidatos_distintos(self):
        st = rot_state([A, B], {"c1": [failed(target="x")],
                                "c2": [failed(target="y")]})
        ops = ac.select_ops(
            st, [{"criterion_id": "c1", "label": "alpha"},
                 {"criterion_id": "c2", "label": "beta"}], 2)
        self.assertEqual([o["kind"] for o in ops],
                         ["read_source", "read_source"])
        targets = [o["target"] for o in ops]
        self.assertEqual(len(set(targets)), 2)
        self.assertEqual(set(targets), {A, B})

    def test_b2_ordenacao_prefere_termo_do_gap(self):
        other = "https://github.com/o/other-utils"
        camera = "https://github.com/o/camera-tools"
        st = rot_state([other, camera], {"c1": [failed(target="x")]})
        ops = ac.select_ops(
            st, [{"criterion_id": "c1", "label": "camera suportada"}],
            1)
        self.assertEqual(ops[0]["kind"], "read_source")
        self.assertEqual(ops[0]["target"], camera)

    def test_b3_falha_nao_reofertada_mesmo_com_sufixo(self):
        broken = "https://example.org/broken.pdf"
        st = rot_state([broken],
                       {"c1": [failed(target=broken + " #1")]})
        ops = ac.select_ops(
            st, [{"criterion_id": "c1", "label": "alpha"}], 1)
        self.assertNotEqual(ops[0].get("kind"), "read_source")
        self.assertNotIn("broken.pdf", ops[0].get("target", ""))

    def test_b3_despacho_stripa_sufixo_antes_do_fetch(self):
        seen = {}

        def fetch(url):
            seen["url"] = url
            return "conteúdo limpo"

        out = ac._run_fetch(fetch, {"op_id": "r0-c1-0"},
                            A + " #2")
        self.assertEqual(out, "conteúdo limpo")
        self.assertEqual(seen["url"], A)


class GeneralMinerTest(unittest.TestCase):
    def test_d1_minera_owner_repo_de_awesome_list_bounded_sem_duplicar(self):
        text = ("awesome: https://github.com/tools/a-tool, "
                "https://github.com/owners/b-lib "
                "dup https://github.com/tools/a-tool, "
                "https://github.com/x/c1 https://github.com/y/c2 "
                "https://github.com/z/c3.")
        links = ac._extract_repo_candidates(
            text, source_url="https://example.org/awesome")
        self.assertEqual(len(links), 4)  # bounded
        self.assertEqual(len(set(links)), 4)  # sem duplicar
        self.assertIn("https://github.com/tools/a-tool", links)

    def test_d1_ignora_mesma_fonte(self):
        text = ("guia https://github.com/my/repo/blob/main/docs/X.md "
                "e https://github.com/other/r")
        links = ac._extract_repo_candidates(
            text, source_url="https://github.com/my/repo")
        self.assertEqual(links, ["https://github.com/other/r"])

    def test_d1_incorporate_registra_minerados_quando_aberto(self):
        st = state_api.new_state("mineração")
        st["discovery"]["open"] = True
        text = ("lista com https://github.com/third/party-tool "
                "e https://github.com/fourth/lib-x")
        ac.incorporate(st, "https://example.org/awesome", text, "op-1", 0,
                       qualification={"status": "usable", "excluded": False,
                                      "usable_text": text})
        self.assertIn("https://github.com/third/party-tool",
                      st["discovery"]["candidates"])
        self.assertIn("https://github.com/fourth/lib-x",
                      st["discovery"]["candidates"])


class ElicitationPromptTest(unittest.TestCase):
    def test_e1_prompt_instrui_propose_entity(self):
        captured = {}

        def model(prompt):
            captured["prompt"] = prompt
            return json.dumps([])

        assess = ac.make_model_assessor(model, max_docs=3)
        plan = {"entities": [{"id": "e1", "label": "Candidato 1"}],
                "criteria": [{"id": "c1", "label": "Melhoria",
                              "required": True, "applies_to": ["e1"]}],
                "open_discovery": {"needed": True}}
        assess(plan,
               {"https://example.org/a": "texto com Projeto X nomeado"},
               {"https://example.org/a": {"status": "usable",
                                          "excluded": False,
                                          "usable_text": "texto"}})
        self.assertIn("propose_entity", captured["prompt"])
        self.assertIn("para versionar o plano", captured["prompt"])


def single_plan():
    return {
        "plan_id": "ctx-1", "version": 1, "question": "Qual ferramenta?",
        "entities": [{"id": "e0", "label": "entidade 0", "required": True}],
        "criteria": [{"id": "c0", "label": "critério 0",
                      "required": True, "applies_to": ["e0"]}],
        "initial_paths": ["consulta inicial"],
    }


U = "https://example.org/ctx/a"


def ctx_transports():
    def search(target, channel="web"):
        return [{"url": U}]

    def fetch(url):
        return "Página A com conteúdo coletado"

    return search, fetch


def ctx_auditor(report, evidence):
    return {"enabled": False, "accepted": False}


class UserContextTest(unittest.TestCase):
    def test_f1_parse_context_key_value_e_erro_exit_2(self):
        self.assertEqual(entry.parse_user_context(["A=1", "B=x=y"]),
                         {"A": "1", "B": "x=y"})
        with self.assertRaises(SystemExit) as cm:
            entry.parse_user_context(["SEM-IGUAL"])
        self.assertEqual(cm.exception.code, 2)

    def test_f1_criterio_so_com_contexto_capa_em_partial(self):
        search, fetch = ctx_transports()

        def assess(plan, evidence, qualification, attempts,
                   user_context=None):
            self.assertEqual(user_context, {"servico": "OpenCode"})
            return [{"criterion_id": "c0", "state": "covered",
                     "justification": "usuário informou o serviço",
                     "origin": "user-provided",
                     "references": [{"url": "user://context/servico"}]}]

        res = ac.run_adaptive(
            "Qual ferramenta?", profile="light", plan=single_plan(),
            search_fn=search, fetch_fn=fetch, assess_fn=assess,
            writer_fn=lambda view: ("Síntese.", {"included_urls": [],
                                                 "cuts": "nenhum"}),
            auditor_fn=ctx_auditor, run_id="ctx-run",
            overrides={"max_rounds": 0},
            user_context={"servico": "OpenCode"})
        by_id = {c["id"]: c for c in
                 res["question_coverage"]["criteria"]}
        self.assertEqual(by_id["c0"]["state"], "partial")
        self.assertFalse(res["question_coverage"]["complete"])

    def test_f1_writer_rotula_contexto_como_informado_pelo_usuario(self):
        search, fetch = ctx_transports()
        captured = {}

        def model(prompt):
            if "Você avalia evidências" in prompt:
                captured["assess"] = prompt
                return json.dumps([])
            captured["writer"] = prompt
            return "relatório parcial honesto"

        res = ac.run_adaptive(
            "Qual ferramenta?", profile="light", plan=single_plan(),
            search_fn=search, fetch_fn=fetch,
            assess_fn=ac.make_model_assessor(model, max_docs=3),
            writer_fn=ac.make_model_writer(model),
            auditor_fn=ctx_auditor, run_id="ctx-run2",
            overrides={"max_rounds": 0},
            user_context={"servico": "OpenCode"})
        self.assertIn("user-provided", captured.get("assess", ""))
        self.assertIn("informado pelo usuário",
                      captured.get("writer", ""))
        self.assertTrue(res["partial"])


def collision_state():
    st = state_api.new_state("colisão")
    st["plan"] = {
        "plan_id": "col-1", "version": 1, "question": "Compare plugins",
        "entities": [{"id": "e1", "label": "slot generico",
                      "required": True}],
        "criteria": [{"id": "c0", "label": "função demonstrada",
                      "required": True, "applies_to": ["e1"]}],
    }
    st["discovery"] = {"candidates": [], "open": True}
    st["evidence"] = {"https://example.org/r": "texto util"}
    st["qualification"] = {"https://example.org/r": {
        "status": "usable", "usable_text": "texto util",
        "excluded": False}}
    return st


class RemapCollisionTest(unittest.TestCase):
    def test_a1_colisao_remapeia_em_vez_de_descartar(self):
        import coverage_ledger as cl
        st = collision_state()
        ledger = cl.Ledger(st["plan"])
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        ac._apply_discovery(
            st, ledger,
            {"entity": {"id": "e1", "label": "Real Plugin",
                        "repo": "o/real"}},
            {"criterion_id": "c0", "url": "https://example.org/r"})
        ids = [e["id"] for e in st["plan"]["entities"]]
        self.assertIn("e1-1", ids)
        self.assertEqual(len(st["plan_versions"]), 1)
        self.assertTrue(any("remapped" in str(n) for n in st["notes"]))

    def test_a2_remap_herda_criterios_e_avaliacao_resolve(self):
        import coverage_ledger as cl
        st = collision_state()
        ledger = cl.Ledger(st["plan"])
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        ac._apply_discovery(
            st, ledger,
            {"entity": {"id": "e1", "label": "Real Plugin",
                        "repo": "o/real"}},
            {"criterion_id": "c0", "url": "https://example.org/r"})
        # Sem herança, evaluate(c0, ..., entity e1-1) levantaria ValueError
        # (entity fora de applies_to) e a descoberta nunca viraria cobertura.
        out = ledger.evaluate(
            "c0", "partial", "função vista no README", "material_selecionado",
            [{"url": "https://example.org/r"}], "e1-1")
        self.assertEqual(out["state"], "partial")

    def test_a3_label_duplicado_continua_descartado(self):
        import coverage_ledger as cl
        st = collision_state()
        ledger = cl.Ledger(st["plan"])
        ledger.set_corpus(dict(st["evidence"]), dict(st["qualification"]))
        n = len(st["plan"]["entities"])
        ac._apply_discovery(
            st, ledger,
            {"entity": {"id": "e1-1", "label": "slot generico"}},
            {"criterion_id": "c0", "url": "https://example.org/r"})
        self.assertEqual(len(st["plan"]["entities"]), n)
        self.assertEqual(len(st["plan_versions"]), 0)


class AnchorStopwordsTest(unittest.TestCase):
    def test_b1_stopwords_removidas_nomes_mantidos(self):
        anchors = ac._question_anchors(
            "Descubra e compare plugins no OpenCode. Considere a versão.")
        self.assertIn("opencode", [a.lower() for a in anchors])
        for junk in ("descubra", "considere", "compare", "versao"):
            self.assertNotIn(junk, [a.lower() for a in anchors])

    def test_b2_sem_ancora_nao_quebra_query_curta(self):
        st = {"question": "o que há?", "plan": {"criteria": [], "entities": []}}
        self.assertTrue(ac._short_gap_query(
            st, {"criterion_id": "c0", "label": "x"}))


if __name__ == "__main__":
    unittest.main()
