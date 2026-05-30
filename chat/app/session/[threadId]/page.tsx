"use client";

import { Suspense, useState, useEffect, useRef } from "react";
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
import {
  Group as PanelGroup,
  Panel,
  Separator as PanelResizeHandle,
} from "react-resizable-panels";
import { TerminalSquare } from "lucide-react";
import { TerminalPanel } from "@/components/terminal/terminal-panel";
import { useTerminalsStore } from "@/lib/stores/terminals-store";

function SessionContent() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
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
    const newThreadId = crypto.randomUUID();
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
        const newThreadId = crypto.randomUUID();
        markAsNew(newThreadId);
        router.replace(`/session/${newThreadId}`);
      }
    });
  };

  const handleThreadNotFound = () => {
    console.log("Thread not accessible - creating new thread");
    const newThreadId = crypto.randomUUID();
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

  // Bloco T — split do terminal
  const showTerminal = useTerminalsStore((s) => s.isOpen(threadId));
  const toggleTerminal = useTerminalsStore((s) => s.togglePanel);

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
        description: "Toggle terminal",
        category: "Navigation",
      },
      handler: () => toggleTerminal(threadId),
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
          isLoading={threadsLoading}
        />
        <div className="flex-1 overflow-hidden relative">
          <PanelGroup orientation="horizontal" className="h-full">
            <Panel defaultSize={showTerminal ? 60 : 100} minSize={30}>
              <div className="h-full flex flex-col">
                <Header
                  showToolCalls={showToolCalls}
                  onToggleToolCalls={() => setShowToolCalls(!showToolCalls)}
                  onNewChat={handleNewChat}
                  agentConfig={agentConfig}
                  onAgentConfigChange={setAgentConfig}
                  onShowShortcuts={() => setShowShortcutsDialog(true)}
                  forceShowTooltip={forceShowTooltip}
                  showSettingsDialog={showSettingsDialog}
                  onSettingsDialogChange={setShowSettingsDialog}
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
            </Panel>
            {showTerminal && (
              <>
                <PanelResizeHandle className="w-1 bg-border/40 hover:bg-border transition-colors" />
                <Panel defaultSize={40} minSize={20}>
                  <TerminalPanel threadId={threadId} />
                </Panel>
              </>
            )}
          </PanelGroup>

          {/* Botão flutuante para abrir/fechar o terminal (atalho Ctrl+`) */}
          <button
            onClick={() => toggleTerminal(threadId)}
            className="absolute bottom-3 right-3 z-40 flex items-center justify-center w-9 h-9 rounded-full bg-background border border-border shadow-md hover:bg-muted/70 text-muted-foreground hover:text-foreground transition-colors"
            title="Ctrl+`"
            aria-label="Terminal"
          >
            <TerminalSquare className="w-4 h-4" />
          </button>
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
