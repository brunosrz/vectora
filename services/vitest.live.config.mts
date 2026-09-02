import { defineConfig } from "vitest/config";

/**
 * Config standalone pro teste de update real contra produção
 * (tests/scripts/live-update.test.ts) — deliberadamente FORA dos `projects`
 * de vitest.config.mts (o config default do `test`/`scons tests`), pra
 * nunca rodar como parte da suíte hermética de CI. Roda sob demanda:
 *
 *   pnpm --dir services exec vitest run --config vitest.live.config.mts
 */
export default defineConfig({
  test: {
    reporters: ["default"],
    include: ["tests/scripts/live-update.test.ts"],
  },
});
