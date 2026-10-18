# Próxima rodada — preservar o significado e a origem dos fatos estruturados

```text
/goal Corrigir as perdas concretas de estrutura, origem e evidência reproduzidas na nova V3, preservando os 39 testes aprovados.

BASE VALIDADA

Repositório: /opt/data/deep_research_outputs/gpt_researcher
Python: /opt/data/home/.agent-reach-venv/bin/python
semantic_review.py atual:
a5526b1c034512610acd9fd3a3f5b3b15f4d37354f331acee1581e3c7336568f

A revisão independente executou as quatro suítes: 39/39 passam, sem modificar seus arquivos. Preserve esse avanço. Foram recuperados os commits dos cinco pacotes, a cobertura incompleta bloqueia aprovação e a inicialização do corpus deixou de reutilizar snapshots anteriores.

Os nove controles anexados em scripts/test_semantic_coverage_structure.py detectam perdas que as suítes anteriores não cobriam. A saída literal contra essa V3 está anexada. Todos são parte do contrato já solicitado: preservar relações, usar origem real, aplicar escopo a todos os caminhos, reutilizar a seleção de evidências e deduplicar com segurança.

Não fazer pesquisa, rede, chamadas ao modelo, troca de modelos ou alteração do relatório/corpus. Faça correções dirigidas. Preserve cópia da base e não faça checkout indiscriminado.

PASSO 1 — REPRODUZIR

Coloque o teste anexo em scripts/ e execute:
/usr/bin/env PYTHONPATH=/opt/data/deep_research_outputs/gpt_researcher /opt/data/home/.agent-reach-venv/bin/python /opt/data/deep_research_outputs/gpt_researcher/scripts/test_semantic_coverage_structure.py

Confirme as falhas antes de editar. Não enfraqueça as asserções nem trate os 39 testes anteriores como prova suficiente destes casos.

PASSO 2 — TABELAS SEPARADAS, ORIGEM E ESCOPO

A extração atual junta as linhas de TODAS as tabelas do report num conjunto, usa o primeiro cabeçalho e atribui tudo ao primeiro bloco. Reproduzido com duas tabelas:
- tabela 1: Pacote | Licença; opencode-alpha | MIT;
- tabela 2: Pacote | Preço; opencode-beta | R$ 99/mês.

A saída contém "Pacote: Licença Preço" e "opencode-beta: Licença R$ 99/mês", ambas ligadas à seção da primeira tabela. Isso altera o significado do relatório.

Processe cada tabela contígua separadamente, preservando seu cabeçalho, orientação, seção e posição. Cabeçalhos e separadores não são fatos. Suporte os sujeitos nas linhas e nas colunas já implementados.

O caminho de tabelas ainda percorre report inteiro. Uma tabela depois de ## 7. Auditoria é extraída mesmo estando fora do hash declarado. Faça TODOS os caminhos consumirem o mesmo escopo. Cubra delimitador presente, ausente e na posição zero, sem divergência entre texto auditado e hash.

PASSO 3 — RELAÇÕES DOS METADADOS E ORIGEM REAL

O parser recupera hashes, mas apaga os qualificadores dos rótulos:
- Commit (tag v1.2.3): AAA vira apenas "commit: AAA";
- Branch `main` HEAD: BBB vira apenas "branch: BBB".

Trocar v1.2.3/main por v9.9.9/dev produz as mesmas afirmações. Preserve na claim enviada ao auditor a tag associada ao commit e o nome da branch cujo HEAD é o hash. Não basta esconder essa informação num campo que o auditor não recebe. Mantenha as relações distintas, sem afirmar contradição por seus hashes diferirem.

As linhas de metadados são localizadas com a primeira correspondência textual no documento. Quando dois pacotes têm "- **Branch:** `main`", a claim do segundo pacote aponta para o bloco do primeiro. No relatório congelado isso ocorre para morph-plugin e tavily, vinculados ao bloco de goal-plugin.

Transporte bloco/posição reais durante o parsing. Não procure a primeira linha igual nem use semelhança de palavras para atribuir origem. Declare a unidade correta das posições; não documente índices de linha como caracteres.

PASSO 4 — SELEÇÃO DE EVIDÊNCIAS NOS CAMINHOS ESTRUTURADOS

As claims de metadados continuam com anchors=[] e evidence="" mesmo havendo fonte pertinente no corpus. Títulos usam anchors=[nome_do_pacote], que não é URL. Tabelas escolhem a primeira fonte que menciona o pacote.

Reprodução: uma célula de preço cita explicitamente https://example.com/pricing. O corpus contém um README genérico primeiro e a página de preço depois. A claim cita a página de preço, mas recebe somente o README e perde PROVA_PRECO.

Faça os caminhos de tabela, título e metadados usarem a seleção já validada, com a identidade correta do sujeito e o contexto necessário. Anchors devem ser URLs presentes no corpus atual. Preserve a prioridade de fonte explicitamente citada, o comportamento de ausência de conteúdo e as janelas de transcrição. Não crie rankings paralelos de "primeira menção" para cada tipo de claim.

PASSO 5 — DEDUPLICAÇÃO SEM APAGAR FATOS DIFERENTES

A chave ainda usa os primeiros 60 caracteres. Duas frases com o mesmo início, uma afirmando licença MIT e outra GPL, fazem a segunda virar excluded_duplicate com duplicate_of=None. São proposições diferentes e ambas precisam ser contabilizadas como fatos.

Use o conteúdo completo normalizado e o contexto/sujeito necessário para identificar duplicatas reais. Não confunda tag, commit de tag e HEAD, nem proposições divergentes.

Duplicatas exatas já têm vínculo no ledger, mas ainda permanecem na lista retornada e são enviadas ao auditor. Exclua-as dos itens efetivamente revisados e do consumo do limite; preserve o registro da ocorrência e o vínculo com a original. Se a original for adiada ou incompleta, não apresente sua duplicata como revisão concluída.

PASSO 6 — VALIDAR E ENTREGAR

Execute o teste anexo e as quatro suítes anteriores. Preserve o controle positivo e as proteções de quórum/falha. A extração, a seleção e a integração devem ser reais; quando necessário, apenas _review_pass pode ser simulado.

Atualize o checklist do relatório congelado usando fatos, valores, relações e origem reais. O checklist atual informa zero claims de tabela, enquanto a extração real produz 99: ele não está contabilizando corretamente os itens. Não marque "Tag/Commit confundidos" só porque uma frase menciona os dois; uma relação entre tag e commit pode ser legítima. Não invente um campo Data onde só existe uma data vinculada a outra relação: preserve o que o texto realmente afirma.

Preserve os artefatos antigos e entregue coverage_delivery_184601_v4.zip contendo:
- arquivos completos alterados;
- testes, incluindo a suíte anexa;
- artefato de cobertura e checklist atualizados;
- comandos, saídas integrais e códigos de saída;
- SHA256SUMS.txt efetivamente incluído no ZIP.

O SHA256SUMS_v3.txt foi listado na entrega anterior, mas não consta no ZIP recebido. Os hashes declarados de código/testes/artefato conferiram; inclua agora o manifesto do pacote final.

Rotule toda revisão simulada e não a apresente como validação semântica real do relatório.

STOP WHEN

Os nove controles de estrutura e os 39 controles anteriores passarem; os exemplos acima preservarem significado, origem e evidência; o checklist corresponder ao conteúdo real; e o pacote refletir o código testado.

Conteúdo que continuar explicitamente incompleto deve bloquear a aprovação. Não afirme recall universal do parser nem conclusão da ferramenta de pesquisa inteira: esta etapa é a cobertura rastreável e sua integração.
```
