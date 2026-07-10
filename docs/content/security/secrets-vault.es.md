---
title: Secrets Vault
weight: 3
---

Las API keys, tokens SSH y otras credenciales sensibles se guardan en una bóveda compatible con el formato **KeePassXC** (`.kdbx`, AES-256) — no en texto plano, ni solo enmascaradas en la UI.

## Estructura

```text
~/.vectora/secrets/
├── system.kdbx           # bóveda del sistema
└── users/{user_id}.kdbx  # una bóveda por usuario
```

## Clave maestra

Derivada vía **PBKDF2-SHA256** (200,000 iteraciones) a partir de la contraseña de login del usuario — no hay una contraseña maestra separada que recordar; la bóveda se desbloquea junto con el login.

## Compatibilidad

Como el formato es el estándar de KeePassXC, puedes auditar la bóveda offline con cualquier cliente compatible: KeePassXC (escritorio), KeePass2Android, Strongbox (iOS).

## Qué no está cifrado

El contenido de las conversaciones en sí (historial del chat) se guarda en **texto plano** en el checkpointer de SQLite — la bóveda protege credenciales, no el contenido de los mensajes. Ver [BYOK & Privacy](../byok-privacy) para el modelo de amenazas completo.
