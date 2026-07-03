---
title: Atualizações
weight: 5
---

## Como funciona hoje

O app desktop usa `electron-updater`, verificando por versões novas contra o worker `services.vectora.company` (`GET /updates/:channel/:os/:arch/latest.yml`). O download e a instalação da atualização acontecem automaticamente em segundo plano.

## Quarentena de versões

Se uma versão nova apresentar taxa de crash acima de um limiar numa janela curta (via telemetria de update), o worker move essa versão pra uma lista de quarentena e volta a servir a `previous_stable` pra novos checks — isso não desfaz instalações já feitas, mas contém o alcance do problema pra quem ainda não atualizou.

## Canal de update

Os binários e o manifesto (`latest.yml`, padrão `electron-updater`) ficam em R2, servidos pelas rotas `/updates/*` e `/download/*` do worker — o mesmo worker que cobre auth/billing/licença da company.

## Roadmap: changelog + aprovação manual + rollback

Um fluxo mais explícito (ver changelog antes de baixar, aprovar manualmente a instalação, backup automático antes de aplicar, rollback real pra versão anterior) está desenhado mas **ainda não implementado** — o comportamento atual é auto-update sem changelog visível nem aprovação manual. Isso é roadmap, não recurso disponível hoje.

## No desenvolvimento a partir do código-fonte

Rodando via `uv run vectora start`, não há auto-update — você atualiza com `git pull` + `uv sync` normalmente.
