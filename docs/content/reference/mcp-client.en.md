---
title: MCP Client
weight: 5
---

Vectora connects to third-party MCP servers as a client — it does not expose itself as an MCP server to other harnesses. Configure connectors in **Settings → Environment → Plugins**, with support for `stdio`, `sse`, and `http` transports.

## Installing a connector

The workbench **Library** tab lists a curated MCP connector marketplace — install/uninstall right there, or register a custom MCP server manually in **Settings → Environment → Plugins**.

## How the agent uses it

Once a connector is installed, the agent can discover and call its tools directly in the conversation — subject to the same permission mode and approval prompts that protect any other chat action.

See [Using settings](../../guides/using-settings) for per-workspace configuration details.
