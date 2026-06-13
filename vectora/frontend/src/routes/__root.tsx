import { useEffect } from "react";
import {
  Outlet,
  createRootRouteWithContext,
  redirect,
  useLocation,
} from "@tanstack/react-router";
import type { RouterContext } from "../router";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useSessionExpiry } from "@/lib/hooks/use-session-expiry";
import { useSettingsStore, type Lang } from "@/lib/stores/settings-store";
import {
  THEME_PRESETS,
  buildThemeTokens,
  applyThemeTokens,
} from "@/lib/theme/presets";
import { Toaster } from "@/components/ui/toaster";
import { NetworkStatusBanner } from "@/components/layout/network-status-banner";

const PUBLIC_PATH_PREFIXES = ["/auth/", "/share/"];

// UX-19 — `Lang` é de granularidade de idioma ("pt" cobre pt-BR/pt-PT…),
// mas o atributo `lang` do HTML quer um código BCP-47 específico. O Vectora
// só atende português brasileiro, então "pt" mapeia para "pt-BR".
const HTML_LANG_BY_SETTING: Record<Lang, string> = {
  en: "en",
  es: "es",
  pt: "pt-BR",
};

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

  // Aguarda o rehydrate do persist antes de inspecionar o store: o
  // contrato do `persist` em Zustand é assíncrono e ler o estado vazio
  // antes da hidratação faria o guard despachar para `/auth/signin`
  // mesmo com sessão válida em `sessionStorage`.
  if (
    typeof (
      useAuthStore as unknown as {
        persist?: { rehydrate?: () => Promise<void> };
      }
    ).persist?.rehydrate === "function"
  ) {
    try {
      await (
        useAuthStore as unknown as {
          persist: { rehydrate: () => Promise<void> };
        }
      ).persist.rehydrate();
    } catch {
      /* rehydrate é best-effort — não bloqueia o guard */
    }
  }

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
  // UX-19 — `lang` refletia "pt-BR" hardcoded; agora segue a preferência
  // persistida em settings-store (idioma de fato escolhido pelo usuário).
  const language = useSettingsStore((s) => s.language);
  // UX-22 — `class="dark"` vinha hardcoded no index.html; agora segue a
  // preferência persistida em settings-store (light/dark/system), com
  // reatividade imediata como já ocorre para o idioma acima.
  const theme = useSettingsStore((s) => s.theme);
  // UX-21 — agenda o aviso "sessão expira em breve" perto da raiz, uma
  // única vez por árvore (não por tela).
  useSessionExpiry();
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = HTML_LANG_BY_SETTING[language] ?? "en";
    }
  }, [language]);
  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    // `:root` já é o tema escuro (default); `.light` sobrescreve as
    // variáveis para o tema claro (ver styles.css). Por isso alternamos
    // as duas classes — não basta remover `.dark`.
    const apply = (dark: boolean) => {
      root.classList.toggle("dark", dark);
      root.classList.toggle("light", !dark);
    };

    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      apply(mq.matches);
      const handler = (e: MediaQueryListEvent) => apply(e.matches);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }

    apply(theme === "dark");
  }, [theme]);

  // UX-23 — paleta de cores (presets inspirados em temas do VS Code ou
  // customização do usuário) sobrepõe os tokens de cor via CSS custom
  // properties em :root, independente de claro/escuro/sistema acima.
  const themePreset = useSettingsStore((s) => s.themePreset);
  const customThemeColors = useSettingsStore((s) => s.customThemeColors);
  useEffect(() => {
    if (themePreset === "default") {
      applyThemeTokens(null);
      return;
    }
    if (themePreset === "custom") {
      applyThemeTokens(
        customThemeColors ? buildThemeTokens(customThemeColors) : null,
      );
      return;
    }
    const preset = THEME_PRESETS.find((p) => p.id === themePreset);
    applyThemeTokens(preset ? buildThemeTokens(preset.colors) : null);
  }, [themePreset, customThemeColors]);

  return (
    <div className="min-h-screen flex flex-col" data-route={location.pathname}>
      <NetworkStatusBanner />
      <Outlet />
      <Toaster />
    </div>
  );
}
