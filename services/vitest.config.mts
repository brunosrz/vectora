import { cloudflarePool, cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

const workerOptions = {
  wrangler: { configPath: "./wrangler.toml" },
  miniflare: {
    bindings: {
      VECTORA_JWT_SECRET: "test-jwt-secret-32-chars-minimum!",
      RELAY_HMAC_SECRET: "test-hmac-secret-32-chars-minimum",
      VECTORA_OAUTH_SECRET: "test-oauth-secret",
      LICENSE_VALIDATE_URL: "https://vectora.company/functions/v1/validate-license",
      // workerd SQLite permanece bloqueado no Windows após o fetch ao DO,
      // impedindo o cleanup do isolated storage. Marca para skip seletivo.
      TEST_IS_WINDOWS: process.platform === "win32" ? "1" : "0",
    },
    kvNamespaces: ["RELAY_METRICS", "KV"],
    r2Buckets: ["R2"],
    durableObjects: {
      RELAY_SESSION: "RelaySession",
    },
  },
};

export default defineConfig({
  // `scripts/` (release.ts) é um CLI Node puro — nunca roda dentro do
  // Worker, só localmente via tsx. Rodar seu teste no pool workerd (isolate
  // sandboxed, sem child_process/fs de verdade) quebra o teardown do
  // miniflare (WebSocket não fecha, "close timed out"). Cada projeto usa o
  // runtime certo pro que está testando.
  test: {
    projects: [
      {
        plugins: [cloudflareTest(workerOptions)],
        test: {
          name: "workers",
          include: ["src/**/*.test.ts"],
          pool: cloudflarePool(workerOptions),
        },
      },
      {
        test: {
          name: "node",
          include: ["scripts/**/*.test.ts"],
        },
      },
    ],
  },
});
