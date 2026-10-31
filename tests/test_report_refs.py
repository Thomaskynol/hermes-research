"""Citation rewriting must not corrupt quoted literals (accept9 artifact)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import report_renderer as rr

IN = "https://github.com/in/corpus"
OUT = "https://fora.example/s"


class QuotedLiteralTest(unittest.TestCase):
    def test_url_dentro_de_literal_citado_e_preservada(self):
        # consultado vs mencionado: literal preservada nao e citacao fora
        text = ('Instale com "plugin": ["superpowers@git+%s"].' % OUT)
        out, outside = rr._rewrite_refs(text, {}, set())
        self.assertIn(OUT, out)
        self.assertNotIn("[fora do corpus]", out)
        self.assertEqual(outside, [])

    def test_url_solta_fora_do_corpus_vira_marcador(self):
        out, outside = rr._rewrite_refs("Veja %s agora." % OUT, {}, set())
        self.assertIn("[fora do corpus]", out)
        self.assertNotIn(OUT, out)
        self.assertEqual(outside, [OUT])

    def test_url_do_corpus_vira_numero(self):
        cited = set()
        out, _ = rr._rewrite_refs("Veja %s." % IN, {rr._norm(IN): 3}, cited)
        self.assertIn("[3]", out)
        self.assertIn(rr._norm(IN), cited)


class PersistedNumbersTest(unittest.TestCase):
    def test_numero_persistido_tem_prioridade(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import diagnose_run as dg
        state = {"report": {"numbers": {"1": "https://a.example/x"},
                            "markdown": "| [1] | https://b.example/y |"}}
        got = dg._number_map(state)
        self.assertEqual(got[1], rr._norm("https://a.example/x"))

    def test_tabela_do_relatorio_e_o_fallback(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import diagnose_run as dg
        state = {"report": {"markdown": "| [2] | https://b.example/y |"},
                 "evidence": {"https://b.example/y": "texto"}}
        got = dg._number_map(state)
        self.assertEqual(got[2], rr._norm("https://b.example/y"))


if __name__ == "__main__":
    unittest.main()


class AnnexCitedCountTest(unittest.TestCase):
    def test_tabela_conta_citacoes_do_proprio_render(self):
        # accept11: counters.json=7, tabela do relatório=0 (snapshot lido
        # antes de record_cited). A tabela deve refletir o texto renderizado.
        state = {"run_id": "t", "question": "q", "plan": {"entities": [],
                 "criteria": []}, "evidence": {}, "qualification": {},
                 "discovery": {}, "attempts": {}, "rounds": [], "notes": []}
        lines = rr._annex_section(state, rr._labels("pt-BR"), None, False,
                                  {IN})
        table = "\n".join(lines)
        self.assertIn("| cited | 1 |", table)
