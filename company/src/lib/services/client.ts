import { getCookie, setCookie } from "@tanstack/react-start/server";

// company fala com o Worker vectora-services server-to-server — o browser
// nunca acessa services diretamente. A sessão é um token opaco de 32 bytes
// guardado num cookie HttpOnly.
export const SERVICES_URL =
  process.env.SERVICES_URL ?? "https://services.vectora.company";

const SESSION_COOKIE = "vsession";

export function getSessionToken(): string | undefined {
  return getCookie(SESSION_COOKIE);
}

// Domain com "." de prefixo compartilha o cookie entre TODOS os
// subdomínios de vectora.company (bot.vectora.company incluído) — sem
// isso, o painel do gha-bot (embutido no Worker services/, servido em
// bot.vectora.company) nunca recebe este cookie do browser, mesmo com o
// usuário já logado na company. Local dev (sem domínio real) não define
// isso — cookie fica com o domínio implícito de sempre.
const COOKIE_DOMAIN =
  process.env.NODE_ENV === "production" ? ".vectora.company" : undefined;

export function setSessionCookie(token: string, expiresAt: string): void {
  setCookie(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    domain: COOKIE_DOMAIN,
    expires: new Date(expiresAt),
  });
}

export function clearSessionCookie(): void {
  setCookie(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    domain: COOKIE_DOMAIN,
    maxAge: 0,
  });
}

/** Lança "unauthorized" cedo, antes de bater na rede, se não há cookie de sessão. */
export function requireSessionToken(): string {
  const token = getSessionToken();
  if (!token) throw new Error("unauthorized");
  return token;
}

interface ServicesErrorBody {
  error?: string;
}

/** fetch tipado pro vectora-services, injeta o Bearer do cookie de sessão quando presente. */
export async function servicesFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getSessionToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${SERVICES_URL}${path}`, { ...init, headers });
  const body = (await res.json().catch(() => ({}))) as T & ServicesErrorBody;
  if (!res.ok) {
    throw new Error(body.error ?? `services_error_${res.status}`);
  }
  return body;
}
