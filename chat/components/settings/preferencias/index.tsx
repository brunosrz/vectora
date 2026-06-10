"use client";

/**
 * PreferenciasDialog
 *
 * Dialog de preferências do usuário. Acessível via Avatar → "Preferências".
 *
 * Abas:
 *   - Conta        — email, role, alterar senha
 *   - Preferências — tema, histórico, system prompt
 *   - Memória      — memórias salvas pelo agente
 *
 * "Ambiente" (Envs/Skills/Plugins/Integrações) e "Administração" (root/admin)
 * são dialogs próprios — ver `AmbienteDialog` e `AdminDialog`.
 *
 * Cada tab é code-split via `lazy()` — o bundle inicial do app não paga
 * o custo de uma feature secundária. O dialog em si carrega imediato
 * (componentes Radix já estão no shell), mas o conteúdo da tab ativa
 * vem on-demand.
 */

import { Suspense, lazy } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  usePreferenciasDialogStore,
  type PreferenciasTab,
} from "@/lib/stores/preferencias-dialog-store";

const ContaTab = lazy(() =>
  import("./tabs/conta-tab").then((m) => ({ default: m.ContaTab })),
);
const MemoriaTab = lazy(() =>
  import("./tabs/memoria-tab").then((m) => ({ default: m.MemoriaTab })),
);
const PreferenciasTab = lazy(() =>
  import("./tabs/preferencias-tab").then((m) => ({
    default: m.PreferenciasTab,
  })),
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
      <DialogContent className="sm:max-w-[560px] max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Preferências</DialogTitle>
          <DialogDescription className="sr-only">
            Gerencie sua conta, preferências e memória.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as PreferenciasTab)}
          className="flex-1 overflow-hidden flex flex-col"
        >
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2">
            <TabsTrigger value="preferencias" className="rounded-md text-xs">
              Preferências
            </TabsTrigger>
            <TabsTrigger value="conta" className="rounded-md text-xs">
              Conta
            </TabsTrigger>
            <TabsTrigger value="memoria" className="rounded-md text-xs">
              Memória
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
            <Suspense fallback={<TabFallback />}>
              <TabsContent value="preferencias" className="mt-0">
                <PreferenciasTab />
              </TabsContent>
              <TabsContent value="conta" className="mt-0">
                <ContaTab />
              </TabsContent>
              <TabsContent value="memoria" className="mt-0">
                <MemoriaTab />
              </TabsContent>
            </Suspense>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
