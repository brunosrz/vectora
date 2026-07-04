import { describe, expect, it, vi } from "vitest";
import { enqueueEmail, enqueueJob } from "../../src/lib/queue";
import type { Env } from "../../src/relay/types";

function fakeEnv(): {
  env: Env;
  emailSend: ReturnType<typeof vi.fn>;
  jobsSend: ReturnType<typeof vi.fn>;
} {
  const emailSend = vi.fn(async () => undefined);
  const jobsSend = vi.fn(async () => undefined);
  const env = {
    EMAIL_QUEUE: { send: emailSend },
    JOBS_QUEUE: { send: jobsSend },
  } as unknown as Env;
  return { env, emailSend, jobsSend };
}

describe("enqueueEmail", () => {
  it("envia a mensagem exatamente como recebida pra EMAIL_QUEUE", async () => {
    const { env, emailSend } = fakeEnv();
    await enqueueEmail(env, {
      to: "user@example.com",
      subject: "Oi",
      html: "<p>Oi</p>",
    });
    expect(emailSend).toHaveBeenCalledExactlyOnceWith({
      to: "user@example.com",
      subject: "Oi",
      html: "<p>Oi</p>",
    });
  });

  it("propaga erro se o .send() da fila falhar", async () => {
    const { env } = fakeEnv();
    (env.EMAIL_QUEUE.send as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("queue down"),
    );
    await expect(
      enqueueEmail(env, { to: "a@b.com", subject: "x", html: "y" }),
    ).rejects.toThrow("queue down");
  });
});

describe("enqueueJob", () => {
  it("envia job do tipo gdpr_delete_user pra JOBS_QUEUE", async () => {
    const { env, jobsSend } = fakeEnv();
    await enqueueJob(env, { type: "gdpr_delete_user", userId: "u1" });
    expect(jobsSend).toHaveBeenCalledExactlyOnceWith({
      type: "gdpr_delete_user",
      userId: "u1",
    });
  });

  it("envia job do tipo update_telemetry pra JOBS_QUEUE", async () => {
    const { env, jobsSend } = fakeEnv();
    await enqueueJob(env, {
      type: "update_telemetry",
      state: "failed",
      version: "1.2.3",
      os: "win32",
      arch: "x64",
    });
    expect(jobsSend).toHaveBeenCalledExactlyOnceWith({
      type: "update_telemetry",
      state: "failed",
      version: "1.2.3",
      os: "win32",
      arch: "x64",
    });
  });

  it("envia job do tipo telemetry_ingest pra JOBS_QUEUE", async () => {
    const { env, jobsSend } = fakeEnv();
    await enqueueJob(env, {
      type: "telemetry_ingest",
      source: "vectora-app",
      eventType: "crash",
      payload: { stack: "..." },
    });
    expect(jobsSend).toHaveBeenCalledExactlyOnceWith({
      type: "telemetry_ingest",
      source: "vectora-app",
      eventType: "crash",
      payload: { stack: "..." },
    });
  });

  it("envia job do tipo rag_reindex pra JOBS_QUEUE", async () => {
    const { env, jobsSend } = fakeEnv();
    await enqueueJob(env, { type: "rag_reindex", packageId: "pkg1" });
    expect(jobsSend).toHaveBeenCalledExactlyOnceWith({
      type: "rag_reindex",
      packageId: "pkg1",
    });
  });

  it("propaga erro se o .send() da fila falhar", async () => {
    const { env } = fakeEnv();
    (env.JOBS_QUEUE.send as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("queue down"),
    );
    await expect(
      enqueueJob(env, { type: "gdpr_delete_user", userId: "u1" }),
    ).rejects.toThrow("queue down");
  });
});
