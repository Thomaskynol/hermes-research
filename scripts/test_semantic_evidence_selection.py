#!/usr/bin/env python3
"""Testes de seleção de evidência para claims Morph e Daytona.

Verifica se as fontes pertinentes chegam ao auditor quando o relatório cita
explicitamente URLs que existem no corpus congelado.
"""

import sys
sys.path.insert(0, '/opt/data/deep_research_outputs/gpt_researcher')

import semantic_review as sr
import json

# Load the real report body (before audit appendix)
with open('/opt/data/deep_research_outputs/gpt_researcher/output/RELATORIO_CORRIGIDO_184601.md') as f:
    full_report = f.read()
cut = full_report.find("## 7. Auditoria")
REPORT_BODY = full_report[:cut] if cut > 0 else full_report

# Load the frozen evidence corpus
with open('/opt/data/deep_research_outputs/gpt_researcher/runs/replay_corrigido_evidence.json') as f:
    evidence_data = json.load(f)

EVIDENCE = evidence_data.get('evidence', {})

def extract_claims_and_check_anchors(report_text, evidence_dict, target_substrings):
    """Extract claims and check if target substrings have correct anchors."""
    claims = sr.extract_claims(report_text, evidence_dict, max_claims=50)
    results = {}
    for claim in claims:
        claim_text = claim['claim']
        anchors = claim['anchors']
        evidence_text = claim['evidence']  # full evidence, not preview
        for target in target_substrings:
            if target.lower() in claim_text.lower():
                results[target] = {
                    'claim_id': claim['id'],
                    'claim_text': claim_text[:200],
                    'anchors': anchors,
                    'evidence_full': evidence_text,  # full evidence
                    'evidence_preview': evidence_text[:500] if evidence_text else '(sem evidência)',  # for display
                    'packages': claim['packages'],
                }
    return results

def check_morph_pricing_claim():
    """Test 1: Morph pricing claim cites morphllm.com/pricing explicitly."""
    print("\n" + "="*70)
    print("TESTE 1: Morph pricing - URL explícita deve ser promovida")
    print("="*70)
   
    targets = ["morphllm.com/pricing", "200 req free every month"]
    results = extract_claims_and_check_anchors(REPORT_BODY, EVIDENCE, targets)
   
    if not results:
        print("  ❌ FALHA: Nenhuma afirmação alvo foi extraída")
        return False
   
    all_pass = True
    for target, data in results.items():
        print(f"\n  Alvo: '{target}'")
        print(f"  Claim ID: {data['claim_id']}")
        print(f"  Claim: {data['claim_text'][:150]}...")
        print(f"  Packages: {data['packages']}")
        print(f"  Anchors (top 3): {data['anchors']}")
        print(f"  Evidence preview: {data['evidence_preview'][:200]}...")
       
        # Check if morphllm.com/pricing is in top anchors
        anchors = data['anchors']
        morph_url = "https://www.morphllm.com/pricing"
        if morph_url in anchors[:2]:
            print(f"  ✅ PASS: {morph_url} está nos top 2 anchors")
        else:
            print(f"  ❌ FALHA: {morph_url} NÃO está nos top 2 anchors (anchors: {anchors})")
            all_pass = False
       
        # Check if evidence contains "200 req" - use full evidence field
        if "200 req" in data['evidence_full']:
            print(f"  ✅ PASS: Evidence contém '200 req'")
        else:
            print(f"  ❌ FALHA: Evidence NÃO contém '200 req'")
            all_pass = False
   
    return all_pass

