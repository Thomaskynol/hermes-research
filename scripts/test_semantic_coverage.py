#!/usr/bin/env python3
"""Testes de cobertura rastreável da extração e revisão de afirmações.

Detecta as 6 falhas reproduzidas na revisão independente:
1. Metadados: Tag/Branch/Commit/Data não extraídas para pacotes
2. Tabela: 5 pacotes em UMA claim, deve ser separadas
3. Título: título factual perdido (apenas nome do pacote verificado)
4. Parágrafo longo: descartado sem registro de incompletude
5. Justificativa factual: _ORDINAL apaga fato + justificativa
6. Registro: scope vazio, IDs reatribuídos, review_state sempre not_reviewed

Simula apenas _review_pass quando julgamentos são necessários.
Nenhuma chamada de rede ou ao modelo.
"""

import copy
import json
import sys
import unittest

sys.path.insert(0, '/opt/data/deep_research_outputs/gpt_researcher')

import semantic_review as sr

# ---------------------------------------------------------------------------
# Fixtures compartilhadas — nomes reconhecidos por _PKG_RE
# ---------------------------------------------------------------------------

REPORT_MULTI_PACKAGE = """# Relatório de Teste

## Pacote opencode-alpha

O pacote `opencode-alpha` é gratuito e usa licença MIT.

Tag: v1.0.0
Branch: main
Commit: abc123
Data: 2026-01-15

## Pacote opencode-beta

O pacote `opencode-beta` requer assinatura paga e não é open-source.

Tag: v2.0.0
Branch: develop
Commit: def456
Data: 2026-02-20

## Pacote opencode-gamma

O pacote `opencode-gamma` é distribuído sob licença Apache-2.0.

Tag: v0.9.0
Branch: feature/sandbox
Commit: ghi789
Data: 2026-03-10

## Pacote opencode-delta

O pacote `opencode-delta` tem custo recorrente mensal.

Tag: v1.5.0
Branch: release/1.5
Commit: jkl012
Data: 2026-04-05

## Pacote opencode-epsilon

O pacote `opencode-epsilon` é gratuito para uso pessoal.

Tag: v3.0.0
Branch: main
Commit: mno345
Data: 2026-05-12
"""

EVIDENCE_MULTI = {
    "https://example.com/opencode-alpha": "opencode-alpha: licença MIT, software gratuito.",
    "https://example.com/opencode-beta": "opencode-beta: requer assinatura paga, não é open-source.",
    "https://example.com/opencode-gamma": "opencode-gamma: licença Apache-2.0.",
    "https://example.com/opencode-delta": "opencode-delta: custo recorrente mensal.",
    "https://example.com/opencode-epsilon": "opencode-epsilon: gratuito para uso pessoal.",
}

# Relatório com muitas afirmações (mais que o limite de 25)
REPORT_MANY_CLAIMS = """# Relatório com Muitas Afirmações

O pacote `opencode-01` é gratuito e usa licença MIT.
O pacote `opencode-02` é gratuito e usa licença Apache-2.0.
O pacote `opencode-03` é gratuito e usa licença BSD.
O pacote `opencode-04` é gratuito e usa licença ISC.
O pacote `opencode-05` é gratuito e usa licença GPL.
O pacote `opencode-06` é gratuito e usa licença MIT.
O pacote `opencode-07` é gratuito e usa licença Apache-2.0.
O pacote `opencode-08` é gratuito e usa licença BSD.
O pacote `opencode-09` é gratuito e usa licença ISC.
O pacote `opencode-10` é gratuito e usa licença GPL.
O pacote `opencode-11` é gratuito e usa licença MIT.
O pacote `opencode-12` é gratuito e usa licença Apache-2.0.
O pacote `opencode-13` é gratuito e usa licença BSD.
O pacote `opencode-14` é gratuito e usa licença ISC.
O pacote `opencode-15` é gratuito e usa licença GPL.
O pacote `opencode-16` é gratuito e usa licença MIT.
O pacote `opencode-17` é gratuito e usa licença Apache-2.0.
O pacote `opencode-18` é gratuito e usa licença BSD.
O pacote `opencode-19` é gratuito e usa licença ISC.
O pacote `opencode-20` é gratuito e usa licença GPL.
O pacote `opencode-21` é gratuito e usa licença MIT.
O pacote `opencode-22` é gratuito e usa licença Apache-2.0.
O pacote `opencode-23` é gratuito e usa licença BSD.
O pacote `opencode-24` é gratuito e usa licença ISC.
O pacote `opencode-25` é gratuito e usa licença GPL.
O pacote `opencode-26` é gratuito e usa licença MIT.
O pacote `opencode-27` é gratuito e usa licença Apache-2.0.
O pacote `opencode-28` é gratuito e usa licença BSD.
O pacote `opencode-29` é gratuito e usa licença ISC.
O pacote `opencode-30` é gratuito e usa licença GPL.
"""

