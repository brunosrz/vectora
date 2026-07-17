import { env } from "cloudflare:test";
import { beforeAll } from "vitest";
// @ts-expect-error — Vite `?raw` import, resolvido em build/test time (esbuild).
import schemaSql from "../migrations/0001_schema.sql?raw";

// Guarda de rede hermética. O `queueConsumers: ["vectora-email"]` do
// vitest.config faz o miniflare ENTREGAR de verdade os emails enfileirados
// (signup, gift, reset de senha…) ao `handleQueue`, que chama `sendEmail` →
// `fetch` real pra api.resend.com com a key fake (`test-resend-key`) → 401
// "API key is invalid" barulhento no stderr, chamada de rede real e teste
// não-hermético. Intercepta só o host do Resend com um 200 benigno; todo o
// resto passa direto. Testes que precisam controlar a resposta do Resend
// (queue-consumer.test.ts) sobrescrevem via `vi.stubGlobal("fetch", …)` e o
// `unstubAllGlobals` do afterEach restaura para esta guarda.
const _realFetch: typeof fetch = globalThis.fetch;
globalThis.fetch = function guardedFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const url =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  if (url.startsWith("https://api.resend.com")) {
    return Promise.resolve(new Response(null, { status: 200 }));
  }
  return _realFetch(input, init);
} as typeof fetch;

async function applyMigration(sql: string): Promise<void> {
  const withoutComments = sql
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n");
  const statements = withoutComments
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean);
  for (const statement of statements) {
    await env.DB.prepare(statement).run();
  }
}

beforeAll(async () => {
  await applyMigration(schemaSql as string);
});
