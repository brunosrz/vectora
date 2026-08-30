/**
 * Sessão web opaca — substitui o JWT/cookie do Supabase Auth.
 *
 * A company (server-to-server, nunca o browser direto) troca credenciais por
 * um token opaco de 32 bytes aqui, guarda o hash em D1 e devolve o raw pra
 * company setar como cookie HttpOnly. Toda chamada subsequente da company
 * pra services manda esse token via `Authorization: Bearer`; services só
 * compara o hash — não há access/refresh token nem JWT porque não existe
 * cliente não-confiável direto (o browser nunca fala com services).
 */

const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 dias

function randomToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256Hex(input: string): Promise<string> {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(input),
  );
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export interface Session {
  token: string;
  expiresAt: string;
}

export async function createSession(
  db: D1Database,
  userId: string,
): Promise<Session> {
  const token = randomToken();
  const tokenHash = await sha256Hex(token);
  const expiresAt = new Date(Date.now() + SESSION_TTL_MS).toISOString();

  await db
    .prepare(
      "INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
    )
    .bind(crypto.randomUUID(), userId, tokenHash, expiresAt)
    .run();

  return { token, expiresAt };
}

/** Retorna o user_id da sessão válida (não expirada, não revogada), ou null. */
export async function resolveSession(
  db: D1Database,
  rawToken: string | null,
): Promise<string | null> {
  if (!rawToken) return null;
  const tokenHash = await sha256Hex(rawToken);
  const row = await db
    .prepare(
      "SELECT user_id, expires_at, revoked_at FROM sessions WHERE token_hash = ?",
    )
    .bind(tokenHash)
    .first<{
      user_id: string;
      expires_at: string;
      revoked_at: string | null;
    }>();

  if (!row) return null;
  if (row.revoked_at) return null;
  if (new Date(row.expires_at).getTime() < Date.now()) return null;

  await db
    .prepare("UPDATE sessions SET last_used_at = ? WHERE token_hash = ?")
    .bind(new Date().toISOString(), tokenHash)
    .run();

  return row.user_id;
}

export async function revokeSession(
  db: D1Database,
  rawToken: string,
): Promise<void> {
  const tokenHash = await sha256Hex(rawToken);
  await db
    .prepare("UPDATE sessions SET revoked_at = ? WHERE token_hash = ?")
    .bind(new Date().toISOString(), tokenHash)
    .run();
}

/** Extrai o token de `Authorization: Bearer <token>`. */
export function bearerToken(req: Request): string | null {
  const auth = req.headers.get("Authorization") ?? "";
  const match = /^Bearer (.+)$/.exec(auth);
  return match?.[1] ?? null;
}
