---
title: Using Settings
weight: 3
---

Everything you configure through the UI lives in three separate dialogs, each with a clear purpose.

## Preferences

Personal settings, for your user.

- **General** — theme (system/light/dark/preset/custom), language, custom system prompt, model fallback order, and custom colors (background, foreground, card, border, primary, accent, muted, sidebar, user bubble color).
- **Memory** — list of persistent memories (key-value pairs). Add, edit inline, delete one or clear all, with a last-updated timeline.
- **Account** — name (editable), email (read-only), role (root/admin/member/viewer).

## Environment

Integration and extensibility settings.

- **Envs** — per-user environment variables (masked in the UI, never exposed in plain text), overriding the system env just for you.
- **Skills** — the agent's skill manager. Install via git URL or local path, check each skill's health, remove. Each skill is a folder with a `SKILL.md` loaded on demand by the deep-agent.
- **Plugins** — external MCP servers configured by the user. Supports `stdio` (command + args), `sse`, and `http` transports. Includes a **Tool Policy** panel to control which tools from that server are enabled.
- **Integrations** — connection cards for external services: manual API key (e.g., some third-party service) or OAuth (GitHub, GitLab, Google, Slack). Shows connected/disconnected status and the webhook URL when applicable.

## Administration (root/admin)

Instance-wide settings — only visible to administrators.

- **Users** — list with role, created at, last login. Change role, delete a user. **Invites** section: create an invite (role + optional email + 1–720h TTL), copy URL, revoke pending invites.
- **Tools** — list of global tools by category, with an enable/disable toggle per tool.
- **Safe Folders** — a whitelist of paths that require extra approval even after being trusted.
- **System** — backend version, Python version, platform, status of each service, recent observability span count.
- **Configuration** — `allow_public_signup`, the instance's default model, agent max recursion depth, database DSN (read-only), integration token.

## See also

- [Security: Authentication and RBAC](../../security/authentication)
- [MCP server](../../reference/mcp-server) — how the Environment tab's MCP plugins connect
