// next.config.mjs
// Arquivo em ESM puro (sem TypeScript) para evitar o uso de jiti durante o
// build — jiti@2.x chama module.register() do Node.js, que foi deprecada
// no Node.js 24 (DEP0205). Usando .mjs o Next.js carrega o arquivo
// diretamente via import() nativo, sem transpilação.
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone: bundla o servidor Next.js com deps mínimas.
  // Necessário para suportar auth server-side (proxy, API routes, cookies).
  // Distribuído junto ao chat/src/ backend como pacote próprio.
  //
  // NOTA: NÃO usar outputFileTracingRoot aqui. Em Windows + pnpm ele faz o
  // Next recriar a árvore de symlinks do store .pnpm no standalone, e
  // `symlink` exige privilégio elevado → EPERM no build. O default copia
  // arquivos reais (sem symlink). A dep @swc/helpers, exigida pelo runtime
  // SWC mas não detectada pelo tracer via pnpm, é copiada no `make build-chat`.
  output: "standalone",

  turbopack: {
    root: rootDir,
  },
  // Strip console calls in production builds
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production"
        ? {
            exclude: ["error", "warn"], // Keep errors and warnings for critical issues
          }
        : false,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'self'",
          },
          {
            key: "X-Frame-Options",
            value: "SAMEORIGIN",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
