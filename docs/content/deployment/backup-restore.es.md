---
title: Backup & Restore
weight: 4
---

## Qué respaldar

Todo lo relevante vive en `~/.vectora/`:

```text
~/.vectora/
├── config.toml
├── auth.key
├── data/               # vectora.db, embedding_queue.db, traces.db, lancedb/
├── artifacts/
├── secrets/            # bóvedas de KeePassXC
├── skills/
├── safe_roots.json
└── workspaces.json
```

Backup simple: archiva todo `~/.vectora/` (menos cachés, si has identificado algún directorio de caché temporal).

## Modo completo

Si estás en modo completo, respaldar los datos de RAG/checkpoint/caché es responsabilidad de tu proveedor gestionado (Supabase, Neon, Qdrant Cloud) o de tu propia rutina de backup de Postgres/Qdrant/Redis — Vectora no respalda automáticamente esos servicios externos por ti.

## Restaurar

Detén Vectora, restaura el contenido de `~/.vectora/` (o el backup de la base de datos gestionada, si aplica), inicia Vectora de nuevo. Hoy no hay un comando de CLI "restore" dedicado — es una operación de archivos/infra, no una función del producto.

## Migrar entre modos de almacenamiento

Para mover datos entre lite y completo (algo distinto a backup/restauración), ver los comandos `vectora storage migrate` en [Almacenamiento: lite vs. completo](../../concepts/storage).
