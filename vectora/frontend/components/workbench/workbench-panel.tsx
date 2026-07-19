"use client";

/**
 * Painel lateral direito do workbench, dividido em 2 partes (estilo VS Code):
 *
 * - `WorkbenchNavBar` — faixa estreita (48px) sempre visível, com os ícones
 *   das abas (Arquivos, Diff, Plano, Terminal). Não é redimensionável.
 *   Clicar numa aba já ativa com o painel aberto colapsa o painel; clicar em
 *   outra aba (ou com o painel fechado) troca/abre.
 * - `WorkbenchContent` — painel de conteúdo da aba ativa, redimensionável,
 *   só renderizado quando o painel está aberto (`isOpen`).
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
  MonitorPlay,
  Brain,
  Radar,
  Waypoints,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useWorkspaceWatcher } from "@/lib/hooks/use-workspace-watcher";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import {
  useWorkbenchStore,
  WORKBENCH_TABS,
  type WorkbenchTab,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { TerminalPanel } from "@/components/workbench/terminal/terminal-panel";
import { FilesTab } from "./files/files-tab";
import { GitTab } from "./git/git-tab";
import { PlanTab } from "./tabs/plan-tab";
import { PreviewTab } from "./tabs/preview-tab";
import { MemoryTab } from "./tabs/memory-tab";
import { TasksTab } from "./tabs/tasks-tab";
import { ContextGraphTab } from "./tabs/context-graph-tab";
import { m } from "@/lib/paraglide/messages";
import { mDyn } from "@/lib/i18n-dyn";
import { useFeatureFlags } from "@/lib/hooks/use-feature-flags";
import { PANEL_TRANSITION } from "@/lib/motion/transitions";

interface WorkbenchPanelProps {
  threadId: string;
  /** Injetar @path no chat ao clicar no botão @ de um arquivo/pasta. */
  onAddToContext?: (path: string) => void;
  /** Inserir texto no composer (god nodes/perguntas sugeridas do Context Graph). */
  onSendPrompt?: (text: string) => void;
}

const TAB_ICON: Record<
  WorkbenchTab,
  React.ComponentType<{ className?: string }>
> = {
  terminal: TerminalSquare,
  files: FolderTree,
  diff: GitCompare,
  plan: FileText,
  preview: MonitorPlay,
  storage: Brain,
  tasks: Radar,
  context_graph: Waypoints,
};

/** Lê o cache do workbench-store e devolve o texto do chip por aba. */
function useTabBadge(
  threadId: string,
  workspaceId: string,
  tab: WorkbenchTab,
  hydrated: boolean,
): string | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  // Selectors são chamados incondicionalmente — Rules of Hooks. Filtramos por
  // aba no return e gateamos por `hydrated` para evitar mismatch SSR (T11).
  const terminals = useWorkbenchStore((s) => s.list(threadId));
  const pinned = useWorkbenchStore((s) => s.pinnedFiles[threadId]?.length ?? 0);
  const planItems = useWorkbenchStore((s) => s.getPlan(threadId).items.length);
  void workspaceId;

  if (!hydrated) return null;
  switch (tab) {
    case "terminal":
      return terminals.length > 0 ? String(terminals.length) : null;
    case "files":
      return pinned > 0 ? String(pinned) : null;
    case "diff":
      // Sem chip de +N −M: o contador de diff poluía mais do que ajudava;
      // o ponto âmbar de "pending" continua sinalizando mudanças.
      return null;
    case "plan":
      return planItems > 0 ? String(planItems) : null;
    case "preview":
    case "storage":
    case "tasks":
    case "context_graph":
      return null;
  }
}

// Context Graph saiu do beta: backend (pipeline + endpoints + tool) e
// frontend (ContextGraphTab) estão completos e religados no switch acima —
// não há mais motivo pra gatear atrás de enableFeaturesBeta.
const BETA_TABS = new Set<WorkbenchTab>([]);

export function ComingSoonTabButton({ tab }: { tab: WorkbenchTab }) {
  const Icon = TAB_ICON[tab];
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-disabled="true"
          tabIndex={-1}
          className="relative flex items-center justify-center w-8 h-8 rounded-md cursor-default text-muted-foreground/40"
        >
          <Icon className="w-4 h-4" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">
        {m.workbench_tab_coming_soon()}
      </TooltipContent>
    </Tooltip>
  );
}

