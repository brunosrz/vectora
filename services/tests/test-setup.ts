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
});
