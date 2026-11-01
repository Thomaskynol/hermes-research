# Relatório técnico da missão pós-28 → accept29

HEAD validado: `1364dc1d7bedb513729752e8e969267833686d6d` · branch `feat/product-v1`.
Código congelado no run: HEAD pré==pós, diffstat vazio.

## 1. Testes offline (pré-pesquisa, código 1364dc1)
- `tests/test_accept28_causes.py`: 36/36 OK (RED antes: 1 falha no positivo por scope sem complementaridade → GREEN após scope `LACUNA explícita; complementaridade plausível, não integração testada`, `verification_report.py:1045-1051`).
- Suíte: 599 OK (skipped=10 pré-existentes), EXIT=0.
- 4 contratos confirmados: (i) positivo com 2 docs declara INFERÊNCIA com limites, nunca integração testada; (ii) negativo sem-âncora/interop rejeitado; (iii) ref frouxa descartada no caminho assess→reconcile→writer/seleção (c12/c13 viram LACUNA no texto entregue); (iv) oráculo `diagnose_audit` é só pós-hoc — documenta, não decide in-product.

## 2. Verificações pós-hoc (não decidem in-product)
- Diagnose accept28: 54/10 → 53/11 (C9 combinação → LACUNA sem-âncora). Accept29: `cells: 46 required | ok=3, partial_legit=10, missing=8, na_bare=4, na_scoped=2, selection_context=18, synthesis_unsupported=1`; síntese 44/14/76.
- Os 14 unsupported do diagnose são linhas honestas de N/A ("não aplicável", overlap < 0.35) e LACUNAs ("versão exata ausente") — o oráculo literal é mais estrito que o gate `support`; `support ok` coexiste com `question partial`. Limitação conhecida, declarada — não virou fix in-product (evita rejeição indiscriminada e recorte de requisito).
- Repro R1/R2/R3: EXIT=0.

## 3. Execução real accept29 (única, sem repetição sem hipótese)
- Dir: `/home/thomaskyn/hermes-runs/accept29/` · run.sh medium `--max-rounds 3 --auto-plan`, pergunta original do aceite, `--context installed_opencode_version=2.1.4`, `HERMES_NATIVE_EMBEDDINGS=1`, EXIT=0, elapsed 478.8s.
- Cobertura 4/40 + 6 N/A = 0.10 `partial`; overall `partial` (execution ok, question partial, review partial, **support ok 4ª vez**); stop `rounds` max_rounds=3 (source=user via CLI; queries 10/30, extractions 48/120, model 5-7/16, elapsed 287s/1800s, reserva preservada, partial=True).
- Infra: vast DOWN, SearXNG DOWN (3 ops falharam, caminho efetivo ddgs+extração 31/39); 8082 `http://172.17.0.1:8082/v1` harrier-oss-v1-0.6b com efeito (4 calls, 34 vetores, 14967 tokens; servidor 27577→42342 + cached 202 reconciliado); gerador separado (tokens/custo unknown); YouTube 0 fetches por ausência de alvo (sem ASR).
- Versão: premissa 2.1.4 (user://context, nunca evidência; comparação numérica >1.0.132 sustentada, funcional sem fonte = LACUNA) vs observada `opencode v2.2.5` registrada à parte.

## 4. Confronto com a pergunta e o aceite
- Pertinência: 4 nomes exigidos (oh-my-opencode, opencode-plan, opencode-code-review, opencode-review); 5º sem nome = LACUNA declarada; alternativas não investigadas listadas sem afirmar fatos. Parcial honesto, sem 5º plugin.
- Fases: planejamento/implementação partial (oh-my-opencode), testes insuficiente/LACUNA geral, revisão covered nos 2 reviewers. Nenhum plugin demonstra testes — LACUNA, não rejeição indiscriminada.
- Identidade: [1]/[2]/[27]/[28]/[30] ancoram entidades; [15] genérico removido da linha de alternativas; [16]/[17] mantidos só como registro não investigado. Sem atribuição frouxa no caminho de entrega.
- Justificativas: §10 traz 4 INFERÊNCIAS marcadas com premissas em fontes distintas ([28]+[1], [30]+[2], [1]+[2]) — positivo permitido; c14/c15 do ledger = insufficient (sem doc-interop direto) convivem como "sem prova direta", não como contradição de cobertura (supported==0 preservado).
- Concordância: síntese (§1 c/ LACUNAs + §10 INFERÊNCIA + §11 lacunas) ⇄ achados (§3: e3 insuficiente, N/A delimitados, c14/c15 insufficient) ⇄ verificação (§8: question partial, support ok) ⇄ conclusão (§6 parcial). O `support ok` ao lado de `question partial` é parcial honesto, não prova de completude; RA8 segue pendente.

## 5. Falhas encontradas / corrigidas nesta fase
Nenhuma causa nova no caminho da entrega. Nenhum fix aplicado pós-run (repetir pesquisa sem hipótese é proibido). Resíduos declarados: oráculo fora do produto; vast/SearXNG DOWN; single-run sem causalidade vs accept28.

## 6. Veredito da missão inteira: PARCIAL, não atendido como completo
Correções demonstradas e verificadas offline; pesquisa real executada sobre código congelado com resultado parcial honesto (4/40, sem testes demonstrados, sem 5º plugin, só INFERÊNCIA para combinação/sobreposição). Não declarar "atendido" integral. Sem ZIP/push/PR/deploy/produção.
