"use client";

/**
 * WorkbenchPanel — container do painel lateral direito multi-aba. O terminal
 * é uma das abas, junto a Arquivos, Diff e Plano.
 *
 * Cada aba mostra um chip de contagem lido do cache do workbench-store (não
 * dispara fetch só para contar):
 *   - terminal: número de PTYs abertos na sessão
 *   - files: número de arquivos fixados
 *   - diff: `+N -M` quando há mudanças
 *   - plan: número de artifacts na sessão
 *
 * Antes de hidratar, o badge fica vazio (consistente com `useHydrated`) para
 * evitar divergência SSR/cliente.
 */

import {
  FileText,
  FolderTree,
  GitCompare,
  TerminalSquare,
  X,
} from "lucide-react";
import { useT } from "@/lib/i18n";
import { useWorkspaceWatcher } from "@/lib/hooks/use-workspace-watcher";
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
  /** Injetar @path no chat ao clicar no botão @ de um arquivo/pasta. */
  onAddToContext?: (path: string) => void;
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
  const t = useT();
  const badge = useTabBadge(threadId, workspaceId, tab, hydrated);
  const pending = useWorkbenchStore((s) =>
    tab === "files"
      ? Boolean(s.pending[workspaceId]?.files)
      : tab === "diff"
        ? Boolean(s.pending[workspaceId]?.diff)
        : false,
  );
  const showPending = hydrated && pending && !active;
  const Icon = TAB_ICON[tab];
  return (
    <button
      onClick={onSelect}
      className={`flex items-center justify-start gap-1.5 px-2 py-1 rounded-md text-xs select-none transition-colors w-full ${
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}
      title={label}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="truncate">{label}</span>
      {showPending && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0"
          aria-label={t("workbench.tab.pending")}
          title={t("workbench.tab.pending")}
        />
      )}
      {badge &&
        (tab === "terminal" ? (
          // Contagem de PTYs — texto pequeno sem fundo/padding para não
          // competir visualmente com o label da aba.
          <span className="text-[10px] text-muted-foreground/70 leading-none tabular-nums">
            {badge}
          </span>
        ) : (
          <span
            className={`ml-0.5 inline-flex items-center justify-center min-w-[1.25rem] h-4 px-1 rounded-full text-[10px] font-mono leading-none ${
              tab === "diff"
                ? "bg-amber-500/15 text-amber-500"
                : "bg-primary/15 text-primary"
            }`}
          >
            {badge}
          </span>
        ))}
    </button>
  );
}

export function WorkbenchPanel({
  threadId,
  onAddToContext,
}: WorkbenchPanelProps) {
  const t = useT();
  const hydrated = useHydrated();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";
  const activeTab = useWorkbenchStore((s) => s.getActiveTab(threadId));
  const setActiveTab = useWorkbenchStore((s) => s.setActiveTab);
  const setPanelOpen = useWorkbenchStore((s) => s.setPanelOpen);

  // A.17 — file watcher SSE: dispara markPending quando arquivos mudam
  useWorkspaceWatcher(wsId || undefined);

  return (
    <div className="h-full flex flex-col bg-background border-l border-border/60">
      {/* Barra de abas — grid 2x2 por padrão; vira 1 linha (4 colunas) quando
          o painel é largo o suficiente. Nunca fica "3 em cima + 1 sozinho".
          Botão fechar fica sempre no canto superior direito alinhado às abas. */}
      <div className="@container flex items-start gap-0.5 px-1.5 py-1 border-b border-border/60 bg-muted/20">
        <div className="grid grid-cols-2 @lg:grid-cols-4 gap-0.5 flex-1 min-w-0">
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
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
          title={t("workbench.close")}
          aria-label={t("workbench.close")}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Body — só monta a aba ativa (poupa recurso) */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "terminal" && <TerminalPanel threadId={threadId} />}
        {activeTab === "files" && (
          <FilesTab threadId={threadId} onAddToContext={onAddToContext} />
        )}
        {activeTab === "diff" && <DiffTab threadId={threadId} />}
        {activeTab === "plan" && <PlanTab threadId={threadId} />}
      </div>
    </div>
  );
}
