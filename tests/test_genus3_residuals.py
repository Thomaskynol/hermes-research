"""genus3 residuals: entity-blind selection, floating citations, audit.

- A: assessor selection must include material for EVERY required entity
  even when none is discovered (genus3: Flask had 31 docs in corpus, 0 in
  every 8-doc selection -> 15 selection_context cells).
- B: writer prompt must demand inline [n] on the claim line (genus3:
  citations sat on a separate "Fontes:" line -> 58 uncited).
- C: synthesis audit must attribute floating cite-only lines
  ("Fontes:" + "- [1]") to the preceding claim instead of ignoring both.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("genus3 residuals test is offline")


sys.addaudithook(deny_network)

import adaptive_coordinator as ac
import tools.diagnose_run as diagnose


def qual(text):
    return {"status": "usable", "usable_text": text, "excluded": False}


DJANGO = "https://docs.example.org/django/"
FASTAPI = "https://docs.example.org/fastapi/"
FLASK = "https://docs.example.org/flask/"


def genus_plan():
    return {
        "plan_id": "g3", "version": 1,
        "entities": [{"id": "e1", "label": "Django", "required": True},
                     {"id": "e2", "label": "FastAPI", "required": True},
                     {"id": "e3", "label": "Flask", "required": True}],
        "criteria": [{"id": "c1", "label": "roteamento", "required": True,
                      "per_candidate": True,
                      "applies_to": ["e1", "e2", "e3"], "description": "Eixo roteamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."}],
        "initial_paths": ["q"],
        "open_discovery": {"needed": False},
    }


def genus_evidence():
    base = {
        DJANGO: "Django URLconfs map routes. ",
        FASTAPI: "FastAPI APIRouter decorator routes. ",
        FLASK: "Flask route decorator maps URLs. ",
    }
    ev = {}
    for url, sent in base.items():
        for i in ("", "views/", "guide/", "api/"):
            ev[url + i] = (sent * 60)
    return ev


class AssessorEntityCoverageTest(unittest.TestCase):
    def test_selection_includes_every_required_entity(self):
        seen = {}

        def model(prompt):
            seen["prompt"] = prompt
            return "[]"

        # Tight budget: naive first-N would starve the last entity.
        assess = ac.make_model_assessor(model, max_docs=24,
                                        excerpt_chars=400,
                                        json_budget=2000)
        ev = genus_evidence()
        assess(genus_plan(), ev,
               {u: qual(t) for u, t in ev.items()}, {})
        sel = list(assess.last_selection.get("urls") or [])
        blob = " ".join(sel).lower()
        for token in ("django", "fastapi", "flask"):
            self.assertIn(token, blob,
                          f"entity {token} missing from selection {sel}")


class EntityAboutnessTest(unittest.TestCase):
    def test_entity_doc_prefers_doc_about_entity_over_mere_mention(self):
        # genus4: _entity_doc returned a JetBrains comparison article for
        # Django/FastAPI and an arXiv URL for Flask — first docs that
        # merely MENTION the token. The reserved slot must hold the doc
        # ABOUT the entity (official reference), not a passing mention.
        ev = {
            "https://blog.example.org/django-flask-fastapi-compared":
                ("Django versus Flask versus FastAPI comparison. " * 40),
            "https://arxiv.example.org/abs/2511.18038v2":
                ("Some paper mentioning flask once. " * 40),
            "https://flask.example.org/en/stable/api/":
                ("Flask API reference. Flask blueprints. Flask install. "
                 * 40),
        }
        ent = {"id": "e3", "label": "Flask", "required": True}
        got = ac._entity_doc(ent, ev,
                             {u: qual(t) for u, t in ev.items()})
        self.assertEqual(got, "https://flask.example.org/en/stable/api/",
                         f"reserved junk instead of the entity doc: {got}")

    def test_entity_doc_distinct_slots_per_entity(self):
        # Comparison article mentions all three; each entity must still
        # get its own official doc, never the same shared mention.
        ev = {
            "https://blog.example.org/django-flask-fastapi-compared":
                ("Django versus Flask versus FastAPI comparison. " * 40),
            "https://docs.example.org/django/": ("Django URLconfs. " * 60),
            "https://docs.example.org/fastapi/": ("FastAPI routes. " * 60),
            "https://docs.example.org/flask/": ("Flask blueprints. " * 60),
        }
        taken = set()
        got = {}
        for ent in ({"id": "e1", "label": "Django"},
                    {"id": "e2", "label": "FastAPI"},
                    {"id": "e3", "label": "Flask"}):
            u = ac._entity_doc(ent, ev,
                               {u: qual(t) for u, t in ev.items()},
                               taken=taken)
            got[ent["id"]] = u
            taken.add(u)
        self.assertEqual(got["e1"], "https://docs.example.org/django/")
        self.assertEqual(got["e2"], "https://docs.example.org/fastapi/")
        self.assertEqual(got["e3"], "https://docs.example.org/flask/")


class WriterInlineCitesTest(unittest.TestCase):
    def test_writer_prompt_demands_inline_citations(self):
        seen = {}

        def model(prompt):
            seen["prompt"] = prompt
            return "texto"

        write = ac.make_model_writer(model, max_chars=4000)
        write({"question": "q", "question_coverage": {},
               "plan": genus_plan(),
               "evidence": {DJANGO: "Django URLconfs map routes."}})
        self.assertIn("mesma linha", seen.get("prompt", "").lower())


class FloatingCitesAuditTest(unittest.TestCase):
    def test_fonte_block_attributes_cites_to_claim(self):
        url = "https://example.org/django-routing"
        doc = ("Django URLconfs map routes with view functions "
               "handling requests and responses documented")
        state = {
            "plan": {"entities": [{"id": "e1", "label": "Django"}],
                     "criteria": []},
            "evidence": {url: doc},
            "report": {
                "markdown": ("- Django URLconfs map routes with view "
                             "functions handling requests and responses "
                             "documented here today.\n\nFontes:\n- [1]\n"),
                "numbers": {"1": url},
            },
        }
        audit = diagnose.synthesis_audit(state)
        self.assertEqual(audit["supported"], 1, audit)
        self.assertEqual(audit["uncited"], 0, audit)


if __name__ == "__main__":
    unittest.main()
