import {
  Outlet,
  createRootRouteWithContext,
  redirect,
  useLocation,
} from "@tanstack/react-router";
import type { RouterContext } from "../router";

// `ToPath = never` faz os paths literais passarem pelo type-check sem
// estarem registrados no `routeTree.gen.ts`. O resolver real do
// TanStack Router valida em runtime.
type ToPath = never;

const PUBLIC_PATH_PREFIXES = ["/auth/", "/share/"];

const AUTH_REQUIRED =
  (import.meta.env.VITE_VECTORA_AUTH_REQUIRED ?? "true").toLowerCase() !==
  "false";

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATH_PREFIXES.some((p) => pathname.startsWith(p));
}

/**
 * Auth guard global. Substitui o middleware `chat/proxy.ts` do Next.js.
 *
 * Estratégia:
 *  1. Rotas públicas (`/auth/*`, `/share/*`) passam direto.
 *  2. Faz `GET /auth/me` para validar a sessão (cookies httpOnly).
 *  3. Se 401, tenta `POST /auth/refresh` silencioso.
 *  4. Falhando, redireciona para `/auth/signin?from=...`.
 *  5. Em primeiro acesso (sem usuários), redireciona para `/auth/signup`.
 */
async function ensureAuthenticated(currentPath: string): Promise<void> {
  if (!AUTH_REQUIRED || isPublicPath(currentPath)) {
    return;
  }

  // Verifica se já existe pelo menos um user — se não, vai pra setup root.
  try {
    const hasUsersRes = await fetch("/auth/has-users", {
      credentials: "include",
    });
    if (hasUsersRes.ok) {
      const data = (await hasUsersRes.json()) as { exists?: boolean };
      if (data.exists === false) {
        throw redirect({ to: "/auth/signup" as ToPath });
      }
    }
  } catch (err) {
    // Se for um redirect lançado pelo TanStack, propaga.
    if (err && typeof err === "object" && "to" in err) throw err;
    // ECONNREFUSED ou backend offline — manda para signin com mensagem.
  }

  let meRes: Response;
  try {
    meRes = await fetch("/auth/me", { credentials: "include" });
  } catch {
    throw redirect({
      to: "/auth/signin" as ToPath,
      search: { from: currentPath } as never,
    });
  }

  if (meRes.ok) return;

  if (meRes.status === 401) {
    // Tenta refresh silencioso.
    try {
      const refreshRes = await fetch("/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (refreshRes.ok) return;
    } catch {
      // ignora — vai cair no redirect.
    }
  }

  throw redirect({
    to: "/auth/signin" as ToPath,
    search: { from: currentPath } as never,
  });
}

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async ({ location }) => {
    await ensureAuthenticated(location.pathname);
  },
  component: RootComponent,
});

function RootComponent() {
  const location = useLocation();
  // Marca o lang no documento para acessibilidade.
  if (typeof document !== "undefined") {
    document.documentElement.lang = "pt-BR";
  }
  return (
    <div className="min-h-screen flex flex-col" data-route={location.pathname}>
      <Outlet />
    </div>
  );
}
