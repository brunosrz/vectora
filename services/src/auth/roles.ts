import type { Env } from "../relay/types";
import { requireUserId } from "./routes";

/** Busca o `role` de um user no D1. `null` se o user não existir. */
export async function getUserRole(
  env: Env,
  userId: string,
): Promise<string | null> {
  const user = await env.DB.prepare("SELECT role FROM users WHERE id = ?")
    .bind(userId)
    .first<{ role: string }>();
  return user?.role ?? null;
}

/** Resolve o user autenticado e retorna seu id só se `role = 'admin'`. */
export async function requireAdmin(c: {
  req: { raw: Request };
  env: Env;
}): Promise<string | null> {
  const userId = await requireUserId(c);
  if (!userId) return null;

  const role = await getUserRole(c.env, userId);
  if (role !== "admin") return null;

  return userId;
}
