# Relatório técnico — missão accept29-ativas (descoberta → seleção → real)

HEAD validado: `b6ee923` (branch `feat/product-v1`). Runs reais: accept30 (HEAD `3a2984b`) e accept31 (HEAD `06a5239`), código congelado pré==pós nos dois.

## 1. O que os testes offline demonstram (e o que não demonstram)

- Suite `633 OK, 10 skipped, EXIT 0` (`/tmp/opencode/suite-m5.log`): 14 testes accept28-causas + 14 accept29-causas (TDD RED→GREEN) + 8 funil accept30 (M1–M4) + 4 re-review yellows + 4 rounds accept31 (M5). Cobrem mecanismos isolados com nomes genéricos (Widget Alpha/Beta): G5 só-candidatas, descoberto=candidate, promoção pós-avaliação, N/A direcional, identidade universal por-ref, sem-âncora→LACUNA, source harness/user/default, partial_declared, anti-quarentena `_sent`, pin dimensão×menção, re-adoção proporcional em expansão.
- Limite: testes provam mecanismos em entradas controladas; diagnose accept28/29/30/31 antes==depois byte-idêntico porque runs congelados não exercitam caminhos novos. Verde ≠ comportamento em produção.

## 2. Verificações pós-hoc (diagnose como oráculo, sem efeito in-product)

- `tools/diagnose_run.py` aplicado aos 4 runs antes/depois de cada fix: sempre idêntico (esperado e declarado). `state["diagnose_audit"]` continua não populado in-product; o gate `partial_declared→partial` atua via `verification_report`, não via oráculo.
- Confronto de granularidade (accept30): diagnose por linha 55/16/102+22 declared vs verificação por frase 61/11/36 — splitters distintos, mesma direção (zero leniência sistêmica). Residual conhecido: `support_docs` do diagnose conta presença de token (≤1500 chars), superestima o miss real em ~5 células (c4, dimensão vazia real).

## 3. Execução real: accept30 (causa nova) e accept31 (confirmação parcial)

- accept30 (`/home/thomaskyn/hermes-runs/accept30/`, HEAD `3a2984b`, EXIT 0): 0/55+0N/A, support failed (1 claim corretamente reprovado — "4/5…LACUNA total" impreciso), overall failed. Causa nova e específica: quarentena `_sent` + teto JSON 12k (docs da r0 nunca recitados na célula) + janela de excerto 1200 chars; by_cells estimado em 46 vs 55 reais. Sistemático e determinístico (stdlib ordenada, sem random), não azar de retrieval. 8082 reconciliado (servidor Δ24215+cached Δ270=24485; 7 calls/57 vetores). Versão observada `v2.2.5`, premissa `2.1.4` separada.
- accept31 (`/home/thomaskyn/hermes-runs/accept31/`, HEAD `06a5239`, EXIT 0, sem `--max-rounds`): 1/53+2N/A partial, overall partial (support partial, 17 unsupported honestos), stop rounds `source=default` não-justificado com folga — hook M3 calculou sobre plano v1 (15 células) e nunca recalculou sobre 55. 8082 reconciliado (Δ12391+Δ74=12465; 4 calls/29 vetores).
- Correções aplicadas após cada run (M1–M4 + remediação 3🟡; M5 re-adoção em expansão com `_proportional_cells`, 2 gates no `_resume_loop`), todas TDD, gates cavecrew sem 🔴 aberto (M5: "No issues"). Nenhum re-run após os fixes — próximo run real os exercitará.

## 4. Confronto do relatório final (accept31) com pergunta e aceite

- A1 descoberta: conjunto de 5 resulta da investigação (nomes distintos do accept29/30 — sem congelamento de favoritos); 5º/explorados fora da seleção declarados, não contados.
- A2 propósito: `code-review` N/A em planejamento/testes com escopo documentado (não exige cada um tudo); lacunas com causa, nunca N/A silencioso.
- A3 identidade: fontes próprias exigidas; menção em terceiros ([4]) = LACUNA declarada; `opencode-plugin`/`oh-my-opencode` sem fonte própria = LACUNA com causa.
- A4 inferência: combinação `shannon+oh-my-opencode` DOCUMENTADA ([9]) conta como partial; demais combinações e qualquer sobreposição sem doc-interop = LACUNA/insufficient — exatamente o contrato (premissa distinta sustenta INFERÊNCIA marcada, nunca integração testada).
- A5 proporcionalidade: stop `source=default` não-justificado declarado como tal; M5 corrige prospectivamente.
- A6 legibilidade: numeração única, "LACUNA com causa", Notas técnicas separadas no §8, verificação correspondente (support partial). Resíduo: tabelas de alcance listam entidades fora da seleção (ruído honesto de escopo, não erro de atribuição).

## 5. Veredito da missão inteira: PARCIAL

Pipeline íntegro e honestamente parcial nos 3 runs (support ok→failed→partial conforme o texto, nunca verde indevido). RA8 segue pendente: nenhum run com cobertura plena; fixes M1–M5 aguardam validação em run real futuro. Sem validação: compat funcional 2.1.4, dimensão testes, combinações além da documentada, custos/preços.

Evidências: suite 633 EXIT 0; commits `3a2984b` (Fase A), `06a5239` (Fase B), `b6ee923` (M5); runs em `/home/thomaskyn/hermes-runs/accept{30,31}/`; sem push/deploy/prod; 8082 preservado (só endpoint autorizado).
