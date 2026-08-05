---
title: Integração Self-Hosted (API Interna)
weight: 6
---

Esta página documenta a **API interna** do Vectora — o mesmo conjunto de endpoints que o próprio frontend chama contra a sua instância self-hosted.

É real, funciona, e é o que move o chat, o RAG, os gateways e os settings. Mas **não é um contrato público estável** — a forma dos endpoints pode mudar entre releases sem aviso de depreciação, como qualquer API interna de frontend. Use pra seus próprios scripts, dashboards ou automações contra a *sua própria* instância do Vectora, não pra construir um produto que roda em servidor de terceiros.

## Autenticação

Duas formas de autenticar, ambas aceitas por todo endpoint abaixo (dependency `get_current_user`, `backend/api/middleware/auth.py`):

1. **Cookie** — o que o frontend usa. `POST /auth/signin` seta um cookie httpOnly `vectora_access`; toda requisição seguinte da mesma sessão do navegador é autenticada automaticamente.
2. **Bearer token** — o que você quer pra scripts. `POST /auth/signin` também devolve `access_token`/`refresh_token` no corpo da resposta; envie como `Authorization: Bearer <access_token>` em cada requisição.

```bash
# Faz login, captura o access token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .access_token)

# Usa em qualquer endpoint abaixo
curl -s http://localhost:8080/auth/me -H "Authorization: Bearer $TOKEN"
```

Access tokens expiram; chame `POST /auth/refresh` com o `refresh_token` pra pegar um par novo sem pedir a senha de novo.

## Schema completo: use o Swagger UI

Esta página dá 1-2 exemplos por área — pra forma exata de request/response de cada campo, a fonte de verdade é a spec OpenAPI auto-gerada, servida pela própria instância:

```text
GET /docs           # Swagger UI interativo — testa requests direto do navegador
GET /openapi.json   # spec crua, pra gerar um cliente
```

## Por área

### `/auth/*` — contas, settings, envs

- `POST /auth/signin` / `POST /auth/signup` — ver acima.
- `GET /auth/me` — perfil do usuário atual.
- `GET /auth/envs` / `POST /auth/envs` / `DELETE /auth/envs/{key}` — ler/escrever settings baseados em variável de ambiente (API keys, config de provider) que ainda não têm endpoint dedicado.

### `/chat/*` — chat em streaming (SSE)

O chat não vive num path plano `/chat` — é `POST /vectora.chat.v1.ChatService/StreamChat`, que devolve um stream de Server-Sent Events (cada evento é um pacote JSON tipado: deltas de token, tool calls, metadata da thread). Deixe `thread_id` vazio pra começar uma conversa nova; o primeiro evento do stream traz o `thread_id` gerado pra reusar na próxima chamada.

```bash
curl -N -X POST http://localhost:8080/vectora.chat.v1.ChatService/StreamChat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"","message":"hello","config":{"chat_mode":true}}'
```

### `/rag/*` — settings de retrieval e coleções

- `GET /rag/settings` / `PATCH /rag/settings` — reranker on/off + top_k, provider de embedding/rerank (`auto`/`cohere`/`voyage`/`ollama`/`openrouter`), tipos de arquivo a ingerir.
- `GET /rag/collections` / `DELETE /rag/collections/{name}` — listar/apagar coleções indexadas.
- `POST /rag/search` — retrieval direto, o mesmo `vector_search` que o agente usa internamente.

### `/gateways/*` — Ollama e OpenRouter

- `GET /gateways/ollama/models` — descobre modelos instalados no host de Ollama configurado (`{OLLAMA_BASE_URL}/api/tags`); `reachable: false` se o host estiver fora do ar, nunca um 500.
- `GET /gateways/openrouter/models?q=` — busca no catálogo público da OpenRouter (cacheado ~1h no backend).
- `POST /gateways/{ollama,openrouter}/registered` — registra um modelo descoberto pra ele aparecer em `GET /models/providers`.

### `/models/providers` — o catálogo agregado de modelos

Combina o catálogo estático de providers (Gemini, OpenAI, Anthropic, Cohere) com o que você registrou via os gateways acima — é isso que alimenta o seletor de modelo na UI do chat.
