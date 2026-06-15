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
 *   - Integrações — conectores externos
 *
 * "Preferências" (Conta/Preferências/Memória) e "Administração" (root/admin)
 * são dialogs próprios — ver `PreferenciasDialog` e `AdminDialog`.
 *
 * Cada tab é code-split via `lazy()` — o bundle inicial do app não paga
 * o custo de uma feature secundária.
 */

import { Suspense, lazy } from "react";
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResizableDialogContent } from "@/components/ui/resizable-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useEnvironmentDialogStore,
  type EnvironmentTab,
} from "@/lib/stores/environment-dialog-store";

const EnvsTab = lazy(() =>
  import("./tabs/envs-tab").then((m) => ({ default: m.EnvsTab })),
);
const SkillsTab = lazy(() =>
  import("./tabs/skills-tab").then((m) => ({ default: m.SkillsTab })),
);
const PluginsTab = lazy(() =>
  import("./tabs/plugins-tab").then((m) => ({ default: m.PluginsTab })),
);
const IntegracoesTab = lazy(() =>
  import("./tabs/integracoes-tab").then((m) => ({
    default: m.IntegracoesTab,
  })),
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
        defaultWidth={560}
        defaultHeight={560}
        className="p-6 gap-4"
      >
        <DialogHeader>
          <DialogTitle>Ambiente</DialogTitle>
          <DialogDescription className="sr-only">
            Gerencie variáveis de ambiente, skills, plugins e integrações.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as EnvironmentTab)}
          className="flex-1 overflow-hidden flex flex-col"
        >
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2">
            <TabsTrigger value="envs" className="rounded-md text-xs">
              Envs
            </TabsTrigger>
            <TabsTrigger value="skills" className="rounded-md text-xs">
              Skills
            </TabsTrigger>
            <TabsTrigger value="plugins" className="rounded-md text-xs">
              Plugins
            </TabsTrigger>
            <TabsTrigger value="integracoes" className="rounded-md text-xs">
              Integrações
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
            <Suspense fallback={<TabFallback />}>
              <TabsContent value="envs" className="mt-0">
                <EnvsTab />
              </TabsContent>
              <TabsContent value="skills" className="mt-0">
                <SkillsTab />
              </TabsContent>
              <TabsContent value="plugins" className="mt-0">
                <PluginsTab />
              </TabsContent>
              <TabsContent value="integracoes" className="mt-0">
                <IntegracoesTab />
              </TabsContent>
            </Suspense>
          </div>
        </Tabs>
      </ResizableDialogContent>
    </Dialog>
  );
}
