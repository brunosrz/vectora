/**
 * Proxy do chat para o update-server (Cloudflare Workers).
 *
 * Apenas dois endpoints públicos consumidos pelo banner do chat:
 * - GET /api/updates/status — qual versão está disponível para esse client.
 * - POST /api/updates/telemetry — repassa estado de update para o server.
 */

import { Hono } from "hono";

const UPDATE_SERVER_URL =
  process.env.VECTORA_UPDATE_SERVER_URL ?? "https://updates.vectora.company";

const updates = new Hono();

function detectOS(ua: string): string {
  if (ua.includes("Windows")) return "win";
  if (ua.includes("Mac")) return "mac";
  return "linux";
}

function detectArch(ua: string): string {
  return ua.includes("arm64") || ua.includes("aarch64") ? "arm64" : "x64";
}

updates.get("/status", async (c) => {
  const channel = c.req.query("channel") ?? "latest";
  const ua = c.req.header("User-Agent") ?? "";
  const os = c.req.query("os") ?? detectOS(ua);
  const arch = c.req.query("arch") ?? detectArch(ua);
  const token = c.req.query("token") ?? "anonymous";
  try {
    const res = await fetch(
      `${UPDATE_SERVER_URL}/updates/${channel}/${os}/${arch}/latest.yml?token=${encodeURIComponent(token)}`,
    );
    if (!res.ok) {
      return c.json({ available: false, version: null }, 200);
    }
    const version = res.headers.get("X-Vectora-Version") ?? null;
    return c.json({ available: true, version, channel, os, arch });
  } catch {
    return c.json({ available: false, version: null }, 200);
  }
});

updates.post("/telemetry", async (c) => {
  const body = await c.req.json().catch(() => null);
  if (!body) return c.json({ ok: false }, 400);
  try {
    const res = await fetch(`${UPDATE_SERVER_URL}/telemetry/update-result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ ok: false }, 503);
  }
});

export default updates;
