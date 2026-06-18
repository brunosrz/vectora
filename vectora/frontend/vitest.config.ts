import { configDefaults, defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Os specs do Playwright (e2e/*.spec.ts) NÃO são testes de vitest — usam o
    // runner do Playwright e o `@playwright/test`. Sem este exclude, o vitest
    // (include default `**/*.spec.ts`) tentaria rodá-los e o `scons tests`
    // quebraria. E2e roda à parte via `pnpm test:e2e`.
    exclude: [...configDefaults.exclude, "e2e/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
      include: ["lib/**", "src/**", "components/**", "hooks/**"],
      exclude: [
        "**/*.gen.ts",
        "**/*.d.ts",
        "tests/**",
        "**/__tests__/**",
        // Saída auto-gerada do paraglide (messages compiladas + README/ignores):
        // não é código nosso e os arquivos não-JS quebram o remap do v8.
        "lib/paraglide/**",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      // Mesmos shims do vite.config: componentes importam next/* que não
      // existem nesta SPA. Sem isto o vitest falha ao resolver os imports.
      "next/navigation": path.resolve(
        __dirname,
        "src/shims/next-navigation.ts",
      ),
      "next/image": path.resolve(__dirname, "src/shims/next-image.tsx"),
      "next/link": path.resolve(__dirname, "src/shims/next-link.tsx"),
    },
  },
});
