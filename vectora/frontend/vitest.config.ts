import { configDefaults, defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    reporters: ["dot"],
    testTimeout: 15000,
    // Sem limite, o pool "forks" usa 1 worker por núcleo — sob scons tests
    // (suíte inteira + outros processos concorrentes), isso satura a CPU e
    // produz timeouts intermitentes de hook/worker mesmo em arquivos leves.
    // Cap conservador reduz a contenção sem alongar o tempo total de forma
    // perceptível (a suíte já é I/O-bound em boa parte via jsdom/imports).
    maxForks: 4,
    onConsoleLog(log: string): false | void {
      if (
        log.includes("[Logger] Initialized") ||
        log.includes("the given storage is currently unavailable")
      ) {
        return false;
      }
    },
    // Os specs do Playwright (e2e/*.spec.ts) NÃO são testes de vitest — usam o
    // runner do Playwright e o `@playwright/test`. Sem este exclude, o vitest
    // (include default `**/*.spec.ts`) tentaria rodá-los e o `scons tests`
    // quebraria. E2e roda à parte via `pnpm test:e2e`.
    //
    // electron/dist/**: saída compilada do tsc (electron/tsconfig.json inclui
    // src/**/* inteiro, inclusive __tests__/) — sem este exclude o vitest
    // roda os mesmos testes duas vezes (fonte .ts em electron/src/ e a cópia
    // .js compilada em electron/dist/).
    exclude: [...configDefaults.exclude, "e2e/**", "electron/dist/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
      include: ["lib/**", "src/**", "components/**", "hooks/**"],
      // Esconde do relatório de texto os arquivos já 100% cobertos (o html
      // mantém tudo) — corta ruído na saída do `scons tests`.
      skipFull: true,
      exclude: [
        "**/*.gen.ts",
        "**/*.d.ts",
        "tests/**",
        "**/__tests__/**",
        // Saída auto-gerada do paraglide (messages compiladas + README/ignores):
        // não é código nosso e os arquivos não-JS quebram o remap do v8.
        "lib/paraglide/**",
        // Não-testáveis: wiring de framework e arquivos puramente declarativos.
        // Tudo que tem lógica testável continua incluído (e deve ser testado).
        "src/main.tsx", // bootstrap do app
        "src/router.tsx", // instancia o router
        "src/routes/**", // árvore de rotas do TanStack (wiring)
        "src/shims/**", // shims de next/* (compat)
        "src/styles.css",
        "components/providers/**", // context providers (wiring)
        "components/icons/**", // SVG puro
        "lib/monaco/**", // setup do editor Monaco (integração externa)
        "lib/theme/**", // presets de tema (dados)
        "lib/types/**", // arquivos só de tipos (sem runtime)
        "**/*-skeleton.tsx", // skeletons de loading (apresentacional puro)
        "**/*.css",
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
