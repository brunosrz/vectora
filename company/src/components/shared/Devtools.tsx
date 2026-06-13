import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { TanStackDevtools } from "@tanstack/react-devtools";
import TanStackQueryDevtools from "#/integrations/tanstack-query/devtools";

/**
 * Devtools — extraído do __root.tsx porque o plugin @tanstack/devtools-vite
 * remove o elemento <TanStackDevtools> no build de produção. O return SEM
 * parênteses é proposital: após a remoção sobra `return ;`, que é válido —
 * com parênteses sobraria `return ( );`, que quebra o parse.
 */
export default function Devtools() {
  if (!import.meta.env.DEV) return null;
  // prettier-ignore
  return <TanStackDevtools
    config={{ position: "bottom-right" }}
    plugins={[
      {
        name: "Tanstack Router",
        render: <TanStackRouterDevtoolsPanel />,
      },
      TanStackQueryDevtools,
    ]}
  />;
}