def check_morph_pricing_absent():
    """Test 2: Morph pricing page removed - should be gap, not fabricated."""
    print("\n" + "="*70)
    print("TESTE 2: Morph pricing AUSENTE - deve dar gap, não fabricar")
    print("="*70)
   
    # Create evidence without morphllm.com/pricing
    evidence_no_morph = {k: v for k, v in EVIDENCE.items() if "morphllm.com/pricing" not in k}
    print(f"  Evidências sem morphllm.com/pricing: {len(evidence_no_morph)} fontes")
   
    targets = ["200 req free every month"]
    results = extract_claims_and_check_anchors(REPORT_BODY, evidence_no_morph, targets)
   
    if not results:
        print("  ❌ FALHA: Afirmação alvo não foi extraída")
        return False
   
    all_pass = True
    for target, data in results.items():
        print(f"\n  Alvo: '{target}'")
        print(f"  Claim ID: {data['claim_id']}")
        print(f"  Anchors: {data['anchors']}")
        print(f"  Evidence preview: {data['evidence_preview'][:200]}...")
       
        # The claim should still be extracted but have no morphllm.com/pricing anchor
        # It should get gap or partial, not sustained
        if "200 req free every month" in data['evidence_full'] and "morphllm.com/pricing" not in str(data['anchors']):
            print(f"  ⚠️  WARNING: Evidence menciona '200 req' mas sem anchor da pricing page")

        # Check that the evidence doesn't contain fabricated pricing content
        if "Open Source Models" in data['evidence_full'] and "morphllm.com/pricing" not in str(data['anchors']):
            print(f"  ❌ FALHA: Evidence parece conter conteúdo da pricing page sem a URL")
            all_pass = False
        else:
            print(f"  ✅ PASS: Sem fabricação de conteúdo da pricing page")
   
    return all_pass

def check_daytona_claim():
    """Test 3: Daytona claim should receive the opencode-plugin README."""
    print("\n" + "="*70)
    print("TESTE 3: Daytona - deve receber README do opencode-plugin")
    print("="*70)
   
    targets = ["opencode-daytona", "isolamento em sandbox"]
    results = extract_claims_and_check_anchors(REPORT_BODY, EVIDENCE, targets)
   
    if not results:
        print("  ❌ FALHA: Nenhuma afirmação alvo foi extraída")
        return False
   
    all_pass = True
    for target, data in results.items():
        print(f"\n  Alvo: '{target}'")
        print(f"  Claim ID: {data['claim_id']}")
        print(f"  Claim: {data['claim_text'][:150]}...")
        print(f"  Packages: {data['packages']}")
        print(f"  Anchors (top 3): {data['anchors']}")
        print(f"  Evidence preview: {data['evidence_preview'][:300]}...")
       
        # Check if the Daytona opencode-plugin README is in top anchors
        daytona_readme = "https://github.com/daytona/integrations/tree/main/packages/opencode-plugin"
        anchors = data['anchors']
        if daytona_readme in anchors[:2]:
            print(f"  ✅ PASS: README do opencode-plugin está nos top 2 anchors")
        else:
            print(f"  ❌ FALHA: README do opencode-plugin NÃO está nos top 2 anchors")
            all_pass = False
       
        # Check if evidence contains sandbox/isolation content - use full evidence
        if "sandbox" in data['evidence_full'].lower() or "isolamento" in data['evidence_full'].lower():
            print(f"  ✅ PASS: Evidence contém conteúdo sobre sandbox/isolamento")
        else:
            print(f"  ❌ FALHA: Evidence NÃO contém conteúdo sobre sandbox/isolamento")
            all_pass = False
   
    return all_pass

def check_daytona_with_distractor():
    """Test 4: Daytona with video distractor - README should win over irrelevant video."""
    print("\n" + "="*70)
    print("TESTE 4: Daytona com vídeo distrator - README deve vencer")
    print("="*70)
   
    targets = ["opencode-daytona", "isolamento em sandbox"]
    results = extract_claims_and_check_anchors(REPORT_BODY, EVIDENCE, targets)
   
    if not results:
        print("  ❌ FALHA: Nenhuma afirmação alvo foi extraída")
        return False
   
    all_pass = True
    for target, data in results.items():
        print(f"\n  Alvo: '{target}'")
        print(f"  Claim ID: {data['claim_id']}")
        print(f"  Anchors: {data['anchors']}")
       
        # Check that README is at position 0 (first)
        daytona_readme = "https://github.com/daytona/integrations/tree/main/packages/opencode-plugin"
        anchors = data['anchors']
        if not anchors:
            print(f"  ❌ FALHA: Nenhum anchor encontrado para claim Daytona")
            all_pass = False
        elif anchors[0] == daytona_readme:
            print(f"  ✅ PASS: README do opencode-plugin está na posição 0 (primeiro)")
        else:
            print(f"  ❌ FALHA: README do opencode-plugin NÃO está na posição 0 (anchors: {anchors})")
            all_pass = False
       
        # Check that YouTube is NOT at position 0
        youtube_at_0 = any("youtube.com" in a for a in data['anchors'][:1])
        if youtube_at_0:
            print(f"  ❌ FALHA: YouTube está na posição 0")
            all_pass = False
        else:
            print(f"  ✅ PASS: YouTube NÃO está na posição 0")
   
    return all_pass

