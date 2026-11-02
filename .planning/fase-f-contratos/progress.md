
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
