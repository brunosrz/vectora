// next.config.mjs
// Arquivo em ESM puro (sem TypeScript) para evitar o uso de jiti durante o
// build — jiti@2.x chama module.register() do Node.js, que foi deprecada
// no Node.js 24 (DEP0205). Usando .mjs o Next.js carrega o arquivo
// diretamente via import() nativo, sem transpilação.
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(fileURLToPath(import.meta.url));

// `allowedDevOrigins` afeta APENAS o `next dev` (HMR e outros recursos
// internos em `/_next/*`). Não tem efeito em produção e não bloqueia
// auth, /api/*, navegação normal nem WebSocket do app. Segurança real
// continua sendo email+senha+cookie httpOnly+SameSite=Lax (Bloco C).
//
// Importante: o Next 16 NÃO suporta globstar (`**`) para
// `allowedDevOrigins`. Cada `*` casa exatamente UM segmento entre pontos.
// Para um IPv4 inteiro (`100.85.240.102`) precisamos de `100.*.*.*`.
// Para hostnames LAN tipo `meupc.local` basta `*.local`.
//
// `NEXT_DEV_ALLOWED_ORIGINS` (CSV) substitui a lista padrão.
const _envOrigins = (process.env.NEXT_DEV_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const _defaultAllowedDevOrigins = [
  // localhost (não bloqueia, mas explícito por garantia)
  "localhost",
  "127.0.0.1",
  // IPv4 catch-all — 4 octetos cobrem qualquer endereço público/privado
  "*.*.*.*",
  // mDNS / Bonjour (impressoras, dispositivos LAN com nome .local)
  "*.local",
  // Tailscale Magic DNS (<machine>.<tailnet>.ts.net)
  "*.ts.net",
  "*.*.ts.net",
  // Túneis comuns
  "*.ngrok.io",
  "*.ngrok-free.app",
  "*.trycloudflare.com",
];

const _allowedDevOrigins =
  _envOrigins.length > 0 ? _envOrigins : _defaultAllowedDevOrigins;

if (process.env.NODE_ENV !== "production") {
  console.info(
    "[vectora] allowedDevOrigins =",
    _allowedDevOrigins.join(", "),
    _envOrigins.length > 0
      ? "(custom via NEXT_DEV_ALLOWED_ORIGINS)"
      : "(default: qualquer IPv4 + LAN + Tailscale + tuneis)",
  );
}

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
