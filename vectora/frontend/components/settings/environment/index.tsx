"use client";

/**
 * EnvironmentDialog
 *
 * Dialog do painel "Ambiente". Acessível via Avatar → "Ambiente".
 *
 * Abas:
 *   - Integrações — conectores externos + variáveis de ambiente customizadas
 *   - Provider Routing — modelos de LLM locais/dinâmicos (Ollama)
 *
 * "Preferências" (Conta/Preferências/Memória) e "Administração" (root/admin)
 * são dialogs próprios — ver `PreferenciasDialog` e `AdminDialog`.
 *
 * Cada tab é code-split via `lazy()` — o bundle inicial do app não paga
 * o custo de uma feature secundária.
 */

import { Suspense } from "react";
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResizableDialogContent } from "@/components/ui/resizable-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { lazyWithRetry } from "@/lib/lazy-with-retry";
import {
  useEnvironmentDialogStore,
  type EnvironmentTab,
} from "@/lib/stores/environment-dialog-store";
import { SettingsGroupTabs } from "@/components/settings/settings-group-tabs";
import { useFeatureFlags } from "@/lib/hooks/use-feature-flags";
import { m } from "@/lib/paraglide/messages";

const IntegracoesTab = lazyWithRetry(
  () =>
    import("./tabs/integracoes-tab").then((mod) => ({
      default: mod.IntegracoesTab,
    })),
  "integracoes-tab",
);
const ProviderRoutingTab = lazyWithRetry(
  () =>
    import("./tabs/provider-routing-tab").then((mod) => ({
      default: mod.ProviderRoutingTab,
    })),
  "provider-routing-tab",
);
const ConnectTab = lazyWithRetry(
  () =>
    import("./tabs/connect-tab").then((mod) => ({
      default: mod.ConnectTab,
    })),
  "connect-tab",
);

function TabFallback() {
  return (
    <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
      Carregando…
    </div>
  );
}

export function EnvironmentDialog() {
  const open = useEnvironmentDialogStore((s) => s.open);
  const setOpen = useEnvironmentDialogStore((s) => s.setOpen);
  const tab = useEnvironmentDialogStore((s) => s.tab);
  const setTab = useEnvironmentDialogStore((s) => s.setTab);
  const { enableFeaturesBeta } = useFeatureFlags();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <ResizableDialogContent
        storageKey="environment"
        defaultWidth={560}
        defaultHeight={520}
        className="p-6 gap-4"
      >
        <SettingsGroupTabs active="environment" />
        {/* DialogHeader oculto: o Radix Dialog exige um título acessível; o
            rótulo visível vem do SettingsGroupTabs acima. */}
        <DialogHeader className="sr-only">
          <DialogTitle>{m.environment_dialog_title()}</DialogTitle>
          <DialogDescription>{m.environment_dialog_desc()}</DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as EnvironmentTab)}
          className="flex-1 overflow-hidden flex flex-col"
        >
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2 -ml-3">
            <TabsTrigger value="integracoes" className="rounded-md text-xs">
              Integrações
            </TabsTrigger>
            <TabsTrigger
              value="provider_routing"
              className="rounded-md text-xs"
            >
              Provider Routing
            </TabsTrigger>
            {enableFeaturesBeta && (
              <TabsTrigger value="connect" className="rounded-md text-xs">
                Connect
              </TabsTrigger>
            )}
          </TabsList>

          {/* pr-2: mantém a barra de rolagem nativa dentro do padding lateral
              do dialog (p-6), em vez de colada ao conteúdo — sem Radix
              ScrollArea (Viewport mede largura por `display:table` e estoura
              o modal com conteúdo sem quebra: URLs, chaves mascaradas). */}
          <div className="flex-1 overflow-y-auto pt-4 custom-scrollbar scroll-gutter-stable">
            <ErrorBoundary>
              <Suspense fallback={<TabFallback />}>
                <TabsContent value="integracoes" className="mt-0">
                  <IntegracoesTab />
                </TabsContent>
                <TabsContent value="provider_routing" className="mt-0">
                  <ProviderRoutingTab />
                </TabsContent>
                {enableFeaturesBeta && (
                  <TabsContent value="connect" className="mt-0">
                    <ConnectTab />
                  </TabsContent>
                )}
              </Suspense>
            </ErrorBoundary>
          </div>
        </Tabs>
      </ResizableDialogContent>
    </Dialog>
  );
}
