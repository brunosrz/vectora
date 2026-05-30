"use client";

/**
 * WorkbenchPanel (Bloco T cont., T5)
 *
 * Container do painel lateral direito multi-aba. Substitui o uso direto do
 * TerminalPanel — agora o terminal é apenas uma das abas, junto a Arquivos
 * (T6), Diff (T7) e Plano (T8). Espelha o painel lateral do Claude Code.
 */

import {
  FileText,
  FolderTree,
  GitCompare,
  TerminalSquare,
  X,
} from "lucide-react";
import { useT } from "@/lib/i18n";
import {
  useWorkbenchStore,
  WORKBENCH_TABS,
  type WorkbenchTab,
} from "@/lib/stores/workbench-store";
import { TerminalPanel } from "@/components/terminal/terminal-panel";
import { FilesTab } from "./tabs/files-tab";
import { DiffTab } from "./tabs/diff-tab";
import { PlanTab } from "./tabs/plan-tab";

interface WorkbenchPanelProps {
  threadId: string;
}

const TAB_ICON: Record<
  WorkbenchTab,
  React.ComponentType<{ className?: string }>
> = {
  terminal: TerminalSquare,
  files: FolderTree,
  diff: GitCompare,
  plan: FileText,
};

export function WorkbenchPanel({ threadId }: WorkbenchPanelProps) {
  const t = useT();
  const activeTab = useWorkbenchStore((s) => s.getActiveTab(threadId));
  const setActiveTab = useWorkbenchStore((s) => s.setActiveTab);
  const setPanelOpen = useWorkbenchStore((s) => s.setPanelOpen);

  return (
    <div className="h-full flex flex-col bg-background border-l border-border/60">
      {/* Barra de abas */}
      <div className="flex items-center gap-0.5 px-1.5 py-1 border-b border-border/60 bg-muted/20">
        <div className="flex items-center gap-0.5 flex-1 overflow-x-auto">
          {WORKBENCH_TABS.map((tab) => {
            const Icon = TAB_ICON[tab];
            const active = tab === activeTab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(threadId, tab)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs select-none transition-colors ${
                  active
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
                title={t(`workbench.tab.${tab}`)}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t(`workbench.tab.${tab}`)}</span>
              </button>
            );
          })}
        </div>
        <button
          onClick={() => setPanelOpen(threadId, false)}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50"
          title={t("workbench.close")}
          aria-label={t("workbench.close")}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Body — só monta a aba ativa (poupa recurso) */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "terminal" && <TerminalPanel threadId={threadId} />}
        {activeTab === "files" && <FilesTab threadId={threadId} />}
        {activeTab === "diff" && <DiffTab threadId={threadId} />}
        {activeTab === "plan" && <PlanTab threadId={threadId} />}
      </div>
    </div>
  );
}
