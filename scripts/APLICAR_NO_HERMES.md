# Aplicar a V4 revisada

Este pacote parte da `coverage_delivery_184601_v4.zip` e foi preparado durante a revisão independente. Ele ainda precisa ser aplicado no ambiente do Hermes.

## O que mudou

- Uma linha de produção em `_declare_scope`: `cut > 0` passou a `cut >= 0`. Quando o delimitador está na posição zero, o hash e o tamanho agora representam o corpo vazio que efetivamente foi extraído.
- Reincluído `scripts/test_semantic_coverage_review.py`, a suíte independente original de 11 testes que não estava no ZIP V4 recebido.
- Adicionado `scripts/test_semantic_scope_boundary.py`, com um teste e três cenários: delimitador ausente, no meio e na posição zero.
- Checklist reconstruído a partir dos itens reais de revisão: 83 fatos de tabela, IDs e origem dos metadados dos cinco pacotes.
- Artefato e saídas independentes atualizados, com revisão simulada identificada.

Os quatro testes presentes no ZIP original não foram modificados. O código, fora da correção de uma linha acima, permanece igual ao original V4.

## Identidade do código

- V4 recebida: `0a1bab3cd55352690eb2be1580bac00bfab256f359c88ef68dc63bd4e2161a67`
- V4 revisada deste pacote: `1765f755d8bcefcd6c2d812dcdfe3cba01a1dee03f70c32ace869cb91de63eb0`

## Instrução para encaminhar ao Hermes

```text
/goal Aplicar o pacote V4 revisado e conferir sua integridade no ambiente local.

Repositório: /opt/data/deep_research_outputs/gpt_researcher
Python: /opt/data/home/.agent-reach-venv/bin/python

Preserve o semantic_review.py atual e os artefatos anteriores. Confira seu hash antes de substituir: a base esperada é 0a1bab3cd55352690eb2be1580bac00bfab256f359c88ef68dc63bd4e2161a67. Se o código atual tiver outras mudanças, examine o diff e preserve-as; não restaure versões antigas indiscriminadamente.

Aplique o semantic_review.py do pacote e os testes, mantendo os caminhos relativos. A única mudança de produção é cut > 0 para cut >= 0 em _declare_scope. Os artefatos revisados têm nomes novos e não exigem sobrescrever os antigos. Preserve relatório e corpus congelados.

Execute as seis suítes:
- scripts/test_semantic_evidence_selection.py
- scripts/test_semantic_failure_guard.py
- scripts/test_semantic_coverage.py
- scripts/test_semantic_coverage_review.py
- scripts/test_semantic_coverage_structure.py
- scripts/test_semantic_scope_boundary.py

Use PYTHONPATH=/opt/data/deep_research_outputs/gpt_researcher e o Python informado. São 49 testes no pacote. A revisão independente já passou todos offline; confirme a aplicação no seu ambiente sem chamadas ao modelo ou à rede.

Confira que o código instalado tem SHA-256 1765f755d8bcefcd6c2d812dcdfe3cba01a1dee03f70c32ace869cb91de63eb0. Informe os códigos de saída e qualquer divergência real. Não modifique testes para contornar falhas nem amplie esta rodada com novas funcionalidades.

Depois da aplicação verificada, encerre a rodada de cobertura para os casos acordados. O relatório congelado continua com um trecho de extração incompleta e accepted=False; a revisão simulada não é aprovação semântica do conteúdo. A ferramenta inteira ainda requer avaliação do corpus e revisão semântica real.
```

## Validação independente

A V4 original passou os 48 testes das cinco suítes. A cópia revisada passou os 49 testes das seis suítes. Apenas as leituras dos dois arquivos congelados foram redirecionadas às cópias locais verificadas; nos testes que exigem julgamentos, apenas `_review_pass` foi simulado. Nenhuma tentativa de rede foi registrada.

O manifesto `SHA256SUMS.txt` cobre todos os arquivos distribuídos, exceto o próprio manifesto.
