import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { paraglideVitePlugin } from "@inlang/paraglide-js";
import { VitePWA } from "vite-plugin-pwa";

const currentDir = dirname(fileURLToPath(import.meta.url));
const shimsDir = resolve(currentDir, "src/shims");

// Apenas o `vite dev` consulta este proxy. O FastAPI da build de produção
// serve `chat/dist/` no mesmo origin do browser, então não há request HTTP
// cruzando a rede.
const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://127.0.0.1:8080";

const apiProxy = {
  target: VECTORA_API_URL,
  changeOrigin: true,
  secure: false,
};
const wsProxy = {
  target: VECTORA_API_URL.replace(/^http/, "ws"),
  changeOrigin: true,
  ws: true,
  secure: false,
};

export default defineConfig({
  plugins: [
    TanStackRouterVite({
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routeTree.gen.ts",
    }),
    paraglideVitePlugin({
      project: "./project.inlang",
      outdir: "./lib/paraglide",
      strategy: ["localStorage", "preferredLanguage", "baseLocale"],
    }),
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: [
        "favicon.ico",
        "favicon-32x32.png",
        "favicon-600x600.png",
        "vectora.svg",
      ],
      manifest: {
        name: "Vectora",
        short_name: "Vectora",
        description:
          "Self-hosted AI agent com RAG, MCP e chat web multi-usuário.",
        theme_color: "#0a0e1a",
        background_color: "#0a0e1a",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "/favicon-32x32.png",
            sizes: "32x32",
            type: "image/png",
          },
          {
            src: "/favicon-600x600.png",
            sizes: "600x600",
            type: "image/png",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        navigateFallback: "/index.html",
        // O Monaco empacota web workers grandes (ts.worker ~7 MB); precisam
        // ser precacheados para o editor funcionar offline (Electron).
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        // Nunca cachear chamadas de API; SSE depende de network direct.
        navigateFallbackDenylist: [
          /^\/auth\//,
          /^\/vectora\./,
          /^\/admin\//,
          /^\/workspaces\b/,
          /^\/plugins\b/,
          /^\/skills\b/,
          /^\/memory\b/,
          /^\/tools\b/,
          /^\/license\b/,
          /^\/artifacts\b/,
          /^\/health\b/,
          /^\/metrics\b/,
        ],
        runtimeCaching: [
          {
            urlPattern: /\.(?:js|css|woff2?|png|svg|ico|webp|avif)$/,
            handler: "CacheFirst",
            options: {
              cacheName: "vectora-assets",
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/auth": apiProxy,
      "/vectora.chat.v1": apiProxy,
      "/vectora.workspace.v1": apiProxy,
      "/vectora.terminal.v1": wsProxy,
      "/admin": apiProxy,
      "/workspaces": apiProxy,
      "/threads": apiProxy,
      "/plugins": apiProxy,
      "/skills": apiProxy,
      "/license": apiProxy,
      "/memory": apiProxy,
      "/tools": apiProxy,
      "/artifacts": apiProxy,
      "/health": apiProxy,
      "/metrics": apiProxy,
    },
  },
  resolve: {
    // Resolução de paths do `tsconfig.json` (`@/*`) — suporte nativo do
    // Vite 8+, dispensa o plugin `vite-tsconfig-paths`.
    tsconfigPaths: true,
    // Os módulos virtuais `next/link`, `next/image` e `next/navigation`
    // resolvem para os shims em `src/shims/`. Sem esses aliases os
    // imports literais falham na resolução do Vite.
    alias: {
      "next/navigation": resolve(shimsDir, "next-navigation.ts"),
      "next/image": resolve(shimsDir, "next-image.tsx"),
      "next/link": resolve(shimsDir, "next-link.tsx"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    target: "es2022",
    chunkSizeWarningLimit: 1500,
    rolldownOptions: {
      checks: { pluginTimings: false },
    },
  },
});
