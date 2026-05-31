// next.config.mjs
// Arquivo em ESM puro (sem TypeScript) para evitar o uso de jiti durante o
// build — jiti@2.x chama module.register() do Node.js, que foi deprecada
// no Node.js 24 (DEP0205). Usando .mjs o Next.js carrega o arquivo
// diretamente via import() nativo, sem transpilação.
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(fileURLToPath(import.meta.url));

// Origens permitidas para HMR no dev quando o dev server é acessado por
// outro host além de localhost (celular na mesma rede, Tailscale, IP da
// LAN, etc.). Sem isso o Next 16 bloqueia o /_next/webpack-hmr.
//
// Lê uma lista separada por vírgula em `NEXT_DEV_ALLOWED_ORIGINS` e mescla
// com um conjunto fixo cobrindo todas as ranges privadas RFC1918 + CGNAT
// (Tailscale usa 100.x). Wildcards do Next são por hostname — `192.168.*`
// cobre toda a sub-rede sem precisar listar IP a IP.
const _envOrigins = (process.env.NEXT_DEV_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const _allowedDevOrigins = [
  ...new Set([
    // Ranges privadas RFC1918 + CGNAT (Tailscale usa 100.64.0.0/10)
    "10.*",
    "192.168.*",
    "172.16.*",
    "172.17.*",
    "172.18.*",
    "172.19.*",
    "172.20.*",
    "172.21.*",
    "172.22.*",
    "172.23.*",
    "172.24.*",
    "172.25.*",
    "172.26.*",
    "172.27.*",
    "172.28.*",
    "172.29.*",
    "172.30.*",
    "172.31.*",
    "100.*",
    ..._envOrigins,
  ]),
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    root: rootDir,
  },
  allowedDevOrigins: _allowedDevOrigins,
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
