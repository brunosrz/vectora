import { useState, useCallback, useMemo } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ChatInterface } from "@/components/chat/chat-interface";
import { WorkbenchPanel } from "@/components/workbench/workbench-panel";
import { LicenseBanner } from "@/components/layout/license-banner";
import { SettingsDialog } from "@/components/layout/settings-dialog";
import { KeyboardShortcutsDialog } from "@/components/layout/keyboard-shortcuts-dialog";
import { Sheet, SheetContent } from "@/components/ui/sheet";

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

  // ── Queries e mutations (TanStack Query) ──────────────────────────────────
  const { data: threads = [], isLoading } = useThreadsQuery(userId);
  const createThreadMutation = useCreateThread();
  const deleteThreadMutation = useDeleteThread();
  const updateThreadMutation = useUpdateThread();

  // ── UI state local ────────────────────────────────────────────────────────
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [showToolCalls, setShowToolCalls] = useState(false);
  const [showShortcutsDialog, setShowShortcutsDialog] = useState(false);
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

  const handleNewChat = useCallback(async () => {
    const thread = await createThreadMutation.mutateAsync();
    goTo(thread.id);
    setIsMobileSidebarOpen(false);
  }, [createThreadMutation, goTo]);

  const handleDeleteThread = useCallback(
    async (id: string) => {
      await deleteThreadMutation.mutateAsync(id);
      if (id === threadId) void navigate({ to: "/" });
    },
    [deleteThreadMutation, threadId, navigate],
  );

  const handleThreadUpdate = useCallback(
    (id: string, title: string) => {
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
        {/* Sidebar desktop — oculto em mobile */}
        <div className="hidden md:flex shrink-0">{sidebar}</div>

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

          <div className="flex flex-1 min-h-0 overflow-hidden">
            <ChatInterface
              threadId={threadId}
              showToolCalls={showToolCalls}
              agentConfig={agentConfig}
              onAgentConfigChange={setAgentConfig}
              onThreadUpdate={handleThreadUpdate}
              onThreadNotFound={() => void navigate({ to: "/" })}
              inputLocked={inputLocked}
            />
            <WorkbenchPanel threadId={threadId} onAddToContext={pushMention} />
          </div>
        </div>
      </div>

      {/* Dialogs globais */}
      <SettingsDialog />
      <KeyboardShortcutsDialog
        open={showShortcutsDialog}
        onOpenChange={setShowShortcutsDialog}
      />
    </div>
  );
}
