import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { registry } from "../../src/registry/routes";

describe("GET /registry/mcp", () => {
  it("returns the seeded mcp_catalog entries (D1 real, migrations/0001_schema.sql)", async () => {
    const res = await registry.request("/mcp", {}, env);
    expect(res.status).toBe(200);
    const body = await res.json<{ entries: Array<{ id: string }> }>();
    expect(body.entries.map((e) => e.id)).toContain("filesystem");
  });
});

describe("GET /registry/skills", () => {
  it("returns an empty entries array — nenhuma skill curada seedada ainda, não é erro", async () => {
    const res = await registry.request("/skills", {}, env);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ entries: [] });
  });
});

describe("GET /registry/extensions", () => {
  it("returns an empty entries array (fora de escopo — SDK de extensões não existe)", async () => {
    const res = await registry.request("/extensions", {}, env);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ entries: [] });
  });
});
