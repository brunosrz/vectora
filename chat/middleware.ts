/**
 * Next.js Edge Middleware — proteção de rotas + refresh automático de token.
 *
 * Comportamento:
 * 1. Rotas /auth/* são sempre públicas.
 * 2. Outras rotas: se não houver vectora_access, redireciona para /auth/signin
 *    (quando auth está habilitado via VECTORA_AUTH_REQUIRED != "false").
 * 3. Se o acesso chegar com cookie mas o backend retornar 401, o middleware
 *    tenta refresh automático via /api/auth/refresh antes de redirecionar.
 *
 * VECTORA_AUTH_REQUIRED=false → middleware não redireciona (modo dev local).
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_REQUIRED =
  process.env.VECTORA_AUTH_REQUIRED?.toLowerCase() !== "false";

const PUBLIC_PATHS = [
  "/auth/signin",
  "/auth/signup",
  "/api/auth/",
  "/_next/",
  "/favicon",
  "/vectora",
  "/assets/",
];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Auth desabilitado (modo dev/local) — passa direto
  if (!AUTH_REQUIRED) {
    return NextResponse.next();
  }

  // Rotas públicas — sempre passam
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get("vectora_access")?.value;
  const refreshToken = request.cookies.get("vectora_refresh")?.value;

  // Sem tokens → redireciona para signin
  if (!accessToken && !refreshToken) {
    const signinUrl = new URL("/auth/signin", request.url);
    signinUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(signinUrl);
  }

  // Tem access token → deixa passar (o backend valida)
  if (accessToken) {
    return NextResponse.next();
  }

  // Só tem refresh token → tenta refresh silencioso
  if (refreshToken) {
    try {
      const refreshRes = await fetch(
        new URL("/api/auth/refresh", request.url).toString(),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Cookie: request.headers.get("cookie") ?? "",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        },
      );

      if (refreshRes.ok) {
        const response = NextResponse.next();
        // Propaga os Set-Cookie do refresh para o browser
        const setCookies = refreshRes.headers.getSetCookie?.() ?? [];
        for (const cookie of setCookies) {
          response.headers.append("Set-Cookie", cookie);
        }
        return response;
      }
    } catch {
      // Falha no refresh → redireciona para signin
    }

    const signinUrl = new URL("/auth/signin", request.url);
    signinUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(signinUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Aplica o middleware em todas as rotas EXCETO:
     * - _next/static (assets estáticos compilados)
     * - _next/image (imagens otimizadas)
     * - favicon.ico
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
