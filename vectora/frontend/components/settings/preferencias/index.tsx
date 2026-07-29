"use client";

/**
 * PreferenciasDialog
 *
 * Dialog de preferências do usuário. Acessível via Avatar → "Preferências".
 *
 * Abas (nessa ordem):
 *   - Geral   — tema, idioma, system prompt e treinamento
 *   - Memória — memórias salvas pelo agente
 *   - Conta   — email, role, alterar senha
 *
 * "Ambiente" (Envs/Skills/Plugins/Integrações) e "Administração" (root/admin)
 * são dialogs próprios — ver `EnvironmentDialog` e `AdminDialog`.
 *
 * Cada tab é code-split via `lazy()` — o bundle inicial do app não paga
 * o custo de uma feature secundária. O dialog em si carrega imediato
 * (componentes Radix já estão no shell), mas o conteúdo da tab ativa
 * vem on-demand.
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
  usePreferenciasDialogStore,
  type PreferenciasTab,
} from "@/lib/stores/preferencias-dialog-store";
import { SettingsGroupTabs } from "@/components/settings/settings-group-tabs";
import { m } from "@/lib/paraglide/messages";

const ContaTab = lazyWithRetry(
  () => import("./tabs/conta-tab").then((mod) => ({ default: mod.ContaTab })),
  "conta-tab",
);
const MemoriaTab = lazyWithRetry(
  () =>
    import("./tabs/memoria-tab").then((mod) => ({ default: mod.MemoriaTab })),
  "memoria-tab",
);
const PreferenciasTab = lazyWithRetry(
  () =>
    import("./tabs/preferencias-tab").then((mod) => ({
      default: mod.PreferenciasTab,
    })),
  "preferencias-tab",
);

function TabFallback() {
  return (
    <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
      Carregando…
    </div>
  );
}

export function PreferenciasDialog() {
  const open = usePreferenciasDialogStore((s) => s.open);
  const setOpen = usePreferenciasDialogStore((s) => s.setOpen);
  const tab = usePreferenciasDialogStore((s) => s.tab);
  const setTab = usePreferenciasDialogStore((s) => s.setTab);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <ResizableDialogContent
        storageKey="preferencias"
        defaultWidth={560}
        defaultHeight={520}
        className="p-6 gap-4"
      >
        <SettingsGroupTabs active="preferencias" />
        {/* DialogHeader oculto: o Radix Dialog exige um título acessível; o
            rótulo visível vem do SettingsGroupTabs acima. */}
        <DialogHeader className="sr-only">
          <DialogTitle>{m.preferencias_dialog_title()}</DialogTitle>
          <DialogDescription>{m.preferencias_dialog_desc()}</DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as PreferenciasTab)}
          className="flex-1 overflow-hidden flex flex-col"
        >
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2 -ml-3">
            <TabsTrigger value="preferencias" className="rounded-md text-xs">
              Geral
            </TabsTrigger>
            <TabsTrigger value="memoria" className="rounded-md text-xs">
              Memória
            </TabsTrigger>
            <TabsTrigger value="conta" className="rounded-md text-xs">
              Conta
            </TabsTrigger>
          </TabsList>

          {/* pr-2: mantém a barra de rolagem nativa dentro do padding lateral
              do dialog (p-6), em vez de colada ao conteúdo — sem trocar por
              Radix ScrollArea, cujo Viewport mede largura por `display:table`
              e estoura o modal com conteúdo sem quebra (paths/URLs/chaves),
              já revertido nesse motivo no wizard (ver StepWorkspaceSelect). */}
          <div className="flex-1 overflow-y-auto pt-4 pr-2">
            <ErrorBoundary>
              <Suspense fallback={<TabFallback />}>
                <TabsContent value="preferencias" className="mt-0">
                  <PreferenciasTab />
                </TabsContent>
                <TabsContent value="memoria" className="mt-0">
                  <MemoriaTab />
                </TabsContent>
                <TabsContent value="conta" className="mt-0">
                  <ContaTab />
                </TabsContent>
              </Suspense>
            </ErrorBoundary>
          </div>
        </Tabs>
      </ResizableDialogContent>
    </Dialog>
  );
}