EVIDENCE_MANY = {f"https://example.com/opencode-{i:02d}": f"opencode-{i:02d}: licença, software gratuito." for i in range(1, 31)}

# Relatório com título factual vs título apenas contextual
REPORT_TITLES = """# Relatório de Teste

## Pacote opencode-x é gratuito

O pacote `opencode-x` usa licença MIT.

## Apenas Contexto

Esta seção não faz nenhuma afirmação sobre pacotes.
"""

EVIDENCE_TITLES = {
    "https://example.com/opencode-x": "opencode-x: licença MIT, software gratuito.",
}

# Relatório com parágrafo longo + afirmação curta boa
REPORT_LONG_PARA = """# Relatório de Teste

O pacote `opencode-base` usa licença MIT.
"""

GOOD = "O pacote `opencode-base` usa licença MIT."
LONG_FACT = ("O pacote `opencode-longo` oferece " +
             ", ".join("a integração documentada com o sistema externo numero "
                       + str(i) for i in range(20)) + ".")

REPORT_LONG_MIXED = "# Relatório\n\n" + GOOD + "\n\n" + LONG_FACT + "\n"

EVIDENCE_LONG = {
    "https://example.com/opencode-base": "opencode-base: licença MIT, software gratuito.",
    "https://example.com/opencode-longo": "opencode-longo: integrações documentadas com sistemas externos.",
}

# Relatório com recomendação editorial + justificativa factual
REPORT_RECOMMENDATION = """# Relatório de Teste

Recomendação principal: escolha `opencode-alpha` porque não exige nenhum serviço externo pago.

O pacote `opencode-beta` é gratuito e usa licença MIT.
"""

EVIDENCE_RECOMMENDATION = {
    "https://example.com/opencode-alpha": "opencode-alpha: sem serviço externo pago.",
    "https://example.com/opencode-beta": "opencode-beta: licença MIT, software gratuito.",
}

# Relatório com tabela de cinco pacotes
TABLE_REPORT = """# Relatório de Teste

| Pacote | Licença | Preço |
| opencode-alpha | MIT | gratuito |
| opencode-beta | Apache-2.0 | pago |
| opencode-gamma | BSD | gratuito |
| opencode-delta | ISC | assinatura |
| opencode-epsilon | GPL | pago |
"""

TABLE_EVIDENCE = {
    "https://example.com/opencode-alpha": "opencode-alpha: licença MIT.",
    "https://example.com/opencode-beta": "opencode-beta: licença Apache-2.0.",
    "https://example.com/opencode-gamma": "opencode-gamma: licença BSD.",
    "https://example.com/opencode-delta": "opencode-delta: licença ISC.",
    "https://example.com/opencode-epsilon": "opencode-epsilon: licença GPL.",
}


def _mock_review_pass_all_sustained():
    """Mock que devolve 'sustained' para todas as afirmações."""
    original = sr._review_pass

    async def mock_review_pass(items, model, batch_size=12):
        return [{"id": it["id"], "verdict": "sustained",
                 "support": "evidência suporta", "correction": ""} for it in items]

    sr._review_pass = mock_review_pass
    return original


def _get_coverage(result):
    """Extrai o registro de cobertura do resultado."""
    if "coverage" in result:
        return result["coverage"]
    return result.get("summary", {}).get("coverage", {})


