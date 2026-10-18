#!/usr/bin/env python3
"""Testes de proteção contra aprovação indevida em falhas técnicas do auditor semântico.

Cada teste isola uma única alteração, extrai a afirmação alvo, confere seu
julgamento e verifica o efeito esperado sobre a aceitação.
"""

import sys
sys.path.insert(0, '/opt/data/deep_research_outputs/gpt_researcher')

import semantic_review as sr

# Relatório de teste simples com uma única afirmação factual
TEST_REPORT = """# Relatório de Teste

O pacote `opencode-example` é gratuito e usa licença MIT.
"""

# Evidência que suporta a afirmação
TEST_EVIDENCE = {
    "https://example.com/opencode-example": "opencode-example: licença MIT, software gratuito.",
}

# Mock para simular _review_pass retornando exatamente a passagem correspondente
def _mock_review_pass(passages):
    """Cria um mock de _review_pass que retorna exatamente a passagem correspondente (pop)."""
    original_review_pass = sr._review_pass
    passages_list = list(passages)  # copia para consumir com pop(0)
    
    async def mock_review_pass(items, model, batch_size=12):
        if passages_list:
            return passages_list.pop(0)
        return []
    
    sr._review_pass = mock_review_pass
    return original_review_pass

def run_test(name, passages, expected_verdict, expected_accepted, expected_valid_count, expected_failure_count, description=""):
    """Executa um teste isolado com mock de _review_pass."""
    print(f"\n{'='*70}")
    print(f"TESTE: {name}")
    if description:
        print(f"  {description}")
    print(f"{'='*70}")
    
    original = _mock_review_pass(passages)
    
    try:
        result = sr.review_report(TEST_REPORT, TEST_EVIDENCE, enabled=True, votes=3)
    finally:
        sr._review_pass = original
    
    print(f"Claims extraídas: {result['claims']}")
    print(f"Estado: {result['verdict_state']}")
    print(f"Accepted: {result['accepted']}")
    print(f"Resumo: {result['summary']}")
    
    # Verifica a afirmação alvo
    target_claims = [v for v in result['verdicts'] if 'opencode-example' in v.get('claim', '').lower()]
    
    if not target_claims:
        print(f"  ❌ FALHA: Claim alvo 'opencode-example' NÃO foi extraída")
        return False
    
    all_pass = True
    for v in target_claims:
        print(f"  -> Claim ID {v['id']}: {v['claim'][:80]}")
        print(f"     Veredito final: {v['verdict']}")
        print(f"     Votos válidos: {v.get('valid_count', 'N/A')}")
        print(f"     Falhas: {v.get('failure_count', 'N/A')}")
        print(f"     Tally: {v.get('vote_tally', {})}")
        
        # Verifica veredito
        if v['verdict'] != expected_verdict:
            print(f"  ❌ FALHA: Esperado veredito '{expected_verdict}', obteve '{v['verdict']}'")
            all_pass = False
        else:
            print(f"  ✅ Veredito correto: {expected_verdict}")
        
        # Verifica contagem de votos válidos
        if v.get('valid_count') != expected_valid_count:
            print(f"  ❌ FALHA: Esperado valid_count={expected_valid_count}, obteve {v.get('valid_count')}")
            all_pass = False
        else:
            print(f"  ✅ valid_count correto: {expected_valid_count}")
        
        # Verifica contagem de falhas
        if v.get('failure_count') != expected_failure_count:
            print(f"  ❌ FALHA: Esperado failure_count={expected_failure_count}, obteve {v.get('failure_count')}")
            all_pass = False
        else:
            print(f"  ✅ failure_count correto: {expected_failure_count}")
    
    # Verifica estado do relatório
    if result['accepted'] != expected_accepted:
        print(f"  ❌ FALHA: Esperado accepted={expected_accepted}, obteve {result['accepted']}")
        all_pass = False
    else:
        print(f"  ✅ accepted correto: {expected_accepted}")
    
    if all_pass:
        print(f"  ✅ PASS")
    
    return all_pass

