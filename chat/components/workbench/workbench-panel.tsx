"use client";

/**
 * WorkbenchPanel (Bloco T cont., T5 + T10.1)
 *
 * Container do painel lateral direito multi-aba. Substitui o uso direto do
 * TerminalPanel — agora o terminal é apenas uma das abas, junto a Arquivos
 * (T6), Diff (T7) e Plano (T8). Espelha o painel lateral do Claude Code.
 *
 * T10.1 — Chips de contagem por aba:
 *   - terminal: número de PTYs abertos na sessão
 *   - files: número de arquivos pinados (T10.2)
 *   - diff: `+N -M` quando há mudanças, ou número de arquivos modificados
 *   - plan: número de artifacts na sessão
 *
 * O badge usa o cache do workbench-store (T11) — não dispara fetch só para
 * contar. Em SSR / antes de hidratar, o badge fica vazio (consistente com
 * o padrão `useHydrated`).
 */

import {
  FileText,
  FolderTree,
  GitCompare,
  TerminalSquare,
  X,
} from "lucide-react";
import { useT } from "@/lib/i18n";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import {
  useWorkbenchStore,
  WORKBENCH_TABS,
  type WorkbenchTab,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
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

/** Lê o cache do workbench-store e devolve o texto do chip por aba. */
function useTabBadge(
  threadId: string,
  workspaceId: string,
  tab: WorkbenchTab,
  hydrated: boolean,
): string | null {
  // Selectors são chamados incondicionalmente — Rules of Hooks. Filtramos por
  // aba no return e gateamos por `hydrated` para evitar mismatch SSR (T11).
  const terminals = useWorkbenchStore((s) => s.list(threadId));
  const pinned = useWorkbenchStore((s) => s.pinnedFiles[threadId]?.length ?? 0);
  const diffSummary = useWorkbenchStore((s) => s.getDiff(workspaceId).summary);
  const planItems = useWorkbenchStore((s) => s.getPlan(threadId).items.length);

  if (!hydrated) return null;
  switch (tab) {
    case "terminal":
      return terminals.length > 0 ? String(terminals.length) : null;
    case "files":
      return pinned > 0 ? String(pinned) : null;
    case "diff":
      if (!diffSummary || !diffSummary.is_git_repo) return null;
      if (diffSummary.files.length === 0) return null;
      return `+${diffSummary.total_additions} −${diffSummary.total_deletions}`;
    case "plan":
      return planItems > 0 ? String(planItems) : null;
  }
}

function TabButton({
  tab,
  active,
  threadId,
  workspaceId,
  hydrated,
  onSelect,
  label,
}: {
  tab: WorkbenchTab;
  active: boolean;
  threadId: string;
  workspaceId: string;
  hydrated: boolean;
  onSelect: () => void;
  label: string;
}) {
  const badge = useTabBadge(threadId, workspaceId, tab, hydrated);
  const Icon = TAB_ICON[tab];
  return (
    <button
      onClick={onSelect}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs select-none transition-colors ${
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}
      title={label}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
      {badge && (
        <span
          className={`ml-0.5 inline-flex items-center justify-center min-w-[1.25rem] h-4 px-1 rounded-full text-[10px] font-mono leading-none ${
            tab === "diff"
              ? "bg-amber-500/15 text-amber-500"
              : "bg-primary/15 text-primary"
          }`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

export function WorkbenchPanel({ threadId }: WorkbenchPanelProps) {
  const t = useT();
  const hydrated = useHydrated();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";
  const activeTab = useWorkbenchStore((s) => s.getActiveTab(threadId));
  const setActiveTab = useWorkbenchStore((s) => s.setActiveTab);
  const setPanelOpen = useWorkbenchStore((s) => s.setPanelOpen);

  return (
    <div className="h-full flex flex-col bg-background border-l border-border/60">
      {/* Barra de abas */}
      <div className="flex items-center gap-0.5 px-1.5 py-1 border-b border-border/60 bg-muted/20">
        <div className="flex items-center gap-0.5 flex-1 overflow-x-auto">
          {WORKBENCH_TABS.map((tab) => (
            <TabButton
              key={tab}
              tab={tab}
              active={tab === activeTab}
              threadId={threadId}
              workspaceId={wsId}
              hydrated={hydrated}
              onSelect={() => setActiveTab(threadId, tab)}
              label={t(`workbench.tab.${tab}`)}
            />
          ))}
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
