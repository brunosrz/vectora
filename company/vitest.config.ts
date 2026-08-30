import { defineConfig } from "vitest/config";
import viteReact from "@vitejs/plugin-react";

export default defineConfig({
  resolve: {
    alias: {
      "#": new URL("./src", import.meta.url).pathname,
    },
  },
  plugins: [viteReact()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
      include: ["src/**"],
      skipFull: true,
      exclude: [
        "**/*.gen.ts",
        "**/*.d.ts",
        "**/__tests__/**",
        "src/paraglide/**", // saída gerada do Paraglide, não é código nosso
        "src/router.tsx", // instancia o router (wiring)
        "src/routeTree.gen.ts",
        "**/*.css",
      ],
    },
  },
});
