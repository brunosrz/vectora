import { env } from "cloudflare:test";
import { describe, expect, it, vi } from "vitest";
import {
  ragLibrary,
  processRagReindex,
  NO_STORAGE_PROVIDER_REASON,
} from "../../src/rag-library/routes";

async function makePackage(status: "ready" | "pending" | "failed" = "ready") {
  const id = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO rag_packages (id, name, source_lib, source_version, size_bytes, checksum, storage_url, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
  )
    .bind(
      id,
      "fastapi-docs",
      "fastapi",
      "0.115.0",
      2048,
      "def456",
      "https://storage.example.com/fastapi-docs.tar.gz",
      status,
    )
    .run();
  return id;
}

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

describe("POST /rag-library/:id/reindex", () => {
  it("marca status=pending e enfileira o job rag_reindex", async () => {
    const id = await makePackage("ready");
    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");

    const res = await ragLibrary.request(
      `/${id}/reindex`,
      { method: "POST" },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true, status: "pending" });
    expect(sendSpy).toHaveBeenCalledExactlyOnceWith({
      type: "rag_reindex",
      packageId: id,
    });

    const row = await env.DB.prepare(
      "SELECT status, status_reason FROM rag_packages WHERE id = ?",
    )
      .bind(id)
      .first<{ status: string; status_reason: string | null }>();
    expect(row).toEqual({ status: "pending", status_reason: null });
  });

  it("404 para pacote inexistente", async () => {
    const res = await ragLibrary.request(
      "/unknown-id/reindex",
      { method: "POST" },
      env,
    );
    expect(res.status).toBe(404);
  });
});

describe("processRagReindex", () => {
  it("marca o pacote como failed com o motivo — sem provedor de storage configurado", async () => {
    const id = await makePackage("pending");

    await processRagReindex(env, id);

    const row = await env.DB.prepare(
      "SELECT status, status_reason FROM rag_packages WHERE id = ?",
    )
      .bind(id)
      .first<{ status: string; status_reason: string | null }>();
    expect(row).toEqual({
      status: "failed",
      status_reason: NO_STORAGE_PROVIDER_REASON,
    });
  });
});
