/**
 * Vectora Connect — adapter Telegram (piloto, Sprint 8 do plano de
 * extensibilidade). Normaliza o webhook do Telegram Bot API pro formato
 * comum que o backend Python consome (`backend/services/gateway/messaging.py`
 * — mesmos campos: platform, platform_user_id, text).
 *
 * Escopo real desta sessão: só o normalizador (puro, testável) e a rota
 * HTTP que o recebe. O encaminhamento de verdade pro backend via
 * `GatewaySession` (Durable Object, WebSocket) e o envio da resposta de
 * volta via `sendMessage` da Bot API ficam para uma sprint de integração
 * dedicada — sem isso ainda funcionando, expor o webhook em produção
 * receberia mensagens reais sem responder nada, pior que não ter o
 * endpoint. Documentado aqui em vez de fingir que já funciona ponta a
 * ponta (CLAUDE.md regra 9).
 */
import { Hono } from "hono";
import type { Env } from "../types";

export const telegramMessaging = new Hono<{ Bindings: Env }>();

export interface NormalizedMessage {
  platform: "telegram";
  platformUserId: string;
  text: string;
}

interface TelegramUpdate {
  message?: {
    text?: string;
    chat?: { id: number };
    from?: { id: number };
  };
}

/**
 * Normaliza um update do Telegram Bot API. Devolve `null` pra updates que
 * não são mensagens de texto simples (edições, updates de canal, stickers
 * sem legenda, etc.) — silenciosamente ignorados, não é erro.
 */
export function normalizeTelegramUpdate(
  update: TelegramUpdate,
): NormalizedMessage | null {
  const chatId = update.message?.chat?.id;
  const text = update.message?.text;
  if (chatId === undefined || !text) return null;
  return {
    platform: "telegram",
    platformUserId: String(chatId),
    text,
  };
}

telegramMessaging.post("/webhook", async (c) => {
  let update: TelegramUpdate;
  try {
    update = await c.req.json<TelegramUpdate>();
  } catch {
    return c.json({ error: "invalid_payload" }, 400);
  }

  const normalized = normalizeTelegramUpdate(update);
  if (!normalized) return c.json({ ok: true, ignored: true });

  // Encaminhamento pro GatewaySession (WebSocket) + resposta via Bot API
  // sendMessage: ver docstring do arquivo (integração fora de escopo
  // desta sessão).
  return c.json({ ok: true, received: normalized });
});
