---
title: Autenticação
weight: 1
---

## Senhas

Hash via Argon2id (`argon2-cffi`), o algoritmo recomendado atual pra hashing de senha — não reversível, resistente a ataques de hardware dedicado.

## Sessão

JWT assinado (HS256), com dois tokens:

- **Access token** — vida curta (15 min).
- **Refresh token** — opaco, 7 dias, rotacionado a cada uso.

Transporte via cookie `httpOnly` + `SameSite=Lax` (protegido contra XSS por não ser acessível via JavaScript), com fallback pra header `Authorization: Bearer` quando cookies não estão disponíveis (CLI, clientes de API).

## Terminal via WebSocket

Cookies `httpOnly` não viajam em conexões WebSocket cross-origin — por isso o terminal obtém um token via `GET /auth/ws-token` e passa na query string da conexão, em vez de depender do cookie de sessão.

## Rate limiting

`slowapi` aplica limites aos endpoints sensíveis `/auth/*` — login, cadastro, troca de senha, refresh de token — por IP ou usuário, pra desacelerar tentativas de força bruta.

## Auditoria

Toda ação sensível (signup, login, troca de senha, tool call destrutiva) é registrada numa tabela de audit — rastreável por administradores.

## Veja também

- [RBAC](../rbac) — controle de acesso por papel
- [Vault de secrets](../secrets-vault) — onde chaves de API e credenciais ficam guardadas
