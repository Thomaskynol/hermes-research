#!/usr/bin/env python3
"""Offline regression checks for information loss in structured claims.

These checks exercise the existing coverage/evidence/origin contract.
They do not make model or network calls.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import semantic_review as sr


def capture_review_input(report, corpus, max_claims=10000):
    """Capture the real items that would enter the auditor, without an LLM."""
    captured = []

    async def fake_review_pass(items, model, batch_size=12):
        captured.extend(items)
        return [{"id": item["id"], "verdict": "gap", "support": "",
                 "correction": "simulated review; no semantic approval"}
                for item in items]

    with patch.object(sr, "_review_pass", fake_review_pass):
        sr.review_report(report, corpus, votes=3, max_claims=max_claims)
    return captured


class StructuredCoverage(unittest.TestCase):
    def test_separate_tables_keep_their_headers_and_origins(self):
        report = ('# Teste\n\n## Licencas\n\n| Pacote | Licença |\n|---|---|\n'
                  '| opencode-alpha | MIT |\n\n## Precos\n\n| Pacote | Preço |\n'
                  '|---|---|\n| opencode-beta | R$ 99/mês |\n')
        claims = sr.extract_claims(report, {}, max_claims=10000)
        target = [c for c in claims if 'opencode-beta' in c['claim']]
        self.assertTrue(target)
        self.assertTrue(any('Preço' in c['claim'] and 'R$ 99/mês' in c['claim'] for c in target),
                        'Second table lost its header: %r' % [c['claim'] for c in target])
        self.assertFalse(any(c['claim'].startswith('Pacote:') for c in claims),
                         'A later header became a factual claim')
        cov = sr.get_coverage_report()
        blocks = {b['id']: b for b in cov['blocks']}
        ids = {c['id'] for c in target}
        for c in cov['claims']:
            if c['id'] in ids:
                self.assertIn('Precos', blocks[c['block_id']]['section'])

    def test_appendix_tables_are_not_extracted(self):
        report = ('# Teste\n\nO pacote `opencode-base` usa licença MIT.\n\n'
                  '## 7. Auditoria\n\n| Pacote | Licença |\n|---|---|\n'
                  '| opencode-outside | GPL |\n')
        claims = sr.extract_claims(report, {}, max_claims=10000)
        self.assertFalse(any('opencode-outside' in c['claim'] for c in claims),
                         'Tables bypassed the declared audit scope')

    def test_tag_and_branch_head_relationships_survive(self):
        tag_sha, head_sha = 'a' * 40, 'b' * 40
        report = ('#### `opencode-alpha`\n- **Commit (tag v1.2.3):** `' + tag_sha + '`\n'
                  '- **Branch `main` HEAD:** `' + head_sha + '`\n')
        claims = sr.extract_claims(report, {}, max_claims=10000)
        self.assertTrue(any(tag_sha in c['claim'] and 'v1.2.3' in c['claim'] for c in claims),
                        'Tag identity was removed from its commit relation')
        self.assertTrue(any(head_sha in c['claim'] and 'main' in c['claim']
                            and 'head' in c['claim'].lower() for c in claims),
                        'Branch identity or HEAD relation was removed')
        self.assertFalse(any(tag_sha in c['claim'] and head_sha in c['claim'] for c in claims))

    def test_repeated_metadata_line_keeps_its_own_block(self):
        report = ('#### `opencode-alpha`\n- **Branch:** `main`\n\n'
                  '#### `opencode-beta`\n- **Branch:** `main`\n')
        sr.extract_claims(report, {}, max_claims=10000)
        cov = sr.get_coverage_report()
        blocks = {b['id']: b for b in cov['blocks']}
        targets = [c for c in cov['claims'] if 'opencode-beta' in c['text']
                   and 'main' in c['text']]
        self.assertTrue(targets)
        for c in targets:
            self.assertIsNotNone(c['block_id'])
            self.assertIn('opencode-beta', blocks[c['block_id']]['section'],
                          'Matching identical line text reused the earlier package block')

    def test_metadata_receives_available_current_evidence(self):
        url = 'https://example.com/opencode-alpha/versions'
        report = '#### `opencode-alpha`\n- **Tag:** v1.2.3\n'
        claims = sr.extract_claims(report, {url: 'opencode-alpha v1.2.3 PROVA_VERSAO'}, max_claims=10000)
        targets = [c for c in claims if 'opencode-alpha' in c['claim'] and 'v1.2.3' in c['claim']]
        self.assertTrue(targets)
        self.assertTrue(any(url in c['anchors'] and 'PROVA_VERSAO' in c['evidence'] for c in targets),
                        'Metadata bypassed the evidence selector')

    def test_table_explicit_source_beats_first_name_match(self):
        url = 'https://example.com/pricing'
        report = ('| Pacote | Preço |\n|---|---|\n'
                  '| opencode-alpha | 200 req free em ' + url + ' |\n')
        evidence = {'https://example.com/readme': 'opencode-alpha: texto geral sem preço.',
                    url: 'opencode-alpha: 200 req free. PROVA_PRECO.'}
        claims = sr.extract_claims(report, evidence, max_claims=10000)
        targets = [c for c in claims if url in c['claim'] and '200 req' in c['claim']]
        self.assertTrue(targets)
        for c in targets:
            self.assertIn(url, c['anchors'][:2], 'Structured claim ignored its explicit source')
            self.assertIn('PROVA_PRECO', c['evidence'])

    def test_title_anchors_are_corpus_urls(self):
        url = 'https://example.com/opencode-alpha'
        evidence = {url: 'opencode-alpha é gratuito. PROVA_ATUAL'}
        claims = sr.extract_claims('## Pacote opencode-alpha é gratuito\n', evidence)
        self.assertTrue(claims)
        target = next(c for c in claims if 'gratuito' in c['claim'])
        self.assertIn(url, target['anchors'], 'Package name is not a source URL')
        self.assertTrue(set(target['anchors']).issubset(evidence))
        self.assertIn('PROVA_ATUAL', target['evidence'])

    def test_different_facts_with_same_prefix_are_not_duplicates(self):
        prefix = 'O pacote `opencode-alpha` documenta suporte para integracao com sistemas externos e usa licença '
        a, b = prefix + 'MIT.', prefix + 'GPL.'
        self.assertEqual(a[:60], b[:60])
        sr.extract_claims('# Teste\n\n' + a + '\n\n' + b + '\n', {}, max_claims=10000)
        cov = sr.get_coverage_report()
        for text in (a, b):
            matches = [c for c in cov['claims'] if c['text'] == text]
            self.assertTrue(matches)
            self.assertTrue(any(c['selection_state'] == 'selected' for c in matches),
                            'Different proposition was excluded as duplicate: ' + text)

    def test_exact_duplicate_is_not_sent_for_review_twice(self):
        fact = 'O pacote `opencode-alpha` usa licença MIT.'
        claims = sr.extract_claims('# Teste\n\n' + fact + '\n\n' + fact + '\n', {}, max_claims=10000)
        self.assertEqual(sum(c['claim'] == fact for c in claims), 1,
                         'Excluded duplicate remained in the returned review items')
        cov = sr.get_coverage_report()
        dup = [c for c in cov['claims'] if c['selection_state'] == 'excluded_duplicate']
        self.assertTrue(dup)
        originals = {c['id'] for c in cov['claims'] if c['selection_state'] == 'selected'}
        self.assertTrue(all(c['duplicate_of'] in originals for c in dup))

    # ------------------------------------------------------------------
    # QUALIFICAÇÃO DE EVIDÊNCIA — distingir conteúdo utilizável de falhas
    # ------------------------------------------------------------------
    def test_payload_erro_sozinho_nao_vira_evidencia(self):
        """Payload composto apenas por erro não chega como conteúdo probatório."""
        url = 'https://example.com/error'
        text = '404: Not Found'
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n',
            {url: text})
        for item in items:
            self.assertNotIn(text, item["evidence"],
                             "Excluded error payload entered the auditor")
            self.assertNotIn(url, item.get("anchors", []),
                             "Excluded URL should not be an anchor")

    def test_documento_com_codigos_http_permanece_utilizavel(self):
        """Documento legítimo mencionando códigos HTTP permanece utilizável."""
        url = 'https://example.com/docs/opencode-alpha'
        text = ('API documentation v2.0\n'
                'Status codes: 404 means not found, 429 means rate limited.\n'
                'opencode-alpha is free and open-source (MIT license).')
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n',
            {url: text})
        self.assertTrue(items, "Documento com códigos HTTP deve gerar items")
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("MIT", combined, "Conteúdo factual deve estar na evidência")
        for item in items:
            self.assertIn(url, item.get("anchors", []),
                          "URL deve estar nos anchors como procedência")

    def test_readme_util_com_erro_preserva_parte_valida(self):
        """README útil acompanhado de erro: preserva a parte válida."""
        url = 'https://github.com/user/opencode-alpha'
        text = ('# opencode-alpha\n\n'
                'License: MIT.\n\n'
                'opencode-alpha does amazing things.\n\n'
                'Note: some legacy endpoint returns 404: Not Found, ignore it.\n')
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n',
            {url: text})
        self.assertTrue(items, "README útil deve gerar items")
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("MIT", combined,
                      "Licença deve ser preservada na evidência")
        self.assertIn("amazing things", combined,
                      "Justificativa factual deve ser preservada")
        self.assertNotRegex(combined, r"(?m)^\s*404: Not Found\s*$",
                            "Linha isolada de erro não deve ser evidência")

    def test_html_cru_sem_conteudo_nao_eh_prova_de_preco(self):
        """HTML de cabeçalho/estilos sem conteúdo pertinente não é prova de pricing."""
        html = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
                '<title>Pricing</title><link rel="stylesheet" href="/style.css"/>'
                '<script src="/app.js"></script></head><body></body></html>')
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` custa $99.\n',
            {'https://example.com/pricing': html})
        for item in items:
            self.assertNotIn('https://example.com/pricing', item.get("anchors", []),
                             "HTML sem conteúdo útil não deve ser anchor")

    def test_fragmento_util_conserva_fato_presente(self):
        """Fragmento útil conserva o fato efetivamente presente."""
        text = 'Partial content: opencode-alpha uses MIT license. [truncated]'
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n',
            {'https://example.com/partial': text})
        self.assertTrue(items, "Fragmento útil deve gerar items")
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("MIT", combined, "Fato presente deve estar na evidência")
        self.assertIn("Partial content", combined, "Fragmento deve ser preservado")

    def test_descricao_e_transcricao_tipos_preservados(self):
        """Descrição e transcrição: tipos preservados."""
        spoken = 'https://www.youtube.com/watch?v=abc123'
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` é gratuito.\n',
            {spoken: '[description] opencode-alpha é gratuito na descrição.'})
        self.assertTrue(items)
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("[description]", combined)
        self.assertNotIn("[spoken", combined)

        items2 = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` é gratuito.\n',
            {spoken: '[spoken 5/11] opencode-alpha é gratuito neste trecho.'})
        self.assertTrue(items2)
        combined2 = "\n".join(item["evidence"] for item in items2)
        self.assertIn("[spoken", combined2)

    def test_controle_positivo_conteudo_limpo(self):
        """Controle positivo com conteúdo factual limpo e procedência correta."""
        url = 'https://example.com/docs/opencode-alpha'
        text = 'opencode-alpha is a free, open-source code assistant. License: MIT.'
        items = capture_review_input(
            '# Relatório\n\nO pacote `opencode-alpha` usa licença MIT.\n',
            {url: text})
        self.assertTrue(items, "Conteúdo limpo deve gerar items")
        combined = "\n".join(item["evidence"] for item in items)
        self.assertIn("MIT", combined, "Evidência deve conter o texto do MIT")
        for item in items:
            self.assertIn(url, item.get("anchors", []),
                          "Procedência deve estar nos anchors")


if __name__ == '__main__':
    unittest.main(verbosity=2)
