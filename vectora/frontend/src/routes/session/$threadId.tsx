import { useState, useCallback, useMemo, useRef } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { Sidebar } from "@/components/sidebar/sidebar";
import { Header } from "@/components/header/header";
import { ChatInterface } from "@/components/chat/chat-interface";
import {
  WorkbenchContent,
  WorkbenchNavBar,
} from "@/components/workbench/workbench-panel";
import { HorizontalSplit } from "@/components/layout/horizontal-split";
import { LicenseBanner } from "@/components/layout/license-banner";
import { KeyboardShortcutsDialog } from "@/components/layout/keyboard-shortcuts-dialog";
import {
  CommandPalette,
  type PaletteCommand,
} from "@/components/layout/command-palette";
import { NewChatDialog } from "@/components/sidebar/new-chat-dialog";
import { WindowLayer } from "@/components/workbench/windows/window-layer";
import { WindowDock } from "@/components/workbench/windows/window-dock";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { usePreferenciasDialogStore } from "@/lib/stores/preferencias-dialog-store";

import {
  useThreadsQuery,
  useDeleteThread,
  useUpdateThread,
  threadsQueryKey,
} from "@/lib/queries/threads";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import {
  listThreads,
  getHistory,
  type Thread as VectoraThread,
} from "@/lib/api/vectora-client";
import { queryClient } from "../../router";
import { useAuthStore } from "@/lib/stores/auth-store";
import { getDefaultModel } from "@/lib/config/deployment-config";
import type { AgentConfig } from "@/components/layout/agent-settings";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { markAsNew, isNew, clearNew } from "@/lib/stores/new-thread-registry";
import { safeRandomUUID } from "@/lib/utils/uuid";
import {
  useBroadcastSync,
  BROADCAST_THREADS,
  BROADCAST_WORKSPACES,
} from "@/lib/hooks/use-broadcast-sync";
import { useGlobalShortcuts } from "@/lib/hooks/use-global-shortcuts";
import {
  SetupWizard,
  isOnboardingDone,
} from "@/components/onboarding/setup-wizard";
import { m } from "@/lib/paraglide/messages";
export const Route = createFileRoute("/session/$threadId")({
  // Prefetch em paralelo: lista de threads (sidebar) + histórico da thread ativa.
  // O histórico fica em cache no queryClient com chave ['thread-history', id]
  // e é consumido por chat-interface.tsx sem segunda viagem ao servidor.
  loader: ({ params }) =>
    Promise.all([
      queryClient.ensureQueryData({
        queryKey: threadsQueryKey,
        queryFn: () => listThreads(50),
        staleTime: 30_000,
      }),
      queryClient.prefetchQuery({
        queryKey: ["thread-history", params.threadId],
        queryFn: () => getHistory(params.threadId),
        staleTime: 30_000,
      }),
    ]),
  component: SessionPage,
});

