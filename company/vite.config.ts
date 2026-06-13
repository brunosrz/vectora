import { defineConfig } from "vite";
import { devtools } from "@tanstack/devtools-vite";
import { paraglideVitePlugin } from "@inlang/paraglide-js";

import { tanstackStart } from "@tanstack/react-start/plugin/vite";

import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { nitro } from "nitro/vite";

const config = defineConfig({
  // host: true — escuta em todas as interfaces (LAN/Tailscale), como o chat;
  // sem isso o dev server só responde em localhost ("use --host to expose").
  server: { host: true },
  resolve: { tsconfigPaths: true },
  plugins: [
    devtools(),
    paraglideVitePlugin({
      project: "./project.inlang",
      outdir: "./src/paraglide",
      // cookie ANTES de baseLocale: a escolha do LocaleSwitcher persiste entre
      // páginas e reloads (antes só url+baseLocale → trocar idioma "não pegava"
      // ao navegar). url continua primeiro para links com prefixo (/en, /es…).
      strategy: ["url", "cookie", "baseLocale"],
    }),
    nitro({
      preset: process.env.NITRO_PRESET ?? "node-server",
      rollupConfig: { external: [/^@sentry\//] },
    }),
    tailwindcss(),
    tanstackStart(),
    viteReact(),
  ],
});

export default config;
