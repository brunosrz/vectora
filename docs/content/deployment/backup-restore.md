---
title: Backup & Restore
weight: 4
---

## O que fazer backup

Tudo relevante mora em `~/.vectora/`:

```text
~/.vectora/
├── config.toml
├── auth.key
├── data/               # vectora.db, embedding_queue.db, traces.db, lancedb/
├── artifacts/
├── secrets/            # vaults KeePassXC
├── skills/
├── safe_roots.json
└── workspaces.json
```

Backup simples: compactar `~/.vectora/` inteiro (menos caches, se você tiver identificado algum diretório de cache temporário).

## Modo complete

Se você estiver no modo complete, o backup de dados de RAG/checkpoint/cache fica sob responsabilidade do seu provedor gerenciado (Supabase, Neon, Qdrant Cloud) ou da sua própria rotina de backup de Postgres/Qdrant/Redis — o Vectora não faz backup automático desses serviços externos por você.

## Restaurar

Pare o Vectora, restaure o conteúdo de `~/.vectora/` (ou o backup do banco gerenciado, se aplicável), suba o Vectora de novo. Não há um comando dedicado de "restore" na CLI hoje — é uma operação de arquivo/infra, não uma feature de produto.

## Migração entre modos de storage

Pra mover dados entre lite e complete (não é a mesma coisa que backup/restore), veja os comandos `vectora storage migrate` em [Storage: lite vs. complete](../../concepts/storage).
