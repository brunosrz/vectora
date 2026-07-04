---
title: RBAC & Permissions
weight: 2
---

## Roles

| Role     | Description                                                                     |
| -------- | ------------------------------------------------------------------------------- |
| `root`   | the first user signed up on the instance; full access, including Administration |
| `admin`  | manages users, global tools, safe folders, and server configuration             |
| `member` | normal use of chat, workspaces, and the workbench                               |
| `viewer` | read-only access                                                                |

Managed in **Settings → Administration → Users**, with email/link invites and a configurable TTL (1–720h).

## Tool policy (ABAC)

Beyond role, each tool can be enabled/disabled globally (**Settings → Administration → Tools**) or per individual MCP server (**Settings → Environment → Plugins → Tool Policy**) — attribute-based access control, not just role-based.

## Trust folder

Independent of RBAC, each **workspace** has its own trust state — a `member` with normal access still needs to explicitly trust a folder before the agent can write to it or run commands. See [First workspace](../../getting-started/first-workspace).

## Safe folders

Administrators can mark specific paths as **safe folders**, requiring extra approval even after being trusted — useful on shared servers where not every `member` should have unrestricted access to certain directories.

## See also

- [Authentication](../authentication)
- [Using settings](../../guides/using-settings) — the Administration tab in detail
