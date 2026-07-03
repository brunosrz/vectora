import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { ragLibrary } from "../../src/rag-library/routes";

describe("GET /rag-library", () => {
  it("lists the catalog and redirects a known package to its storage URL, 404 for unknown", async () => {
    const id = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO rag_packages (id, name, source_lib, source_version, size_bytes, checksum, storage_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
    )
      .bind(
        id,
        "langchain-docs",
        "langchain",
        "0.3.0",
        1024,
        "abc123",
        "https://storage.example.com/langchain-docs.tar.gz",
      )
      .run();

    const list = await ragLibrary.request("/", {}, env);
    expect(list.status).toBe(200);
    const body = await list.json<Array<{ id: string; name: string }>>();
    expect(body.some((p) => p.id === id)).toBe(true);

    const download = await ragLibrary.request(
      `/${id}/download`,
      { redirect: "manual" },
      env,
    );
    expect(download.status).toBe(302);
    expect(download.headers.get("Location")).toBe(
      "https://storage.example.com/langchain-docs.tar.gz",
    );

    const missing = await ragLibrary.request("/unknown-id/download", {}, env);
    expect(missing.status).toBe(404);
  });
});
