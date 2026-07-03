import { cloudflarePool, cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

const workerOptions = {
  wrangler: { configPath: "./wrangler.toml" },
  miniflare: {
    bindings: {
      VECTORA_JWT_SECRET: "test-jwt-secret-32-chars-minimum!",
      RELAY_HMAC_SECRET: "test-hmac-secret-32-chars-minimum",
      VECTORA_OAUTH_SECRET: "test-oauth-secret",
      APP_URL: "https://vectora.company",
      RELAY_URL: "https://relay.vectora.chat",
      RESEND_API_KEY: "test-resend-key",
      STRIPE_SECRET_KEY: "sk_test_fake",
      STRIPE_WEBHOOK_SECRET: "whsec_test_fake",
      STRIPE_PRICE_PRO_USD: "price_test_fake",
      ASAAS_API_KEY: "test-asaas-key",
      ASAAS_API_URL: "https://api.asaas.com/v3",
      // workerd SQLite permanece bloqueado no Windows após o fetch ao DO,
      // impedindo o cleanup do isolated storage. Marca para skip seletivo.
      TEST_IS_WINDOWS: process.platform === "win32" ? "1" : "0",
    },
    kvNamespaces: ["RELAY_METRICS", "KV"],
    r2Buckets: ["R2"],
    d1Databases: ["DB"],
    durableObjects: {
      RELAY_SESSION: "RelaySession",
    },
    queueProducers: {
      EMAIL_QUEUE: "vectora-email",
      JOBS_QUEUE: "vectora-jobs",
    },
    queueConsumers: ["vectora-email", "vectora-jobs"],
  },
};

export default defineConfig({
  // `scripts/` (release.ts) é um CLI Node puro — nunca roda dentro do
  // Worker, só localmente via tsx. Rodar seu teste no pool workerd (isolate
  // sandboxed, sem child_process/fs de verdade) quebra o teardown do
  // miniflare (WebSocket não fecha, "close timed out"). Cada projeto usa o
  // runtime certo pro que está testando.
  test: {
    // Istanbul, não V8 — o coverage nativo do vitest não instrumenta workerd.
    // `relay-session.ts` fica perto de 0% quando rodado no Windows: os testes
    // que tocam o Durable Object (itDO em relay-session.test.ts) são pulados
    // aqui pelo mesmo motivo do skip seletivo (SQLite do DO trava o cleanup do
    // isolated storage no Windows) — em CI (Linux) esses testes rodam e a
    // cobertura reflete o arquivo inteiro.
    coverage: {
      provider: "istanbul",
      reporter: ["text", "html"],
      include: ["src/**/*.ts"],
    },
    projects: [
      {
        plugins: [cloudflareTest(workerOptions)],
        test: {
          name: "workers",
          include: ["tests/**/*.test.ts"],
          exclude: ["tests/scripts/**"],
          setupFiles: ["./tests/test-setup.ts"],
          pool: cloudflarePool(workerOptions),
        },
      },
      {
        test: {
          name: "node",
          include: ["tests/scripts/**/*.test.ts"],
        },
      },
    ],
  },
});
