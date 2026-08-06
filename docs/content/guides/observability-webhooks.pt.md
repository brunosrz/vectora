---
title: Webhooks de Observabilidade
weight: 7
---

A infraestrutura de webhook do Vectora (`backend/api/handlers/webhooks.py`) já vem com suporte nativo a alguns providers (GitHub, GitLab, Slack, Linear, email). Pra ferramentas de alerta e observabilidade — Sentry, Grafana, PagerDuty e o resto desse universo — não existe um parser específico de vendor. Em vez disso, existe um endpoint genérico com um contrato de payload fixo e documentado: aponte o webhook de saída da sua ferramenta pra ele, e ajuste o payload pra bater com o formato abaixo.

Essa é uma escolha deliberada. Um parser dedicado de Sentry/Grafana/PagerDuty precisaria acompanhar o formato de payload de cada vendor conforme evolui; um contrato fixo nunca fica desatualizado, ao custo de você fazer o mapeamento de campos uma vez na configuração de webhook da sua ferramenta de alerta.

## Endpoint

```
POST /webhook/observability
X-Webhook-Secret: <seu secret>
Content-Type: application/json

{
  "title": "Erro 500 em /checkout",
  "description": "NullPointerException no gateway de pagamento",
  "severity": "critical",
  "url": "https://sentry.io/issues/1",
  "external_id": "sentry-1"
}
```

| Campo         | Obrigatório | Notas                                                                 |
|---------------|-------------|------------------------------------------------------------------------|
| `title`       | sim         | Vira o nome do card do Kanban.                                        |
| `external_id` | sim         | Chave de idempotência — um id estável da sua ferramenta de alerta (id do alerta/incidente). Reentrega do mesmo `external_id` atualiza o card existente em vez de criar um duplicado. |
| `description` | não         | Vira o corpo da instrução do card (truncado a 2000 caracteres).       |
| `severity`    | não         | `critical` / `high` / `medium` / `low`. Ver mapeamento abaixo.        |
| `url`         | não         | Link de volta pro alerta na sua ferramenta, guardado no card.         |

Autenticação é um secret estático, não uma assinatura HMAC: configure `OBSERVABILITY_WEBHOOK_SECRET` no backend e mande de volta no header `X-Webhook-Secret` em toda requisição. Um secret ausente ou incorreto devolve `401` antes mesmo do payload ser parseado. Um corpo malformado, ou faltando `title`/`external_id`, devolve `400`.

## Severidade → status do Kanban

O board do Kanban não tem campo de prioridade nativo, então a severidade mapeia pro status inicial do card:

- `critical` / `high` → **triage** (precisa de atenção imediata)
- `medium` / `low` (ou ausente/não reconhecido) → **todo**

Reentrega reavalia a severidade e move o card de acordo — um alerta que começou `critical` e depois reporta `low` num payload seguinte sai do triage.

## Ligando o sync

Igual ao sync de Issues do GitHub → Kanban, isso vem desligado por padrão. Ativa quando existe pelo menos uma tarefa em segundo plano `webhook` habilitada cujo `trigger_config` é `{"provider": "observability"}` — a sessão e o workspace dessa tarefa viram a casa de todo card que o sync cria. Sem essa tarefa, o endpoint continua aceitando e persistindo eventos (então nada se perde enquanto você está configurando), mas nenhum card é criado.

Isso roda inteiramente sem o LLM: é um insert-or-update determinístico contra a mesma tabela `vectora_background_tasks` que o resto do modelo do Kanban usa (`backend/scheduling/background_tasks.py::sync_observability_alert_to_kanban`), o mesmo padrão que o sync de Issues do GitHub (`sync_github_issue_to_kanban`) já estabeleceu.

## Exemplos de configuração por provider

Esses são mapeamentos honestos de melhor esforço — nenhuma dessas ferramentas fala o contrato do Vectora nativamente, então você está traduzindo o payload de webhook de saída delas pro formato acima, tipicamente via o recurso de "payload customizado" ou templating da própria ferramenta onde disponível, ou um relay leve caso contrário.

### Sentry — Alert Rules → Webhook Action

1. **Settings → Alerts → Rules** → edite ou crie uma regra.
2. Adicione uma ação do tipo **"Send a notification via an integration"** → **Webhook**, ou use **Internal Integrations** (**Settings → Developer Settings → Custom Integrations**) pra pegar uma URL de webhook dedicada com mais controle sobre o payload.
3. Aponte a URL do webhook pra `https://<seu-backend>/webhook/observability`.
4. Configure o header `X-Webhook-Secret` com o valor do seu `OBSERVABILITY_WEBHOOK_SECRET` (headers customizados estão disponíveis em Internal Integrations; webhooks simples de Alert Rule podem precisar de um pequeno relay se o seu plano do Sentry não suportar headers customizados).
5. Mapeie os campos do payload do Sentry pros do Vectora: `event.title` → `title`, `event.culprit`/`event.message` → `description`, `event.level` (`fatal`/`error` → `critical`/`high`, `warning` → `medium`, `info`/`debug` → `low`) → `severity`, `url` → `url`, `event.event_id` ou o id da issue → `external_id`.

### Grafana Alerting — Contact Point (Webhook)

1. **Alerting → Contact points → Add contact point**.
2. Tipo de integração: **Webhook**.
3. URL: `https://<seu-backend>/webhook/observability`.
4. Em **Optional Webhook settings**, adicione um header HTTP customizado `X-Webhook-Secret` com seu secret.
5. O payload padrão do Grafana é seu próprio formato JSON (`alerts[]`, `commonLabels`, etc.), não o contrato do Vectora — use um **Custom Payload / message template** se sua versão do Grafana suportar, pra emitir `{title, description, severity, url, external_id}` diretamente, mapeando `alertname`/`summary` → `title`, `description`/`annotations` → `description`, o label `severity` do alerta → `severity`, `generatorURL` → `url`, e `fingerprint` → `external_id` (o fingerprint do Grafana é estável ao longo do ciclo de vida do alerta, exatamente o que a reentrega idempotente precisa).

### PagerDuty — Custom Webhook (Extensions)

1. **Service → Integrations → Add a webhook**, ou **Extensions → Add extension** → **Generic V3 Webhook** no escalation policy/service que você quer encaminhar.
2. URL do webhook: `https://<seu-backend>/webhook/observability`.
3. Os Generic Webhooks do PagerDuty não suportam headers customizados nativamente — a maioria das configurações precisa de um pequeno relay (Cloudflare Worker, Lambda, etc.) que recebe o payload nativo do PagerDuty, adiciona o header `X-Webhook-Secret`, e remolda o corpo pro contrato do Vectora.
4. Mapeamento de campos do payload `incident` do PagerDuty: `incident.title` → `title`, `incident.description` ou os detalhes do evento que disparou → `description`, `incident.urgency` (`high` → `high`, `low` → `low`) ou `incident.priority` → `severity`, `incident.html_url` → `url`, `incident.id` → `external_id`.

## Veja também

- [Automação do Agente](../agent-automation) — agendamento, delegação e os demais gatilhos de tarefa em segundo plano por webhook
- [Usando o Workbench](../using-the-workbench) — a aba Tasks onde os cards sincronizados aparecem
