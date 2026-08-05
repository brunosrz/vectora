---
title: Integración Self-Hosted (API Interna)
weight: 6
---

Esta página documenta la **API interna** de Vectora — el mismo conjunto de endpoints que el frontend de Vectora usa contra tu propia instancia self-hosted.

Es real, funciona, y es lo que impulsa el chat, el RAG, los gateways y los settings. Pero **no es un contrato público estable** — la forma de los endpoints puede cambiar entre releases sin aviso de deprecación, como pasa con cualquier API interna de frontend. Úsala para tus propios scripts, dashboards o automatizaciones contra *tu propia* instancia de Vectora, no para construir un producto que corre en servidores de terceros.

## Autenticación

Dos formas de autenticarse, ambas aceptadas por cada endpoint de abajo (dependencia `get_current_user`, `backend/api/middleware/auth.py`):

1. **Cookie** — lo que usa el frontend. `POST /auth/signin` setea una cookie httpOnly `vectora_access`; cada request siguiente desde la misma sesión del navegador se autentica automáticamente.
2. **Bearer token** — lo que quieres para scripts. `POST /auth/signin` también devuelve `access_token`/`refresh_token` en el body de la respuesta; envíalo como `Authorization: Bearer <access_token>` en cada request.

```bash
# Inicia sesión, captura el access token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .access_token)

# Úsalo en cualquier endpoint de abajo
curl -s http://localhost:8080/auth/me -H "Authorization: Bearer $TOKEN"
```

Los access tokens expiran; llama a `POST /auth/refresh` con el `refresh_token` para obtener un par nuevo sin pedir la contraseña otra vez.

## Schema completo: usa el Swagger UI

Esta página da 1-2 ejemplos por área — para la forma exacta de request/response de cada campo, la fuente de verdad es el spec OpenAPI generado automáticamente, servido por la propia instancia:

```text
GET /docs           # Swagger UI interactivo — prueba requests desde el navegador
GET /openapi.json   # spec crudo, para generar un cliente
```

## Por área

### `/auth/*` — cuentas, settings, envs

- `POST /auth/signin` / `POST /auth/signup` — ver arriba.
- `GET /auth/me` — perfil del usuario actual.
- `GET /auth/envs` / `POST /auth/envs` / `DELETE /auth/envs/{key}` — leer/escribir settings respaldados por variables de entorno (API keys, config de provider) que todavía no tienen un endpoint dedicado.

### `/chat/*` — chat en streaming (SSE)

El chat no vive en un path plano `/chat` — es `POST /vectora.chat.v1.ChatService/StreamChat`, que devuelve un stream de Server-Sent Events (cada evento es un paquete JSON tipado: deltas de tokens, tool calls, metadata del thread). Deja `thread_id` vacío para empezar una conversación nueva; el primer evento del stream trae el `thread_id` generado para reusar en la próxima llamada.

```bash
curl -N -X POST http://localhost:8080/vectora.chat.v1.ChatService/StreamChat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"","message":"hello","config":{"chat_mode":true}}'
```

### `/rag/*` — settings de retrieval y colecciones

- `GET /rag/settings` / `PATCH /rag/settings` — reranker on/off + top_k, provider de embedding/rerank (`auto`/`cohere`/`voyage`/`ollama`/`openrouter`), tipos de archivo a ingerir.
- `GET /rag/collections` / `DELETE /rag/collections/{name}` — listar/borrar colecciones indexadas.
- `POST /rag/search` — retrieval directo, el mismo `vector_search` que usa el agente internamente.

### `/gateways/*` — Ollama y OpenRouter

- `GET /gateways/ollama/models` — descubre modelos instalados en el host de Ollama configurado (`{OLLAMA_BASE_URL}/api/tags`); `reachable: false` si el host está caído, nunca un 500.
- `GET /gateways/openrouter/models?q=` — busca en el catálogo público de OpenRouter (cacheado ~1h del lado del servidor).
- `POST /gateways/{ollama,openrouter}/registered` — registra un modelo descubierto para que aparezca en `GET /models/providers`.

### `/models/providers` — el catálogo agregado de modelos

Combina el catálogo estático de providers (Gemini, OpenAI, Anthropic, Cohere) con lo que hayas registrado vía los gateways de arriba — esto alimenta el selector de modelo en la UI del chat.
