
## 2026-11-02 — 4 contratos + revisão, rumo ao aceite
- Fixer entregou C1–C4 TDD (19 testes RED→GREEN) + migração de 52 arquivos de teste.
- Revisão independente: 4🔴 confirmados e corrigidos (fallback sem dominância removido;
  targets[0]→global-first; explicit+quality; veto por frase), 6🟡 aceitos, resto documentado.
- Removido _promote_discovery_news (órfão do gate antigo, sem chamadores/testes).
- Suite 687 OK / 10 skips EXIT 0.

## 2026-11-02 — accept36 diagnosticado (plano colapsado) + fix do prompt
- accept36: freeze OK (HEAD/hashes iguais, 8082 +13363/+143). Stop rounds=3, 0.0, 15 lacunas.
- Causa: v1 com 1/15 per_candidate (accept34/35 v1: 10/15); descoberta estendeu só c2 → 5 células → hook nunca adotou. C1/descriptions OK (15/15).
- Fix: exemplo com 2 formas + regra anti-rebaixamento; `_collapsed_per_candidate_warning` observável. Testes novos 3/3; suite 690 OK/10 skips. Commit f09e4ed.
- accept36 preservado como parcial honesto, invalidado p/ aceite (defeito de plano).

## 2026-11-02 — higiene do renderer + revisão + accept38
- Lane hygiene (G1/G2) + revisão independente (5🟡1❓ triados: idem+chave normalizada aplicados; demais documentados).
- Suite 695 OK/10 skips. Commit 5b7e973. accept37 preservado (report com vazamentos = pré-higiene).

## 2026-11-02 — fixes accept38 + aceite accept39 lançado
- 3 fixes (placeholder [(fonte)], lookup barra-final, detector hifen-consciente) TDD 11 testes; revisão 2🔴+1🟡 triada (bare-trail corrigido direto; compound-refutado revertido; fail-open aceito).
- Suite 708 OK/10 skips EXIT 0. Commit 29a44b6. Congelamento accept39 (HEAD 29a44b6, 13 módulos, 8082 pré 200419/3994).
- Run accept39 em background (sh_19b7b771b001mVg2qzqQaUt3ED): mesma pergunta + premissa 2.1.4. Aguardar notificação.

## 2026-11-02 — higiene + 4 achados + C3, aceite accept41
- Revisão ses_e64568cab (0🔴 4🟡, todos confirmados) → lane fixer (RED 7→GREEN 8, suite 733 OK/10 skips).
- Diff próprio verificado (genérico, sem literais); suite re-executada pelo controlador: 733 OK EXIT 0.
- Demo C3 honesta: reais inertes + par mínimo até Markdown real (valid-fase-f/c3-substitution/).
- Commit 934f373. accept36/37/38/39/40 preservados.

## 2026-11-02 — demo C3 + revisão + fixes + accept41 lançado
- Demo C3 honesta (offline, valid-fase-f/c3-substitution/): reais accept40 NÃO disparam troca (política inerte, correto); par mínimo Alpha/Beta dispara _maybe_substitute→_do_substitute+render reais com triple no Markdown (plan_version type=substitution + substitutions + motivo §8). Originais intactos (sha).
- Revisão ses_e64568cab (0🔴 4🟡); lane ses_e6455c641 corrigiu os 4 (RED 7→GREEN 8); suite 733 OK/10 skips.
- Commit 934f373; congelamento accept41 (HEAD 934f373, 8082 pré 235087/4368, opencode v2.2.5); run accept41 em background (sh_19bacf859001d5IZlbKQtXPpQB), mesma pergunta + premissa 2.1.4.
- Não tocar produto até o run concluir.

## 2026-11-02 — aceite accept41 + entrega
- accept41 EXIT=0 sobre 934f373 (hashes iguais, 8082 com efeito). 2/41 partial; support ok; 15 lacunas; stop rounds=6.
- Relatório lido como usuário (792 linhas); corpo limpo; URLs ok (unknown=[]).
- Técnico em docs/RELATORIO_TECNICO_MISSAO_FASE_F.md; CONTINUIDADE atualizada.
- [x] Aceite sobre código congelado. [x] Relatório técnico + CONTINUIDADE + commits.
