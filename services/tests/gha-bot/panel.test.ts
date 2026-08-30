import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { ghaBotPanel } from "../../src/gha-bot/panel";

describe("gha-bot panel", () => {
  it("serves the panel HTML shell at GET /", async () => {
    const res = await ghaBotPanel.request("/", {}, env);
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toContain("text/html");
    const html = await res.text();
    expect(html).toContain("Vectora Bot");
    expect(html).toContain("/gha-bot/tokens");
  });
});
