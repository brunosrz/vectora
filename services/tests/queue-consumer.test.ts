import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { handleQueue } from "../src/queue-consumer";
import { hashPassword } from "../src/auth/password";

afterEach(() => {
  vi.unstubAllGlobals();
});

function fakeMessage<T>(body: T) {
  return { body, ack: vi.fn(), retry: vi.fn() };
}

function fakeBatch<T>(queue: string, bodies: T[]) {
  const messages = bodies.map((b) => fakeMessage(b));
  return { queue, messages } as unknown as MessageBatch<unknown>;
}

describe("handleQueue — vectora-email", () => {
  it("chama sendEmail e faz ack quando o Resend responde ok", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const batch = fakeBatch("vectora-email", [
      { to: "a@b.com", subject: "Oi", html: "<p>Oi</p>" },
    ]);
    await handleQueue(batch, env);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    expect(batch.messages[0]!.retry).not.toHaveBeenCalled();
  });

  it("faz retry (não ack) quando o Resend falha", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("bad", { status: 500 })),
    );
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const batch = fakeBatch("vectora-email", [
      { to: "a@b.com", subject: "Oi", html: "<p>Oi</p>" },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.retry).toHaveBeenCalledOnce();
    expect(batch.messages[0]!.ack).not.toHaveBeenCalled();
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("processa cada mensagem do batch de forma independente", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 200 })),
    );

    const batch = fakeBatch("vectora-email", [
      { to: "a@b.com", subject: "1", html: "<p>1</p>" },
      { to: "c@d.com", subject: "2", html: "<p>2</p>" },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    expect(batch.messages[1]!.ack).toHaveBeenCalledOnce();
  });
});

describe("handleQueue — vectora-jobs / gdpr_delete_user", () => {
  it("chama hardDeleteOneUser e deleta o usuário do D1", async () => {
    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
    )
      .bind(userId, `${userId}@example.com`, await hashPassword("x"))
      .run();

    const batch = fakeBatch("vectora-jobs", [
      { type: "gdpr_delete_user", userId },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });
});

describe("handleQueue — vectora-jobs / update_telemetry", () => {
  it("chama processUpdateTelemetry (incrementa o contador no KV)", async () => {
    const batch = fakeBatch("vectora-jobs", [
      {
        type: "update_telemetry",
        state: "completed",
        version: "9.9.9",
        os: "win",
        arch: "x64",
      },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    expect(await env.KV.get("telem:9.9.9:completed")).toBe("1");
  });
});

describe("handleQueue — vectora-jobs / telemetry_ingest", () => {
  it("chama recordTelemetryEvent (grava em telemetry_events)", async () => {
    const batch = fakeBatch("vectora-jobs", [
      {
        type: "telemetry_ingest",
        source: "vectora-app",
        eventType: "crash",
        payload: { stack: "boom" },
      },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    const row = await env.DB.prepare(
      "SELECT source, event_type FROM telemetry_events WHERE source = ? AND event_type = ?",
    )
      .bind("vectora-app", "crash")
      .first();
    expect(row).toMatchObject({ source: "vectora-app", event_type: "crash" });
  });
});

describe("handleQueue — vectora-jobs / rag_reindex", () => {
  it("chama processRagReindex (marca o pacote como failed)", async () => {
    const packageId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO rag_packages (id, name, source_lib, source_version, size_bytes, checksum, storage_url, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
    )
      .bind(packageId, "n", "l", "v", 1, "c", "https://x")
      .run();

    const batch = fakeBatch("vectora-jobs", [
      { type: "rag_reindex", packageId },
    ]);
    await handleQueue(batch, env);

    expect(batch.messages[0]!.ack).toHaveBeenCalledOnce();
    const row = await env.DB.prepare(
      "SELECT status FROM rag_packages WHERE id = ?",
    )
      .bind(packageId)
      .first<{ status: string }>();
    expect(row?.status).toBe("failed");
  });

  it("faz retry (não ack) quando o job lança", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const batch = fakeBatch("vectora-jobs", [
      { type: "rag_reindex", packageId: "unknown-but-query-still-runs" },
    ]);
    // UPDATE em id inexistente não lança no D1 (0 rows afetadas) — força um
    // erro real via DB.prepare quebrado, pra provar que o catch funciona.
    const prepareSpy = vi
      .spyOn(env.DB, "prepare")
      .mockImplementationOnce(() => {
        throw new Error("db down");
      });

    await handleQueue(batch, env);

    expect(batch.messages[0]!.retry).toHaveBeenCalledOnce();
    expect(batch.messages[0]!.ack).not.toHaveBeenCalled();
    expect(errorSpy).toHaveBeenCalled();

    prepareSpy.mockRestore();
    errorSpy.mockRestore();
  });
});
