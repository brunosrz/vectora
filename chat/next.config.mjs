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
// Para que o Vectora possa ser servido de qualquer host em dev (LAN,
// VPS, Tailscale, túneis tipo ngrok, IP novo da rede), abrimos para
// todos os origins via globstar `**` — Next 16 usa picomatch e `**`
// casa qualquer hostname/IP, com qualquer número de segmentos.
//
// Se algum operador quiser restringir explicitamente em dev (zona de
// trabalho compartilhada, etc.), `NEXT_DEV_ALLOWED_ORIGINS` substitui
// a lista padrão por uma CSV custom.
const _envOrigins = (process.env.NEXT_DEV_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const _allowedDevOrigins = _envOrigins.length > 0 ? _envOrigins : ["**"];

if (process.env.NODE_ENV !== "production") {
  console.info(
    "[vectora] allowedDevOrigins =",
    _allowedDevOrigins.join(", "),
    _envOrigins.length > 0
      ? "(custom via NEXT_DEV_ALLOWED_ORIGINS)"
      : "(catch-all — qualquer host)",
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
