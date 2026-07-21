import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import {
  telegramMessaging,
  normalizeTelegramUpdate,
} from "../../../src/gateway/messaging/telegram";

describe("normalizeTelegramUpdate", () => {
  it("normaliza uma mensagem de texto simples", () => {
    const result = normalizeTelegramUpdate({
      message: { text: "oi", chat: { id: 42 }, from: { id: 42 } },
    });

    expect(result).toEqual({
      platform: "telegram",
      platformUserId: "42",
      text: "oi",
    });
  });

  it("ignora updates sem mensagem de texto (edição, sticker sem legenda) — não é erro", () => {
    expect(normalizeTelegramUpdate({})).toBeNull();
    expect(
      normalizeTelegramUpdate({ message: { chat: { id: 1 } } }),
    ).toBeNull();
  });
});

describe("POST /webhook", () => {
  it("aceita um update válido e devolve a mensagem normalizada", async () => {
    const res = await telegramMessaging.request(
      "/webhook",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: { text: "oi", chat: { id: 99 } },
        }),
      },
      env,
    );

    expect(res.status).toBe(200);
    const body = await res.json<{ ok: boolean; received: unknown }>();
    expect(body.ok).toBe(true);
    expect(body.received).toEqual({
      platform: "telegram",
      platformUserId: "99",
      text: "oi",
    });
  });

  it("payload malformado (não-JSON) não quebra o handler — 400", async () => {
    const res = await telegramMessaging.request(
      "/webhook",
      { method: "POST", body: "not json" },
      env,
    );

    expect(res.status).toBe(400);
  });

  it("update sem mensagem de texto é ignorado silenciosamente (200, ignored)", async () => {
    const res = await telegramMessaging.request(
      "/webhook",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edited_message: { text: "editado" } }),
      },
      env,
    );

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true, ignored: true });
  });
});
