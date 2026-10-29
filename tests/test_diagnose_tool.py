"""Offline checks for tools/diagnose_run.py (cells + synthesis audit)."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import diagnose_run as diag  # noqa: E402

DOC1 = "https://alpha.example/docs"
DOC2 = "https://beta.example/docs"


def make_state() -> dict:
    return {
        "plan": {
            "entities": [
                {"id": "e1", "label": "Widget Alpha", "required": True},
                {"id": "e2", "label": "Widget Beta", "required": True},
            ],
            "criteria": [{
                "id": "c1",
                "label": "Compatibilidade com a versão instalada",
                "required": True,
                "applies_to": ["e1", "e2"],
            }],
        },
        "evidence": {
            DOC1: ("Widget Alpha is compatible with the installed version and "
                   "supports the alpha-run feature. It requires version 2.0."),
            DOC2: "Widget Beta version 1 is compatible with the host.",
        },
        "evaluations": [
            {"criterion_id": "c1", "entity_id": "e1", "state": "covered",
             "references": [{"url": DOC1}],
             "justification": "documented"},
            {"criterion_id": "c1", "entity_id": "e2", "state": "insufficient",
             "references": [], "justification": "no usable excerpt"},
        ],
        "report": {"markdown": (
            "# Relatório\n\n"
            "Widget Alpha is compatible with the installed version and "
            "supports the alpha-run feature [1].\n\n"
            "Widget Beta requires a paid subscription and ships with a "
            "graphical installer [2].\n\n"
            "This paragraph makes a broad claim without any source citation "
            "attached to it at all.\n"
        )},
    }


class CellsTest(unittest.TestCase):
    def test_buckets_por_celula(self):
        out = diag.classify(make_state())
        self.assertEqual(out["counts"], {"ok": 1, "selection_context": 1})
        by_entity = {row["entity_id"]: row["bucket"] for row in out["rows"]}
        self.assertEqual(by_entity, {"e1": "ok", "e2": "selection_context"})


class SynthesisTest(unittest.TestCase):
    def test_supported_unsupported_uncited(self):
        out = diag.synthesis_audit(make_state())
        self.assertEqual(out["supported"], 1)
        self.assertEqual(out["unsupported"], 1)
        self.assertEqual(out["uncited"], 1)
        self.assertEqual(len(out["unsupported_items"]), 1)
        item = out["unsupported_items"][0]
        self.assertEqual(item["cites"], ["2"])
        self.assertIn("Widget Beta", item["sentence"])
        self.assertIn("overlap", item["reason"])

    def test_declaracao_de_lacuna_citada_e_sustentada(self):
        state = make_state()
        state["report"]["markdown"] += (
            "\nNenhum excerto do corpus em [1] afirma ou nega o preço.\n")
        out = diag.synthesis_audit(state)
        self.assertEqual(out["supported"], 2)
        self.assertEqual(out["unsupported"], 1)

    def test_sigla_maiuscula_e_palavra_de_conteudo(self):
        self.assertIn("mit", diag.content_words("`License MIT` — fonte: [1]"))
        self.assertIn("v2", diag.content_words("API V2 estável"))

    def test_numbering_follows_obtained_order(self):
        state = make_state()
        # Persisted evidence is sorted; the obtained counter keeps the
        # renderer's acquisition order (doc2 was cited first).
        state["evidence"] = {DOC1: state["evidence"][DOC1],
                             DOC2: state["evidence"][DOC2]}
        state["counters"] = {"documents": {"obtained": [DOC2, DOC1]}}
        numbers = diag._number_map(state)
        self.assertTrue(numbers[1].endswith("beta.example/docs"))


class CliTest(unittest.TestCase):
    def test_exit_2_para_diretorio_inexistente(self):
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = diag.main(["diagnose_run.py", "/caminho/que/nao/existe"])
        self.assertEqual(code, 2)
        self.assertIn("state", err.getvalue())

    def test_run_dir_valido_imprime_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "state.json").write_text(
                json.dumps(make_state()), encoding="utf-8")
            payload_path = run_dir / "diag.json"
            with redirect_stdout(io.StringIO()) as out:
                code = diag.main(["diagnose_run.py", str(run_dir),
                                  "--json", str(payload_path)])
            self.assertEqual(code, 0)
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertIn("cells", payload)
            self.assertEqual(payload["synthesis"]["supported"], 1)
            self.assertIn('"synthesis"', out.getvalue())


if __name__ == "__main__":
    unittest.main()
