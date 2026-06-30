import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    reporters: ["dot"],
    include: ["src/**/__tests__/**/*.test.ts"],
  },
});
