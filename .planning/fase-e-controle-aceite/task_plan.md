# Plano — Fase E: validação controlada + aceite (missão aberta)

Data: 2026-11-02 · Branch: `feat/product-v1` · HEAD inicial: `0e6ad16`
Fonte de verdade: `docs/MODELAGEM_PRODUTO_PESQUISA_HERMES_v1.1.md` (§§6, 8, 9, 12, 13, 16) + pedido do usuário (@67).

## Objetivo

1. Validação controlada dos 5 itens (sem nova pesquisa completa, plano/corpus/artefatos
   originais preservados; replays em cópias identificadas).
2. Correções autorizadas (seleção/ranking, dimensionamento de rodadas, demonstração
   integrada; defaults/heurísticas internas; tetos globais NÃO aumentam).
3. Revisão independente dos comportamentos.
4. Aceite original sobre código congelado (pergunta accept34 + `installed_opencode_version=2.1.4`
   como premissa controlada), novo run preservando accept34, URLs validadas.
5. Entrega: relatório técnico + pesquisa final (2 Markdowns), plano + continuidade atualizados.

## Critérios de aceite observáveis

- (i) M-A demonstrada pelo caminho integrado: quais trechos/células influenciou, o que
  chegou ao assessor e ao writer; 1 caso em que muda a seleção + 1 em que manter é correto.
- (ii) Context7: explicação exata do que sustenta cada estado de célula (definição do
  critério, evidência, avaliação acumulada, renderização); documentado ≠ testado.
- (iii) Finalistas: ligação investigação→pertinência→evidência→seleção demonstrada,
  sem nomes especiais no código.
- (iv) Inferências de combinação/sobreposição: prudentes por premissas distintas
  preservadas; extrapolações rejeitadas; "sem evidência de interoperabilidade" não
  substitui a avaliação do critério.
- (v) Parada: limites explícitos vs defaults vs projeções distinguidos; política
  justificada frente a consumo observado e lacunas relevantes.
- Afirmação incorreta/contraditória no texto = defeito mesmo sem mudar o placar.
- Novo relatório do produto: comparação útil, referências verificadas, URLs inteiras.
- Restrições: só embeddings llama.cpp 8082; produção intacta; commits locais; sem push/PR/deploy.

## Hipóteses

- H1: M-A nunca engajou em produção (sem trilha) ou engajou sem efeito observável.
- H2: "só ranking" nos achados vs funcionalidades no relatório = divergência de camada
  (critério exige dimensão não coberta pelo excerto) ou falso-negativo do auditor.
- H3: Finalistas sem documentação persistem por auto-plan sem gate de evidência mínima.
- H4: Writer substitui avaliação de combinação por nota de interoperabilidade.
- H5: `max_rounds` default por comparabilidade é o teto vinculante sem base em saturação.

## Evidências / pendências / próximo passo

Ver `findings.md` e `progress.md` neste diretório.
