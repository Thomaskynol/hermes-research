#!/usr/bin/env python3
"""Verify the scope hash for absent, present and zero-position delimiters."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import semantic_review as sr

class ScopeBoundary(unittest.TestCase):
    def test_scope_hash_matches_exact_extracted_body(self):
        body = '# Relatorio\n\nO pacote `opencode-base` usa licença MIT.\n\n'
        appendix = '## 7. Auditoria\n\nO pacote `opencode-outside` usa licença GPL.\n'
        for report, expected in [(appendix, ''), (body + appendix, body), (body, body)]:
            with self.subTest(delimiter_position=report.find('## 7. Auditoria')):
                claims = sr.extract_claims(report, {}, max_claims=10000)
                scope = sr.get_coverage_report()['scope']
                self.assertEqual(scope['chars'], len(expected))
                self.assertEqual(scope['hash_sha256'], hashlib.sha256(expected.encode()).hexdigest())
                self.assertFalse(any('opencode-outside' in c['claim'] for c in claims))

if __name__ == '__main__':
    unittest.main(verbosity=2)
