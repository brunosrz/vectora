---
title: Git Workflows
weight: 4
---

El sub-agente `coder` tiene 14 operaciones git nativas, disponibles tanto en el chat (lenguaje natural) como en la pestaña **Diff (Git)** del workbench (UI directa).

## En el chat

Pide en lenguaje natural:

```text
Haz commit de estos cambios con un mensaje descriptivo
```

```text
Crea una nueva rama desde main y haz checkout
```

Los commits y pushes son acciones destructivas — pasan por HITL a menos que el modo de permiso activo sea "Autónomo". Ver [Orchestrator & Subagents](../../concepts/sub-agents).

## En el workbench

La pestaña **Diff (Git)** tiene dos vistas:

- **Cambios** — archivos modificados/staged/sin seguimiento con diff en línea; stage/unstage por archivo o por hunk.
- **Historial** — log de commits; hacer clic en un commit muestra el diff completo de ese commit.

Modales dedicados cubren **Stash** (guardar cambios temporalmente), **Worktrees** (múltiples ramas en checkout en paralelo) y **creación de PR** (vía la CLI `gh`, si está disponible en el sistema).

## Requisito previo

El workspace necesita estar **confiable** (ver [Primer workspace](../../getting-started/first-workspace)) — las operaciones git que cambian estado no se ejecutan en un workspace sin confianza.

## CLI `gh`

Las operaciones de GitHub (crear un PR, comentar en un issue, revisar) usan la CLI `gh` instalada en tu sistema, reutilizando la autenticación que ya tienes (`gh auth login`) — Vectora no pide un token de GitHub separado.
