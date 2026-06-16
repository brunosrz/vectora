import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";

import { router, queryClient } from "./router";
import { getLocale, setLocale } from "@/lib/paraglide/runtime";
import { useSettingsStore } from "@/lib/stores/settings-store";
import "./styles.css";

// Sincroniza o locale do Paraglide com o idioma persistido antes de renderizar,
// para que as mensagens m.* saiam no idioma correto já no primeiro paint.
{
  const lang = useSettingsStore.getState().language;
  if (getLocale() !== lang) setLocale(lang, { reload: false });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("#root não encontrado em index.html");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <TooltipProvider delayDuration={200}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} context={{ queryClient }} />
      </QueryClientProvider>
    </TooltipProvider>
  </React.StrictMode>,
);
