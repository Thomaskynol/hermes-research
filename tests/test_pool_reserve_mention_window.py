"""B3 pool reserve + B4 entity-mention window (RED first, TDD).

B3: mined pool candidates without their own cell die in the pool because
select_ops only reads the pool on failed/nogain. One slot per round must
go to the best pool candidate tied to an open entity (same _rank_unfetched
ranking), within the op cap.
B4: assessor excerpts (1200 chars) lose the entity mention (full text
sustains, excerpt shows only install). The assessor lot must prioritize
the window containing the cell entity mention, same budgets.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("pool reserve test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api


def b3_plan():
    return {
        "plan_id": "b3", "version": 1,
        "question": "Compare widgets?",
        "entities": [
            {"id": "e1", "label": "AlphaWidget", "required": True},
            {"id": "e2", "label": "BetaGadget", "required": True},
        ],
        "criteria": [
            {"id": "c0", "label": "custo de licenca", "required": True,
             "per_candidate": True, "applies_to": ["e1", "e2"]},
        ],
        "initial_paths": ["q"],
    }


def b3_gaps():
    return [
        {"criterion_id": "c0", "entity_id": "e1",
         "entity_label": "AlphaWidget", "label": "custo de licenca",
         "state": "insufficient"},
        {"criterion_id": "c0", "entity_id": "e2",
         "entity_label": "BetaGadget", "label": "custo de licenca",
         "state": "insufficient"},
    ]


def b3_state(pool, attempts=None):
    st = state_api.new_state("Compare widgets?")
    st["plan"] = b3_plan()
    st["discovery"] = {"candidates": list(pool), "open": True}
    st["attempts"] = dict(attempts or {})
    return st


class PoolReserveTest(unittest.TestCase):
    def test_reserva_um_slot_para_pool_sem_falha(self):
        pool = ["https://github.com/o/alphawidget-tool",
                "https://github.com/o/betagadget-tool"]
        st = b3_state(pool, {})
        ops = ac.select_ops(st, b3_gaps(), 3)
        self.assertLessEqual(len(ops), 3, "cap respeitado")
        kinds = [o.get("kind") for o in ops]
        self.assertIn("read_source", kinds,
                      "pool minerado sem falha deve ganhar 1 read_source")
        targets = [o.get("target", "") for o in ops
                   if o.get("kind") == "read_source"]
        self.assertTrue(any("alphawidget" in t.lower() or "betagadget" in t.lower()
                            for t in targets))
        # melhor candidato pelo mesmo ranking _rank_unfetched
        ranked = ac._rank_unfetched(
            st, pool, {"criterion_id": "c0", "label": "custo de licenca",
                       "entity_id": "e1", "entity_label": "AlphaWidget"})
        self.assertIn(targets[0], ranked)

    def test_reserva_respeita_falha_e_evidencia(self):
        pool = ["https://example.org/broken",
                "https://github.com/o/betagadget-tool"]
        st = b3_state(pool, {})
        st["evidence"] = {"https://example.org/broken": "ja coletado"}
        st["attempts"] = {"c0": [{"channel": "web", "outcome": "failed",
                                  "target": "https://example.org/broken"}]}
        ops = ac.select_ops(st, b3_gaps(), 3)
        targets = [o.get("target", "") for o in ops]
        self.assertFalse(any("broken" in t for t in targets),
                         "falha/evidencia nunca reabre")
        # URL boa assume a reserva: read_source para o candidato valido
        self.assertTrue(any(o.get("kind") == "read_source"
                            and "betagadget-tool" in o.get("target", "")
                            for o in ops),
                        "URL boa sem falha/evidencia assume a reserva")
        self.assertTrue(any("pool reserve" in n and "betagadget-tool" in n
                            for n in st.get("notes", [])),
                        "reserva registrada em notes")

    def test_sem_pool_mantem_comportamento(self):
        st = b3_state([], {})
        ops = ac.select_ops(st, b3_gaps(), 2)
        self.assertEqual(len(ops), 2)
        # sem pool: nenhuma reserva inventada
        self.assertEqual(ac._pick_pool_reserve(st, b3_gaps(), []),
                         (None, None))
        self.assertFalse(any(o.get("kind") == "read_source" for o in ops),
                         "sem pool, sem read_source de reserva")
        self.assertFalse(any("pool reserve" in n
                             for n in st.get("notes", [])),
                         "sem pool, sem nota de reserva")
        self.assertFalse(any(o.get("kind") == "read_source" and
                             "github.com" in o.get("target", "")
                             for o in ops))


class EntityMentionWindowTest(unittest.TestCase):
    def test_assessor_prioriza_janela_com_mencao_da_entidade(self):
        # Head dominado por instalacao + secoes de fatos (licenca/custo/
        # versao/manutencao) + criterios ricos: grupos consomem o budget
        # de 1200 antes do ranking global alcançar a mencao isolada da
        # entidade (só o nome, sem termos de criterio/ancora).
        install_head = ("Install with npm install tool instructions. " * 60 + "\n")
        cost = ("Price free paid subscription cost details. " * 30 + "\n")
        version = ("Version release changelog compatib v1 v2. " * 30 + "\n")
        maint = ("Maintainer contributors maintenance notes. " * 30 + "\n")
        lic = ("License MIT Apache BSD GPL terms. " * 30 + "\n")
        crit = ("Recursos offline caching sync recursos offline. " * 40 + "\n")
        mention = ("BetaGadget xyzzy blorpt quux. " * 8 + "\n")
        doc = install_head + cost + version + maint + lic + crit + mention + crit
        self.assertGreater(len(doc), 6000)

        seen = {}

        def fake_client(prompt):
            seen["prompt"] = prompt
            return "[]"

        plan = {
            "plan_id": "b4", "version": 1,
            "entities": [{"id": "e2", "label": "BetaGadget",
                          "required": True}],
            "criteria": [
                {"id": f"c{i}", "label": f"dimensao {i} recursos offline",
                 "required": True, "applies_to": ["e2"]}
                for i in range(4)],
            "initial_paths": [],
        }
        assess = ac.make_model_assessor(
            fake_client, max_docs=8, excerpt_chars=1200, json_budget=12000)
        assess(plan, {"https://example.org/beta": doc},
               {"https://example.org/beta": {"status": "usable",
                                             "excluded": False,
                                             "usable_text": doc}}, {})
        prompt = seen.get("prompt", "")
        # xyzzy só existe na janela da menção (o plano tem BetaGadget mas
        # nunca xyzzy): prova que o excerto carrega a menção, não só o head
        self.assertIn("xyzzy", prompt.lower(),
                      "lote do assessor deve conter a mencao da entidade, "
                      "mesmo com instalacao dominando o head")
        # budgets intactos
        sel = assess.last_selection
        total = sum(sel.get("excerpt_chars", {}).values())
        self.assertLessEqual(total, 1200 + 50)
        self.assertLessEqual(len(sel.get("urls", [])), 8)

    def test_relevant_excerpt_com_entidade_nao_estoura_limite(self):
        doc = ("Install with npm install betagadget-tool. " * 60 + "\n"
               + "BetaGadget review offline caching. " * 40)
        groups = ac._criterion_groups({
            "criteria": [{"id": "c0", "label": "recursos offline"}],
            "entities": [{"id": "e2", "label": "BetaGadget"}]})
        # chamada legada continua valida e dentro do limite
        exc, _, _ = ac._relevant_excerpt(doc, 1200, ["offline"], groups=groups)
        self.assertLessEqual(len(exc), 1250)


if __name__ == "__main__":
    unittest.main()
