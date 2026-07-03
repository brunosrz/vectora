/**
 * registry/ (Fase F) — "um registry, três catálogos"
 * (documents/extensibility-roadmap.md §5): mcp, skills e extensions são
 * recursos irmãos do mesmo Worker, não três serviços diferentes.
 *
 * Schema por entrada (mesmo pros três, §5): id, name, description, homepage,
 * repo, permissions, signature, vectora_verified, community_score,
 * last_updated — só o payload muda (`tools`/`transport` pra mcp,
 * `required_tools`/frontmatter pra skills, `contributes`/`entrypoints` pra
 * extensions).
 *
 * Os três devolvem lista vazia hoje — virar de verdade um proxy/curadoria
 * (GitHub, awesome-mcp-servers, PR de submissão) é trabalho futuro fora
 * deste escopo. O cliente Vectora já sabe cair pro fallback local
 * (~/.vectora/mcp-registry/index.json) quando o registry remoto está vazio.
 *
 * Fora de escopo aqui (documentado, não implementado): os SDKs de autoria
 * (`vectora_ext` Python, `@vectora/extension-sdk` TS), o Extension Host
 * (backend/frontend) e a CLI `vectora ext` — isso é trabalho de
 * `vectora/backend`/`vectora/frontend`, não deste Worker.
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";

export const registry = new Hono<{ Bindings: Env }>();

registry.get("/mcp", (c) => c.json({ entries: [] }));
registry.get("/skills", (c) => c.json({ entries: [] }));
registry.get("/extensions", (c) => c.json({ entries: [] }));
