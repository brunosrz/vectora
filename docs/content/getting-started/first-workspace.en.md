---
title: First Workspace
weight: 5
---

A **workspace** is a folder on your filesystem registered in Vectora. It's the unit around which the agent organizes context: RAG, Context Graph, git, terminal, and the file editor all operate within the active workspace.

## Add a workspace

In the workspace selector (top of chat), choose "Add workspace" and point to a local folder. There's no limit on registered workspaces — switch between them any time without losing conversation history.

## Trusting a folder

By default, a newly added workspace is **untrusted**: the agent can read files, but **cannot** write, run terminal commands, or execute git. This exists to prevent the agent from running arbitrary commands in a folder you only meant to browse.

Click "Trust this folder" to unlock:

- File writes (`file_write`, `file_edit`)
- Terminal (real PTY)
- State-changing git operations (commit, push, checkout)

Trust is per-folder, not global — opening a new folder always starts untrusted.

## Safe folders (admin)

Administrators can configure a list of **safe folders** in **Settings → Administration → Safe Folders** — paths that require extra approval even after being trusted, useful for protecting sensitive directories on a shared server.

## Git

If the folder is already a git repository, Vectora detects it automatically and enables the **Diff (Git)** tab in the workbench. If not, you can ask the agent to run `git init`, or do it yourself before trusting the folder.

## `.vectoraignore`

A `.vectoraignore` file at the workspace root (same syntax as `.gitignore`) hides paths from all of Vectora — RAG, Context Graph, filesystem, and chat. Use it to exclude `node_modules/`, build output, secrets, etc.

## Next step

→ [Using the chat](../../guides/using-the-chat)
