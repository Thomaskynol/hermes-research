"""Ponto 1: extração genérica de claims + transporte de revisão injetável.

- Relatórios factuais (sem pacotes/licenças) devem produzir claims>0 quando
  houver citações [n]/URLs ou âncora em evidência real (generic=True).
- generic=False (default) preserva o contrato histórico do corpus.
- review_fn injetável substitui o transporte OpenRouter; falhas viram
  transport_error (nunca aprovação); zero claims continua revisão
  incompleta mesmo com review_fn que aprovaria tudo.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("generic audit test is offline")


sys.addaudithook(offline_guard)

import semantic_review as sr

URL1 = "https://example.org/docs/cache"
URL2 = "https://example.org/blog/uv-guide"

REPORT_FACTUAL = """# Como o uv gerencia cache

## Achados

O uv armazena pacotes em um cache global compartilhado [1]. O comando
`uv cache clean` remove 2,4 GB de artefatos obsoletos em instalações típicas [1].

A resolução de dependências do uv é mais rápida que a do pip em projetos
grandes [2]. Este relatório responde à pergunta original.
"""

EVIDENCE_FACTUAL = {
    URL1: "uv cache: pacotes ficam num cache global compartilhado. "
          "uv cache clean remove artefatos obsoletos, 2,4 GB em testes.",
    URL2: "Comparativo: resolução do uv mais rápida que pip em projetos "
          "grandes com muitas dependências.",
}

REPORT_VACUOUS = """# Resumo

## Achados

Este relatório responde à pergunta original. Os detalhes estão acima.
"""


def sustained_stub(payload, model):
    return [{"id": it["id"], "verdict": "sustained",
             "support": "stub", "correction": ""} for it in payload]


class GenericExtractionTest(unittest.TestCase):
    def test_factual_report_yields_claims_with_generic_true(self):
        claims = sr.extract_claims(REPORT_FACTUAL, EVIDENCE_FACTUAL,
                                   generic=True)
        self.assertGreater(len(claims), 0, "relatório factual produziu 0 claims")
        generics = [c for c in claims if c.get("generic")]
        self.assertGreater(len(generics), 0, "nenhuma claim genérica extraída")
        for c in generics:
            self.assertTrue(c.get("anchors") or c.get("evidence"),
                            f"claim genérica sem âncora: {c['claim'][:60]}")

    def test_default_preserves_historical_contract(self):
        claims = sr.extract_claims(REPORT_FACTUAL, EVIDENCE_FACTUAL)
        self.assertEqual(
            [c for c in claims if c.get("generic")], [],
            "default extraiu genéricas (quebra contrato histórico)")

    def test_vacuous_prose_yields_no_generic_claims(self):
        claims = sr.extract_claims(REPORT_VACUOUS, EVIDENCE_FACTUAL,
                                   generic=True)
        self.assertEqual(
            [c for c in claims if c.get("generic")], [],
            "prosa vacua virou claim genérica")

    def test_zero_claims_stays_incomplete_even_with_approving_transport(self):
        result = sr.review_report("Nada verificável aqui.", {}, enabled=True,
                                  generic=True, review_fn=sustained_stub,
                                  votes=1)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict_state"], "revisão incompleta")
        self.assertEqual(result["claims"], 0)


class InjectableReviewTransportTest(unittest.TestCase):
    def test_stub_review_approves_real_claims(self):
        # Quórum exige >=2 passagens válidas; stub determinístico aprova nas 3.
        result = sr.review_report(REPORT_FACTUAL, EVIDENCE_FACTUAL,
                                  enabled=True, generic=True,
                                  review_fn=sustained_stub, votes=3)
        self.assertGreater(result["claims"], 0)
        self.assertGreater(result["claims_reviewed"], 0)
        self.assertTrue(result["accepted"], result.get("verdict_state"))

    def test_failing_transport_is_never_favourable(self):
        def boom(payload, model):
            raise ConnectionError("rede simulada fora")
        result = sr.review_report(REPORT_FACTUAL, EVIDENCE_FACTUAL,
                                  enabled=True, generic=True,
                                  review_fn=boom, votes=1)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict_state"], "revisão incompleta")

    def test_default_transport_still_requires_credential(self):
        result = sr.review_report(REPORT_FACTUAL, EVIDENCE_FACTUAL,
                                  enabled=True, generic=True, votes=1)
        # Sem OPENROUTER_API_KEY válida no ambiente de teste: credential_error
        # (nunca aprovação silenciosa). Com chave válida, tentaria a rede --
        # o audithook bloquearia; ambos os casos são não-aprovação aqui.
        self.assertFalse(result.get("accepted", False))


if __name__ == "__main__":
    unittest.main()
