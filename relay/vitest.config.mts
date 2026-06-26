import { cloudflarePool, cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

const workerOptions = {
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
};

export default defineConfig({
  plugins: [cloudflareTest(workerOptions)],
  test: {
    pool: cloudflarePool(workerOptions),
  },
});