def check_real_run_selection():
    """Test 5: Execute selection on real report with frozen corpus."""
    print("\n" + "="*70)
    print("TESTE 5: Seleção real no corpo do relatório com corpus congelado")
    print("="*70)
   
    claims = sr.extract_claims(REPORT_BODY, EVIDENCE, max_claims=50)
   
    # Find Morph pricing claim
    morph_claims = [c for c in claims if "morphllm.com/pricing" in c['claim'] or "200 req free" in c['claim']]
    print(f"\n  Claims sobre Morph pricing: {len(morph_claims)}")
    morph_ok = True
    if not morph_claims:
        print(f"  ❌ FALHA: Nenhuma claim sobre Morph pricing extraída")
        morph_ok = False
    for c in morph_claims:
        print(f"  Claim {c['id']}: {c['claim'][:120]}...")
        print(f"  Anchors: {c['anchors'][:3]}")
        print(f"  Evidence has '200 req': {'200 req' in c['evidence']}")
        morph_url = "https://www.morphllm.com/pricing"
        if morph_url in c['anchors'][:2]:
            print(f"  ✅ Morph pricing URL nos top 2 anchors")
        else:
            print(f"  ❌ Morph pricing URL NÃO nos top 2: {c['anchors'][:3]}")
            morph_ok = False
        if "200 req" not in c['evidence']:
            print(f"  ❌ Evidence NÃO contém '200 req'")
            morph_ok = False
   
    # Find Daytona claims
    daytona_claims = [c for c in claims if "opencode-daytona" in c['claim'].lower() or "daytona" in c['claim'].lower()]
    print(f"\n  Claims sobre Daytona: {len(daytona_claims)}")
    daytona_ok = True
    if not daytona_claims:
        print(f"  ❌ FALHA: Nenhuma claim sobre Daytona extraída")
        daytona_ok = False
    for c in daytona_claims:
        print(f"  Claim {c['id']}: {c['claim'][:120]}...")
        print(f"  Packages: {c['packages']}")
        print(f"  Anchors: {c['anchors'][:3]}")
        daytona_readme = "https://github.com/daytona/integrations/tree/main/packages/opencode-plugin"
        if daytona_readme in c['anchors'][:2]:
            print(f"  ✅ Daytona README nos top 2 anchors")
        else:
            print(f"  ❌ Daytona README NÃO nos top 2: {c['anchors'][:3]}")
            daytona_ok = False
        if "sandbox" not in c['evidence'].lower() and "isolamento" not in c['evidence'].lower():
            print(f"  ❌ Evidence NÃO contém conteúdo sobre sandbox/isolamento")
            daytona_ok = False
   
    print(f"\n  Total claims extraídas: {len(claims)}")
   
    if not morph_ok or not daytona_ok:
        return False
    return True

def check_real_run_on_claims(claims_list):
    """Run the real verification logic on a given list of claims.
    Returns True if Morph and Daytona pass, False otherwise."""
    morph_ok = True
    daytona_ok = True
    
    # Find Morph pricing claim
    morph_claims = [c for c in claims_list if "morphllm.com/pricing" in c['claim'] or "200 req free" in c['claim']]
    if not morph_claims:
        morph_ok = False
    for c in morph_claims:
        morph_url = "https://www.morphllm.com/pricing"
        if morph_url not in c['anchors'][:2]:
            morph_ok = False
        if "200 req" not in c['evidence']:
            morph_ok = False
    
    # Find Daytona claims
    daytona_claims = [c for c in claims_list if "opencode-daytona" in c['claim'].lower() or "daytona" in c['claim'].lower()]
    if not daytona_claims:
        daytona_ok = False
    for c in daytona_claims:
        daytona_readme = "https://github.com/daytona/integrations/tree/main/packages/opencode-plugin"
        if daytona_readme not in c['anchors'][:2]:
            daytona_ok = False
        if "sandbox" not in c['evidence'].lower() and "isolamento" not in c['evidence'].lower():
            daytona_ok = False
    
    return morph_ok and daytona_ok

