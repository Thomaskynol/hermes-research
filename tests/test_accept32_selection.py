#!/usr/bin/env python3
"""accept32 — excerto do reenvio prioriza a janela da célula aberta.

Widget Alpha / eixo failure: doc em _sent que sustenta a célula aberta
é reenviado, mas o excerto global (head + round-robin de 150 chars)
perde a passagem de sustentação — termo da dimensão e menção da
entidade estão a ~350 chars um do outro (dentro dos 1500 da
localidade do reenvio) e caem em janelas separadas. O excerto da URL
reenviada deve conter UMA janela com ambos os sinais, dentro dos
mesmos limites (1200/12000). Sem hardcode de entidade/fonte.
"""
import json as _json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("accept32 selection test is offline")


sys.addaudithook(offline_guard)

import adaptive_coordinator as ac

URL_S = "https://example.org/widget-alpha-manual"


def qual(text):
    return {"status": "usable", "reason": "ok", "usable_text": text,
            "excluded": False}


def support_doc():
    head = ("failure modes overview and limitation notes. " * 60)
    gap = ("lorem ipsum dolor sit amet consectetur adipiscing elit. " * 70)
    support = ("Widget Alpha field notes. " + "padding word " * 25
               + "the failure procedure is documented here. ")
    return head + "\n\n" + gap + "\n\n" + support


def global_plan():
    return {"plan_id": "q", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": False, "discovered": True,
                          "source_url": URL_S}],
            "criteria": [{"id": "c0", "label": "overview",
                          "required": True}],
            "initial_paths": ["q"]}


def cell_plan():
    return {"plan_id": "q", "version": 1, "question": "q",
            "entities": [{"id": "w1", "label": "Widget Alpha",
                          "required": True, "discovered": True,
                          "source_url": URL_S}],
            "criteria": [{"id": "c1", "label": "failure modes",
                          "required": True, "per_candidate": True,
                          "applies_to": ["w1"]}],
            "initial_paths": ["q"]}


def excerpts_of(prompt, url):
    marker = "Material selecionado: "
    items, _ = _json.JSONDecoder().raw_decode(
        prompt[prompt.index(marker) + len(marker):])
    return [it.get("excerpt", "") for it in items
            if isinstance(it, dict) and it.get("url") == url]


def has_joint_window(excerpt):
    return any("widget alpha" in s and "failure" in s
               for s in excerpt.lower().split("[...]"))


class ResendExcerptFocusTest(unittest.TestCase):
    def test_resent_excerpt_keeps_support_window(self):
        doc = support_doc()
        self.assertGreater(len(doc), 6000)
        seen = {}

        def fake_client(prompt):
            seen.setdefault("prompts", []).append(prompt)
            return "[]"

        assess = ac.make_model_assessor(fake_client)
        assess(global_plan(), {URL_S: doc}, {URL_S: qual(doc)})
        first = excerpts_of(seen["prompts"][-1], URL_S)[0]
        self.assertLessEqual(len(first), 1200, len(first))
        assess(cell_plan(), {URL_S: doc}, {URL_S: qual(doc)})
        sel = list((assess.last_selection or {}).get("urls") or [])
        self.assertIn(URL_S, sel,
                      f"doc em _sent que sustenta célula aberta deve voltar: {sel[:4]}")
        second = excerpts_of(seen["prompts"][-1], URL_S)[0]
        self.assertLessEqual(len(second), 1200, len(second))
        self.assertTrue(
            has_joint_window(second),
            "excerto do reenvio deve conter UMA janela com menção da "
            "entidade + termo da dimensão da célula que motivou o envio")


if __name__ == "__main__":
    unittest.main()
