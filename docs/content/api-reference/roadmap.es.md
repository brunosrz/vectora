---
title: Roadmap
weight: 5
---

Para ser transparentes sobre qué existe hoy versus qué está planeado:

## ✓ Disponible hoy

- `POST /v1/classify`
- `POST /v1/extract`
- `POST /v1/jobs` + `GET /v1/jobs/{id}/events` (SSE)
- Documentación automática de OpenAPI en `/docs` y `/openapi.json`

## 📋 Planeado, no implementado

- **Autenticación dedicada de API** — client credentials OAuth2 para uso servidor-a-servidor (hoy los endpoints `/v1/*` son públicos, diferenciados solo por límite de tasa).
- **Endpoints de chat/documentos/proyectos vía API** — hoy el chat solo es accesible vía el SSE interno del frontend, MCP, o la CLI; todavía no hay un `/v1/chat` o `/v1/documents` público.
- **SDKs oficiales** — `pip install vectora-sdk` (Python) y `@vectora/sdk` (TypeScript) todavía no existen.
- **Webhooks salientes** (Vectora → sistemas externos) — hoy Vectora solo recibe webhooks de terceros (GitHub/GitLab/Slack) para tareas en segundo plano, no emite los suyos propios.
- **Compatibilidad con la API de OpenAI** — permitiría que SDKs de OpenAI existentes apunten a Vectora; aún no implementado.

Si dependes de alguna de estas funciones, [abre un issue](https://github.com/vectora-company/vectora/issues) o contáctanos vía [soporte](https://vectora.company/support) — ayuda a priorizar el roadmap.
