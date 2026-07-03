---
title: Vault de Secrets
weight: 3
---

Chaves de API, tokens SSH e outras credenciais sensíveis ficam guardadas num vault compatível com o formato **KeePassXC** (`.kdbx`, AES-256) — não em texto puro, e não só mascaradas na UI.

## Estrutura

```text
~/.vectora/secrets/
├── system.kdbx           # vault do sistema
└── users/{user_id}.kdbx  # um vault por usuário
```

## Chave mestra

Derivada via **PBKDF2-SHA256** (200 mil iterações) a partir da senha de login do usuário — não existe uma senha mestra separada pra lembrar; o vault destrava junto com o login.

## Compatibilidade

Como o formato é KeePassXC padrão, dá pra auditar o vault offline com qualquer cliente compatível: KeePassXC (desktop), KeePass2Android, Strongbox (iOS).

## O que não é criptografado

O conteúdo de conversas em si (histórico de chat) fica em **claro** no checkpointer SQLite — o vault protege credenciais, não o conteúdo das mensagens. Veja [BYOK & Privacidade](../byok-privacy) pro modelo de ameaça completo.