def demonstrate_loss_detection():
    """Demonstrate that tests detect loss of claims, evidence content, and context.
    Uses the real verifier (check_real_run_on_claims) on modified extractions."""
    print("\n" + "="*70)
    print("DEMONSTRAÇÃO DE DETECÇÃO DE PERDA")
    print("="*70)

    # A. Remoção das claims alvo de Morph/Daytona - create a report WITHOUT these claims
    print("\nA. Remoção das claims alvo (simulando relatório sem as claims):")
    report_no_targets = """# Relatório de Teste

Este é um relatório de teste completamente genérico.

## 1. Introdução

Este relatório não menciona nada sobre aqueles pacotes, nem sobre as empresas por trás deles.
"""
    claims_no_targets = sr.extract_claims(report_no_targets, EVIDENCE, max_claims=50)
    # Run the real verifier on this extraction
    if not check_real_run_on_claims(claims_no_targets):
        print("  ✅ PASS: Verificador rejeita extração sem claims alvo")
    else:
        print("  ❌ FALHA: Verificador aceitou extração sem claims alvo")
        return False

    # B. Remoção apenas do campo evidence das claims sobre Morph, mantendo anchors e o corpus original
    print("\nB. Remoção apenas do campo evidence das claims sobre Morph:")
    import copy
    claims_original = sr.extract_claims(REPORT_BODY, EVIDENCE, max_claims=50)
    claims_evidence_removed = copy.deepcopy(claims_original)
    for c in claims_original:
        if "morphllm.com/pricing" in c['claim'] or "200 req free" in c['claim']:
            for c2 in claims_evidence_removed:
                if c2['id'] == c['id']:
                    c2['evidence'] = ""
                    break
    # Run the real verifier on this modified extraction
    if not check_real_run_on_claims(claims_evidence_removed):
        print("  ✅ PASS: Verificador rejeita extração com evidence Morph removido")
    else:
        print("  ❌ FALHA: Verificador aceitou extração com evidence Morph removido")
        return False

    # C. Remoção apenas do campo evidence das claims sobre Daytona
    print("\nC. Remoção apenas do campo evidence das claims sobre Daytona:")
    claims_evidence_removed_daytona = copy.deepcopy(claims_original)
    for c in claims_original:
        if "opencode-daytona" in c['claim'].lower() or "daytona" in c['claim'].lower():
            for c2 in claims_evidence_removed_daytona:
                if c2['id'] == c['id']:
                    c2['evidence'] = ""
                    break
    # Run the real verifier on this modified extraction
    if not check_real_run_on_claims(claims_evidence_removed_daytona):
        print("  ✅ PASS: Verificador rejeita extração com evidence Daytona removido")
    else:
        print("  ❌ FALHA: Verificador aceitou extração com evidence Daytona removido")
        return False

    return True

