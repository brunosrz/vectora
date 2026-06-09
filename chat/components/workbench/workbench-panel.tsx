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
  ExternalLink,
  FileText,
  FolderTree,
  GitCompare,
  TerminalSquare,
  X,
} from "lucide-react";
import { useCallback, useState } from "react";
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
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs select-none transition-colors ${
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}
      title={label}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
      {showPending && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0"
          aria-label={t("workbench.tab.pending")}
          title={t("workbench.tab.pending")}
        />
      )}
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

interface VscodeOption {
  strategy: string;
  label: string;
  url: string;
}

function VscodeMenu({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<VscodeOption[]>([]);

  const handleOpen = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(
      `/workspaces/${encodeURIComponent(workspaceId)}/vscode-options`,
    );
    if (res.ok) {
      const data = await res.json();
      setOptions((data.options as VscodeOption[]) ?? []);
    }
    setOpen((v) => !v);
  }, [workspaceId]);

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
        title={t("workbench.open_vscode")}
        aria-label={t("workbench.open_vscode")}
      >
        <ExternalLink className="w-3.5 h-3.5" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-popover border border-border/60 rounded-md shadow-lg py-1 min-w-[200px]">
            {options.length === 0 ? (
              <p className="px-3 py-1.5 text-xs text-muted-foreground">
                {t("workbench.open_vscode_unavailable")}
              </p>
            ) : (
              options.map((opt) => (
                <a
                  key={opt.strategy}
                  href={opt.url}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-muted/40 transition-colors"
                >
                  <ExternalLink className="w-3 h-3 text-muted-foreground shrink-0" />
                  {opt.label}
                </a>
              ))
            )}
          </div>
        </>
      )}
    </div>
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
      {/* Barra de abas — wrap em grid quando o painel é estreito demais
          para a linha única. Botão fechar fica sempre no canto superior
          direito alinhado às abas. */}
      <div className="flex items-start gap-0.5 px-1.5 py-1 border-b border-border/60 bg-muted/20">
        <div className="flex flex-wrap items-center gap-0.5 flex-1 min-w-0">
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
        {wsId && <VscodeMenu workspaceId={wsId} />}
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
