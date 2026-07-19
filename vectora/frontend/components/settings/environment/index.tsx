"use client";

/**
 * EnvironmentDialog
 *
 * Dialog do painel "Ambiente". Acessível via Avatar → "Ambiente".
 *
 * Abas:
 *   - Envs        — variáveis de ambiente por usuário
 *   - Skills      — skills instaladas
 *   - Plugins     — plugins/MCP servers + política de ferramentas
 *   - Gateways    — modelos de LLM locais/dinâmicos (Ollama)
 *   - Integrações — conectores externos
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

const EnvsTab = lazyWithRetry(
  () => import("./tabs/envs-tab").then((mod) => ({ default: mod.EnvsTab })),
  "envs-tab",
);
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
const GatewaysTab = lazyWithRetry(
  () =>
    import("./tabs/gateways-tab").then((mod) => ({
      default: mod.GatewaysTab,
    })),
  "gateways-tab",
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
            <TabsTrigger value="envs" className="rounded-md text-xs">
              Envs
            </TabsTrigger>
            <TabsTrigger value="skills" className="rounded-md text-xs">
              Skills
            </TabsTrigger>
            <TabsTrigger value="plugins" className="rounded-md text-xs">
              Plugins
            </TabsTrigger>
            <TabsTrigger value="gateways" className="rounded-md text-xs">
              Gateways
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
            <ErrorBoundary>
              <Suspense fallback={<TabFallback />}>
                <TabsContent value="integracoes" className="mt-0">
                  <IntegracoesTab />
                </TabsContent>
                <TabsContent value="envs" className="mt-0">
                  <EnvsTab />
                </TabsContent>
                <TabsContent value="skills" className="mt-0">
                  <SkillsTab />
                </TabsContent>
                <TabsContent value="plugins" className="mt-0">
                  <PluginsTab />
                </TabsContent>
                <TabsContent value="gateways" className="mt-0">
                  <GatewaysTab />
                </TabsContent>
              </Suspense>
            </ErrorBoundary>
          </div>
        </Tabs>
      </ResizableDialogContent>
    </Dialog>
  );
}
