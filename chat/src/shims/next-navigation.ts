/**
 * Shim para `next/navigation` — substitui as APIs do Next.js App Router
 * pelas equivalentes do TanStack Router.
 *
 * Mapeado via `resolve.alias` no `vite.config.ts`. Os componentes
 * importam `from "next/navigation"` e o Vite redireciona para este arquivo.
 */

import {
  useNavigate,
  useLocation,
  useParams as useTanstackParams,
} from "@tanstack/react-router";

type Href = string;

interface RouterShim {
  push(href: Href): void;
  replace(href: Href): void;
  back(): void;
  forward(): void;
  refresh(): void;
  prefetch(href: Href): void;
}

export function useRouter(): RouterShim {
  const navigate = useNavigate();
  return {
    // `as never` evita o type-check estrito do TanStack Router sobre `to`:
    // este shim recebe paths em runtime (do código herdado do Next.js) que
    // o type system não consegue validar contra o routeTree.
    push: (href) => void navigate({ to: href as never }),
    replace: (href) => void navigate({ to: href as never, replace: true }),
    back: () => window.history.back(),
    forward: () => window.history.forward(),
    refresh: () => window.location.reload(),
    prefetch: () => {
      // TanStack Router faz prefetch automático via `defaultPreload: 'intent'`
    },
  };
}

export function usePathname(): string {
  const location = useLocation();
  return location.pathname;
}

export function useSearchParams(): URLSearchParams {
  const location = useLocation();
  // location.searchStr não está no tipo público do TanStack Router em todas as
  // versões — fazemos cast para acessar quando disponível.
  const maybeSearchStr = (location as { searchStr?: string }).searchStr;
  if (typeof maybeSearchStr === "string") {
    return new URLSearchParams(maybeSearchStr);
  }
  // Fallback: usa window.location.search.
  if (typeof window !== "undefined") {
    return new URLSearchParams(window.location.search);
  }
  return new URLSearchParams();
}

export function useParams<
  T extends Record<string, string> = Record<string, string>,
>(): T {
  // O `useParams` do TanStack Router muda a forma do options entre versões;
  // o cast intermediário absorve a diferença sem nos prender a um shape.
  return (useTanstackParams as unknown as (opts: { strict: false }) => T)({
    strict: false,
  });
}

export function redirect(href: Href): never {
  if (typeof window !== "undefined") {
    window.location.replace(href);
  }
  throw new Error(`redirect: ${href}`);
}

export function notFound(): never {
  throw new Error("notFound()");
}
