import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
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
import { DockedEditor } from "@/components/workbench/windows/docked-editor";
import { SessionSwitcher } from "@/components/header/session-switcher";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { PANEL_TRANSITION } from "@/lib/motion/transitions";
import { useFeatureFlags } from "@/lib/hooks/use-feature-flags";
import { useWebhookWorkbench } from "@/lib/hooks/use-webhook-workbench";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { usePreferenciasDialogStore } from "@/lib/stores/preferencias-dialog-store";

import {
  useThreadsQuery,
  useDeleteThread,
  useUpdateThread,
  threadsQueryKey,
} from "@/lib/queries/threads";
import { useWindowsStore } from "@/lib/stores/windows-store";
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
import {
  markWorkspaceChosen,
  isWorkspaceChosen,
} from "@/lib/stores/workspace-choice-registry";
import {
  signalWorkspacePreChosen,
  consumeWorkspacePreChosen,
} from "@/lib/stores/new-session-signal";
import { safeRandomUUID } from "@/lib/utils/uuid";
import {
  useBroadcastSync,
  BROADCAST_THREADS,
  BROADCAST_WORKSPACES,
} from "@/lib/hooks/use-broadcast-sync";
import { useGlobalShortcuts } from "@/lib/hooks/use-global-shortcuts";
import { isOnboardingDone } from "@/components/onboarding/setup-wizard";
import { m } from "@/lib/paraglide/messages";
export const Route = createFileRoute("/session/$threadId")({
  // Prefetch em paralelo: lista de threads (sidebar) + histórico da thread ativa.
  // O histórico fica em cache no queryClient com chave ['thread-history', id]
  // e é consumido por chat-interface.tsx sem segunda viagem ao servidor.
  // Para "new", o histórico não existe ainda — só prefetch da lista de threads.
  loader: ({ params }) =>
    params.threadId === "new"
      ? queryClient.ensureQueryData({
          queryKey: threadsQueryKey,
          queryFn: () => listThreads(50),
          staleTime: 30_000,
        })
      : Promise.all([
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

// Largura da sidebar colapsada — bate com o w-16 do <CollapsedSidebar>.
const SIDEBAR_COLLAPSED_WIDTH = 64;

function SessionPage() {
  const { threadId: routeParam } = Route.useParams() as { threadId: string };
  const navigate = useNavigate();

  // /session/new: o UUID vive só em memória; a URL só recebe o ID real quando
  // a primeira mensagem for persistida (handleThreadUpdate com lastMessage).
  const isNewRoute = routeParam === "new";
  const [localNewId] = useState<string>(() => {
    if (!isNewRoute) return "";
    const id = safeRandomUUID();
    markAsNew(id);
    // consumeWorkspacePreChosen() lê e zera o sinal one-shot definido em
    // handleConfirmNewChat quando o workspace já foi confirmado antes da navegação.
    if (consumeWorkspacePreChosen()) markWorkspaceChosen(id);
    return id;
  });
  const threadId = isNewRoute ? localNewId : routeParam;
  const userId = useAuthStore((s) => s.user?.id);
  const pushMention = useChatInputStore((s) => s.pushMention);

  // Painel do workbench: visível e redimensionável via workbench-store. O gate
  // de hidratação evita divergência SSR/cliente do estado persistido.
  const hydrated = useHydrated();
  const workbenchOpen = useWorkbenchStore((s) => s.isOpen(threadId));
  const splitSize = useWorkbenchStore((s) => s.splitSize);
  const setSplitSize = useWorkbenchStore((s) => s.setSplitSize);

  // CI em tempo real: webhook do GitHub → toast + badge no git-tab (sem F5).
  useWebhookWorkbench();

  // Largura da sidebar (desktop) arrastável pela borda direita.
  const sidebarWidth = useSettingsStore((s) => s.sidebarWidth);
  const setSidebarWidth = useSettingsStore((s) => s.setSidebarWidth);
  const sidebarPosition = useSettingsStore((s) => s.sidebarPosition);
  const sidebarOnRight = sidebarPosition === "right";
  const chatMode = useSettingsStore((s) => s.chatMode);
  const setChatMode = useSettingsStore((s) => s.setChatMode);
  const ideMode = useSettingsStore((s) => s.ideMode);
  const { enableFeaturesBeta } = useFeatureFlags();
  const chatSidebarWidth = useSettingsStore((s) => s.chatSidebarWidth);
  const setChatSidebarWidth = useSettingsStore((s) => s.setChatSidebarWidth);
  // Modelo do chat — lido do store persistido (sobrevive a restart/reload).
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const setSelectedModel = useSettingsStore((s) => s.setSelectedModel);
  const sidebarWrapRef = useRef<HTMLDivElement>(null);
  const draggingSidebar = useRef(false);

  // Resize do painel de workbench content no modo IDE (borda direita do painel)
  const workbenchResizeRef = useRef<HTMLDivElement>(null);
  const draggingWorkbench = useRef(false);
  const onWorkbenchResizeDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      draggingWorkbench.current = true;
      (e.target as Element).setPointerCapture?.(e.pointerId);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [],
  );
  const onWorkbenchResizeMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingWorkbench.current) return;
      const rect = workbenchResizeRef.current?.getBoundingClientRect();
      if (rect) setSplitSize(Math.max(150, e.clientX - rect.left));
    },
    [setSplitSize],
  );
  const onWorkbenchResizeUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingWorkbench.current) return;
      draggingWorkbench.current = false;
      (e.target as Element).releasePointerCapture?.(e.pointerId);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    },
    [],
  );

  // Resize do painel de chat lateral no modo IDE (borda esquerda do painel)
  const chatSidebarRef = useRef<HTMLDivElement>(null);
  const draggingChatSidebar = useRef(false);
  const onChatSidebarResizeDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      draggingChatSidebar.current = true;
      (e.target as Element).setPointerCapture?.(e.pointerId);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [],
  );
  const onChatSidebarResizeMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingChatSidebar.current) return;
      const rect = chatSidebarRef.current?.getBoundingClientRect();
      if (rect) setChatSidebarWidth(rect.right - e.clientX);
    },
    [setChatSidebarWidth],
  );
  const onChatSidebarResizeUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingChatSidebar.current) return;
      draggingChatSidebar.current = false;
      (e.target as Element).releasePointerCapture?.(e.pointerId);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    },
    [],
  );

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
  const [inputLocked, setInputLocked] = useState(false);
  // `model` reflete `selectedModel` do settings-store (persistido) — o
  // restante de AgentConfig (repos, etc.) é local/efêmero por thread.
  const [agentConfig, setAgentConfigState] = useState<AgentConfig>(() => ({
    model: selectedModel || getDefaultModel(),
  }));
  // Qualquer troca de modelo (seletor no composer, fallback automático por
  // quota) persiste no settings-store — sem isso o modelo escolhido não
  // sobrevivia a um restart/reload (cada mount reiniciava em
  // getDefaultModel()).
  const setAgentConfig = useCallback(
    (config: AgentConfig) => {
      setAgentConfigState(config);
      if (config.model) setSelectedModel(config.model);
    },
    [setSelectedModel],
  );
  // A rehidratação do zustand/persist é assíncrona — no primeiro render
  // `selectedModel` ainda pode ser o default da store recém-criada. Mantém
  // `agentConfig.model` em sincronia sempre que `selectedModel` mudar (por
  // rehidratação ou por outra aba via broadcast); mudanças partindo do
  // próprio `setAgentConfig` já deixam os dois iguais, então o efeito vira
  // no-op nesse caso (sem loop).
  useEffect(() => {
    if (selectedModel && selectedModel !== agentConfig.model) {
      setAgentConfigState((prev) => ({ ...prev, model: selectedModel }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModel]);

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
      // Abrir uma sessão entra no modo dela (chat/dev).
      const t = threads.find((th) => th.thread_id === id);
      if (t) setChatMode((t.mode ?? "dev") === "chat");
      goTo(id);
      setIsMobileSidebarOpen(false);
    },
    [goTo, threads, setChatMode],
  );

  const handleNewChat = useCallback(() => {
    // Chat: cria sessão direto (sem workspace/folders). Dev: dialog de workspace.
    // Reset do fundo: fecha janelas de arquivo da sessão anterior para a nova
    // conversa não herdar o conteúdo visual da atual.
    useWindowsStore.getState().closeAll();
    if (chatMode) {
      void navigate({ to: "/session/$threadId", params: { threadId: "new" } });
      setIsMobileSidebarOpen(false);
      return;
    }
    setShowNewChatDialog(true);
  }, [chatMode, navigate]);

  const handleStartChatFromWelcome = useCallback(() => {
    setChatMode(true);
    markWorkspaceChosen(threadId);
  }, [threadId, setChatMode]);

  const handleConfirmNewChat = useCallback(
    (workspaceId: string | null) => {
      // Não persiste a thread no backend ainda — isso evita acumular
      // conversas vazias na sidebar. A thread só é criada (via StreamChat)
      // quando a primeira mensagem é enviada.
      useWindowsStore.getState().closeAll();
      if (workspaceId) {
        void useWorkspacesStore.getState().setActive(workspaceId);
      }
      if (isNewRoute) {
        // Já em /session/new: apenas marca o workspace como escolhido (sem navegar).
        markWorkspaceChosen(threadId);
      } else {
        // Saindo de uma sessão existente: sinaliza que workspace já foi confirmado
        // para que o componente destino não reabra o seletor automaticamente.
        signalWorkspacePreChosen();
        void navigate({
          to: "/session/$threadId",
          params: { threadId: "new" },
        });
      }
      setIsMobileSidebarOpen(false);
    },
    [isNewRoute, navigate, threadId],
  );

  const handleDeleteThread = useCallback(
    async (id: string) => {
      await deleteThreadMutation.mutateAsync(id);
      if (id !== threadId) return;
      useWindowsStore.getState().closeAll();
      if (chatMode) {
        void navigate({ to: "/" });
      } else {
        // Code: não herda uma sessão; navega pra /session/new (sem isso a
        // rota continuava apontando pra thread já deletada, deixando o chat
        // antigo renderizado atrás do modal) e reabre o seletor de workspace
        // (mesmo fluxo da "Nova conversa"), em vez de cair numa sessão herdada.
        void navigate({
          to: "/session/$threadId",
          params: { threadId: "new" },
        });
        setShowNewChatDialog(true);
      }
    },
    [deleteThreadMutation, threadId, navigate, chatMode],
  );

  const handleThreadNotFound = useCallback(() => {
    void navigate({ to: "/" });
  }, [navigate]);

  // A 1ª mensagem de uma thread nova falhou antes de qualquer token chegar
  // (conexão nunca alcançou o backend) — a thread nunca foi persistida
  // (`_upsert_session` só roda quando a requisição de fato chega), então o
  // otimista inserido no cache antes do envio (handleThreadUpdate com
  // lastMessage="") fica sendo uma sessão fantasma só local. Remove.
  const handleThreadPersistFailed = useCallback((id: string) => {
    queryClient.setQueryData<{ threads: VectoraThread[] }>(
      threadsQueryKey,
      (old) => ({
        threads: (old?.threads ?? []).filter((th) => th.id !== id),
      }),
    );
  }, []);

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
      // Se estávamos em /session/new, atualiza a URL para o ID real (replace
      // para que o botão Voltar do browser não retorne a /session/new vazio).
      if (isNewRoute) {
        void navigate({
          to: "/session/$threadId",
          params: { threadId: id },
          replace: true,
        });
      }
      // Patch local imediato do cache — a sidebar não pode depender só do
      // round-trip de `updateThreadMutation` (rede lenta/generateTitle
      // assíncrono) para refletir a thread: sem isso ela só aparecia após
      // reload, quando ListThreads era refeito do zero. Atualiza a entrada
      // existente (posta pelo passo otimista acima) ou insere uma nova —
      // defensivo para o caso de handleRegenerate/handleEditAndRerun
      // chamarem onThreadUpdate direto numa thread ainda não presente.
      queryClient.setQueryData<{ threads: VectoraThread[] }>(
        threadsQueryKey,
        (old) => {
          const existing = old?.threads ?? [];
          const now = new Date().toISOString();
          if (existing.some((th) => th.id === id)) {
            return {
              threads: existing.map((th) =>
                th.id === id ? { ...th, title, updated_at: now } : th,
              ),
            };
          }
          const inserted: VectoraThread = {
            id,
            created_at: now,
            updated_at: now,
            title,
            workspace_id: useWorkspacesStore.getState().active_id ?? "",
          };
          return { threads: [inserted, ...existing] };
        },
      );
      void updateThreadMutation.mutate({ id, updates: { title } });
    },
    [updateThreadMutation, isNewRoute, navigate],
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

  // Sessão nova/vazia (ainda sem 1ª mensagem persistida) → destaca "Nova sessão".
  const isNewSession = isNew(threadId);

  // Threads do workspace ativo (para o session switcher do IDE mode).
  const activeWorkspaceId = useWorkspacesStore((s) => s.active_id);
  const wsThreads = useMemo(
    () =>
      activeWorkspaceId
        ? threads.filter((t) => t.workspace_id === activeWorkspaceId)
        : threads,
    [threads, activeWorkspaceId],
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
        isNewSession={isNewSession}
      />
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [threads, threadId, isLoading, isSidebarCollapsed, isNewSession],
  );

  return (
    <div className="flex flex-col h-full overflow-hidden bg-background">
      <LicenseBanner fullWidth onBlockingChange={setInputLocked} />

      <AnimatePresence mode="wait" initial={false}>
        {ideMode && !chatMode && enableFeaturesBeta ? (
          // ── Layout IDE: sidebars ao topo, Header só acima do DockedEditor ──
          <motion.div
            key="ide"
            initial={{ opacity: 0, x: 18 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -18 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="flex flex-1 min-h-0 overflow-hidden"
          >
            {/* WorkbenchNavBar — esquerda, 48px, vai ao topo absoluto */}
            <WorkbenchNavBar threadId={threadId} side="left" />

            {/* WorkbenchContent — esquerda, redimensionável, vai ao topo */}
            {hydrated && workbenchOpen && (
              <div
                ref={workbenchResizeRef}
                className="relative shrink-0"
                style={{ width: splitSize }}
              >
                <WorkbenchContent
                  threadId={threadId}
                  side="left"
                  onAddToContext={pushMention}
                />
                <div
                  role="separator"
                  aria-orientation="vertical"
                  aria-label="Redimensionar workbench"
                  onPointerDown={onWorkbenchResizeDown}
                  onPointerMove={onWorkbenchResizeMove}
                  onPointerUp={onWorkbenchResizeUp}
                  onPointerCancel={onWorkbenchResizeUp}
                  className="absolute right-0 top-0 z-10 h-full w-1 cursor-col-resize bg-transparent hover:bg-primary/30 transition-colors"
                />
              </div>
            )}

            {/* DockedEditor — coluna central: Header ao topo + editor abaixo */}
            <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
              <Header
                showToolCalls={showToolCalls}
                onToggleToolCalls={() => setShowToolCalls((v) => !v)}
                onShowShortcuts={() => setShowShortcutsDialog(true)}
                onOpenSidebar={() => setIsMobileSidebarOpen(true)}
                showModeSwitch={!chatMode && enableFeaturesBeta}
              />
              <div className="flex-1 min-h-0 overflow-hidden">
                <DockedEditor />
              </div>
            </div>

            {/* Chat sidebar — direita, vai ao topo, bg-sidebar em tudo */}
            <div
              ref={chatSidebarRef}
              className="relative shrink-0 flex flex-col border-l border-border/60 bg-sidebar"
              style={{ width: hydrated ? chatSidebarWidth : 256 }}
            >
              <div
                role="separator"
                aria-orientation="vertical"
                aria-label="Redimensionar chat"
                onPointerDown={onChatSidebarResizeDown}
                onPointerMove={onChatSidebarResizeMove}
                onPointerUp={onChatSidebarResizeUp}
                onPointerCancel={onChatSidebarResizeUp}
                className="absolute left-0 top-0 z-10 h-full w-1 cursor-col-resize bg-transparent hover:bg-primary/30 transition-colors"
              />
              <div className="flex items-center gap-1 px-2 py-1.5 border-b border-border/40 shrink-0 min-w-0">
                <SessionSwitcher
                  threads={wsThreads}
                  currentThreadId={threadId}
                  onSelectThread={handleSelectThread}
                  onNewSession={handleNewChat}
                />
              </div>
              <div className="flex-1 min-h-0">
                <ChatInterface
                  threadId={threadId}
                  showToolCalls={showToolCalls}
                  agentConfig={agentConfig}
                  onAgentConfigChange={setAgentConfig}
                  onThreadUpdate={handleThreadUpdate}
                  onThreadPersistFailed={handleThreadPersistFailed}
                  onThreadNotFound={handleThreadNotFound}
                  inputLocked={inputLocked}
                  isNewThread={isNew(threadId)}
                  compact
                />
              </div>
            </div>

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
              onConfirm={(workspaceId) =>
                void handleConfirmNewChat(workspaceId)
              }
            />
          </motion.div>
        ) : (
          // ── Layout Assistente/Chat (atual) ─────────────────────────────────
          <motion.div
            key="assistente"
            initial={{ opacity: 0, x: -18 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 18 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="flex flex-1 min-h-0 overflow-visible"
          >
            {/* Sidebar desktop — oculto em mobile. Largura arrastável quando
                expandida; colapsada anima até SIDEBAR_COLLAPSED_WIDTH. Width
                animado via motion (não CSS transition) pra reusar o mesmo
                PANEL_TRANSITION do resto do app; duration 0 durante o drag do
                resize-handle, senão o arrasto ficaria com lag atrás do ponteiro. */}
            <motion.div
              ref={sidebarWrapRef}
              className={`hidden md:flex shrink-0 relative ${sidebarOnRight ? "order-last" : ""}`}
              animate={{
                width: isSidebarCollapsed
                  ? SIDEBAR_COLLAPSED_WIDTH
                  : hydrated
                    ? sidebarWidth
                    : 224,
              }}
              transition={
                draggingSidebar.current ? { duration: 0 } : PANEL_TRANSITION
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
            </motion.div>

            {/* Sidebar mobile como Sheet overlay */}
            <Sheet
              open={isMobileSidebarOpen}
              onOpenChange={setIsMobileSidebarOpen}
            >
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
                      showModeSwitch={!chatMode && enableFeaturesBeta}
                    />
                    <div className="flex-1 min-h-0">
                      <ChatInterface
                        threadId={threadId}
                        showToolCalls={showToolCalls}
                        agentConfig={agentConfig}
                        onAgentConfigChange={setAgentConfig}
                        onThreadUpdate={handleThreadUpdate}
                        onThreadPersistFailed={handleThreadPersistFailed}
                        onThreadNotFound={handleThreadNotFound}
                        inputLocked={inputLocked}
                        isNewThread={isNew(threadId)}
                        onStartChat={
                          hydrated &&
                          isNewRoute &&
                          !isWorkspaceChosen(threadId) &&
                          (!userId || isOnboardingDone(userId))
                            ? handleStartChatFromWelcome
                            : undefined
                        }
                        onStartCode={
                          hydrated &&
                          isNewRoute &&
                          !isWorkspaceChosen(threadId) &&
                          (!userId || isOnboardingDone(userId))
                            ? () => setShowNewChatDialog(true)
                            : undefined
                        }
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
                <div
                  className={`shrink-0 ${sidebarOnRight ? "order-first" : ""}`}
                >
                  <WorkbenchNavBar threadId={threadId} />
                </div>
              )}
            </div>

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
              onConfirm={(workspaceId) =>
                void handleConfirmNewChat(workspaceId)
              }
            />

            {/* Workstation: janelas flutuantes de arquivos + dock de minimizadas */}
            <WindowLayer />
            <WindowDock />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