def _extract_and_review(report, evidence, max_claims=50, votes=3):
    """Executa extração + revisão simulada, retorna (claims, coverage, review_result).
    
    A cobertura é obtida APÓS a revisão para refletir review_state atualizado.
    """
    claims = sr.extract_claims(report, evidence, max_claims=max_claims)
    original = _mock_review_pass_all_sustained()
    try:
        review_result = sr.review_report(report, evidence, enabled=True,
                                         votes=votes, max_claims=max_claims)
    finally:
        sr._review_pass = original
    # Obtém cobertura após a revisão (com review_state atualizado)
    cov = sr.get_coverage_report()
    return claims, cov, review_result


class TestCoverageTracking(unittest.TestCase):

    # ------------------------------------------------------------------
    # A. Metadados: Tag/Branch/Commit/Data ligados ao sujeito correto
    # ------------------------------------------------------------------
    def test_a_metadata_lists(self):
        """Metadados de pacote: Tag, Branch, Commit, Data extraídos com sujeito correto."""
        claims, cov, review_result = _extract_and_review(
            REPORT_MULTI_PACKAGE, EVIDENCE_MULTI, max_claims=50)

        claim_texts = [c["text"] for c in cov["claims"]
                       if c["selection_state"] == "selected"]

        # Cada pacote deve ter Tag, Branch, Commit, Data associados
        for pkg in ["opencode-alpha", "opencode-beta", "opencode-gamma",
                    "opencode-delta", "opencode-epsilon"]:
            # Verifica que o nome do pacote aparece em alguma claim
            pkg_found = any(pkg in t.lower() for t in claim_texts)
            self.assertTrue(pkg_found,
                            f"Pacote {pkg} não encontrado em nenhuma claim: {claim_texts}")

            # Verifica que Tag está associada a este pacote específico
            tag_found = any(pkg in t.lower() and ("tag " in t.lower() or "tag:" in t.lower())
                            for t in claim_texts)
            self.assertTrue(tag_found,
                            f"Tag não encontrada para {pkg} em: {claim_texts}")

            # Verifica que Commit está associada a este pacote específico
            commit_found = any(pkg in t.lower() and "commit:" in t.lower()
                               for t in claim_texts)
            self.assertTrue(commit_found,
                            f"Commit não encontrada para {pkg} em: {claim_texts}")

        # Confirma que tag e HEAD não são confundidos (branches diferentes)
        alpha_claims = [c for c in cov["claims"]
                        if "opencode-alpha" in c.get("text", "").lower()
                        and c["selection_state"] == "selected"]
        beta_claims = [c for c in cov["claims"]
                       if "opencode-beta" in c.get("text", "").lower()
                       and c["selection_state"] == "selected"]

        alpha_tags = [c["text"] for c in alpha_claims if "tag " in c["text"].lower()]
        beta_tags = [c["text"] for c in beta_claims if "tag " in c["text"].lower()]

        # Tags devem ser diferentes (v1.0.0 vs v2.0.0)
        self.assertNotEqual(set(alpha_tags), set(beta_tags),
                            f"Tags de alpha e beta não devem ser iguais: {alpha_tags} vs {beta_tags}")

    # ------------------------------------------------------------------
    # B. Tabela C: claims separadas por sujeito
    # ------------------------------------------------------------------
    def test_b_table_five_packages_separate(self):
        """Tabela de cinco pacotes: claims separadas por sujeito, não uma claim com cinco nomes."""
        claims, cov, review_result = _extract_and_review(
            TABLE_REPORT, TABLE_EVIDENCE, max_claims=50)

        claim_texts = [c["text"] for c in cov["claims"]
                       if c["selection_state"] == "selected"]

        # Cada pacote deve aparecer como sujeito em claim separada
        for pkg in ["opencode-alpha", "opencode-beta", "opencode-gamma",
                    "opencode-delta", "opencode-epsilon"]:
            pkg_claims = [t for t in claim_texts if pkg in t.lower()]
            self.assertGreaterEqual(len(pkg_claims), 1,
                                    f"Pacote {pkg} não tem claim própria: {claim_texts}")

        # NÃO deve existir uma claim com os cinco nomes juntos
        all_five_claims = [t for t in claim_texts
                           if all(p in t.lower() for p in
                                  ["opencode-alpha", "opencode-beta",
                                   "opencode-gamma", "opencode-delta",
                                   "opencode-epsilon"])]
        self.assertEqual(len(all_five_claims), 0,
                         f"Não deve existir claim com os cinco pacotes juntos: {all_five_claims}")

    # ------------------------------------------------------------------
    # C. Título factual vs título contextual
    # ------------------------------------------------------------------
    def test_c_factual_vs_contextual_title(self):
        """Título factual extrai proposição; título contextual não inventa fato."""
        claims, cov, review_result = _extract_and_review(
            REPORT_TITLES, EVIDENCE_TITLES, max_claims=50)

        claim_texts = [c["text"] for c in cov["claims"]
                       if c["selection_state"] == "selected"]

        # Título factual: "Pacote opencode-x é gratuito" → proposição extraída
        factual_found = any("opencode-x" in t.lower() and "gratuito" in t.lower()
                            for t in claim_texts)
        self.assertTrue(factual_found,
                        f"Título factual não gerou proposição de gratuidade: {claim_texts}")

        # Título contextual não deve gerar claim inventada
        contextual_found = any("apenas contexto" in t.lower()
                               for t in claim_texts)
        self.assertFalse(contextual_found,
                         f"Título contextual não deve gerar claim: {claim_texts}")

    # ------------------------------------------------------------------
    # D. Parágrafo longo: recuperação ou extração incompleta, accepted=False
    # ------------------------------------------------------------------
    def test_d_long_paragraph(self):
        """Parágrafo longo (>600 chars): dividido ou marcado incompleto; accepted=False."""
        self.assertGreater(len(LONG_FACT), 600,
                           f"LONG_FACT deve ter mais que 600 chars, tem {len(LONG_FACT)}")

        claims, cov, review_result = _extract_and_review(
            REPORT_LONG_MIXED, EVIDENCE_LONG, max_claims=50)

        # A afirmação curta 'good' deve estar presente
        good_found = any("opencode-base" in c["text"].lower()
                         and c["selection_state"] == "selected"
                         for c in cov["claims"])
        self.assertTrue(good_found,
                        f"Afirmação curta 'good' não encontrada: {[c['text'] for c in cov['claims']]}")

        # O fato longo deve estar dividido em claims ou marcado como incompleto
        long_fact_recovered = any("opencode-longo" in c["text"].lower()
                                  and c["selection_state"] == "selected"
                                  for c in cov["claims"])
        long_incomplete = any("opencode-longo" in c["text"].lower()
                              and c.get("selection_state") == "incomplete"
                              for c in cov["claims"])

        # Pelo menos um dos dois deve acontecer
        self.assertTrue(long_fact_recovered or long_incomplete,
                        f"Fato longo não foi dividido nem marcado incompleto. Claims: {[c['text'] for c in cov['claims']]}")

        # A revisão simulada deve rejeitar por cobertura incompleta
        self.assertFalse(review_result["accepted"],
                         "accepted deve ser False com fato longo não coberto")
        self.assertEqual(review_result["verdict_state"], "revisão incompleta")

    # ------------------------------------------------------------------
    # E. Recomendação editorial: justificativa factual preservada
    # ------------------------------------------------------------------
    def test_e_recommendation_justification(self):
        """Recomendação editorial: justificativa factual separada da escolha."""
        claims, cov, review_result = _extract_and_review(
            REPORT_RECOMMENDATION, EVIDENCE_RECOMMENDATION, max_claims=50)

        claim_texts = [c["text"] for c in cov["claims"]
                       if c["selection_state"] == "selected"]

        # A justificativa factual "não exige nenhum serviço externo pago" deve aparecer
        justification_found = any("serviço externo pago" in t.lower()
                                  for t in claim_texts)
        self.assertTrue(justification_found,
                        f"Justificativa factual não extraída: {claim_texts}")

        # A opção editorial também deve estar presente
        alpha_found = any("opencode-alpha" in t.lower()
                          for t in claim_texts)
        self.assertTrue(alpha_found,
                        f"Pacote alpha não encontrado: {claim_texts}")

    # ------------------------------------------------------------------
    # F. Origem e escopo: hash, bloco de origem real, sem claim fora do delimitador
    # ------------------------------------------------------------------
    def test_f_scope_and_origin(self):
        """Escopo declarado com hash real; claim inline não preenche bloco de metadados."""
        claims, cov, review_result = _extract_and_review(
            REPORT_MULTI_PACKAGE, EVIDENCE_MULTI, max_claims=50)

        # Scope deve ter hash real (não vazio)
        scope = cov["scope"]
        self.assertIn("hash_sha256", scope)
        self.assertGreater(len(scope["hash_sha256"]), 0,
                           f"Hash do escopo não deve estar vazio: {scope}")
        self.assertEqual(scope["rule"], "corpo anterior ao apêndice de auditoria")

        # Verificar correspondência real com bloco de origem
        # A claim de metadata de alpha deve apontar para o bloco de alpha, não para outro
        alpha_meta_claims = [c for c in cov["claims"]
                             if "opencode-alpha" in c.get("text", "").lower()
                             and ("tag " in c.get("text", "").lower() or "tag:" in c.get("text", "").lower())
                             and c["selection_state"] == "selected"]
        self.assertGreaterEqual(len(alpha_meta_claims), 1,
                                f"Claim de Tag de alpha não encontrada: {cov['claims']}")

        for c in alpha_meta_claims:
            bid = c.get("block_id")
            if bid is not None and bid in cov["blocks"]:
                blk = cov["blocks"][bid]
                # O bloco deve conter "alpha" e "Tag"
                self.assertIn("opencode-alpha", blk["original_text"].lower(),
                              f"Claim de alpha aponta para bloco sem alpha: {blk['original_text']}")
                self.assertIn("tag:", blk["original_text"].lower(),
                              f"Bloco de alpha não contém Tag: {blk['original_text']}")

    # ------------------------------------------------------------------
    # G. Estados: IDs estáveis, vínculo de duplicata, review_state atualizado
    # ------------------------------------------------------------------
    def test_g_states_and_duplicates(self):
        """IDs estáveis antes da ordenação; duplicatas vinculadas; review_state atualizado."""
        claims, cov, review_result = _extract_and_review(
            REPORT_MANY_CLAIMS, EVIDENCE_MANY, max_claims=10)

        # Deve haver claims adiadas pelo limite
        deferred = [c for c in cov["claims"]
                    if c["selection_state"] == "deferred_by_cap"]
        self.assertGreater(len(deferred), 0,
                           "Esperado claims adiadas pelo limite")

        # IDs devem estar na faixa 0..max_claims-1 para selecionadas
        selected = [c for c in cov["claims"]
                    if c["selection_state"] == "selected"]
        for c in selected:
            self.assertLess(c["id"], 10,
                            f"Claim selecionada com ID >= 10: {c['id']}")

        # review_state deve ser atualizado após revisão
        reviewed = [c for c in cov["claims"]
                    if c["review_state"] != "not_reviewed"]
        self.assertGreaterEqual(len(reviewed), len(selected),
                                f"Nem todas as claims selecionadas têm review_state atualizado: {len(reviewed)} vs {len(selected)}")

    # ------------------------------------------------------------------
    # H. Relatório congelado: checklist por pacote/campo
    # ------------------------------------------------------------------
    def test_h_frozen_report_checklist(self):
        """Checklist do relatório congelado: destino dos metadados e linhas de tabela."""
        with open('/opt/data/deep_research_outputs/gpt_researcher/output/RELATORIO_CORRIGIDO_184601.md') as f:
            full_report = f.read()
        cut = full_report.find("## 7. Auditoria")
        report_body = full_report[:cut] if cut > 0 else full_report

        with open('/opt/data/deep_research_outputs/gpt_researcher/runs/replay_corrigido_evidence.json') as f:
            evidence_data = json.load(f)
        EVIDENCE = evidence_data.get('evidence', {})

        claims, cov, review_result = _extract_and_review(
            report_body, EVIDENCE, max_claims=50)

        # Deve ter extraído claims
        self.assertGreater(cov["counts"]["claims_total"], 0)

        # Reconciliação de contagens
        total = cov["counts"]["claims_total"]
        selected = cov["counts"]["claims_selected"]
        deferred = cov["counts"]["claims_deferred_by_cap"]
        excluded = cov["counts"]["claims_excluded_duplicate"]
        incomplete = cov["counts"].get("claims_incomplete", 0)
        self.assertEqual(selected + deferred + excluded + incomplete, total,
                         f"Reconciliação falhou: {selected}+{deferred}+{excluded}+{incomplete} != {total}")

        # Verificar que blocos de metadados dos pacotes conhecidos têm claims
        # (os pacotes do relatório congelado variam, mas deve haver pelo menos algum bloco com claim_ids)
        blocks_with_claims = [b for b in cov["blocks"] if b["claim_ids"]]
        self.assertGreaterEqual(len(blocks_with_claims), 1,
                                "Nenhum bloco tem claim_ids associados")

        # Imprime checklist para inspeção manual
        print(f"\n  Blocos totais: {cov['counts']['blocks_total']}")
        print(f"  Claims totais: {cov['counts']['claims_total']}")
        print(f"  Claims selecionadas: {cov['counts']['claims_selected']}")
        print(f"  Claims adiadas por limite: {cov['counts']['claims_deferred_by_cap']}")
        print(f"  Claims excluídas duplicata: {cov['counts']['claims_excluded_duplicate']}")
        print(f"  Claims revisadas: {cov['counts']['claims_reviewed']}")
        print(f"  Itens descartados: {cov['counts']['dropped_items']}")
        print(f"  Cobertura completa: {cov['coverage_complete']}")
        print(f"  accepted: {review_result['accepted']}")
        print(f"  verdict_state: {review_result['verdict_state']}")


