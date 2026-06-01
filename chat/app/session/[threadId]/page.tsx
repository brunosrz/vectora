"use client";

import { Suspense, useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryState } from "nuqs";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ChatInterface } from "@/components/chat/chat-interface";
import { KeyboardShortcutsDialog } from "@/components/layout/keyboard-shortcuts-dialog";
import { useThreads, type ClientProfile } from "@/lib/hooks/threads";
import { useUserId, useClientProfile } from "@/lib/hooks/auth";
import { useThreadsStore } from "@/lib/stores/threads-store";
import { resolveClientProfile } from "@/lib/config/client-config";
import type { AgentConfig } from "@/components/layout/agent-settings";
import { generateQuickTitle, generateThreadTitle } from "@/lib/utils/string";
import {
  getAllowedModels,
  getAllowedAgents,
  getDefaultModel,
  getDefaultAgent,
  CONFIG_STORAGE,
  type ModelOption,
  type AgentType,
} from "@/lib/config/deployment-config";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { markAsNew, isNew } from "@/lib/stores/new-thread-registry";
import { HorizontalSplit } from "@/components/layout/horizontal-split";
import { WorkbenchPanel } from "@/components/workbench/workbench-panel";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { safeRandomUUID } from "@/lib/utils/uuid";

function SessionContent() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;

  // Inicia collapsed para evitar overlay cobrindo a tela no primeiro paint
  // em mobile. Effect abaixo expande automaticamente em viewports ≥768px.
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(min-width: 768px)").matches
    ) {
      setIsSidebarCollapsed(false);
    }
  }, []);
  const [showToolCalls, setShowToolCalls] = useState(false);
  const [showShortcutsDialog, setShowShortcutsDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [forceShowTooltip, setForceShowTooltip] = useState(0);

  // Threads recém-criados que ainda não existem no backend
  const [newThreads, setNewThreads] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    if (isNew(threadId)) initial.add(threadId);
    return initial;
  });

  // Suporte a ?q=... para envio automático ao abrir
  const [initialPrompt, setInitialPrompt] = useQueryState("q");

  const userId = useUserId();

  const [agentConfig, setAgentConfig] = useState<AgentConfig>(() => {
    if (typeof window !== "undefined") {
      const savedVersion = localStorage.getItem(CONFIG_STORAGE.versionKey);
      if (savedVersion !== CONFIG_STORAGE.version) {
        localStorage.removeItem(CONFIG_STORAGE.key);
        localStorage.setItem(CONFIG_STORAGE.versionKey, CONFIG_STORAGE.version);
        console.log(
          `Config version updated to ${CONFIG_STORAGE.version}, resetting to defaults`,
        );
      } else {
        const saved = localStorage.getItem(CONFIG_STORAGE.key);
        if (saved) {
          try {
            return JSON.parse(saved);
          } catch (e) {
            console.error("Failed to parse saved agent config:", e);
          }
        }
      }
    }
    return {
      model: getDefaultModel(),
      recursionLimit: 100,
      agentType: getDefaultAgent(),
    };
  });

  useEffect(() => {
    localStorage.setItem(CONFIG_STORAGE.key, JSON.stringify(agentConfig));
  }, [agentConfig]);

  const {
    threads,
    isLoading: threadsLoading,
    updateThreadMetadata,
    deleteThread,
    addOptimisticThread,
  } = useThreads(userId || undefined);

  const { clientProfile } = useClientProfile();

  const handleNewChat = () => {
    const newThreadId = safeRandomUUID();
    markAsNew(newThreadId);
    setNewThreads((prev) => new Set(prev).add(newThreadId));
    if (userId) {
      addOptimisticThread({
        thread_id: newThreadId,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: {
          user_id: userId,
          title: "Untitled",
          lastMessage: "",
          client: resolveClientProfile(clientProfile),
        },
      });
    }
    router.push(`/session/${newThreadId}`);
  };

  const handleSelectThread = (selectedThreadId: string) => {
    router.push(`/session/${selectedThreadId}`);
  };

  const invalidateThreadCache = useThreadsStore((s) => s.invalidate);
  const handleDeleteThread = (threadIdToDelete: string) => {
    deleteThread(threadIdToDelete, () => {
      invalidateThreadCache(threadIdToDelete);
      if (threadIdToDelete === threadId) {
        const newThreadId = safeRandomUUID();
        markAsNew(newThreadId);
        router.replace(`/session/${newThreadId}`);
      }
    });
  };

  const handleThreadNotFound = () => {
    console.log("Thread not accessible - creating new thread");
    const newThreadId = safeRandomUUID();
    markAsNew(newThreadId);
    setNewThreads((prev) => new Set(prev).add(newThreadId));
    if (userId) {
      addOptimisticThread({
        thread_id: newThreadId,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: {
          user_id: userId,
          title: "Untitled",
          lastMessage: "",
          client: resolveClientProfile(clientProfile),
        },
      });
    }
    router.replace(`/session/${newThreadId}`);
  };

  const handleThreadUpdate = async (
    currentThreadId: string,
    title: string,
    lastMessage: string,
    client?: ClientProfile,
    messageCount?: number,
  ) => {
    if (!userId) return;

    if (newThreads.has(currentThreadId)) {
      setNewThreads((prev) => {
        const updated = new Set(prev);
        updated.delete(currentThreadId);
        return updated;
      });
    }

    const resolvedClient = resolveClientProfile(client ?? clientProfile);

    const existingThread = threads.find((t) => t.thread_id === currentThreadId);
    const isUntitledThread = existingThread?.metadata?.title === "Untitled";
    const shouldGenerateAITitle =
      !existingThread ||
      isUntitledThread ||
      (messageCount && messageCount > 1 && messageCount % 5 === 0);

    if (!existingThread || isUntitledThread) {
      if (!existingThread) {
        addOptimisticThread({
          thread_id: currentThreadId,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          metadata: {
            user_id: userId,
            title: "Untitled",
            lastMessage,
            client: resolvedClient,
          },
        });
      }

      await updateThreadMetadata(currentThreadId, {
        user_id: userId,
        lastMessage,
        client: resolvedClient,
      });

      // F.2.5 — Adições otimistas no envio da 1ª mensagem chegam aqui
      // com `lastMessage === ""`. Geração de título pela IA precisa do
      // par (pergunta, resposta); sem resposta, apenas registra a
      // thread e espera o 2º call (pós-stream) gerar o título.
      if (lastMessage.length > 0) {
        generateThreadTitle({
          userMessage: title,
          assistantResponse: lastMessage,
        })
          .then((aiTitle) => {
            if (aiTitle.length > 0) {
              console.log("Setting AI title:", aiTitle);
              updateThreadMetadata(currentThreadId, {
                user_id: userId,
                title: aiTitle,
                lastMessage,
                client: resolvedClient,
              });
            }
          })
          .catch((error) => {
            console.error("Failed to generate AI title:", error);
            const quickTitle = generateQuickTitle(title);
            updateThreadMetadata(currentThreadId, {
              user_id: userId,
              title: quickTitle,
              lastMessage,
              client: resolvedClient,
            });
          });
      }
    } else if (shouldGenerateAITitle && messageCount) {
      console.log(`Regenerating AI title at message ${messageCount}`);

      await updateThreadMetadata(currentThreadId, {
        user_id: userId,
        lastMessage,
        client: resolvedClient,
      });

      generateThreadTitle({
        userMessage: title,
        assistantResponse: lastMessage,
      })
        .then((aiTitle) => {
          if (aiTitle.length > 0) {
            console.log("Updated title at message", messageCount, "→", aiTitle);
            updateThreadMetadata(currentThreadId, {
              user_id: userId,
              title: aiTitle,
              lastMessage,
              client: resolvedClient,
            });
          }
        })
        .catch((error) => {
          console.error("Failed to regenerate AI title:", error);
        });
    } else {
      await updateThreadMetadata(currentThreadId, {
        user_id: userId,
        lastMessage,
        client: resolvedClient,
      });
    }
  };

  // Keyboard shortcuts
  const handleCycleModel = () => {
    const models = getAllowedModels();
    const currentIndex = models.indexOf(agentConfig.model as ModelOption);
    const nextIndex = (currentIndex + 1) % models.length;
    setAgentConfig({ ...agentConfig, model: models[nextIndex] });
    setForceShowTooltip((prev) => prev + 1);
  };

  const handleCycleAgent = () => {
    const agents = getAllowedAgents();
    const currentIndex = agents.indexOf(agentConfig.agentType as AgentType);
    const nextIndex = (currentIndex + 1) % agents.length;
    setAgentConfig({ ...agentConfig, agentType: agents[nextIndex] });
    setForceShowTooltip((prev) => prev + 1);
  };

  // Bloco T — split do workbench (Terminal · Arquivos · Diff · Plano)
  // `useHydrated` evita hydration mismatch: o store usa persist do Zustand,
  // então isOpen/splitSize partem do default no SSR e mudam para os valores
  // do localStorage no primeiro effect. Sem o gate, o PanelGroup ganhava
  // filhos diferentes entre server e client → "Hydration failed".
  const hydrated = useHydrated();
  const showWorkbenchRaw = useWorkbenchStore((s) => s.isOpen(threadId));
  const showWorkbench = hydrated && showWorkbenchRaw;
  const toggleWorkbench = useWorkbenchStore((s) => s.togglePanel);
  const setActiveTab = useWorkbenchStore((s) => s.setActiveTab);
  const workbenchSplitSize = useWorkbenchStore((s) => s.splitSize);
  const setSplitSize = useWorkbenchStore((s) => s.setSplitSize);

  useKeyboardShortcuts([
    {
      shortcut: {
        key: "/",
        metaKey: true,
        description: "Toggle keyboard shortcuts",
        category: "Navigation",
      },
      handler: () => setShowShortcutsDialog(!showShortcutsDialog),
    },
    {
      shortcut: {
        key: "b",
        metaKey: true,
        description: "Toggle sidebar",
        category: "Navigation",
      },
      handler: () => setIsSidebarCollapsed(!isSidebarCollapsed),
    },
    {
      shortcut: {
        key: "i",
        metaKey: true,
        description: "Create new chat",
        category: "Navigation",
      },
      handler: handleNewChat,
    },
    {
      shortcut: {
        key: "s",
        metaKey: true,
        description: "Toggle settings",
        category: "Navigation",
      },
      handler: () => setShowSettingsDialog(!showSettingsDialog),
    },
    {
      shortcut: {
        key: "j",
        metaKey: true,
        description: "Switch model",
        category: "Model & Agent",
      },
      handler: handleCycleModel,
    },
    {
      shortcut: {
        key: "k",
        metaKey: true,
        description: "Switch agent",
        category: "Model & Agent",
      },
      handler: handleCycleAgent,
    },
    {
      shortcut: {
        key: "`",
        metaKey: true,
        description: "Toggle workbench (terminal)",
        category: "Navigation",
      },
      handler: () => {
        setActiveTab(threadId, "terminal");
        toggleWorkbench(threadId);
      },
    },
    {
      shortcut: {
        key: "T",
        metaKey: true,
        shiftKey: true,
        description: "Workbench: Terminal",
        category: "Workbench",
      },
      handler: () => setActiveTab(threadId, "terminal"),
    },
    {
      shortcut: {
        key: "F",
        metaKey: true,
        shiftKey: true,
        description: "Workbench: Files",
        category: "Workbench",
      },
      handler: () => setActiveTab(threadId, "files"),
    },
    {
      shortcut: {
        key: "D",
        metaKey: true,
        shiftKey: true,
        description: "Workbench: Diff",
        category: "Workbench",
      },
      handler: () => setActiveTab(threadId, "diff"),
    },
    {
      shortcut: {
        key: "P",
        metaKey: true,
        shiftKey: true,
        description: "Workbench: Plan",
        category: "Workbench",
      },
      handler: () => setActiveTab(threadId, "plan"),
    },
  ]);

  return (
    <>
      <KeyboardShortcutsDialog
        open={showShortcutsDialog}
        onOpenChange={setShowShortcutsDialog}
      />
      <div className="flex h-screen bg-background">
        <Sidebar
          isCollapsed={isSidebarCollapsed}
          onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          threads={threads}
          currentThreadId={threadId}
          onSelectThread={handleSelectThread}
          onDeleteThread={handleDeleteThread}
          onNewChat={handleNewChat}
          isLoading={threadsLoading}
        />
        <div className="flex-1 overflow-hidden relative">
          <HorizontalSplit
            showRight={showWorkbench}
            rightSize={workbenchSplitSize}
            onResize={setSplitSize}
            left={
              <div className="h-full flex flex-col">
                <Header
                  showToolCalls={showToolCalls}
                  onToggleToolCalls={() => setShowToolCalls(!showToolCalls)}
                  agentConfig={agentConfig}
                  onAgentConfigChange={setAgentConfig}
                  onShowShortcuts={() => setShowShortcutsDialog(true)}
                  forceShowTooltip={forceShowTooltip}
                  showSettingsDialog={showSettingsDialog}
                  onSettingsDialogChange={setShowSettingsDialog}
                  onOpenSidebar={
                    isSidebarCollapsed
                      ? () => setIsSidebarCollapsed(false)
                      : undefined
                  }
                />
                <ChatInterface
                  key={threadId}
                  showToolCalls={showToolCalls}
                  threadId={threadId}
                  onThreadUpdate={handleThreadUpdate}
                  onThreadNotFound={handleThreadNotFound}
                  agentConfig={agentConfig}
                  onAgentConfigChange={setAgentConfig}
                  isNewThread={newThreads.has(threadId)}
                  initialMessage={initialPrompt}
                  autoSend={!!initialPrompt}
                  onInitialMessageSent={() => setInitialPrompt(null)}
                />
              </div>
            }
            right={
              showWorkbench ? <WorkbenchPanel threadId={threadId} /> : null
            }
          />
        </div>
      </div>
    </>
  );
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
      }
    >
      <SessionContent />
    </Suspense>
  );
}