def main():
    all_passed = True
    
    # TESTE 1: failure, failure, failure → revisão incompleta; accepted=False
    all_passed &= run_test(
        name="Três falhas técnicas (failure, failure, failure)",
        passages=[
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 1"}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 2"}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 3"}],
        ],
        expected_verdict="review_incomplete",
        expected_accepted=False,
        expected_valid_count=0,
        expected_failure_count=3,
        description="0 julgamentos válidos → sem quórum → revisão incompleta"
    )
    
    # TESTE 2: sustained, failure, failure → revisão incompleta; accepted=False
    all_passed &= run_test(
        name="Um válido, duas falhas (sustained, failure, failure)",
        passages=[
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 1"}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 2"}],
        ],
        expected_verdict="review_incomplete",
        expected_accepted=False,
        expected_valid_count=1,
        expected_failure_count=2,
        description="1 julgamento válido < 2 → sem quórum → revisão incompleta"
    )
    
    # TESTE 3: sustained, unsupported, failure → disputed_tie registrado; revisão incompleta; accepted=False
    all_passed &= run_test(
        name="Dois válidos divergentes + falha (sustained, unsupported, failure)",
        passages=[
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "unsupported", "support": "evidência contradiz", "correction": "não suportado"}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha"}],
        ],
        expected_verdict="disputed_tie",
        expected_accepted=False,
        expected_valid_count=2,
        expected_failure_count=1,
        description="2 julgamentos válidos mas empate (1-1) → disputed_tie → não aprova"
    )
    
    # TESTE 4: sustained, sustained, failure → sustained; accepted=True; uma falha registrada
    all_passed &= run_test(
        name="Consenso válido + falha (sustained, sustained, failure)",
        passages=[
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha"}],
        ],
        expected_verdict="sustained",
        expected_accepted=True,
        expected_valid_count=2,
        expected_failure_count=1,
        description="2 julgamentos válidos concordam (2-0) → consenso → sustained; falha registrada mas não bloqueia"
    )
    
    # TESTE 5: unsupported, unsupported, sustained → reprovado; accepted=False
    all_passed &= run_test(
        name="Consenso unsupported (unsupported, unsupported, sustained)",
        passages=[
            [{"id": 0, "verdict": "unsupported", "support": "evidência contradiz", "correction": "não suportado"}],
            [{"id": 0, "verdict": "unsupported", "support": "evidência contradiz", "correction": "não suportado"}],
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
        ],
        expected_verdict="unsupported",
        expected_accepted=False,
        expected_valid_count=3,
        expected_failure_count=0,
        description="2 unsupported vs 1 sustained → maioria unsupported → reprovado"
    )
    
    # TESTE 6: sustained, sustained, sustained → aceito; accepted=True
    all_passed &= run_test(
        name="Consenso unânime sustained (sustained, sustained, sustained)",
        passages=[
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
            [{"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""}],
        ],
        expected_verdict="sustained",
        expected_accepted=True,
        expected_valid_count=3,
        expected_failure_count=0,
        description="3 sustained → consenso unânime → aceito"
    )
    
    # TESTE 7: Passagens vazias [], [], [] → revisão incompleta; accepted=False
    all_passed &= run_test(
        name="Três passagens vazias ([], [], [])",
        passages=[
            [],
            [],
            [],
        ],
        expected_verdict="review_incomplete",
        expected_accepted=False,
        expected_valid_count=0,
        expected_failure_count=3,
        description="0 julgamentos válidos (3 missing_result) → sem quórum → revisão incompleta"
    )
    
    # TESTE 8: Primeira passagem: duas entradas sustained com mesmo ID. Segunda e terceira: review_failure.
    # Esperado: duplicata invalida os votos → 0 válidos, 3 falhas → revisão incompleta
    all_passed &= run_test(
        name="Duplicata na primeira passagem + falhas nas outras",
        passages=[
            [
                {"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""},
                {"id": 0, "verdict": "sustained", "support": "evidência ok", "correction": ""},
            ],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 1"}],
            [{"id": 0, "verdict": "review_failure", "support": "", "correction": "falha 2"}],
        ],
        expected_verdict="review_incomplete",
        expected_accepted=False,
        expected_valid_count=0,
        expected_failure_count=3,
        description="Duplicata invalida votos da primeira passagem (2 invalid_json); outras 2 falham → 0 válidos, 3 falhas"
    )
    
    print(f"\n{'='*70}")
    if all_passed:
        print("TODOS OS 8 TESTES DE PROTEÇÃO PASSARAM")
    else:
        print("ALGUNS TESTES FALHARAM")
    print(f"{'='*70}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())