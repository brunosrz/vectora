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

import { Suspense, lazy } from "react";
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResizableDialogContent } from "@/components/ui/resizable-dialog";
import { useAdministracaoDialogStore } from "@/lib/stores/administracao-dialog-store";
import { useT } from "@/lib/i18n";

const AdminTab = lazy(() =>
  import("./admin-tab").then((m) => ({ default: m.AdminTab })),
);

function AdminFallback() {
  const t = useT();
  return (
    <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
      {t("admin.loading")}
    </div>
  );
}

export function AdminDialog() {
  const t = useT();
  const open = useAdministracaoDialogStore((s) => s.open);
  const setOpen = useAdministracaoDialogStore((s) => s.setOpen);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <ResizableDialogContent
        storageKey="administracao"
        defaultWidth={640}
        defaultHeight={480}
        className="p-6 gap-4"
      >
        <DialogHeader>
          <DialogTitle>{t("admin.dialog_title")}</DialogTitle>
          <DialogDescription className="sr-only">
            {t("admin.dialog_desc")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pt-2">
          <Suspense fallback={<AdminFallback />}>
            <AdminTab />
          </Suspense>
        </div>
      </ResizableDialogContent>
    </Dialog>
  );
}
