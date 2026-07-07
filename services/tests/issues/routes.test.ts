import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import {
  issues,
  MAX_ISSUE_FILES,
  ISSUE_FILE_LIMITS,
} from "../../src/issues/routes";

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockResendFetch() {
  return vi.fn(async () => new Response(JSON.stringify({})));
}

function issueFormData(files: File[] = []) {
  const form = new FormData();
  form.set("title", "Crash com anexos");
  form.set("category", "bug");
  form.set("description", "Descrição com evidências");
  form.set("turnstileToken", "test-token");
  for (const file of files) form.append("files", file);
  return form;
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

describe("POST /issues — anexos (multipart)", () => {
  it("aceita print + vídeo, grava no R2 e lista as keys sem expor o email", async () => {
    vi.stubGlobal("fetch", mockResendFetch());

    const image = new File([new Uint8Array(1024)], "print.png", {
      type: "image/png",
    });
    const video = new File([new Uint8Array(2048)], "repro.mp4", {
      type: "video/mp4",
    });
    const res = await issues.request(
      "/",
      { method: "POST", body: issueFormData([image, video]) },
      env,
    );
    expect(res.status).toBe(200);

    const list = await issues.request("/", {}, env);
    const body = await list.json<
      Array<{ title: string; files: string[]; email?: string }>
    >();
    const created = body.find((i) => i.title === "Crash com anexos");
    expect(created?.files).toHaveLength(2);
    expect(created?.files[0]).toMatch(/^issues\//);
    expect(created && "email" in created).toBe(false);

    for (const key of created?.files ?? []) {
      const stored = await env.R2.get(key);
      expect(stored).not.toBeNull();
    }

    const served = await issues.request(
      `/files/${created?.files[0]}`,
      {},
      env,
    );
    expect(served.status).toBe(200);
    expect(served.headers.get("Content-Type")).toBe("image/png");
  });

  it("recusa tipo proibido (400), excesso de arquivos (400) e arquivo grande demais (413)", async () => {
    vi.stubGlobal("fetch", mockResendFetch());

    const exe = new File([new Uint8Array(16)], "virus.exe", {
      type: "application/x-msdownload",
    });
    const badType = await issues.request(
      "/",
      { method: "POST", body: issueFormData([exe]) },
      env,
    );
    expect(badType.status).toBe(400);
    expect(await badType.json()).toEqual({ error: "invalid_file_type" });

    const many = Array.from(
      { length: MAX_ISSUE_FILES + 1 },
      (_, i) =>
        new File([new Uint8Array(8)], `p${i}.png`, { type: "image/png" }),
    );
    const tooMany = await issues.request(
      "/",
      { method: "POST", body: issueFormData(many) },
      env,
    );
    expect(tooMany.status).toBe(400);
    expect(await tooMany.json()).toEqual({ error: "too_many_files" });

    const huge = new File(
      [new Uint8Array(ISSUE_FILE_LIMITS["image/png"] + 1)],
      "huge.png",
      { type: "image/png" },
    );
    const tooBig = await issues.request(
      "/",
      { method: "POST", body: issueFormData([huge]) },
      env,
    );
    expect(tooBig.status).toBe(413);
    expect(await tooBig.json()).toEqual({ error: "file_too_large" });
  });

  it("GET /files com key inexistente → 404 (par de erro)", async () => {
    const res = await issues.request(
      "/files/issues/nao-existe/arquivo.png",
      {},
      env,
    );
    expect(res.status).toBe(404);
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
