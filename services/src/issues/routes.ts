/** issues/ — porta company/src/server/fns/issues.ts (issues + waitlist, públicos). */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { verifyTurnstile } from "../lib/turnstile";
import { sendEmail, SUPPORT_EMAIL, waitlistJoinedHtml } from "../lib/email";

export const issues = new Hono<{ Bindings: Env }>();

const CATEGORIES = new Set(["bug", "feedback", "feature"]);

issues.post("/", async (c) => {
  const body = await c.req.json<{
    title?: string;
    category?: string;
    description?: string;
    email?: string;
    turnstileToken?: string;
  }>();

  if (!body.title || body.title.length < 3 || body.title.length > 200) {
    return c.json({ error: "invalid_title" }, 400);
  }
  if (!body.category || !CATEGORIES.has(body.category)) {
    return c.json({ error: "invalid_category" }, 400);
  }
  if (!body.turnstileToken) return c.json({ error: "turnstile_required" }, 400);

  const turnstile = await verifyTurnstile(
    body.turnstileToken,
    c.env.TURNSTILE_SECRET_KEY,
    c.req.header("cf-connecting-ip"),
  );
  if (!turnstile.success) return c.json({ error: "turnstile_failed" }, 400);

  await c.env.DB.prepare(
    "INSERT INTO issues (id, title, category, description, email) VALUES (?, ?, ?, ?, ?)",
  )
    .bind(
      crypto.randomUUID(),
      body.title,
      body.category,
      body.description ?? null,
      body.email || null,
    )
    .run();

  await sendEmail(c.env.RESEND_API_KEY, {
    to: SUPPORT_EMAIL,
    subject: `[${body.category.toUpperCase()}] ${body.title}`,
    html: `
      <p><strong>Categoria:</strong> ${body.category}</p>
      <p><strong>Título:</strong> ${body.title}</p>
      <p><strong>Descrição:</strong> ${body.description ?? "—"}</p>
      <p><strong>Email:</strong> ${body.email ?? "—"}</p>
    `,
  });

  return c.json({ ok: true });
});

// Lista pública das issues abertas. NUNCA seleciona `email` (privacidade do
// reporter).
issues.get("/", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, title, category, description, created_at FROM issues ORDER BY created_at DESC LIMIT 100",
  ).all();
  return c.json(results);
});

issues.post("/waitlist", async (c) => {
  const body = await c.req.json<{
    email?: string;
    source?: string;
    turnstileToken?: string;
  }>();

  if (!body.email || !body.email.includes("@")) {
    return c.json({ error: "invalid_email" }, 400);
  }
  if (!body.turnstileToken) return c.json({ error: "turnstile_required" }, 400);

  const turnstile = await verifyTurnstile(
    body.turnstileToken,
    c.env.TURNSTILE_SECRET_KEY,
    c.req.header("cf-connecting-ip"),
  );
  if (!turnstile.success) return c.json({ error: "turnstile_failed" }, 400);

  try {
    await c.env.DB.prepare(
      "INSERT INTO waitlist (id, email, source) VALUES (?, ?, ?)",
    )
      .bind(crypto.randomUUID(), body.email.toLowerCase(), body.source ?? null)
      .run();

    await sendEmail(c.env.RESEND_API_KEY, {
      to: body.email,
      subject: "Você está na lista — Vectora",
      html: waitlistJoinedHtml(),
    });
  } catch {
    // já cadastrado (email UNIQUE) — idempotente do ponto de vista do
    // usuário, não é erro visível.
  }

  return c.json({ ok: true });
});
