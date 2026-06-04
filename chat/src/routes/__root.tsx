import {
  Outlet,
  createRootRouteWithContext,
  redirect,
  useLocation,
} from "@tanstack/react-router";
import type { RouterContext } from "../router";
import { useAuthStore } from "@/lib/stores/auth-store";

const PUBLIC_PATH_PREFIXES = ["/auth/", "/share/"];

const AUTH_REQUIRED =
  (import.meta.env.VITE_VECTORA_AUTH_REQUIRED ?? "true").toLowerCase() !==
  "false";

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATH_PREFIXES.some((p) => pathname.startsWith(p));
}

function redirectToSignin(currentPath: string): never {
  // `as unknown as Parameters<...>`: a tipagem estrita do RedirectOptions
  // exige `from` para inferir tipos de `search`. O guard roda na raiz e
  // não tem `from` ainda.
  throw redirect({
    to: "/auth/signin",
    search: { from: currentPath },
  } as unknown as Parameters<typeof redirect>[0]);
}

/**
 * Guard chamado pelo `beforeLoad` da rota raiz.
 *
 * Fluxo:
 *  1. Rotas públicas (`/auth/*`, `/share/*`) passam direto.
 *  2. `GET /auth/has-users`: vazio → redirect `/auth/signup` (setup root).
 *  3. `GET /auth/me`: 200 → libera + atualiza store.
 *  4. 401 → `POST /auth/refresh` silencioso; sucesso libera, falha
 *     limpa o store e vai para `/auth/signin?from=<currentPath>`.
 *
 * Cookies `vectora_access`/`vectora_refresh` httpOnly viajam em todas as
 * chamadas via `credentials: "include"`. O auth-store NUNCA é a fonte
 * de verdade — sempre validamos contra o backend.
 */
async function ensureAuthenticated(currentPath: string): Promise<void> {
  if (!AUTH_REQUIRED || isPublicPath(currentPath)) return;

  const store = useAuthStore.getState();

  // Setup wizard: backend sem usuários → manda para signup.
  try {
    const hasUsersRes = await fetch("/auth/has-users", {
      credentials: "include",
    });
    if (hasUsersRes.ok) {
      const data = (await hasUsersRes.json()) as { exists?: boolean };
      if (data.exists === false) {
        store.clearUser();
        throw redirect({ to: "/auth/signup" });
      }
    }
  } catch (err) {
    if (err && typeof err === "object" && "to" in err) throw err;
    // Backend offline — não interrompe. O fetch abaixo vai falhar igual.
  }

  let meRes: Response;
  try {
    meRes = await fetch("/auth/me", { credentials: "include" });
  } catch {
    // ECONNREFUSED ou rede offline: limpa store local para evitar
    // renderização com dados stale e manda para a tela de login.
    store.clearUser();
    redirectToSignin(currentPath);
  }

  if (meRes.ok) {
    // Sincroniza o store com a resposta canônica do backend.
    // Se o JSON falhar (ex.: proxy retornou index.html quando backend está
    // offline), trata como não autenticado — NÃO retorna silenciosamente.
    try {
      const user = await meRes.json();
      if (user?.id) {
        useAuthStore.getState().setUser(user);
        return;
      }
    } catch {
      /* corpo inválido — cai no clear+redirect abaixo */
    }
    store.clearUser();
    redirectToSignin(currentPath);
  }

  if (meRes.status === 401) {
    try {
      const refresh = await fetch("/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (refresh.ok) {
        const retry = await fetch("/auth/me", { credentials: "include" });
        if (retry.ok) {
          try {
            useAuthStore.getState().setUser(await retry.json());
          } catch {
            /* idem */
          }
          return;
        }
      }
    } catch {
      /* cai no clear+redirect abaixo */
    }
  }

  store.clearUser();
  redirectToSignin(currentPath);
}

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async ({ location }) => {
    await ensureAuthenticated(location.pathname);
  },
  component: RootComponent,
});

function RootComponent() {
  const location = useLocation();
  if (typeof document !== "undefined") {
    document.documentElement.lang = "pt-BR";
  }
  return (
    <div className="min-h-screen flex flex-col" data-route={location.pathname}>
      <Outlet />
    </div>
  );
}
