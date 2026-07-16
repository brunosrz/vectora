import { env } from "cloudflare:test";
import { beforeAll } from "vitest";
// @ts-expect-error — Vite `?raw` import, resolvido em build/test time (esbuild).
import initSql from "../migrations/0001_init.sql?raw";
// @ts-expect-error — idem.
import telemetryAndRagStatusSql from "../migrations/0002_telemetry_and_rag_status.sql?raw";
// @ts-expect-error — idem.
import rbacBillingSql from "../migrations/0003_rbac_billing.sql?raw";
// @ts-expect-error — idem.
import seedAdminSql from "../migrations/0004_seed_admin.sql?raw";
// @ts-expect-error — idem.
import issueFilesSql from "../migrations/0005_issue_files.sql?raw";
// @ts-expect-error — idem.
import issueResponseSql from "../migrations/0006_issue_response.sql?raw";
// @ts-expect-error — idem.
import issueArchiveSql from "../migrations/0007_issue_archive.sql?raw";

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
  await applyMigration(initSql as string);
  await applyMigration(telemetryAndRagStatusSql as string);
  await applyMigration(rbacBillingSql as string);
  await applyMigration(seedAdminSql as string);
  await applyMigration(issueFilesSql as string);
  await applyMigration(issueResponseSql as string);
  await applyMigration(issueArchiveSql as string);
});
