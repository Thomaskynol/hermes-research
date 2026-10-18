# Instrução para o Hermes — corrigir as pendências concretas da V2

Envie este pacote ao Hermes e copie o bloco abaixo.

```text
/goal Corrigir as pendências reproduzidas da coverage_delivery_184601_v2.zip, usando os testes independentes anexados.

BASE E LIMITES

Repositório: /opt/data/deep_research_outputs/gpt_researcher
Python: /opt/data/home/.agent-reach-venv/bin/python
semantic_review.py da V2:
3902f0c6797c1cf38b0a9392cb0978ef9c3b0a0bd3050300b219e4e89414a5a2

Preserve uma cópia dessa versão para reproduzir os defeitos. Faça correções direcionadas, sem reescrita geral, nova pesquisa, rede, LLM, modelos novos ou alteração do relatório/corpus congelado.

A V2 corrigiu a extração do título factual, a tabela simples por linha e o bloqueio de aprovação do parágrafo longo. Preservar esses avanços, os 9 testes de seleção, os 8 de proteção e os controles positivos. A soma dos testes entregues é 28 (9+8+11), não 26.

A alteração no teste de seleção foi apenas a proteção contra anchors vazios; a versão original também passou na revisão. Não é necessário reabrir essa etapa.

O arquivo scripts/test_semantic_coverage_review.py deste pacote contém controles independentes do contrato já solicitado. Eles usam extração e integração reais, simulando somente _review_pass. A saída literal contra a V2 está anexada. Os testes apontam dez defeitos concretos; há também um controle positivo de aprovação para documento pequeno.

PASSO 1 — REPRODUZIR ANTES DE EDITAR

Coloque o teste independente em scripts/ sem alterar seu conteúdo para enfraquecer as asserções. Use a cópia original do relatório congelado.

Execute:
/usr/bin/env PYTHONPATH=/opt/data/deep_research_outputs/gpt_researcher /opt/data/home/.agent-reach-venv/bin/python /opt/data/deep_research_outputs/gpt_researcher/scripts/test_semantic_coverage_review.py

Registre as falhas literais da V2. Não declare conclusão com base só na suíte atual, cujas asserções ainda deixam passar as omissões abaixo.

PASSO 2 — CORRIGIR A EXTRAÇÃO E A ORIGEM NO DOCUMENTO REAL

1. As cinco seções de metadados do corpo congelado continuam sem claim_ids. O parser procura Tag:/Branch:/Commit:/Data: sem bullets e negrito, enquanto o relatório usa - **Tag:**, - **Commit (tag ...):**, - **Branch `trunk` HEAD:** etc. No fixture simples, os quatro campos são juntados em um único valor de tag, por exemplo:
   metadata_label=tag
   metadata_value="v1.2.3 Branch: main Commit: aaaa... Data: 2026-10-16"
   Isso não são quatro fatos separados.

   Preserve os limites de cada item antes de juntar prosa. Normalize a marcação para interpretar os rótulos, preservando o trecho original e o sujeito herdado do título. Extraia os valores e relações distintos; não confunda commit de tag com HEAD de branch. Os cinco pacotes específicos ficam nas fixtures/checklist, não em regras fixas de produção.

2. A tabela simples com pacotes nas linhas funciona. A tabela comparativa com pacotes nos cabeçalhos de coluna perde os fatos. Exemplo:
   | Aspecto | `opencode-alpha` | `opencode-beta` |
   |---|---|---|
   | Licenca | MIT | GPL |
   | Servico pago obrigatorio | nenhum | sim |
   Na V2 isso retorna zero claims e coverage_complete=True. Preserve os cabeçalhos e associe cada célula factual ao sujeito correto. Processe cada tabela separadamente; não reúna todas as tabelas do documento sob o primeiro cabeçalho/bloco.

3. O ledger declara somente o corpo anterior a ## 7. Auditoria, mas os loops de tabelas e a prosa ainda processam report inteiro. Uma afirmação posterior ao delimitador é extraída e vinculada ao bloco anterior. Use o MESMO scope_text em todos os caminhos e no hash. Trate delimitador ausente e na posição zero.

4. A origem ainda é atribuída por busca de palavras, com fallback para qualquer palavra com mais de cinco caracteres. Isso não comprova a origem. Preserve o vínculo do trecho durante o parsing, com posições e unidade corretas. _split_into_blocks documenta posição de caractere, mas ainda armazena o índice da linha. Não atribua uma claim inline a um bloco de metadados só por ter palavras semelhantes.

PASSO 3 — CORRIGIR EVIDÊNCIA DOS NOVOS CAMINHOS

A V2 extrai tabelas ANTES de atualizar _EVIDENCE_STORE para o corpus atual. Reproduzido:
- chamada anterior contém SNAPSHOT_ANTERIOR para a URL do pacote;
- chamada atual contém SNAPSHOT_ATUAL para a mesma URL;
- a claim atual da tabela recebe SNAPSHOT_ANTERIOR.

Inicialize o contexto de evidências da chamada antes de qualquer seleção. Não reaproveite texto de outra extração. A saída de uma chamada deve depender de seu relatório/corpus, não da ordem dos testes.

Além disso, os caminhos de título factual, metadados e divisão de parágrafo criam claims com anchors/evidence vazios e não passam pelo seletor já validado, mesmo havendo evidência pertinente. Passe as claims produzidas pelos caminhos novos pela mesma seleção validada, preservando sujeitos, citações, prioridade explícita de URLs e janelas de transcrição. Não reescreva o ranking para corrigir a inicialização ou acrescentar evidência aos caminhos novos.

PASSO 4 — CORRIGIR LEDGER E RESULTADO

1. IDs estáveis foram corrigidos, mas a seleção usa cid < max_claims depois de ordenar por prioridade. Isso diverge do slice real. Exemplo de duas claims:
   id 0: opencode-low usa MIT
   id 1: opencode-high é gratuito e usa MIT
   max_claims=1 retorna id 1, enquanto o ledger marca id 0 como selected e id 1 como deferred_by_cap.
   Defina os estados pelo conjunto efetivamente selecionado após ordenação, mantendo os IDs estáveis. Atualize o registro sem duplicar vínculos nos blocos.

2. A cobertura retorna coverage_complete=True com claims_incomplete=1. Inclua a extração incompleta na condição de completude, além dos adiamentos. Preserve accepted=False nesses casos. Não envie uma representação truncada como se fosse o fato integral revisado; diferencie tentativa de extração e julgamento concluído.

3. review_report obtém coverage antes da revisão e altera os dicionários depois. O objeto retornado mostra estados atualizados nas claims, mas claims_reviewed=0 mesmo com uma claim julgada. Gere o snapshot final depois de atualizar os estados; faça contagens coerentes e distinguíveis para tentativas, julgamentos concluídos e falhas. Preserve a cobertura também no retorno de falha técnica.

4. Duas afirmações idênticas continuam selected e duplicate_of=None. Implemente deduplicação rastreável, apontando a duplicata para a original. Não reutilize a variável seen da seleção de URLs para a deduplicação de claims.

PASSO 5 — CHECKLIST E TESTES

Execute o teste independente até os controles passarem com a implementação real. Não altere suas expectativas para considerar suficiente achar o nome de um pacote, ignorar a origem ou aceitar evidência de outra chamada.

Fortaleça scripts/test_semantic_coverage.py onde as asserções atuais são insuficientes:
- A ainda aceita os campos todos dentro do valor de tag e não verifica valores/HEAD separados;
- F promete checar origem, mas usa if bid in cov['blocks'] quando blocks é uma lista de dicionários; o corpo dessa checagem não executa;
- G confunde IDs com posições no limite, não verifica duplicatas e consulta o registro global para contornar contagens antigas no resultado;
- H só exige pelo menos um bloco com claim_ids e imprime totais, sem verificar os cinco blocos conhecidos nem as tabelas.

No relatório congelado, apresente checklist verificável por pacote/campo e fatos das tabelas, com sujeito, valor, ID e origem. As listas conhecidas devem ser recuperadas. Outras limitações devem ser registradas como incompletas e bloquear a aprovação, sem afirmar recall semântico universal.

Execute também as três suítes anteriores. Preserve a política de quórum e falhas do auditor e o controle positivo; não resolva os defeitos bloqueando tudo indiscriminadamente.

ENTREGA E PARADA

Gere artefato V3 sem sobrescrever os anteriores, com hash do escopo correto, ledger coerente, checklist e limitação explícita. Qualquer revisão com julgamentos simulados deve continuar rotulada como simulada; não equivale a aprovação semântica real.

Envie um ZIP novo com:
- arquivos completos de produção alterados;
- testes independentes e testes alterados;
- artefato e checklist;
- comandos, saídas literais e códigos de saída dos testes;
- SHA256SUMS dos arquivos.

O ZIP V2 não continha os logs de execução prometidos. Na V3 inclua as saídas, além de um resumo.

Concluir somente quando os controles independentes e anteriores passarem, os cinco blocos reais tiverem os campos recuperados com origem correta, e nenhum resultado indicar cobertura completa enquanto registra extração incompleta ou evidência de outra chamada.
```