function SessionPage() {
  const { threadId } = Route.useParams() as { threadId: string };
  const navigate = useNavigate();
  const userId = useAuthStore((s) => s.user?.id);
  const pushMention = useChatInputStore((s) => s.pushMention);

  // Painel do workbench: visível e redimensionável via workbench-store. O gate
  // de hidratação evita divergência SSR/cliente do estado persistido.
  const hydrated = useHydrated();
  const workbenchOpen = useWorkbenchStore((s) => s.isOpen(threadId));
  const splitSize = useWorkbenchStore((s) => s.splitSize);
  const setSplitSize = useWorkbenchStore((s) => s.setSplitSize);

  // Largura da sidebar (desktop) arrastável pela borda direita.
  const sidebarWidth = useSettingsStore((s) => s.sidebarWidth);
  const setSidebarWidth = useSettingsStore((s) => s.setSidebarWidth);
  const sidebarPosition = useSettingsStore((s) => s.sidebarPosition);
  const sidebarOnRight = sidebarPosition === "right";
  const chatMode = useSettingsStore((s) => s.chatMode);
  const sidebarWrapRef = useRef<HTMLDivElement>(null);
  const draggingSidebar = useRef(false);

  const onSidebarResizeDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      draggingSidebar.current = true;
      (e.target as Element).setPointerCapture?.(e.pointerId);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [],
  );
  const onSidebarResizeMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingSidebar.current) return;
      const rect = sidebarWrapRef.current?.getBoundingClientRect();
      if (rect) {
        setSidebarWidth(
          sidebarOnRight ? rect.right - e.clientX : e.clientX - rect.left,
        );
      }
    },
    [setSidebarWidth, sidebarOnRight],
  );
  const onSidebarResizeUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingSidebar.current) return;
      draggingSidebar.current = false;
      (e.target as Element).releasePointerCapture?.(e.pointerId);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    },
    [],
  );

  // ── Queries e mutations (TanStack Query) ──────────────────────────────────
  const {
    data: threads = [],
    isLoading,
    refetch: refetchThreads,
  } = useThreadsQuery(userId);
  const deleteThreadMutation = useDeleteThread();
  const updateThreadMutation = useUpdateThread();

  // Sincronização multi-aba: quando outra aba cria/deleta/renomeia uma thread
  // ou altera workspaces, revalida o cache desta aba silenciosamente.
  useBroadcastSync(BROADCAST_THREADS, () => void refetchThreads(), !!userId);
  useBroadcastSync(BROADCAST_WORKSPACES, () => void refetchThreads(), !!userId);

  // Registry central de atalhos globais (C.11) + command palette / cheatsheet (C.30).
  useGlobalShortcuts({
    "ctrl+t": () => {
      void handleConfirmNewChat(null);
      return true;
    },
    "ctrl+backslash": () => {
      const { togglePanel } = useWorkbenchStore.getState();
      togglePanel(threadId);
      return true;
    },
    "ctrl+,": () => {
      usePreferenciasDialogStore.getState().openAt("conta");
      return true;
    },
    "ctrl+k": () => {
      setShowCommandPalette(true);
      return true;
    },
    "ctrl+?": () => {
      setShowShortcutsDialog(true);
      return true;
    },
  });

  // ── UI state local ────────────────────────────────────────────────────────
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [showToolCalls, setShowToolCalls] = useState(false);
  const [showShortcutsDialog, setShowShortcutsDialog] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(
    () => !!userId && !isOnboardingDone(userId),
  );
  const [inputLocked, setInputLocked] = useState(false);
  const [agentConfig, setAgentConfig] = useState<AgentConfig>(() => ({
    model: getDefaultModel(),
  }));

  // ── Navegação ─────────────────────────────────────────────────────────────
  const goTo = useCallback(
    (id: string) =>
      void navigate({
        to: "/session/$threadId",
        params: { threadId: id },
      }),
    [navigate],
  );

  const handleSelectThread = useCallback(
    (id: string) => {
      goTo(id);
      setIsMobileSidebarOpen(false);
    },
    [goTo],
  );

  const handleNewChat = useCallback(() => {
    setShowNewChatDialog(true);
  }, []);

  const handleConfirmNewChat = useCallback(
    (workspaceId: string | null) => {
      // Não persiste a thread no backend ainda — isso evita acumular
      // conversas vazias na sidebar. A thread só é criada (via StreamChat)
      // quando a primeira mensagem é enviada.
      if (workspaceId) {
        void useWorkspacesStore.getState().setActive(workspaceId);
      }
      const id = safeRandomUUID();
      markAsNew(id);
      goTo(id);
      setIsMobileSidebarOpen(false);
    },
    [goTo],
  );

  const handleDeleteThread = useCallback(
    async (id: string) => {
      await deleteThreadMutation.mutateAsync(id);
      if (id === threadId) void navigate({ to: "/" });
    },
    [deleteThreadMutation, threadId, navigate],
  );

  const handleThreadNotFound = useCallback(() => {
    void navigate({ to: "/" });
  }, [navigate]);

  const handleThreadUpdate = useCallback(
    (id: string, title: string, lastMessage?: string) => {
      // Chamada otimista do envio da 1ª mensagem (lastMessage vazio): a thread
      // ainda não existe no backend (StreamChat ainda não rodou), então só
      // refletimos na sidebar localmente — sem chamar UpdateThread (404).
      if (isNew(id) && !lastMessage) {
        queryClient.setQueryData<{ threads: VectoraThread[] }>(
          threadsQueryKey,
          (old) => {
            const existing = old?.threads ?? [];
            if (existing.some((th) => th.id === id)) return old;
            const now = new Date().toISOString();
            const optimistic: VectoraThread = {
              id,
              created_at: now,
              updated_at: now,
              title,
              workspace_id: useWorkspacesStore.getState().active_id ?? "",
            };
            return { threads: [optimistic, ...existing] };
          },
        );
        return;
      }
      // Primeira persistência da thread no backend: remove do registry de novas.
      if (isNew(id)) clearNew(id);
      void updateThreadMutation.mutate({ id, updates: { title } });
    },
    [updateThreadMutation],
  );

  // ── Command palette — lista de ações navegáveis (C.30) ───────────────────
  const paletteCommands = useMemo<PaletteCommand[]>(
    () => [
      {
        id: "new-chat",
        label: m.palette_cmd_new_chat(),
        category: m.palette_cat_navigation(),
        shortcut: "Ctrl+T",
        run: () => void handleConfirmNewChat(null),
      },
      {
        id: "settings",
        label: m.palette_cmd_settings(),
        category: m.palette_cat_navigation(),
        shortcut: "Ctrl+,",
        run: () => usePreferenciasDialogStore.getState().openAt("conta"),
      },
      {
        id: "keyboard-shortcuts",
        label: m.palette_cmd_keyboard_shortcuts(),
        category: m.palette_cat_navigation(),
        shortcut: "Ctrl+?",
        run: () => setShowShortcutsDialog(true),
      },
      {
        id: "toggle-workbench",
        label: m.palette_cmd_toggle_workbench(),
        category: m.palette_cat_workbench(),
        shortcut: "Ctrl+\\",
        run: () => useWorkbenchStore.getState().togglePanel(threadId),
      },
      {
        id: "clear-messages",
        label: m.palette_cmd_clear_messages(),
        category: m.palette_cat_chat(),
        shortcut: "Ctrl+L",
        run: () => {
          // Disparado pelo atalho Ctrl+L — o chat-interface escuta esse evento.
          document.dispatchEvent(new CustomEvent("vectora:clear-messages"));
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [threadId],
  );

  // ── Sidebar (instância única reutilizada em desktop e mobile Sheet) ───────
  const sidebar = useMemo(
    () => (
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed((v) => !v)}
        threads={threads}
        currentThreadId={threadId}
        onSelectThread={handleSelectThread}
        onDeleteThread={handleDeleteThread}
        onNewChat={handleNewChat}
        isLoading={isLoading}
      />
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [threads, threadId, isLoading, isSidebarCollapsed],
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <LicenseBanner fullWidth onBlockingChange={setInputLocked} />

      <div className="flex flex-1 min-h-0 overflow-visible">
        {/* Sidebar desktop — oculto em mobile. Largura arrastável quando
            expandida; colapsada usa a largura própria (w-16) do componente. */}
        <div
          ref={sidebarWrapRef}
          className={`hidden md:flex shrink-0 relative ${sidebarOnRight ? "order-last" : ""}`}
          style={
            isSidebarCollapsed
              ? undefined
              : { width: hydrated ? sidebarWidth : 224 }
          }
        >
          {sidebar}
          {!isSidebarCollapsed && (
            <div
              role="separator"
              aria-orientation="vertical"
              onPointerDown={onSidebarResizeDown}
              onPointerMove={onSidebarResizeMove}
              onPointerUp={onSidebarResizeUp}
              onPointerCancel={onSidebarResizeUp}
              className={`absolute top-0 ${sidebarOnRight ? "left-0" : "right-0"} z-50 h-full w-1 cursor-col-resize bg-transparent hover:bg-border transition-colors`}
            />
          )}
        </div>

        {/* Sidebar mobile como Sheet overlay */}
        <Sheet open={isMobileSidebarOpen} onOpenChange={setIsMobileSidebarOpen}>
          <SheetContent side="left" className="p-0 w-72 border-r">
            {sidebar}
          </SheetContent>
        </Sheet>

        {/* Área principal — split ocupa altura total para que o painel do
            workbench (right) vá do topo ao rodapé, como a sidebar; o Header
            fica restrito à coluna do chat (left). A nav-bar do workbench
            (faixa de 48px, sempre visível) fica fora do split, à direita —
            não é redimensionável; só o painel de conteúdo é. */}
        <div className="flex-1 min-w-0 flex h-full">
          <HorizontalSplit
            className="flex-1 min-w-0"
            side={sidebarOnRight ? "left" : "right"}
            showRight={hydrated && workbenchOpen && !chatMode}
            rightSize={splitSize}
            onResize={setSplitSize}
            left={
              <div className="flex flex-col h-full min-w-0 overflow-visible">
                <Header
                  showToolCalls={showToolCalls}
                  onToggleToolCalls={() => setShowToolCalls((v) => !v)}
                  onShowShortcuts={() => setShowShortcutsDialog(true)}
                  onOpenSidebar={() => setIsMobileSidebarOpen(true)}
                />
                <div className="flex-1 min-h-0">
                  <ChatInterface
                    threadId={threadId}
                    showToolCalls={showToolCalls}
                    agentConfig={agentConfig}
                    onAgentConfigChange={setAgentConfig}
                    onThreadUpdate={handleThreadUpdate}
                    onThreadNotFound={handleThreadNotFound}
                    inputLocked={inputLocked}
                    isNewThread={isNew(threadId)}
                  />
                </div>
              </div>
            }
            right={
              <WorkbenchContent
                threadId={threadId}
                onAddToContext={pushMention}
              />
            }
          />
          {!chatMode && (
            <div className={`shrink-0 ${sidebarOnRight ? "order-first" : ""}`}>
              <WorkbenchNavBar threadId={threadId} />
            </div>
          )}
        </div>
      </div>

      {/* Wizard de primeiro acesso — aparece uma vez por usuário */}
      {showOnboarding && userId && (
        <SetupWizard
          userId={userId}
          onComplete={() => setShowOnboarding(false)}
        />
      )}

      {/* Dialogs globais */}
      <KeyboardShortcutsDialog
        open={showShortcutsDialog}
        onOpenChange={setShowShortcutsDialog}
      />
      <CommandPalette
        open={showCommandPalette}
        onOpenChange={setShowCommandPalette}
        commands={paletteCommands}
      />
      <NewChatDialog
        open={showNewChatDialog}
        onOpenChange={setShowNewChatDialog}
        onConfirm={(workspaceId) => void handleConfirmNewChat(workspaceId)}
      />

      {/* Workstation: janelas flutuantes de arquivos + dock de minimizadas */}
      <WindowLayer />
      <WindowDock />
    </div>
  );
}
