/** issues/ — porta company/src/server/fns/issues.ts (issues + waitlist, públicos). */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { verifyTurnstile } from "../lib/turnstile";
import { SUPPORT_EMAIL, waitlistJoinedHtml } from "../lib/email";
import { enqueueEmail } from "../lib/queue";

export const issues = new Hono<{ Bindings: Env }>();

const CATEGORIES = new Set(["bug", "feedback", "feature"]);

export const MAX_ISSUE_FILES = 3;

// Tipos aceitos como anexo e o teto de bytes de cada um. Vídeo tem teto
// maior porque 30s de tela em mp4/webm passam fácil de 5 MiB.
export const ISSUE_FILE_LIMITS: Record<string, number> = {
  "image/png": 5 * 1024 * 1024,
  "image/jpeg": 5 * 1024 * 1024,
  "image/webp": 5 * 1024 * 1024,
  "video/mp4": 50 * 1024 * 1024,
  "video/webm": 50 * 1024 * 1024,
};

interface IssueFields {
  title?: string;
  category?: string;
  description?: string;
  email?: string;
  turnstileToken?: string;
  files: File[];
}

async function readIssueBody(c: {
  req: {
    header: (name: string) => string | undefined;
    json: <T>() => Promise<T>;
    parseBody: (opts: { all: true }) => Promise<Record<string, unknown>>;
  };
}): Promise<IssueFields> {
  const contentType = c.req.header("Content-Type") ?? "";
  if (!contentType.includes("multipart/form-data")) {
    const body = await c.req.json<Omit<IssueFields, "files">>();
    return { ...body, files: [] };
  }
  const body = await c.req.parseBody({ all: true });
  const raw = body.files;
  const files = (Array.isArray(raw) ? raw : raw ? [raw] : []).filter(
    (f): f is File => f instanceof File,
  );
  return {
    title: typeof body.title === "string" ? body.title : undefined,
    category: typeof body.category === "string" ? body.category : undefined,
    description:
      typeof body.description === "string" ? body.description : undefined,
    email: typeof body.email === "string" ? body.email : undefined,
    turnstileToken:
      typeof body.turnstileToken === "string" ? body.turnstileToken : undefined,
    files,
  };
}

issues.post("/", async (c) => {
  const body = await readIssueBody(c);

  if (!body.title || body.title.length < 3 || body.title.length > 200) {
    return c.json({ error: "invalid_title" }, 400);
  }
  if (!body.category || !CATEGORIES.has(body.category)) {
    return c.json({ error: "invalid_category" }, 400);
  }
  if (body.files.length > MAX_ISSUE_FILES) {
    return c.json({ error: "too_many_files" }, 400);
  }
  for (const file of body.files) {
    const limit = ISSUE_FILE_LIMITS[file.type];
    if (limit === undefined) return c.json({ error: "invalid_file_type" }, 400);
    if (file.size > limit) return c.json({ error: "file_too_large" }, 413);
  }
  if (!body.turnstileToken) return c.json({ error: "turnstile_required" }, 400);

  const turnstile = await verifyTurnstile(
    body.turnstileToken,
    c.env.TURNSTILE_SECRET_KEY,
    c.req.header("cf-connecting-ip"),
  );
  if (!turnstile.success) return c.json({ error: "turnstile_failed" }, 400);

  const issueId = crypto.randomUUID();
  const fileKeys: string[] = [];
  for (const file of body.files) {
    // UUID na key torna o caminho não-enumerável — o GET /files é público,
    // mas só quem tem a key (listagem da issue) chega no arquivo.
    const safeName = file.name.replace(/[^\w.-]/g, "_").slice(0, 80);
    const key = `issues/${issueId}/${crypto.randomUUID()}-${safeName}`;
    await c.env.R2.put(key, file.stream(), {
      httpMetadata: { contentType: file.type },
    });
    fileKeys.push(key);
  }

  await c.env.DB.prepare(
    "INSERT INTO issues (id, title, category, description, email, files) VALUES (?, ?, ?, ?, ?, ?)",
  )
    .bind(
      issueId,
      body.title,
      body.category,
      body.description ?? null,
      body.email || null,
      fileKeys.length > 0 ? JSON.stringify(fileKeys) : null,
    )
    .run();

  const filesHtml =
    fileKeys.length > 0
      ? `<p><strong>Anexos:</strong> ${fileKeys
          .map(
            (k) =>
              `<a href="https://services.vectora.company/issues/files/${k}">${k}</a>`,
          )
          .join(" · ")}</p>`
      : "";
  await enqueueEmail(c.env, {
    to: SUPPORT_EMAIL,
    subject: `[${body.category.toUpperCase()}] ${body.title}`,
    html: `
      <p><strong>Categoria:</strong> ${body.category}</p>
      <p><strong>Título:</strong> ${body.title}</p>
      <p><strong>Descrição:</strong> ${body.description ?? "—"}</p>
      <p><strong>Email:</strong> ${body.email ?? "—"}</p>
      ${filesHtml}
    `,
  });

  return c.json({ ok: true });
});

// Lista pública das issues abertas. NUNCA seleciona `email` (privacidade do
// reporter). `files` sai como array de keys R2 (servidas em GET /files/*).
issues.get("/", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, title, category, description, files, created_at FROM issues WHERE archived_at IS NULL ORDER BY created_at DESC LIMIT 100",
  ).all<{ files: string | null } & Record<string, unknown>>();
  return c.json(
    results.map((row) => ({
      ...row,
      files: row.files ? (JSON.parse(row.files) as string[]) : [],
    })),
  );
});

// Serve um anexo do R2. Público por design: a key contém UUID e não é
// enumerável; quem tem a key veio da listagem pública da issue. Declarado
// ANTES de GET /:id — "files" nunca deve casar com o param de id.
issues.get("/files/*", async (c) => {
  const key = c.req.path.replace(/^.*?\/files\//, "");
  if (!key.startsWith("issues/")) return c.text("not found", 404);
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

// Detalhe público de uma issue (página /issues/$issueId no company). Mesma
// projeção sem `email` da listagem — privacidade do reporter. Arquivada
// (soft-delete) responde 404 igual a inexistente — quem precisa ver mesmo
// arquivada é admin, via GET /admin/issues/:id.
issues.get("/:id", async (c) => {
  const row = await c.env.DB.prepare(
    "SELECT id, title, category, description, files, status, created_at FROM issues WHERE id = ? AND archived_at IS NULL",
  )
    .bind(c.req.param("id"))
    .first<{ files: string | null } & Record<string, unknown>>();
  if (!row) return c.json({ error: "not_found" }, 404);
  return c.json({
    ...row,
    files: row.files ? (JSON.parse(row.files) as string[]) : [],
  });
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

    await enqueueEmail(c.env, {
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
