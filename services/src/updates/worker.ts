/**
 * updates/ — distribuição de releases do desktop Vectora (dentro do vectora-services).
 *
 * Serve manifestos ``latest*.yml`` para o ``electron-updater`` do desktop
 * Vectora, com rollout faseado e quarantine automática por crash report, e a
 * rota pública de primeira instalação (`/download/...`, sem token).
 *
 * `scripts/release.ts` publica os binários assinados no R2 e regenera
 * `config` no KV.
 */

import { Hono } from "hono";
import type { Env } from "../relay/types";
import { enqueueJob } from "../lib/queue";

interface ChannelConfig {
  version: string;
  rollout_percent: number;
  previous_stable?: string;
  // Versões retidas em R2 pro canal (mais antiga primeiro), gravado por
  // scripts/release.ts — o worker não lê, só preserva o formato do KV.
  history?: string[];
}

interface RuntimeConfig {
  channels: Record<string, ChannelConfig>;
  quarantined: string[];
  // "<channel>/<version>" → chaves R2 publicadas por essa versão, usado por
  // scripts/release.ts pra podar sem precisar listar o bucket.
  uploads?: Record<string, string[]>;
}

const app = new Hono<{ Bindings: Env }>();

app.get("/health", (c) =>
  c.json({
    ok: true,
    server: "vectora-services/updates",
    timestamp: Date.now(),
  }),
);

/** Hash determinístico estável → bucket [0..99] para rollout faseado. */
export function rolloutBucket(token: string): number {
  let h = 0;
  for (const ch of token) {
    h = (h * 31 + ch.charCodeAt(0)) | 0;
  }
  return Math.abs(h) % 100;
}

async function getConfig(kv: KVNamespace): Promise<RuntimeConfig> {
  const raw = await kv.get("config");
  if (!raw) {
    return { channels: {}, quarantined: [] };
  }
  return JSON.parse(raw) as RuntimeConfig;
}

/** Decide qual versão servir para o client baseado em rollout. */
export function resolveVersion(
  config: RuntimeConfig,
  channel: string,
  token: string,
): string | null {
  const ch = config.channels[channel];
  if (!ch) return null;
  if (config.quarantined.includes(ch.version)) {
    // Versão quarentinada → fallback para previous_stable.
    return ch.previous_stable ?? null;
  }
  if (rolloutBucket(token) < ch.rollout_percent) {
    return ch.version;
  }
  return ch.previous_stable ?? null;
}

// Sem token: Free não tem conta, checar/baixar atualização não pode depender
// de estar logado. Rollout/quarentena continuam controlando QUAL versão é
// servida — isso é sobre segurança de release, não sobre autenticação.
app.get("/updates/:channel/:os/:arch/latest.yml", async (c) => {
  const token = c.req.query("token") ?? c.req.header("X-Vectora-Token") ?? "";
  const { channel, os, arch } = c.req.param();
  const config = await getConfig(c.env.KV);
  const version = resolveVersion(config, channel, token);
  if (!version) {
    return c.text("no version available", 404);
  }
  // O manifesto YAML em si é pré-gerado pelo script de release e fica
  // em R2 em ``<channel>/<os>/<arch>/<version>/latest.yml``.
  const key = `${channel}/${os}/${arch}/${version}/latest.yml`;
  const obj = await c.env.R2.get(key);
  if (!obj) return c.text("manifest missing", 404);
  return new Response(obj.body, {
    headers: {
      "Content-Type": "application/x-yaml",
      "Cache-Control": "public, max-age=60",
      "X-Vectora-Version": version,
    },
  });
});

app.get("/updates/:channel/:os/:arch/:version/:filename", async (c) => {
  const { channel, os, arch, version, filename } = c.req.param();
  const key = `${channel}/${os}/${arch}/${version}/${filename}`;
  const obj = await c.env.R2.get(key);
  if (!obj) return c.text("not found", 404);
  return new Response(obj.body, {
    headers: {
      "Content-Type":
        obj.httpMetadata?.contentType ?? "application/octet-stream",
      "Cache-Control": "public, max-age=3600",
      ETag: obj.httpEtag,
    },
  });
});

/** Nome do instalador conforme o artifactName do electron-builder. */
export function installerFilename(
  version: string,
  os: string,
  arch: string,
  ext: string,
): string {
  return `Vectora-${version}-${os}-${arch}.${ext}`;
}

// Download de primeira instalação — sem token (o visitante do site ainda não
// tem app nem conta) e sem participar do rollout gradual (esse é só pra quem
// já tem o app e está checando update; quem baixa pela primeira vez recebe a
// versão estável do canal direto, ignorando quarentena/rollout_percent).
app.get("/download/:channel/:os/:arch/:ext", async (c) => {
  const { channel, os, arch, ext } = c.req.param();
  const config = await getConfig(c.env.KV);
  const ch = config.channels[channel];
  if (!ch) return c.text("unknown channel", 404);
  const version = config.quarantined.includes(ch.version)
    ? (ch.previous_stable ?? null)
    : ch.version;
  if (!version) return c.text("no version available", 404);

  const filename = installerFilename(version, os, arch, ext);
  const key = `${channel}/${os}/${arch}/${version}/${filename}`;
  const obj = await c.env.R2.get(key);
  if (!obj) return c.text("not found", 404);
  return new Response(obj.body, {
    headers: {
      "Content-Type":
        obj.httpMetadata?.contentType ?? "application/octet-stream",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "public, max-age=300",
      "X-Vectora-Version": version,
    },
  });
});

interface TelemetryBody {
  state: "started" | "completed" | "failed";
  version: string;
  os: string;
  arch: string;
}

/**
 * Lógica de verdade da telemetria de update (contagem + quarentena
 * automática) — roda dentro do consumer da fila `vectora-jobs`
 * (`max_concurrency = 1`, ver wrangler.toml), nunca direto na rota HTTP.
 * Antes era um read-modify-write direto em KV na própria rota: duas
 * instalações reportando ao mesmo tempo podiam se pisar na contagem. Rodando
 * serializado no consumer, essa race não existe mais.
 */
export async function processUpdateTelemetry(
  env: Env,
  body: TelemetryBody,
): Promise<void> {
  const bucket = `telem:${body.version}:${body.state}`;
  const current = parseInt((await env.KV.get(bucket)) ?? "0", 10);
  await env.KV.put(bucket, String(current + 1), { expirationTtl: 3600 });

  if (body.state === "failed" && current + 1 >= 3) {
    // 3+ falhas na mesma versão dentro de 1h → quarentina automática.
    const config = await getConfig(env.KV);
    if (!config.quarantined.includes(body.version)) {
      config.quarantined.push(body.version);
      await env.KV.put("config", JSON.stringify(config));
    }
  }
}

app.post("/telemetry/update-result", async (c) => {
  const body = await c.req.json<TelemetryBody>();
  await enqueueJob(c.env, { type: "update_telemetry", ...body });
  return c.json({ ok: true });
});

export default app;
