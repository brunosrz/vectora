"use client";

/**
 * SettingsDialog — Bloco L2
 *
 * Dialog de configurações do usuário. Acessível via Avatar → "Configurações".
 *
 * Abas:
 *   - Conta       — email, role, alterar senha
 *   - Preferências — tema, histórico, system prompt (L3/L4)
 *   - Memória     — placeholder (Bloco N)
 *   - Integrações — placeholder (Bloco O)
 *   - Envs        — env vars por usuário (Bloco C10)
 *
 * Administração (root/admin only) é um dialog próprio — `AdminDialog`,
 * aberto via menu do usuário (P4) — não uma aba aqui.
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
  useSettingsDialogStore,
  type SettingsTab,
} from "@/lib/stores/settings-dialog-store";

const ContaTab = lazy(() =>
  import("./tabs/conta-tab").then((m) => ({ default: m.ContaTab })),
);
const EnvsTab = lazy(() =>
  import("./tabs/envs-tab").then((m) => ({ default: m.EnvsTab })),
);
const IntegracoesTab = lazy(() =>
  import("./tabs/integracoes-tab").then((m) => ({
    default: m.IntegracoesTab,
  })),
);
const MemoriaTab = lazy(() =>
  import("./tabs/memoria-tab").then((m) => ({ default: m.MemoriaTab })),
);
const PluginsTab = lazy(() =>
  import("./tabs/plugins-tab").then((m) => ({ default: m.PluginsTab })),
);
const PreferenciasTab = lazy(() =>
  import("./tabs/preferencias-tab").then((m) => ({
    default: m.PreferenciasTab,
  })),
);
const SkillsTab = lazy(() =>
  import("./tabs/skills-tab").then((m) => ({ default: m.SkillsTab })),
);

function TabFallback() {
  return (
    <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
      Carregando…
    </div>
  );
}

export function SettingsDialog() {
  const open = useSettingsDialogStore((s) => s.open);
  const setOpen = useSettingsDialogStore((s) => s.setOpen);
  const tab = useSettingsDialogStore((s) => s.tab);
  const setTab = useSettingsDialogStore((s) => s.setTab);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-[560px] max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Configurações</DialogTitle>
          <DialogDescription className="sr-only">
            Gerencie sua conta, preferências, memória, integrações e variáveis
            de ambiente.
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as SettingsTab)}
          className="flex-1 overflow-hidden flex flex-col"
        >
          <TabsList className="flex-wrap h-auto gap-1 justify-start bg-transparent p-0 border-b rounded-none pb-2">
            <TabsTrigger value="conta" className="rounded-md text-xs">
              Conta
            </TabsTrigger>
            <TabsTrigger value="preferencias" className="rounded-md text-xs">
              Preferências
            </TabsTrigger>
            <TabsTrigger value="memoria" className="rounded-md text-xs">
              Memória
            </TabsTrigger>
            <TabsTrigger value="integracoes" className="rounded-md text-xs">
              Integrações
            </TabsTrigger>
            <TabsTrigger value="plugins" className="rounded-md text-xs">
              Plugins
            </TabsTrigger>
            <TabsTrigger value="skills" className="rounded-md text-xs">
              Skills
            </TabsTrigger>
            <TabsTrigger value="envs" className="rounded-md text-xs">
              Envs
            </TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
            <Suspense fallback={<TabFallback />}>
              <TabsContent value="conta" className="mt-0">
                <ContaTab />
              </TabsContent>
              <TabsContent value="preferencias" className="mt-0">
                <PreferenciasTab />
              </TabsContent>
              <TabsContent value="memoria" className="mt-0">
                <MemoriaTab />
              </TabsContent>
              <TabsContent value="integracoes" className="mt-0">
                <IntegracoesTab />
              </TabsContent>
              <TabsContent value="plugins" className="mt-0">
                <PluginsTab />
              </TabsContent>
              <TabsContent value="skills" className="mt-0">
                <SkillsTab />
              </TabsContent>
              <TabsContent value="envs" className="mt-0">
                <EnvsTab />
              </TabsContent>
            </Suspense>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