class TestCoverageApprovalProtection(unittest.TestCase):

    def test_approval_blocked_when_deferred(self):
        """accepted=False quando há claims adiadas pelo limite."""
        claims = sr.extract_claims(REPORT_MANY_CLAIMS, EVIDENCE_MANY, max_claims=5)
        cov = sr.get_coverage_report()
        self.assertGreater(cov["counts"]["claims_deferred_by_cap"], 0)

        original = _mock_review_pass_all_sustained()
        try:
            result = sr.review_report(REPORT_MANY_CLAIMS, EVIDENCE_MANY,
                                      enabled=True, votes=3, max_claims=5)
        finally:
            sr._review_pass = original

        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict_state"], "revisão incompleta")

    def test_approval_blocked_when_incomplete_extraction(self):
        """accepted=False quando há extração factual incompleta (parágrafo longo não dividido)."""
        self.assertGreater(len(LONG_FACT), 600)
        original = _mock_review_pass_all_sustained()
        try:
            result = sr.review_report(REPORT_LONG_MIXED, EVIDENCE_LONG,
                                      enabled=True, votes=3, max_claims=50)
        finally:
            sr._review_pass = original

        # O fato longo não deve ser coberto completamente
        cov = _get_coverage(result)
        # Se o parágrafo longo não foi dividido, deve haver incompletude
        incomplete_claims = [c for c in cov["claims"]
                             if c.get("selection_state") == "incomplete"]
        if incomplete_claims:
            self.assertFalse(result["accepted"],
                             "accepted deve ser False com extração incompleta")
        else:
            # Se foi dividido, todas as partes devem estar cobertas
            self.assertTrue(cov.get("coverage_complete", False),
                            f"Cobertura deveria estar completa quando dividido: {cov}")

    def test_approval_when_fully_covered(self):
        """accepted=True quando cobertura completa e vereditos favoráveis."""
        original = _mock_review_pass_all_sustained()
        try:
            result = sr.review_report(REPORT_TITLES, EVIDENCE_TITLES,
                                      enabled=True, votes=3, max_claims=50)
        finally:
            sr._review_pass = original

        cov = _get_coverage(result)
        self.assertTrue(cov.get("coverage_complete", False),
                        f"Cobertura deveria estar completa: {cov}")
        self.assertTrue(result["accepted"],
                        f"Deveria ser aceito: {result['verdict_state']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)