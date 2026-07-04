---
title: Secrets Vault
weight: 3
---

API keys, SSH tokens, and other sensitive credentials are kept in a vault compatible with the **KeePassXC** format (`.kdbx`, AES-256) — not in plain text, and not just masked in the UI.

## Structure

```text
~/.vectora/secrets/
├── system.kdbx           # system vault
└── users/{user_id}.kdbx  # one vault per user
```

## Master key

Derived via **PBKDF2-SHA256** (200,000 iterations) from the user's login password — there's no separate master password to remember; the vault unlocks along with login.

## Compatibility

Since the format is standard KeePassXC, you can audit the vault offline with any compatible client: KeePassXC (desktop), KeePass2Android, Strongbox (iOS).

## What isn't encrypted

Conversation content itself (chat history) is kept in **plaintext** in the SQLite checkpointer — the vault protects credentials, not message content. See [BYOK & Privacy](../byok-privacy) for the full threat model.