def check_readme_pertinence():
    """PASSO 3: Test README pertinence - only relevant READMEs should be boosted.
   
    - Claim about sandbox of opencode-example.
    - Pertinent source at vendor.example.com/documentation/overview containing package, claim, and PROVA_PERTINENTE.
    - Two READMEs of other-tool and another-tool that only mention opencode-example in comparison.
    The pertinent source and PROVA_PERTINENTE must remain in evidence.
    Currently, the two READMEs push it to third position and its proof disappears.
    """
    print("\n" + "="*70)
    print("PASSO 3: Pertinência de READMEs - apenas READMEs pertinentes devem ser promovidos")
    print("="*70)
   
    test_report = """# Relatório de Teste

O pacote `opencode-example` oferece isolamento em sandbox.
"""
   
    test_evidence = {
        "https://vendor.example.com/documentation/overview": 
            "Documentação do opencode-example: isolamento em sandbox com sync git. PROVA_PERTINENTE: sandbox isolado com sync git.",
        "https://github.com/other/other-tool/README.md": 
            "# other-tool\n\nComparação com opencode-example: nosso sandbox é melhor.",
        "https://github.com/another/another-tool/README.md": 
            "# another-tool\n\nDiferente do opencode-example, nosso sandbox não tem sync git.",
    }
   
    claims = sr.extract_claims(test_report, test_evidence, max_claims=10)
   
    if not claims:
        print("  ❌ FALHA: Nenhuma claim extraída")
        return False
   
    # Find the claim about sandbox
    target_claims = [c for c in claims if "sandbox" in c['claim'].lower() or "isolamento" in c['claim'].lower()]
   
    if not target_claims:
        print("  ❌ FALHA: Afirmação sobre sandbox não extraída")
        return False
   
    claim = target_claims[0]
    print(f"  Claim: {claim['claim'][:150]}...")
    print(f"  Packages: {claim['packages']}")
    print(f"  Anchors: {claim['anchors'][:3]}")
    print(f"  Evidence: {claim['evidence'][:300]}...")
   
    all_pass = True
   
    # The pertinent documentation should be in anchors
    pertinent_url = "https://vendor.example.com/documentation/overview"
    if pertinent_url in claim['anchors']:
        print(f"  ✅ PASS: Fonte pertinente está nos anchors")
    else:
        print(f"  ❌ FALHA: Fonte pertinente NÃO está nos anchors")
        all_pass = False
   
    # PROVA_PERTINENTE should be in evidence (full evidence)
    if "PROVA_PERTINENTE" in claim['evidence']:
        print(f"  ✅ PASS: PROVA_PERTINENTE está na evidence")
    else:
        print(f"  ❌ FALHA: PROVA_PERTINENTE NÃO está na evidence")
        all_pass = False
   
    # The two irrelevant READMEs should NOT be at position 0
    if claim['anchors'][0] != "https://github.com/other/other-tool/README.md" and claim['anchors'][0] != "https://github.com/another/another-tool/README.md":
        print(f"  ✅ PASS: READMEs irrelevantes NÃO estão na posição 0")
    else:
        print(f"  ❌ FALHA: README irrelevante está na posição 0")
        all_pass = False
   
    return all_pass

def check_cited_video_with_competing_readmes():
    """Test 6: Explicitly cited video with spoken segment + two competing READMEs.
   
    The URL and cited spoken segment must remain in the delivered evidence.
    """
    print("\n" + "="*70)
    print("TESTE 6: Vídeo explicitamente citado com spoken + 2 READMEs concorrentes")
    print("="*70)
   
    # Build a mini-report with a claim citing a video and its [spoken] segment,
    # plus two package READMEs that also match the package name
    test_report = """# Relatório de Teste

O pacote `opencode-example` tem um tutorial em vídeo em https://www.youtube.com/watch?v=test123 que diz "[spoken 1/5] instale com npm install opencode-example".
"""
   
    test_evidence = {
        "https://www.youtube.com/watch?v=test123": "Tutorial do opencode-example. [spoken 1/5] instale com npm install opencode-example. [spoken 2/5] configure o plugin.",
        "https://github.com/example/opencode-example": "# opencode-example\n\nREADME do pacote opencode-example.",
        "https://github.com/other/opencode-example": "# opencode-example\n\nOutro README do mesmo pacote.",
    }
   
    claims = sr.extract_claims(test_report, test_evidence, max_claims=10)
   
    if not claims:
        print("  ❌ FALHA: Nenhuma claim extraída")
        return False
   
    # Find the claim about the video
    target_claims = [c for c in claims if "spoken 1/5" in c['claim'] or "youtube" in c['claim'].lower()]
   
    if not target_claims:
        print("  ❌ FALHA: Afirmação sobre vídeo citado não foi extraída")
        return False
   
    claim = target_claims[0]
    print(f"  Claim: {claim['claim'][:150]}...")
    print(f"  Anchors: {claim['anchors'][:3]}")
    print(f"  Evidence: {claim['evidence'][:300]}...")
   
    all_pass = True
   
    # The YouTube URL must be in anchors (ideally first)
    youtube_url = "https://www.youtube.com/watch?v=test123"
    if youtube_url in claim['anchors']:
        print(f"  ✅ PASS: URL do YouTube citada está nos anchors")
    else:
        print(f"  ❌ FALHA: URL do YouTube citada NÃO está nos anchors")
        all_pass = False
   
    # The spoken segment must appear in the evidence (full evidence)
    if "[spoken 1/5]" in claim['evidence']:
        print(f"  ✅ PASS: Segmento falado citado está na evidence")
    else:
        print(f"  ❌ FALHA: Segmento falado citado NÃO está na evidence")
        all_pass = False
   
    # The YouTube URL should be at position 0 (explicitly cited)
    if claim['anchors'][0] == "https://www.youtube.com/watch?v=test123":
        print(f"  ✅ PASS: Vídeo citado está na posição 0")
    else:
        print(f"  ❌ FALHA: Vídeo citado NÃO está na posição 0")
        all_pass = False
   
    return all_pass

