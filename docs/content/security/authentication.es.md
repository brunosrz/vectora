---
title: Authentication
weight: 1
---

## Contraseñas

Hasheadas vía Argon2id (`argon2-cffi`), el algoritmo de hash de contraseñas recomendado actualmente — no reversible, resistente a ataques con hardware dedicado.

## Sesión

JWT firmado (HS256), con dos tokens:

- **Access token** — de corta duración (15 min).
- **Refresh token** — opaco, 7 días, rotado en cada uso.

Transportado vía una cookie `httpOnly` + `SameSite=Lax` (protegida contra XSS ya que no es accesible desde JavaScript), con un fallback al header `Authorization: Bearer` cuando las cookies no están disponibles (CLI, clientes de API).

## Terminal vía WebSocket

Las cookies `httpOnly` no viajan en conexiones WebSocket cross-origin — por eso la terminal obtiene un token vía `GET /auth/ws-token` y lo pasa en el query string de la conexión, en lugar de depender de la cookie de sesión.

## Rate limiting

`slowapi` aplica límites por IP/usuario/email — por ejemplo, los intentos de login y la API REST `/v1/*` (10/min en el nivel Free, 100/min en Pro).

## Auditoría

Toda acción sensible (registro, login, cambio de contraseña, llamada a herramienta destructiva) se registra en una tabla de auditoría — rastreable por administradores.

## Ver también

- [RBAC](../rbac) — control de acceso basado en roles
- [Bóveda de secretos](../secrets-vault) — dónde se guardan las API keys y credenciales
