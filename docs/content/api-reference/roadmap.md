---
title: Roadmap
weight: 5
---

Pra ser transparente sobre o que existe hoje versus o que está planejado:

## ✓ Disponível hoje

- `POST /v1/classify`
- `POST /v1/extract`
- `POST /v1/jobs` + `GET /v1/jobs/{id}/events` (SSE)
- Documentação OpenAPI automática em `/docs` e `/openapi.json`

## 📋 Planejado, não implementado

- **Autenticação dedicada da API** — OAuth2 client credentials pra uso server-to-server (hoje os endpoints `/v1/*` são públicos, diferenciados só por rate limit).
- **Endpoints de chat/documentos/projetos via API** — hoje o chat só é acessível via SSE interno do frontend, MCP, ou CLI; não existe um `/v1/chat` ou `/v1/documents` públicos ainda.
- **SDKs oficiais** — `pip install vectora-sdk` (Python) e `@vectora/sdk` (TypeScript) ainda não existem.
- **Webhooks de saída** (Vectora → sistemas externos) — hoje o Vectora só recebe webhooks de terceiros (GitHub/GitLab/Slack) pra tarefas em segundo plano, não emite os próprios.
- **Compatibilidade com a API da OpenAI** — permitiria apontar SDKs OpenAI existentes pro Vectora; ainda não implementado.

Se você depende de alguma dessas features, [abra uma issue](https://github.com/vectora-company/vectora/issues) ou fale no [suporte](https://vectora.company/support) — isso ajuda a priorizar o roadmap.
