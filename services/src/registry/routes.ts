/**
 * registry/ (Fase F) — placeholder mínimo do MCP registry centralizado.
 *
 * Schema por entrada (documents/mcp-library.md): id, name, description,
 * homepage, repo, transport, install_command, tools, permissions,
 * signature, vectora_verified, community_score, last_updated.
 *
 * Hoje devolve lista vazia — virar de verdade um proxy pro GitHub (registry
 * oficial + awesome-mcp-servers) é trabalho futuro fora deste escopo. O
 * cliente Vectora já sabe cair pro fallback local
 * (~/.vectora/mcp-registry/index.json) quando o registry remoto está vazio.
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";

export const registry = new Hono<{ Bindings: Env }>();

registry.get("/mcp", (c) => c.json({ entries: [] }));
