import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { registry } from "./routes";

describe("GET /registry/mcp", () => {
  it("returns an empty entries array (no aggregator yet)", async () => {
    const res = await registry.request("/mcp", {}, env);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ entries: [] });
  });
});
