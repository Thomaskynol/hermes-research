#!/usr/bin/env python3
"""Independent offline checks for the existing coverage contract.

Run in the Hermes repository after placing this file under scripts/.
Only _review_pass is simulated; extraction, evidence selection, registry,
voting and report integration are real. No network calls are needed.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import semantic_review as sr

REPORT_PATH = Path(os.environ.get(
    'COVERAGE_REVIEW_REPORT',
    '/opt/data/deep_research_outputs/gpt_researcher/output/RELATORIO_CORRIGIDO_184601.md'))

GOOD = 'O pacote `opencode-base` usa licença MIT.'
LONG_FACT = 'O pacote `opencode-longo` oferece ' + ', '.join(
    'a integração documentada com o sistema externo numero ' + str(i)
    for i in range(20)) + '.'
URL = 'https://example.com/opencode-alpha'

async def favorable(items, model, batch_size=12):
    return [{'id': c['id'], 'verdict': 'sustained',
             'support': 'OFFLINE SIMULATION', 'correction': ''} for c in items]

def review(report, evidence=None, max_claims=10000):
    with patch.object(sr, '_review_pass', favorable):
        return sr.review_report(report, evidence or {}, votes=3,
                                enabled=True, max_claims=max_claims)

class CoverageContract(unittest.TestCase):
    def test_positive_control_small_complete_review(self):
        result = review('# Relatorio\n\n' + GOOD + '\n',
                        {'https://example.com/opencode-base': GOOD})
        self.assertTrue(result['accepted'])
        self.assertTrue(result['coverage']['coverage_complete'])
        self.assertEqual(len(result['verdicts']), 1)
        self.assertEqual(result['verdicts'][0]['valid_count'], 3)

    def test_markdown_metadata_are_extracted_with_subject(self):
        """Actual Markdown list syntax must preserve every known field."""
        tag_sha, head_sha = 'a' * 40, 'b' * 40
        report = ('# Relatorio\n\n' + GOOD + '\n\n#### `opencode-alpha`\n'
                  '- **Tag:** v1.2.3\n- **Branch:** `main`\n'
                  '- **Commit (tag v1.2.3):** `' + tag_sha + '`\n'
                  '- **Branch `main` HEAD:** `' + head_sha + '`\n'
                  '- **Data:** 2026-10-16\n')
        result = review(report, {URL: report})
        texts = [c['claim'] for c in result['verdicts']
                 if 'opencode-alpha' in c['claim']]
        missing = [value for value in ['v1.2.3', 'main', tag_sha, head_sha, '2026-10-16']
                   if not any(value in text for text in texts)]
        self.assertEqual(missing, [],
                         'Metadata lost; accepted=%s coverage_complete=%s missing=%r'
                         % (result['accepted'], result['coverage']['coverage_complete'], missing))
        self.assertFalse(any(tag_sha in text and head_sha in text for text in texts),
                         'Tag commit and branch HEAD need distinct relations')

    def test_frozen_report_commit_checklist(self):
        """All five original metadata blocks must produce their commit facts."""
        report = REPORT_PATH.read_text().split('## 7. Auditoria', 1)[0]
        expected = {
            'oh-my-opencode': '7a752ab5a88c2d255b926aff1c687b6d91758d02',
            'opencode-goal-plugin': '7f0b15fc8dd7792eafa84dcc001174d32284e520',
            'opencode-morph-plugin': 'cc06c49572c75a8bd0823450495fd7266ffaea81',
            'opencode-morph-fast-apply': '7f347df7d17f13f1f24083de9ae4b9b2d173d1fb',
            'opencode-tavily': '61e70c3bc0354fc0616c1826d73e18a3515afc43',
        }
        for sha in expected.values():
            self.assertIn(sha, report, 'Wrong frozen fixture')
        sr.extract_claims(report, {}, max_claims=10000)
        cov = sr.get_coverage_report()
        blocks = {b['id']: b for b in cov['blocks']}
        missing = [pkg for pkg, sha in expected.items()
                   if not any(pkg in c['text'] and sha in c['text']
                              and pkg in blocks.get(c.get('block_id'), {}).get('section', '')
                              and sha in blocks.get(c.get('block_id'), {}).get('original_text', '')
                              for c in cov['claims'])]
        self.assertEqual(missing, [], 'Missing commit facts from original blocks: ' + str(missing))

    def test_package_columns_preserve_each_fact(self):
        """The real report also has subjects in columns, not just in rows."""
        report = ('| Aspecto | `opencode-alpha` | `opencode-beta` |\n'
                  '|---|---|---|\n| Licenca | MIT | GPL |\n'
                  '| Servico pago obrigatorio | nenhum | sim |\n')
        sr.extract_claims(report, {}, max_claims=10000)
        cov = sr.get_coverage_report()
        missing = [(pkg, value) for pkg, value in
                   [('opencode-alpha', 'MIT'), ('opencode-beta', 'GPL')]
                   if not any(pkg in c['text'] and value in c['text']
                              for c in cov['claims'])]
        self.assertEqual(missing, [], 'Column facts lost; coverage_complete=%s missing=%r'
                         % (cov['coverage_complete'], missing))

    def test_table_evidence_is_from_current_corpus(self):
        """A second extraction must never reuse the previous snapshot."""
        sr.extract_claims('O pacote `opencode-alpha` usa licenca MIT.',
                          {URL: 'opencode-alpha SNAPSHOT_ANTERIOR'})
        table = '| Pacote | Licenca |\n|---|---|\n| opencode-alpha | MIT |\n'
        claims = sr.extract_claims(table, {URL: 'opencode-alpha SNAPSHOT_ATUAL licenca MIT.'})
        self.assertTrue(claims, 'Table must produce a claim')
        target = next(c for c in claims if 'opencode-alpha' in c['claim'])
        self.assertIn('SNAPSHOT_ATUAL', target['evidence'],
                      'Evidence was not selected from the current corpus')
        self.assertNotIn('SNAPSHOT_ANTERIOR', target['evidence'])

    def test_factual_title_receives_available_evidence(self):
        """A new extraction path must use the validated evidence selection."""
        # Use the supported Portuguese title pattern; do not accept an empty extraction.
        claims = sr.extract_claims('## Pacote opencode-alpha é gratuito\n',
                                  {URL: 'opencode-alpha PROVA_ATUAL titulo gratuito.'})
        self.assertTrue(claims)
        target = next(c for c in claims if 'gratuito' in c['claim'])
        self.assertIn('PROVA_ATUAL', target['evidence'])

    def test_audit_appendix_is_outside_extraction_scope(self):
        body = '# Relatorio\n\n' + GOOD + '\n\n'
        report = body + '## 7. Auditoria\n\nO pacote `opencode-outside` exige servico pago.\n'
        claims = sr.extract_claims(report, {}, max_claims=10000)
        cov = sr.get_coverage_report()
        self.assertEqual(cov['scope']['hash_sha256'], hashlib.sha256(body.encode()).hexdigest())
        self.assertFalse(any('opencode-outside' in c['claim'] for c in claims),
                         'Claim after declared scope was extracted')

    def test_cap_registry_matches_actual_priority_selection(self):
        report = ('# Relatorio\n\nO pacote `opencode-low` usa licenca MIT.\n\n'
                  'O pacote `opencode-high` é gratuito e usa licenca MIT.\n')
        claims = sr.extract_claims(report, {}, max_claims=1)
        cov = sr.get_coverage_report()
        returned = {c['id'] for c in claims}
        recorded = {c['id'] for c in cov['claims'] if c['selection_state'] == 'selected'}
        self.assertEqual(returned, recorded,
                         'Registry used id < cap instead of actual priority selection')
        self.assertIn('opencode-high', claims[0]['claim'])

    def test_incomplete_extraction_means_incomplete_coverage(self):
        self.assertGreater(len(LONG_FACT), 600)
        result = review('# Relatorio\n\n' + GOOD + '\n\n' + LONG_FACT + '\n')
        cov = result['coverage']
        if any(c['selection_state'] == 'incomplete' for c in cov['claims']):
            self.assertFalse(cov['coverage_complete'],
                             'Incomplete claim was recorded as complete coverage')
            self.assertFalse(result['accepted'])
        else:
            # Dividing successfully is allowed, but all twenty clauses must survive.
            text = '\n'.join(c['text'] for c in cov['claims'])
            for i in range(20):
                self.assertIn('numero ' + str(i), text)

    def test_duplicate_points_to_original(self):
        fact = 'O pacote `opencode-alpha` usa licenca MIT.'
        sr.extract_claims('# Relatorio\n\n' + fact + '\n\n' + fact + '\n', {})
        cov = sr.get_coverage_report()
        duplicates = [c for c in cov['claims'] if c['selection_state'] == 'excluded_duplicate']
        self.assertTrue(duplicates, 'Duplicate must have a traceable original')
        ids = {c['id'] for c in cov['claims']}
        for c in duplicates:
            self.assertIn(c['duplicate_of'], ids)
            self.assertNotEqual(c['duplicate_of'], c['id'])

    def test_returned_review_counts_are_updated(self):
        result = review('# Relatorio\n\n' + GOOD + '\n')
        self.assertTrue(result['accepted'], 'Positive control with favorable judgments')
        completed = [v for v in result['verdicts'] if v['verdict'] == 'sustained']
        self.assertEqual(result['coverage']['counts']['claims_reviewed'], len(completed),
                         'Returned counts describe the extraction before review')

if __name__ == '__main__':
    unittest.main(verbosity=2)
