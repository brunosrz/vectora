import { defineWorkersConfig } from "@cloudflare/vitest-pool-workers/config";

export default defineWorkersConfig({
  test: {
    poolOptions: {
      workers: {
        wrangler: { configPath: "./wrangler.toml" },
        miniflare: {
          bindings: {
            VECTORA_JWT_SECRET: "test-jwt-secret-32-chars-minimum!",
            RELAY_HMAC_SECRET: "test-hmac-secret-32-chars-minimum",
            // workerd SQLite permanece bloqueado no Windows após o fetch ao DO,
            // impedindo o cleanup do isolated storage. Marca para skip seletivo.
            TEST_IS_WINDOWS: process.platform === "win32" ? "1" : "0",
          },
          kvNamespaces: ["RELAY_METRICS"],
          durableObjects: {
            RELAY_SESSION: "RelaySession",
          },
        },
      },
    },
  },
});