def check_cited_url_not_in_keywords():
    """Test 7: Explicitly cited URL not in keyword candidates but in corpus.
   
    If URL is in corpus, its content must be selected even if keywords didn't match.
    """
    print("\n" + "="*70)
    print("TESTE 7: URL explicitamente citada fora dos candidatos por palavras-chave")
    print("="*70)
   
    # Build a report where a claim cites a URL but the URL's content
    # doesn't share enough keywords with the claim
    test_report = """# Relatório de Teste

A página https://example.com/pricing anuncia "200 req free every month" para o plano gratuito do `opencode-example`.
"""
   
    test_evidence = {
        "https://example.com/pricing": "Pricing page: 200 req free every month. No limits. Usage-based billing.",
        "https://example.com/readme": "This is a README about something completely different with no pricing info.",
    }
   
    claims = sr.extract_claims(test_report, test_evidence, max_claims=10)
   
    if not claims:
        print("  ❌ FALHA: Nenhuma claim extraída")
        return False
   
    # Find the claim about pricing
    target_claims = [c for c in claims if "200 req free" in c['claim'] or "pricing" in c['claim'].lower()]
   
    if not target_claims:
        print("  ❌ FALHA: Afirmação sobre pricing não extraída")
        return False
   
    claim = target_claims[0]
    print(f"  Claim: {claim['claim'][:150]}...")
    print(f"  Packages: {claim['packages']}")
    print(f"  Anchors: {claim['anchors'][:3]}")
    print(f"  Evidence: {claim['evidence'][:300]}...")
   
    all_pass = True
   
    pricing_url = "https://example.com/pricing"
   
    # The pricing URL must be in anchors (explicitly cited)
    if pricing_url in claim['anchors'][:2]:
        print(f"  ✅ PASS: URL explicitamente citada está nos top 2 anchors")
    else:
        print(f"  ❌ FALHA: URL explicitamente citada NÃO está nos top 2 anchors")
        all_pass = False
   
    # The pricing content must be in evidence
    if "200 req free every month" in claim['evidence']:
        print(f"  ✅ PASS: Conteúdo da pricing page está na evidence")
    else:
        print(f"  ❌ FALHA: Conteúdo da pricing page NÃO está na evidence")
        all_pass = False
   
    return all_pass

def main():
    print("="*70)
    print("TESTES DE SELEÇÃO DE EVIDÊNCIA - MORPH E DAYTONA (+ CONTROLES EXTRAS)")
    print("="*70)
   
    all_passed = True
    all_passed &= check_morph_pricing_claim()
    all_passed &= check_morph_pricing_absent()
    all_passed &= check_daytona_claim()
    all_passed &= check_daytona_with_distractor()
    all_passed &= check_real_run_selection()
    all_passed &= demonstrate_loss_detection()
    all_passed &= check_readme_pertinence()
    all_passed &= check_cited_video_with_competing_readmes()
    all_passed &= check_cited_url_not_in_keywords()
   
    print(f"\n{'='*70}")
    if all_passed:
        print("TODOS OS 9 TESTES DE SELEÇÃO DE EVIDÊNCIA PASSARAM")
    else:
        print("ALGUNS TESTES FALHARAM")
    print(f"{'='*70}")
   
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())