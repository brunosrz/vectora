import { useState, useCallback, useMemo, useRef } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ChatInterface } from "@/components/chat/chat-interface";
import { WorkbenchPanel } from "@/components/workbench/workbench-panel";
import { HorizontalSplit } from "@/components/layout/horizontal-split";
import { LicenseBanner } from "@/components/layout/license-banner";
import { SettingsDialog } from "@/components/layout/settings-dialog";
import { KeyboardShortcutsDialog } from "@/components/layout/keyboard-shortcuts-dialog";
import { NewChatDialog } from "@/components/layout/new-chat-dialog";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { useSettingsStore } from "@/lib/stores/settings-store";

import {
  useThreadsQuery,
  useCreateThread,
  useDeleteThread,
  useUpdateThread,
  threadsQueryKey,
} from "@/lib/queries/threads";
import { listThreads } from "@/lib/api/vectora-client";
import { queryClient } from "../../router";
import { useAuthStore } from "@/lib/stores/auth-store";
import { getDefaultModel } from "@/lib/config/deployment-config";
import type { AgentConfig } from "@/components/layout/agent-settings";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { markAsNew, isNew, clearNew } from "@/lib/stores/new-thread-registry";
import {
  useBroadcastSync,
  BROADCAST_THREADS,
  BROADCAST_WORKSPACES,
} from "@/lib/hooks/use-broadcast-sync";
import { useGlobalShortcuts } from "@/lib/hooks/use-global-shortcuts";

export const Route = createFileRoute("/session/$threadId")({
  // Garante que a lista de threads está em cache antes do componente montar
  // (sidebar aparece preenchida sem flash de "carregando").
  loader: () =>
    queryClient.ensureQueryData({
      queryKey: threadsQueryKey,
      queryFn: () => listThreads(50),
      staleTime: 30_000,
    }),
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
      if (rect) setSidebarWidth(e.clientX - rect.left);
    },
    [setSidebarWidth],
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
  const createThreadMutation = useCreateThread();
  const deleteThreadMutation = useDeleteThread();
  const updateThreadMutation = useUpdateThread();

  // Sincronização multi-aba: quando outra aba cria/deleta/renomeia uma thread
  // ou altera workspaces, revalida o cache desta aba silenciosamente.
  useBroadcastSync(BROADCAST_THREADS, () => void refetchThreads(), !!userId);
  useBroadcastSync(BROADCAST_WORKSPACES, () => void refetchThreads(), !!userId);

  // Registry central de atalhos globais (C.11).
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
      setShowShortcutsDialog(true);
      return true;
    },
  });

  // ── UI state local ────────────────────────────────────────────────────────
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [showToolCalls, setShowToolCalls] = useState(false);
  const [showShortcutsDialog, setShowShortcutsDialog] = useState(false);
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
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
    async (workspaceId: string | null) => {
      const thread = await createThreadMutation.mutateAsync(workspaceId);
      markAsNew(thread.id);
      goTo(thread.id);
      setIsMobileSidebarOpen(false);
    },
    [createThreadMutation, goTo],
  );

  const handleDeleteThread = useCallback(
    async (id: string) => {
      await deleteThreadMutation.mutateAsync(id);
      if (id === threadId) void navigate({ to: "/" });
    },
    [deleteThreadMutation, threadId, navigate],
  );

  const handleThreadUpdate = useCallback(
    (id: string, title: string) => {
      // Primeira persistência da thread no backend: remove do registry de novas.
      if (isNew(id)) clearNew(id);
      void updateThreadMutation.mutate({ id, updates: { title } });
    },
    [updateThreadMutation],
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

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar desktop — oculto em mobile. Largura arrastável quando
            expandida; colapsada usa a largura própria (w-16) do componente. */}
        <div
          ref={sidebarWrapRef}
          className="hidden md:flex shrink-0 relative"
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
              className="absolute top-0 right-0 z-50 h-full w-1 cursor-col-resize bg-transparent hover:bg-border transition-colors"
            />
          )}
        </div>

        {/* Sidebar mobile como Sheet overlay */}
        <Sheet open={isMobileSidebarOpen} onOpenChange={setIsMobileSidebarOpen}>
          <SheetContent side="left" className="p-0 w-72 border-r">
            {sidebar}
          </SheetContent>
        </Sheet>

        {/* Área principal */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <Header
            agentConfig={agentConfig}
            onAgentConfigChange={setAgentConfig}
            showToolCalls={showToolCalls}
            onToggleToolCalls={() => setShowToolCalls((v) => !v)}
            onShowShortcuts={() => setShowShortcutsDialog(true)}
            onOpenSidebar={() => setIsMobileSidebarOpen(true)}
          />

          <HorizontalSplit
            className="flex-1 min-h-0"
            showRight={hydrated && workbenchOpen}
            rightSize={splitSize}
            onResize={setSplitSize}
            left={
              <ChatInterface
                threadId={threadId}
                showToolCalls={showToolCalls}
                agentConfig={agentConfig}
                onAgentConfigChange={setAgentConfig}
                onThreadUpdate={handleThreadUpdate}
                onThreadNotFound={() => void navigate({ to: "/" })}
                inputLocked={inputLocked}
                isNewThread={isNew(threadId)}
              />
            }
            right={
              <WorkbenchPanel
                threadId={threadId}
                onAddToContext={pushMention}
              />
            }
          />
        </div>
      </div>

      {/* Dialogs globais */}
      <SettingsDialog />
      <KeyboardShortcutsDialog
        open={showShortcutsDialog}
        onOpenChange={setShowShortcutsDialog}
      />
      <NewChatDialog
        open={showNewChatDialog}
        onOpenChange={setShowNewChatDialog}
        onConfirm={(workspaceId) => void handleConfirmNewChat(workspaceId)}
      />
    </div>
  );
}
