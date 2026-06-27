"use client";

/**
 * AdminDialog (P4)
 *
 * Painel de Administração como dialog próprio — separado do `SettingsDialog`
 * de preferências do usuário, já que `AdminTab` reúne vários sub-painéis
 * (Usuários, Ferramentas, Pastas Seguras, Sistema, Config) com escopo de
 * servidor/instância, não de conta pessoal. Acessível via menu do usuário
 * → "Administração" (root/admin only).
 *
 * `AdminTab` é code-split via `lazy()` — o conteúdo só é carregado quando
 * o dialog é aberto pela primeira vez.
 */

import { Suspense } from "react";
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResizableDialogContent } from "@/components/ui/resizable-dialog";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { lazyWithRetry } from "@/lib/lazy-with-retry";
import { useAdministracaoDialogStore } from "@/lib/stores/administracao-dialog-store";
import { m as msg } from "@/lib/paraglide/messages";
import { SettingsGroupTabs } from "@/components/settings/settings-group-tabs";
const AdminTab = lazyWithRetry(
  () => import("./admin-tab").then((m) => ({ default: m.AdminTab })),
  "admin-tab",
);

function AdminFallback() {
  return (
    <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
      {msg.admin_loading()}
    </div>
  );
}

export function AdminDialog() {
  const open = useAdministracaoDialogStore((s) => s.open);
  const setOpen = useAdministracaoDialogStore((s) => s.setOpen);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <ResizableDialogContent
        storageKey="administracao"
        defaultWidth={640}
        defaultHeight={520}
        className="p-6 gap-4"
      >
        <SettingsGroupTabs active="admin" />
        <DialogHeader>
          <DialogTitle>{msg.admin_dialog_title()}</DialogTitle>
          <DialogDescription className="sr-only">
            {msg.admin_dialog_desc()}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pt-2">
          <ErrorBoundary>
            <Suspense fallback={<AdminFallback />}>
              <AdminTab />
            </Suspense>
          </ErrorBoundary>
        </div>
      </ResizableDialogContent>
    </Dialog>
  );
}
