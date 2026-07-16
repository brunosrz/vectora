import { getSession } from "#/server/fns/auth";

export interface ViewerRole {
  isAdmin: boolean;
}

/**
 * Resolve o papel do viewer atual a partir da sessão — reaproveitável por
 * qualquer loader que precise decidir "mostra controle de admin ou não" sem
 * duplicar a checagem de role (mesmo `getSession()` já usado em
 * `admin/route.tsx:beforeLoad`).
 *
 * Fail-safe: getSession() já devolve null em qualquer erro de sessão
 * (cookie ausente, token inválido, rede) — aqui isso vira isAdmin: false,
 * nunca lança. Uma página que chame isso errado nunca vaza controle de
 * admin por causa de uma falha transiente.
 */
export async function resolveViewerRole(): Promise<ViewerRole> {
  const session = await getSession().catch(() => null);
  return { isAdmin: session?.role === "admin" };
}
