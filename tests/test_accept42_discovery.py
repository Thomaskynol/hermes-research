"""accept42 (lane descoberta H2, incrementos 1+2): descoberta disciplinada.

Incremento 1 — admissão:
- o minerador (_extract_repo_candidates) admitia URLs que o leitor
  (repo_readme.raw_readme_url) recusa: owners reservados (apps/...),
  caminhos de asset (user-attachments), placeholder (SEU_USUARIO),
  "-" e nomes com extensão de arquivo — cada um virava candidate e
  gastava extração.
- o link-following (_extract_same_repo_links) admitia subpáginas
  (issues/stargazers/releases/tree) e o próprio repo com ".git",
  que o leitor não honra.

Incremento 2 — orçamento e seleção do pool:
- pool cheio descartava o recém-chegado (break no cap 64) em vez de
  evictar entrada (overlap 0 ∧ nunca tocada ∧ sem identidade) quando
  o novo tem overlap>0 com gap aberto; nunca evictar por nome.
- reserva (_pick_pool_reserve) sem gate de identidade: a URL reservada
  deve mencionar a entidade do gap servido; sem menção → próxima com
  menção ou None; .git duplicado nunca reservado 2×.
- required travava sem fonte própria: _maybe_substitute substitui
  required ALL-insufficient/sem refs quando há alternativa com
  fontes próprias mencionadas (registra substitution); nunca swap
  para MENOS evidência.
- re-leitura: 2 rounds sem ganho no mesmo alvo → próximo round mira
  entidade inexplorada com overlap>0 (nunca mesma URL nem variante
  normalizada); failed/nogain cobre variantes.

Regras (sem nomes de plugin/vencedores):
- nunca admitir o que raw_readme_url recusa;
- identicons/user-attachments, placeholders e extensões de arquivo
  ficam fora;
- ".git" do repo já obtido = duplicate, sem gastar extração.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept42 discovery test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac
import adaptive_state as state_api
import coverage_ledger as cl

REPO = "https://github.com/o/r"


def _open_state():
    st = state_api.new_state("accept42")
    st["discovery"] = {"candidates": [], "open": True}
    return st


def _qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def _desc(label):
    return (f"Eixo {label}: o que conta como evidencia operacional para "
            f"este eixo, com exemplos e condicoes de aceite.")


class RepoCandidateAdmissionTest(unittest.TestCase):
    def test_reserved_owner_apps_recusado(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "veja https://github.com/apps/meuapp para instalar",
                source_url="https://example.com/lista"),
            [])

    def test_user_attachments_recusado(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "asset em https://github.com/user-attachments/assets/abc123.zip",
                source_url="https://example.com/lista"),
            [])

    def test_placeholder_seu_usuario_recusado(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "exemplo https://github.com/SEU_USUARIO/meu-plugin",
                source_url="https://example.com/lista"),
            [])

    def test_traco_como_owner_recusado(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "estranho https://github.com/-/weird",
                source_url="https://example.com/lista"),
            [])

    def test_extensao_de_arquivo_recusada(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "print em https://github.com/acme/screenshot.png",
                source_url="https://example.com/lista"),
            [])

    def test_dotgit_normaliza_para_raiz(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "clone https://github.com/acme/widget.git",
                source_url="https://example.com/lista"),
            ["https://github.com/acme/widget"])

    def test_repo_real_admitido(self):
        self.assertEqual(
            ac._extract_repo_candidates(
                "plugins https://github.com/acme/widget e "
                "https://github.com/other/gadget",
                source_url="https://example.com/lista"),
            ["https://github.com/acme/widget",
             "https://github.com/other/gadget"])


class SameRepoLinkGateTest(unittest.TestCase):
    TEXT = ("links https://github.com/o/r/issues/3 "
            "https://github.com/o/r/stargazers "
            "https://github.com/o/r/releases/tag/v1 "
            "https://github.com/o/r/tree/main/docs "
            "https://github.com/o/r/blob/main "
            "https://github.com/o/r/blob/main/README.md")

    def test_subpaginas_fora_blob_arquivo_dentro(self):
        self.assertEqual(
            ac._extract_same_repo_links(self.TEXT, REPO),
            ["https://github.com/o/r/blob/main/README.md"])

    def test_dotgit_do_proprio_repo_e_duplicate(self):
        self.assertEqual(
            ac._extract_same_repo_links(
                "clone https://github.com/o/r.git", REPO),
            [])


class IncorporateAdmissionTest(unittest.TestCase):
    def test_incorporate_so_admite_repo_legivel(self):
        st = _open_state()
        ac.incorporate(
            st, "https://example.com/lista",
            "repositorios https://github.com/acme/widget "
            "asset https://github.com/user-attachments/assets/abc "
            "exemplo https://github.com/SEU_USUARIO/demo "
            "print https://github.com/acme/screenshot.png",
            "op1", 1)
        self.assertEqual(st["discovery"]["candidates"],
                         ["https://github.com/acme/widget"])

    def test_incorporate_dotgit_do_repo_obtido_nao_vira_candidate(self):
        st = _open_state()
        ac.incorporate(st, REPO, "corpo com link https://github.com/o/r.git",
                       "op1", 1)
        self.assertIn(REPO, st["evidence"])
        self.assertEqual(st["discovery"]["candidates"], [])


def _pool_plan():
    return {
        "plan_id": "a42-pool", "version": 1, "question": "compare widgets?",
        "entities": [
            {"id": "eA", "label": "AlphaWidget", "required": True},
            {"id": "eB", "label": "BetaGadget", "required": True},
        ],
        "criteria": [
            {"id": "c1", "label": "eixo um", "required": True,
             "per_candidate": True, "applies_to": ["eA", "eB"],
             "description": _desc("eixo um")},
        ],
        "initial_paths": ["q"],
    }


def _pool_gaps():
    return [
        {"criterion_id": "c1", "entity_id": "eA",
         "entity_label": "AlphaWidget", "label": "eixo um",
         "state": "insufficient"},
        {"criterion_id": "c1", "entity_id": "eB",
         "entity_label": "BetaGadget", "label": "eixo dois",
         "state": "insufficient"},
    ]


class PoolFullEvictionTest(unittest.TestCase):
    def _full_state(self, pool):
        st = _open_state()
        st["plan"] = _pool_plan()
        st["gaps"] = _pool_gaps()
        st["discovery"] = {"candidates": list(pool), "open": True}
        return st

    def test_novo_valido_evicta_invalido(self):
        fillers = [f"https://example.com/filler{i:03d}" for i in range(60)]
        valids = [f"https://example.com/alphawidget-doc{i}" for i in range(4)]
        st = self._full_state(fillers + valids)
        ac.incorporate(st, "https://example.com/lista",
                       "veja https://github.com/acme/alphawidget", "op1", 1)
        cands = st["discovery"]["candidates"]
        self.assertEqual(len(cands), 64, "teto intacto")
        self.assertIn("https://github.com/acme/alphawidget", cands,
                      "novo com overlap>0 entra")
        self.assertNotIn(fillers[0], cands, "invalido (overlap 0) sai")
        for v in valids:
            self.assertIn(v, cands, "nunca evictar por nome: com overlap fica")
        self.assertTrue(any("evict" in str(n).lower()
                            for n in st.get("notes", [])),
                        "eviccao auditavel em notes")

    def test_novo_invalido_descartado_com_pool_cheio_de_validos(self):
        pool = [f"https://example.com/alphawidget-v{i:02d}" for i in range(64)]
        st = self._full_state(pool)
        ac.incorporate(st, "https://example.com/lista",
                       "veja https://github.com/acme/zeta-tool", "op1", 1)
        cands = st["discovery"]["candidates"]
        self.assertEqual(cands, pool, "sem vitima evictavel: novo descartado")


class PoolReserveIdentityTest(unittest.TestCase):
    def _state(self, pool, evidence=None):
        st = state_api.new_state("compare widgets?")
        st["plan"] = {
            "plan_id": "a42-res", "version": 1,
            "question": "compare widgets?",
            "entities": [{"id": "eZ", "label": "ZetaWidget",
                          "required": True}],
            "criteria": [{"id": "c1", "label": "eixo zeta",
                          "required": True, "per_candidate": True,
                          "applies_to": ["eZ"],
                          "description": _desc("eixo zeta")}],
            "initial_paths": ["q"],
        }
        st["discovery"] = {"candidates": list(pool), "open": True}
        st["evidence"] = dict(evidence or {})
        st["attempts"] = {}
        return st

    def _gap(self):
        return {"criterion_id": "c1", "entity_id": "eZ",
                "entity_label": "ZetaWidget", "label": "eixo zeta",
                "state": "insufficient"}

    def test_sem_mencao_sem_reserva(self):
        st = self._state(["https://example.com/planning-with-files-eixo-zeta"])
        self.assertEqual(ac._pick_pool_reserve(st, [self._gap()],
                                              list(st["discovery"]
                                                   ["candidates"])),
                         (None, None))

    def test_proxima_com_mencao_assume(self):
        pool = ["https://example.com/planning-with-files-eixo-zeta",
                "https://example.com/zetawidget-guide"]
        st = self._state(pool)
        target, gap = ac._pick_pool_reserve(st, [self._gap()], list(pool))
        self.assertEqual(target, "https://example.com/zetawidget-guide")
        self.assertEqual((gap or {}).get("entity_id"), "eZ")

    def test_dotgit_do_repo_obtido_nunca_reservado_2x(self):
        src = "https://github.com/acme/alphawidget"
        body = "AlphaWidget corpo com eixo um. " * 40
        st = self._state([src + ".git"], {src: body})
        st["plan"]["entities"] = [{"id": "eA", "label": "AlphaWidget",
                                   "required": True}]
        st["plan"]["criteria"][0]["applies_to"] = ["eA"]
        gap = {"criterion_id": "c1", "entity_id": "eA",
               "entity_label": "AlphaWidget", "label": "eixo um",
               "state": "insufficient"}
        self.assertEqual(ac._pick_pool_reserve(st, [gap], [src + ".git"]),
                         (None, None))
        ops = ac.select_ops(st, [gap], 2)
        self.assertFalse(any(o.get("target", "").endswith(".git")
                             for o in ops),
                         "digest duplicado nunca reabre leitura")


class SubstitutionEvidenceTest(unittest.TestCase):
    def _plan(self, n_weak=5):
        ents = [{"id": f"e{i}", "label": f"Fraco{i}",
                 "required": True, "discovered": True,
                 "source_url": f"https://example.com/fraco{i}"}
                for i in range(1, n_weak + 1)]
        ents.append({"id": "e6", "label": "ZetaWidget", "required": False,
                     "discovered": True,
                     "source_url": "https://example.com/zeta1"})
        return {
            "plan_id": "a42-sub", "version": 1, "question": "compare?",
            "candidate_target": 6,
            "entities": ents,
            "criteria": [{"id": "c1", "label": "eixo um", "required": True,
                          "per_candidate": True,
                          "applies_to": [e["id"] for e in ents],
                          "description": _desc("eixo um")}],
        }

    def _state(self, plan, evidence):
        st = state_api.new_state("compare?")
        st["plan"] = plan
        st["evidence"] = dict(evidence)
        st["qualification"] = {u: _qual(t) for u, t in evidence.items()}
        st["rounds"] = [{"round": 0}, {"round": 1}]
        return st

    def test_fraco_travado_cede_a_alternativa_com_3_fontes_proprias(self):
        plan = self._plan()
        ev = {f"https://example.com/fraco{i}": f"Fraco{i} texto. " * 20
              for i in range(1, 6)}
        ev.update({f"https://example.com/zeta{i}":
                   "ZetaWidget eixo um com detalhes. " * 20
                   for i in range(1, 4)})
        st = self._state(plan, ev)
        led = cl.Ledger(plan, run_id=st["run_id"])
        led.set_corpus(dict(ev), {u: _qual(t) for u, t in ev.items()})
        for i in range(1, 6):
            led.evaluate("c1", "insufficient", f"Fraco{i} sem refs",
                         "assessor", [], f"e{i}")
        st["evaluations"] = [dict(v) for v in led._evals.values()]
        self.assertTrue(ac._maybe_substitute(st, led),
                        f"esperava troca: {st.get('notes')}")
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(emap["e6"].get("required", True))
        flipped = [i for i in range(1, 6)
                   if not emap[f"e{i}"].get("required", True)]
        self.assertEqual(len(flipped), 1, "uma troca por chamada")
        rec = st["plan_versions"][-1]
        self.assertEqual(rec.get("type"), "substitution")
        self.assertEqual(rec.get("new"), "e6")
        subs = st.get("substitutions") or []
        self.assertTrue(any(s.get("new") == "e6" for s in subs),
                       "substitution registrada")

    def test_fortes_com_fracos_sem_swap(self):
        plan = self._plan()
        ev = {}
        for i in range(1, 6):
            ev[f"https://example.com/fraco{i}"] = f"Fraco{i} eixo um. " * 20
        st = self._state(plan, ev)
        led = cl.Ledger(plan, run_id=st["run_id"])
        led.set_corpus(dict(ev), {u: _qual(t) for u, t in ev.items()})
        for i in range(1, 6):
            led.evaluate("c1", "covered", f"Fraco{i} cobre",
                         "assessor",
                         [{"url": f"https://example.com/fraco{i}"}], f"e{i}")
        st["evaluations"] = [dict(v) for v in led._evals.values()]
        self.assertFalse(ac._maybe_substitute(st, led))
        emap = {e["id"]: e for e in st["plan"]["entities"]}
        self.assertTrue(all(emap[f"e{i}"].get("required", True)
                            for i in range(1, 6)))
        self.assertFalse(emap["e6"].get("required", True))


class ReReadVariantTest(unittest.TestCase):
    def _state(self):
        st = state_api.new_state("compare widgets?")
        st["plan"] = _pool_plan()
        st["discovery"] = {"candidates": [], "open": False}
        st["evidence"] = {}
        return st

    def test_2_nogain_mira_outra_entidade_sem_reabrir_variante(self):
        tried = "https://example.com/eixo-dois-rascunho"
        fresh = "https://example.com/betagadget-doc"
        st = self._state()
        st["discovery"] = {"candidates": [tried, tried + "/", fresh],
                           "open": True}
        st["attempts"] = {"c1": [
            {"channel": "web", "outcome": "nogain", "target": tried},
            {"channel": "web", "outcome": "nogain", "target": tried}]}
        gap = {"criterion_id": "c1", "entity_id": "eB",
               "entity_label": "BetaGadget", "label": "eixo dois",
               "state": "insufficient"}
        ops = ac.select_ops(st, [gap], 2)
        reads = [o for o in ops if o.get("kind") == "read_source"]
        self.assertTrue(reads, "esperava read_source para entidade inexplorada")
        self.assertEqual(reads[0].get("target"), fresh)
        for o in ops:
            self.assertNotIn(o.get("target"), (tried, tried + "/"),
                             "mesma URL/variante nunca reabre")


class PoolFullLinkFollowingTest(unittest.TestCase):
    """Remediação de revisão: o laço same-repo ignorava o teto 64.

    Mesmo gate do laço minerado (dedupe + cap/evict/descarte), agora nos
    dois laços: pool cheio + 4 blob-links do mesmo repo não estouram.
    """

    def _full_state(self, pool):
        st = _open_state()
        st["plan"] = _pool_plan()
        st["gaps"] = _pool_gaps()
        st["discovery"] = {"candidates": list(pool), "open": True}
        return st

    def test_pool_cheio_via_link_following_nao_estoura(self):
        fillers = [f"https://example.com/filler{i:03d}" for i in range(60)]
        valids = [f"https://example.com/alphawidget-doc{i}" for i in range(4)]
        st = self._full_state(fillers + valids)
        blobs = [f"https://github.com/o/r/blob/main/alphawidget-extra{i}.md"
                 for i in range(4)]
        ac.incorporate(st, "https://github.com/o/r",
                       "docs " + " ".join(blobs), "op1", 1)
        cands = st["discovery"]["candidates"]
        self.assertEqual(len(cands), 64, "teto intacto no link-following")
        for b in blobs:
            self.assertIn(b, cands, "blob com overlap>0 entra via eviccao")
        for v in valids:
            self.assertIn(v, cands, "nunca evictar por nome: com overlap fica")

    def test_link_following_invalido_descartado_com_pool_cheio(self):
        pool = [f"https://example.com/alphawidget-v{i:02d}" for i in range(64)]
        st = self._full_state(pool)
        blob = "https://github.com/o/r/blob/main/zeta-manual.md"
        ac.incorporate(st, "https://github.com/o/r",
                       f"doc {blob}", "op1", 1)
        self.assertEqual(st["discovery"]["candidates"], pool,
                         "sem overlap e sem vitima: novo descartado")


class TechnicalAnnexWriteTest(unittest.TestCase):
    """Entrega separada: technical_annex.md ao lado de report.md.

    O principal continua existindo igual (sem perda); o anexo carrega
    os marcadores técnicos (transport failure, semantic boost, repo
    minerado, tabela de rodadas, outside detalhado). Falha do renderer
    nunca derruba a entrega nem toca o principal.
    """

    def _state(self):
        st = _open_state()
        st["plan"] = _pool_plan()
        st["profile"] = "medium"
        st["rounds"] = [
            {"round": 0, "kind": "sweep", "target_gaps": ["c1"],
             "new_evidence": 1, "delta": 0.5, "decision": "continuar"},
            {"round": 1, "kind": "gap", "target_gaps": [],
             "new_evidence": 0, "delta": 0.0, "decision": "encerrar"},
        ]
        st["stop"] = {"reason": "saturation", "partial": True,
                      "detail": "d"}
        st["notes"] = ["transport failure em webfetch: timeout",
                       "semantic boost: selecao ordenada",
                       "repo minerado: https://github.com/o/r (de x)"]
        st["evidence"] = {"https://example.com/a": "AlphaWidget texto"}
        st["counters"]["outside_corpus_citations"] = [
            "https://example.com/fora"]
        return st

    def _verification(self):
        return {"overall": {"status": "partial"},
                "dimensions": {
                    "support": {"dimension": "support", "status": "ok",
                                "evidence": {"a": 1}, "notes": []}}}

    def test_grava_annex_sem_tocar_principal(self):
        import os
        import tempfile
        st = self._state()
        with tempfile.TemporaryDirectory() as d:
            main = os.path.join(d, "report.md")
            with open(main, "w", encoding="utf-8") as f:
                f.write("# Principal\n\ncorpo.\n")
            annex = ac._write_technical_annex(d, st, self._verification())
            self.assertEqual(annex, os.path.join(d, "technical_annex.md"))
            with open(annex, encoding="utf-8") as f:
                body = f.read()
            for marker in ("transport failure", "semantic boost",
                           "repo minerado", "| Rodada |",
                           "https://example.com/fora"):
                self.assertIn(marker, body,
                              f"anexo sem marcador {marker!r}")
            with open(main, encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Principal\n\ncorpo.\n")

    def test_falha_do_renderer_nunca_derruba_nem_toca_principal(self):
        import os
        import tempfile
        st = self._state()
        with tempfile.TemporaryDirectory() as d:
            main = os.path.join(d, "report.md")
            with open(main, "w", encoding="utf-8") as f:
                f.write("# Principal\n")
            annex = ac._write_technical_annex(
                d, st, {"dimensions": ["quebrado"]})
            self.assertEqual(annex, "")
            self.assertTrue(any("annex failed" in str(n)
                                for n in st.get("notes", [])))
            with open(main, encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Principal\n")


if __name__ == "__main__":
    unittest.main()
