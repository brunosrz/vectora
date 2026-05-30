"use client";

/**
 * WorkbenchToggle (T5)
 *
 * Botão no header que abre/fecha o painel lateral do workbench. Substitui
 * o antigo botão flutuante do terminal — o atalho ⌃` continua disparando
 * o mesmo `togglePanel` no store.
 */

import { PanelRight } from "lucide-react";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";

export function WorkbenchToggle() {
  const t = useT();
  const params = useParams();
  const threadId = (params?.threadId as string | undefined) ?? "";
  // Gate de hidratação: o persist do Zustand muda `open` entre SSR e client.
  // Sem isso, o className condicional do botão diverge → hydration mismatch.
  const hydrated = useHydrated();
  const openRaw = useWorkbenchStore((s) =>
    threadId ? s.isOpen(threadId) : false,
  );
  const open = hydrated && openRaw;
  const toggle = useWorkbenchStore((s) => s.togglePanel);

  if (!threadId) return null;

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => toggle(threadId)}
      className={`hover:bg-muted/70 hover:text-foreground ${
        open ? "text-foreground" : "text-muted-foreground"
      }`}
      aria-label={t("workbench.toggle")}
      title={t("workbench.toggle")}
    >
      <PanelRight className="w-4 h-4" />
    </Button>
  );
}
