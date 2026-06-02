/**
 * vectora-update-server — Cloudflare Worker.
 *
 * Serve manifestos ``latest*.yml`` para o ``electron-updater`` do desktop
 * Vectora, com rollout faseado e quarantine automática por crash report.
 *
 * Implementação inicial: skeleton com health-check + manifest stub.
 * `release.ts` (scripts/) publica os binários assinados no R2 e
 * regenera `config.yml` em KV.
 */

import { Hono } from "hono";

interface Bindings {
  R2: R2Bucket;
  KV: KVNamespace;
  LICENSE_VALIDATE_URL: string;
}

interface ChannelConfig {
  version: string;
  rollout_percent: number;
  previous_stable?: string;
}

interface RuntimeConfig {
  channels: Record<string, ChannelConfig>;
  quarantined: string[];
}

const app = new Hono<{ Bindings: Bindings }>();

app.get("/health", (c) =>
  c.json({ ok: true, server: "vectora-update-server", timestamp: Date.now() }),
);

/** Hash determinístico estável → bucket [0..99] para rollout faseado. */
function rolloutBucket(token: string): number {
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
function resolveVersion(
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

app.get("/updates/:channel/:os/:arch/latest.yml", async (c) => {
  const token = c.req.query("token") ?? c.req.header("X-Vectora-Token") ?? "";
  if (!token) {
    return c.text("missing token", 401);
  }
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
  const token = c.req.query("token") ?? c.req.header("X-Vectora-Token") ?? "";
  if (!token) return c.text("missing token", 401);
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

interface TelemetryBody {
  state: "started" | "completed" | "failed";
  version: string;
  os: string;
  arch: string;
}

app.post("/telemetry/update-result", async (c) => {
  const body = await c.req.json<TelemetryBody>();
  const bucket = `telem:${body.version}:${body.state}`;
  const current = parseInt((await c.env.KV.get(bucket)) ?? "0", 10);
  await c.env.KV.put(bucket, String(current + 1), { expirationTtl: 3600 });

  if (body.state === "failed" && current + 1 >= 3) {
    // 3+ falhas na mesma versão dentro de 1h → quarentina automática.
    const config = await getConfig(c.env.KV);
    if (!config.quarantined.includes(body.version)) {
      config.quarantined.push(body.version);
      await c.env.KV.put("config", JSON.stringify(config));
    }
  }
  return c.json({ ok: true });
});

export default app;
