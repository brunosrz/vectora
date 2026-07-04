import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { issues } from "../../src/issues/routes";

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockResendFetch() {
  return vi.fn(async () => new Response(JSON.stringify({})));
}

describe("POST /issues", () => {
  it("creates an issue and lists it publicly without exposing the reporter email", async () => {
    vi.stubGlobal("fetch", mockResendFetch());

    const res = await issues.request(
      "/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Crash on startup",
          category: "bug",
          description: "It crashes",
          email: "reporter@example.com",
          turnstileToken: "test-token",
        }),
      },
      env,
    );
    expect(res.status).toBe(200);

    const list = await issues.request("/", {}, env);
    const body = await list.json<Array<Record<string, unknown>>>();
    expect(body.some((i) => i.title === "Crash on startup")).toBe(true);
    expect(body.every((i) => !("email" in i))).toBe(true);
  });

  it("rejects a too-short title, an invalid category, and a missing turnstile token", async () => {
    const base = { turnstileToken: "test-token" };
    const tooShort = await issues.request(
      "/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...base, title: "ab", category: "bug" }),
      },
      env,
    );
    expect(tooShort.status).toBe(400);

    const badCategory = await issues.request(
      "/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...base,
          title: "Valid title",
          category: "nope",
        }),
      },
      env,
    );
    expect(badCategory.status).toBe(400);

    const noTurnstile = await issues.request(
      "/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Valid title", category: "bug" }),
      },
      env,
    );
    expect(noTurnstile.status).toBe(400);
  });

  it("rejects a failed turnstile verification", async () => {
    const customEnv = { ...env, TURNSTILE_SECRET_KEY: "test-secret" };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ success: false }))),
    );

    const res = await issues.request(
      "/",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Valid title",
          category: "bug",
          turnstileToken: "bad-token",
        }),
      },
      customEnv as never,
    );
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "turnstile_failed" });
  });
});

describe("POST /issues/waitlist", () => {
  it("is idempotent for a duplicate email", async () => {
    vi.stubGlobal("fetch", mockResendFetch());
    const emailAddr = `${crypto.randomUUID()}@example.com`;
    const body = { email: emailAddr, turnstileToken: "test-token" };
    const first = await issues.request(
      "/waitlist",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      env,
    );
    expect(first.status).toBe(200);

    const second = await issues.request(
      "/waitlist",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      env,
    );
    expect(second.status).toBe(200);

    const row = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM waitlist WHERE email = ?",
    )
      .bind(emailAddr)
      .first<{ count: number }>();
    expect(row?.count).toBe(1);
  });

  it("rejects an invalid email and a missing turnstile token", async () => {
    const res = await issues.request(
      "/waitlist",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "not-an-email",
          turnstileToken: "test-token",
        }),
      },
      env,
    );
    expect(res.status).toBe(400);

    const noTurnstile = await issues.request(
      "/waitlist",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "a@b.com" }),
      },
      env,
    );
    expect(noTurnstile.status).toBe(400);
  });

  it("rejects a failed turnstile verification", async () => {
    const customEnv = { ...env, TURNSTILE_SECRET_KEY: "test-secret" };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ success: false }))),
    );

    const res = await issues.request(
      "/waitlist",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "a@b.com", turnstileToken: "bad" }),
      },
      customEnv as never,
    );
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "turnstile_failed" });
  });
});
