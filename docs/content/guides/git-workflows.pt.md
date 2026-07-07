---
title: Workflows de Git
weight: 4
---

O subagente `coder` tem 14 operações de git nativas, disponíveis tanto no chat (linguagem natural) quanto na aba **Diff (Git)** da workbench (UI direta).

## No chat

Peça em linguagem natural:

```text
Faça commit dessas mudanças com uma mensagem descritiva
```

```text
Cria uma branch nova a partir da main e me dá checkout nela
```

Commits e pushes são ações destrutivas — passam pelo HITL a menos que o modo de permissão ativo seja "Autônomo". Veja [Orchestrator & Subagentes](../../concepts/sub-agents).

## Na workbench

A aba **Diff (Git)** tem duas visões:

- **Mudanças** — arquivos modificados/staged/untracked com diff inline; stage/unstage por arquivo ou por hunk.
- **Histórico** — log de commits; clique num commit mostra o diff completo daquele commit.

Modais dedicados cobrem **Stash** (guardar mudanças temporariamente), **Worktrees** (múltiplas branches checked out em paralelo) e **criação de PR** (via `gh` CLI, se disponível no sistema).

## Pré-requisito

O workspace precisa estar **confiável** (veja [Primeiro workspace](../../getting-started/first-workspace)) — operações git que alteram estado não rodam em workspace não confiável.

## `gh` CLI

Operações de GitHub (criar PR, comentar issue, revisar) usam o `gh` CLI instalado no seu sistema, reaproveitando a autenticação que você já tem (`gh auth login`) — o Vectora não pede token do GitHub separado.
