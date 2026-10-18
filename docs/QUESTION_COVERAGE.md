# Cobertura da pergunta (primeiro incremento)

Contrato + estado persistido + integração ao resultado. Sem planejamento
automático, sem ciclos adaptativos, sem novas rodadas de coleta.

## Separação de dimensões

- `semantic_review.py` (intocado): a aprovação diz se o relatório diz o que
  a evidência diz. `coverage_complete` / `dropped_incomplete` de lá são da
  extração de claims — nunca reutilizados aqui.
- `coverage_ledger.py` (novo): diz se tudo que a PERGUNTA pediu foi
  investigado, e onde está a evidência utilizável de cada ponto.
- Aprovação semântica NÃO implica cobertura da pergunta.

## Uso

```bash
python3 gpt_researcher_integration.py "pergunta" light --coverage-plan plan.json
```

Sem `--coverage-plan`: `question_coverage.status="unevaluated"`,
`proportion=null`, sem heurísticas. Com plano: avaliado contra registros
explícitos; o fluxo não mapeia evidência→critério sozinho (insuficiência
preservada, nunca fabricada).

Plano (descreve o trabalho ESPERADO, nunca o cumprimento):

```json
{
  "plan_id": "harbor-2026-10",
  "version": 1,
  "entities": [{"id": "e1", "label": "seção norte", "required": true}],
  "criteria": [{"id": "c1", "label": "período de rotação",
                "required": true, "applies_to": ["e1"]}]
}
```

Qualquer campo tipo `pre_satisfied`/`satisfied`/resultado no plano é
rejeitado (`ValueError`, run nem começa).

Estados por critério: `uninvestigated, insufficient, partial, covered,
contradictory, blocked`. `covered` exige justificativa + origem +
referência(s) a material obtido com qualificação aprovada (não excluída);
`partial` só sustenta seu alcance; falha de acesso → `blocked`
(nunca ausência); conclusão negativa bem sustentada PODE cobrir
(`origin="negative_conclusion"` + refs utilizáveis).

Bloco persistido (`question_coverage` em `*_depth.json` + run dir):

```json
{
  "status": "partial", "complete": false,
  "plan_id": "harbor-2026-10", "plan_version": 1, "run_id": "…",
  "proportion": 0.0,
  "criteria": [{"id": "c1", "state": "partial", "justification": "…",
                "origin": "…", "references": [{"url": "…"}]}],
  "gaps": [{"criterion_id": "c1", "state": "partial"}],
  "observed_counts": {"discovered": 6, "obtained": 6, "qualified": 6,
                      "analyzed": 0, "used": 0, "cited": 1}
}
```

`proportion` = obrigatórios cobertos / todos obrigatórios aplicáveis
(denominador inclui `blocked`/`uninvestigated`). Decisão final de parada
usa essa medição real ou `null` (`flow_end` ≠ prova); os fictícios
`1.0/0.5` foram eliminados. Saída ao usuário: coberta / parcial /
não avaliada + rastreio ao texto auditado.

## Caso 6/1

Seis entidades obrigatórias, uma com material parcial:

- `status="partial"`, `complete=false`, `proportion=0.0`
  (parcial não conta como coberto);
- critério 1 `partial` com justificativa/origem/refs; critérios 2–6
  `uninvestigated`; `gaps` com os 6.

## Limites restantes (NÃO feito aqui)

Planejamento automático do plano, avaliação automática
evidência→critério, ciclos adaptativos novos, validação real no Hermes.
`analyzed`/`used` ficam em 0 até existir essa análise explícita.