function NavTabButton({
  tab,
  active,
  threadId,
  workspaceId,
  hydrated,
  onSelect,
}: {
  tab: WorkbenchTab;
  active: boolean;
  threadId: string;
  workspaceId: string;
  hydrated: boolean;
  onSelect: () => void;
}) {
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
  const label = mDyn(`workbench.tab.${tab}`);
  const tooltipText = badge ? `${label} (${badge})` : label;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onSelect}
          className={`relative flex items-center justify-center w-8 h-8 rounded-md transition-colors ${
            active
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <Icon className="w-4 h-4" />
          <AnimatePresence initial={false}>
            {showPending && (
              <motion.span
                key="pending-dot"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ type: "spring", damping: 18, stiffness: 380 }}
                className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-amber-500"
                aria-label={m.workbench_tab_pending()}
              />
            )}
          </AnimatePresence>
          {badge && (
            <span className="absolute -bottom-1 -right-1 inline-flex items-center justify-center min-w-[1rem] h-4 px-1 rounded-full text-[9px] font-mono leading-none bg-primary/15 text-primary">
              {badge}
            </span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">{tooltipText}</TooltipContent>
    </Tooltip>
  );
}

/**
 * Faixa estreita (48px), sempre visível, com os ícones de cada aba —
 * equivalente à Activity Bar do VS Code. Não é redimensionável.
 *
 * `side="right"` (padrão): layout Assistente, borda esquerda, spacer h-16.
 * `side="left"`: layout IDE, borda direita, sem spacer (Header já está no topo).
 */
export function WorkbenchNavBar({
  threadId,
  side = "right",
}: {
  threadId: string;
  side?: "left" | "right";
}) {
  const hydrated = useHydrated();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";
  const activeTab = useWorkbenchStore((s) => s.getActiveTab(threadId));
  const isOpen = useWorkbenchStore((s) => s.isOpen(threadId));
  const selectTab = useWorkbenchStore((s) => s.selectTab);
  const { enableFeaturesBeta } = useFeatureFlags();
  return (
    <div
      className={`h-full w-12 shrink-0 flex flex-col items-center bg-sidebar ${
        side === "left" ? "border-r" : "border-l"
      } border-border/60`}
    >
      {/* Spacer h-16: alinha com o Header quando a NavBar está à direita (layout
          Assistente). No layout IDE o Header já está no topo — sem spacer. */}
      {side === "right" && (
        <div className="h-16 w-full shrink-0 border-b border-border/60" />
      )}
      <div className="flex flex-col items-center gap-1 pt-2">
        {WORKBENCH_TABS.map((tab) =>
          !enableFeaturesBeta && BETA_TABS.has(tab) ? (
            <ComingSoonTabButton key={tab} tab={tab} />
          ) : (
            <NavTabButton
              key={tab}
              tab={tab}
              active={hydrated && isOpen && tab === activeTab}
              threadId={threadId}
              workspaceId={wsId}
              hydrated={hydrated}
              onSelect={() => selectTab(threadId, tab)}
            />
          ),
        )}
      </div>
    </div>
  );
}

/**
 * Conteúdo da aba ativa — redimensionável, montado apenas quando o painel
 * está aberto (`isOpen`). Vive ao lado (à esquerda, na ordem visual) da
 * `WorkbenchNavBar`.
 *
 * `side="right"` (padrão): layout Assistente, borda esquerda.
 * `side="left"`: layout IDE, borda direita (editor fica à direita do painel).
 */
export function WorkbenchContent({
  threadId,
  onAddToContext,
  onSendPrompt,
  side = "right",
}: WorkbenchPanelProps & { side?: "left" | "right" }) {
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";
  const activeTab = useWorkbenchStore((s) => s.getActiveTab(threadId));
  const setPanelOpen = useWorkbenchStore((s) => s.setPanelOpen);
  const ActiveIcon = TAB_ICON[activeTab];

  // A.17 — file watcher SSE: dispara markPending quando arquivos mudam
  useWorkspaceWatcher(wsId || undefined);

  return (
    <div
      className={`h-full flex flex-col bg-sidebar ${
        side === "left" ? "border-r" : "border-l"
      } border-border/60`}
    >
      <div className="flex h-16 items-center justify-between px-3 border-b border-border/60 bg-sidebar">
        <span className="flex items-center gap-2 text-sm font-medium">
          <ActiveIcon className="w-4 h-4 text-muted-foreground" />
          {mDyn(`workbench.tab.${activeTab}`)}
        </span>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => setPanelOpen(threadId, false)}
              aria-label={m.workbench_toggle()}
              className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="left">{m.workbench_toggle()}</TooltipContent>
        </Tooltip>
      </div>

      {/* Body — só monta a aba ativa (poupa recurso); troca com slide suave */}
      <div className="flex-1 min-h-0 overflow-hidden relative">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -6 }}
            transition={PANEL_TRANSITION}
            className="absolute inset-0"
          >
            {activeTab === "terminal" && <TerminalPanel threadId={threadId} />}
            {activeTab === "files" && (
              <FilesTab threadId={threadId} onAddToContext={onAddToContext} />
            )}
            {activeTab === "diff" && <GitTab threadId={threadId} />}
            {activeTab === "plan" && <PlanTab threadId={threadId} />}
            {activeTab === "preview" && <PreviewTab threadId={threadId} />}
            {activeTab === "storage" && <MemoryTab threadId={threadId} />}
            {activeTab === "tasks" && <TasksTab threadId={threadId} />}
            {activeTab === "context_graph" && (
              <ContextGraphTab
                threadId={threadId}
                onSendPrompt={onSendPrompt}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
