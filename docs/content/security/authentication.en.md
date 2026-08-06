---
title: Authentication
weight: 1
---

## Passwords

Hashed via Argon2id (`argon2-cffi`), the current recommended password hashing algorithm — non-reversible, resistant to dedicated hardware attacks.

## Session

Signed JWT (HS256), with two tokens:

- **Access token** — short-lived (15 min).
- **Refresh token** — opaque, 7 days, rotated on each use.

Transported via an `httpOnly` + `SameSite=Lax` cookie (protected against XSS since it's not accessible from JavaScript), with a fallback to the `Authorization: Bearer` header when cookies aren't available (CLI, API clients).

## Terminal over WebSocket

`httpOnly` cookies don't travel over cross-origin WebSocket connections — that's why the terminal obtains a token via `GET /auth/ws-token` and passes it in the connection's query string, instead of relying on the session cookie.

## Rate limiting

`slowapi` applies limits to sensitive `/auth/*` endpoints — sign in, sign up, password change, token refresh — by IP or user, to slow down brute-force attempts.

## Auditing

Every sensitive action (signup, login, password change, destructive tool call) is logged to an audit table — traceable by administrators.

## See also

- [RBAC](../rbac) — role-based access control
- [Secrets vault](../secrets-vault) — where API keys and credentials are kept
