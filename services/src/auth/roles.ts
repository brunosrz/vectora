import type { Env } from "../relay/types";
import { requireUserId } from "./routes";

/** Resolve o user autenticado e retorna seu id só se `role = 'admin'`. */
export async function requireAdmin(c: {
  req: { raw: Request };
  env: Env;
}): Promise<string | null> {
  const userId = await requireUserId(c);
  if (!userId) return null;

  const user = await c.env.DB.prepare("SELECT role FROM users WHERE id = ?")
    .bind(userId)
    .first<{ role: string }>();
  if (!user || user.role !== "admin") return null;

  return userId;
}
