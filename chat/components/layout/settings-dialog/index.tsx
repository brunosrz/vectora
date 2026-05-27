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
 *   - Administração — root/admin only (Bloco P)
 */

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/lib/stores/auth-store";
import { ContaTab } from "./tabs/conta-tab";
import { PreferenciasTab } from "./tabs/preferencias-tab";
import { MemoriaTab } from "./tabs/memoria-tab";
import { IntegracoesTab } from "./tabs/integracoes-tab";
import { EnvsTab } from "./tabs/envs-tab";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const user = useAuthStore((s) => s.user);
  const isAdminOrRoot = user?.role === "root" || user?.role === "admin";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px] max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Configurações</DialogTitle>
        </DialogHeader>

        <Tabs
          defaultValue="conta"
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
            <TabsTrigger value="envs" className="rounded-md text-xs">
              Envs
            </TabsTrigger>
            {isAdminOrRoot && (
              <TabsTrigger value="admin" className="rounded-md text-xs">
                Administração
              </TabsTrigger>
            )}
          </TabsList>

          <div className="flex-1 overflow-y-auto pt-4">
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
            <TabsContent value="envs" className="mt-0">
              <EnvsTab />
            </TabsContent>
            {isAdminOrRoot && (
              <TabsContent value="admin" className="mt-0">
                <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">
                    Painel de Administração
                  </p>
                  <p className="text-xs text-muted-foreground max-w-[260px]">
                    Gerenciamento de usuários, permissões e configurações do
                    servidor. Disponível no Bloco P.
                  </p>
                </div>
              </TabsContent>
            )}
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
