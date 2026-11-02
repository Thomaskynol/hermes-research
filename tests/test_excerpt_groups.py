"""Excerpt must reach fact sections at the tail (accept12: license unseen)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import adaptive_coordinator as ac


def doc_with_tail_facts():
    body = ("Overview. " + "This plugin coordinates planning work. " * 60
            + "\n## Development\n\n```bash\nnpm test\n```\n"
            + "Compatibility was verified with OpenCode V1 1.18.22 and V2 beta. "
            * 20
            + "\n## License\n\nMIT\n")
    return body


def plan():
    return {
        "plan_id": "excerpt", "version": 1,
        "entities": [{"id": "e1", "label": "opencode-planner",
                      "required": True}],
        "criteria": [
            {"id": "c1", "label": "melhoria de planejamento",
             "required": True, "applies_to": ["e1"], "description": "Eixo melhoria de planejamento: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
            {"id": "c2", "label": "custos e licenca",
             "required": True, "applies_to": ["e1"], "description": "Eixo custos e licenca: o que conta como evidencia operacional para este eixo, com exemplos e condicoes de aceite."},
        ],
    }


class ExcerptGroupQuotaTest(unittest.TestCase):
    def test_licenca_no_rodape_entra_no_excerpt(self):
        text = doc_with_tail_facts()
        groups = ac._criterion_groups(plan())
        excerpt, _, _ = ac._relevant_excerpt(text, 1200, [], groups=groups)
        low = excerpt.lower()
        self.assertIn("license", low)
        self.assertIn("mit", low)
        self.assertIn("1.18.22", excerpt)

    def test_sem_groups_mantem_comportamento_antigo(self):
        text = doc_with_tail_facts()
        excerpt, _, _ = ac._relevant_excerpt(text, 1200, ["planning"])
        self.assertNotIn("## License", excerpt)

    def test_ancora_tem_subgrupos_de_fatos(self):
        groups = ac._criterion_groups(plan())
        for name in ("ancora:licenca", "ancora:custo", "ancora:versao",
                     "ancora:instalacao", "ancora:manutencao"):
            self.assertIn(name, groups)


if __name__ == "__main__":
    unittest.main()
