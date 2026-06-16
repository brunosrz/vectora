"use client";

/**
 * TasksTab — lista artifacts/tarefas do plano da sessão.
 */

import { FileText } from "lucide-react";
import { useT } from "@/lib/i18n";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";

export function TasksTab({ threadId }: { threadId: string }) {
  const t = useT();
  const plan = useWorkbenchStore((s) => s.getPlan(threadId));

  if (!plan.items || plan.items.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
        <FileText className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm text-foreground/60">
          {t("workbench.plan.empty")}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="divide-y divide-border/40">
          {plan.items.map((item, idx) => (
            <div
              key={idx}
              className="p-3 hover:bg-accent/40 transition-colors text-xs"
            >
              {item.title}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
