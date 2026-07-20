"use client";

/**
 * EnvironmentDialog
 *
 * Dialog do painel "Ambiente". Acessível via Avatar → "Ambiente".
 *
 * Abas:
 *   - Integrações — conectores externos + variáveis de ambiente customizadas
 *                   (absorveu a antiga aba Envs — Sprint 12)
 *   - Skills      — skills instaladas
 *   - Plugins     — plugins/MCP servers + política de ferramentas
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
import { m } from "@/lib/paraglide/messages";

const SkillsTab = lazyWithRetry(
  () => import("./tabs/skills-tab").then((mod) => ({ default: mod.SkillsTab })),
  "skills-tab",
);
const PluginsTab = lazyWithRetry(
  () =>
    import("./tabs/plugins-tab").then((mod) => ({ default: mod.PluginsTab })),
  "plugins-tab",
);
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
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2">
            <TabsTrigger value="integracoes" className="rounded-md text-xs">
              Integrações
            </TabsTrigger>
            <TabsTrigger value="skills" className="rounded-md text-xs">
              Skills
            </TabsTrigger>
            <TabsTrigger value="plugins" className="rounded-md text-xs">
              Plugins
            </TabsTrigger>
            <TabsTrigger
              value="provider_routing"
              className="rounded-md text-xs"
            >
              Provider Routing
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
            <ErrorBoundary>
              <Suspense fallback={<TabFallback />}>
                <TabsContent value="integracoes" className="mt-0">
                  <IntegracoesTab />
                </TabsContent>
                <TabsContent value="skills" className="mt-0">
                  <SkillsTab />
                </TabsContent>
                <TabsContent value="plugins" className="mt-0">
                  <PluginsTab />
                </TabsContent>
                <TabsContent value="provider_routing" className="mt-0">
                  <ProviderRoutingTab />
                </TabsContent>
              </Suspense>
            </ErrorBoundary>
          </div>
        </Tabs>
      </ResizableDialogContent>
    </Dialog>
  );
}
