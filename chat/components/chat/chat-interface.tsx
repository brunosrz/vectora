"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type { ClientProfile } from "@/lib/hooks";
import type { Message, ImageAttachment } from "@/lib/types";
import {
  createUserMessage,
  generateMessageId,
  extractTextFromContent,
} from "@/lib/utils/chat";
import { truncate } from "@/lib/utils/string";
import { useStreamHandler, useFeedback, useChatState } from "@/lib/hooks/chat";
import { useUserId } from "@/lib/hooks/auth";
import { useFileUpload, useVoiceInput } from "@/lib/hooks/files";
import { MessageList } from "./message-list";
import { EmptyStateHeader } from "./features/empty-state-header";
import { ChatInput } from "./chat-input";
import type { AgentConfig } from "@/components/layout/agent-settings";
import { VECTORA_API_URL } from "@/lib/constants/api";
import { getHistory, getThread } from "@/lib/api/vectora-client";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { useThreadMessages } from "@/lib/hooks/chat/use-thread-messages";
import { estimateTokens } from "@/lib/utils/tokens";
import { useThreadsStore } from "@/lib/stores/threads-store";
import { useSettingsStore, type Lang } from "@/lib/stores/settings-store";
import { useRouter } from "next/navigation";
import { useT, t as translate } from "@/lib/i18n";
import { useToastStore } from "@/lib/stores/toast-store";
import { consumeInterruptedFlag } from "@/lib/utils/stream-interruption";
import {
  getAllowedModels,
  getModelDisplayName,
  type ModelOption,
} from "@/lib/config/deployment-config";
import {
  SLASH_COMMANDS,
  parseSlashCommand,
  isKnownCommand,
} from "@/lib/constants/slash-commands";
import { detectAtMention } from "@/components/chat/features/at-mention-menu";

/** Idioma da UI → código BCP-47 do reconhecimento de voz. */
const VOICE_LANG: Record<Lang, string> = {
  en: "en-US",
  es: "es-ES",
  pt: "pt-BR",
};

// Stubs de compatibilidade — LangSmith removido
const readRun = async (_runId: string) => null;
const shareRun = async (_runId: string): Promise<string> => "";
import { LARGE_PASTE_THRESHOLD } from "@/lib/constants/features";

// Enhanced scrollbar styles with smooth transitions
const scrollbarStyles = `
  .custom-scrollbar {
    scroll-behavior: smooth;
    will-change: scroll-position;
  }
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #7FC8FF;
    border-radius: 3px;
    transition: background 0.2s ease;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #7FC8FF;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:active {
    background: #7FC8FF;
  }
`;

interface ChatInterfaceProps {
  showToolCalls?: boolean;
  threadId: string;
  onThreadUpdate?: (
    threadId: string,
    title: string,
    lastMessage: string,
    client?: ClientProfile,
    messageCount?: number,
  ) => void;
  onThreadNotFound?: () => void;
  agentConfig?: AgentConfig;
  onAgentConfigChange?: (config: AgentConfig) => void;
  isNewThread?: boolean;
  customTitle?: string | null;
  /** Pre-fill or auto-send a message. Use with autoSend to control behavior. */
  initialMessage?: string | null;
  /** If true, initialMessage is sent immediately. If false, it just populates the input. */
  autoSend?: boolean;
  /** Called after auto-send completes (use to clear URL params, etc.) */
  onInitialMessageSent?: () => void;
  /** When true, the input is locked (license expired/revoked). */
  inputLocked?: boolean;
  /** Localized reason shown when the input is locked. */
  inputLockedReason?: string;
}

interface QueuedMessage {
  content: string;
  files: ImageAttachment[];
  userMessage: Message;
}

export function ChatInterface({
  showToolCalls = false,
  threadId,
  onThreadUpdate,
  onThreadNotFound,
  initialMessage,
  customTitle,
  agentConfig,
  onAgentConfigChange,
  isNewThread = false,
  autoSend = false,
  onInitialMessageSent,
  inputLocked = false,
}: ChatInterfaceProps) {
  // ============================================================================
  // State Management
  // ============================================================================

  // Cached por threadId via Zustand — switching back não causa flash vazio.
  const [messages, setMessages] = useThreadMessages(threadId);

  // Idioma do reconhecimento de voz acompanha o idioma da interface.
  const voiceLang = useSettingsStore((s) => s.language);

  // A.2d — workspace ativo para o botão de rewind por mensagem.
  const activeWorkspaceId = useWorkspacesStore((s) => s.active_id ?? undefined);

  const router = useRouter();
  const t = useT();

  // Workspace acompanha a sessão: ao abrir/trocar de chat, ativa o workspace
  // gravado naquela thread. Threads novas (sem workspace ainda) são ignoradas —
  // o backend cria o padrão em Documents/src/<id> na primeira mensagem.
  useEffect(() => {
    if (!threadId) return;
    let cancelled = false;
    getThread(threadId)
      .then((thread) => {
        if (!cancelled && thread.workspace_id) {
          void useWorkspacesStore.getState().setActive(thread.workspace_id);
        }
      })
      .catch(() => {
        /* thread nova ou inexistente — sem workspace a restaurar */
      });
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  // UI state with reducer
  const {
    state: uiState,
    dispatch: uiDispatch,
    setInput,
  } = useChatState(threadId);
  const [inputError, setInputError] = useState<string | null>(null);
  const inputLengthRef = useRef(uiState.input.length);

  // T10.4 — Consume drafts pré-populados por outras áreas (ex.: empty
  // state do PlanTab que faz "Pedir um plano ao Vectora"). O draft é
  // escrito no chat-input-store; aqui consumimos uma única vez ao mount
  // e a cada mudança no campo `draft`. Limpa o store após consumir.
  const pendingDraft = useChatInputStore((s) => s.draft);
  const consumeDraft = useChatInputStore((s) => s.consumeDraft);
  useEffect(() => {
    if (pendingDraft) {
      setInput(pendingDraft);
      consumeDraft();
    }
  }, [pendingDraft, setInput, consumeDraft]);

  // Consume @mentions injetados pelo painel de arquivos (Files tab → chat).
  const pendingMention = useChatInputStore((s) => s.mention);
  const consumeMention = useChatInputStore((s) => s.consumeMention);
  // Ref estável para o input atual sem torná-lo dep do efeito.
  const currentInputRef = useRef(uiState.input);
  currentInputRef.current = uiState.input;
  useEffect(() => {
    if (!pendingMention) return;
    const cur = currentInputRef.current.trimEnd();
    setInput(cur ? `${cur} @${pendingMention} ` : `@${pendingMention} `);
    consumeMention();
    setTimeout(() => textareaRef.current?.focus(), 50);
  }, [pendingMention, setInput, consumeMention]);

  // File upload state
  const {
    attachedFiles,
    uploadError,
    isDragging,
    handleFileSelect,
    handlePaste,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    removeFile,
    clearFiles,
    setUploadError,
    processFiles,
  } = useFileUpload({ disableImageUploads: false });

  // Message queue for sending while AI is responding
  const messageQueueRef = useRef<QueuedMessage[]>([]);
  const isProcessingQueueRef = useRef(false);
  const [queuedMessagesDisplay, setQueuedMessagesDisplay] = useState<
    { content: string; id: string }[]
  >([]);

  // Track the "base" input text (before voice input started + finalized transcripts)
  const baseInputRef = useRef(uiState.input);

  // Sem limite de tamanho de input — paste grande vira anexo via
  // handleInputPaste (F.4.1). Mantemos o nome `setLimitedInput` por
  // compatibilidade com os call sites; ele apenas limpa erro e propaga.
  const setLimitedInput = useCallback(
    (value: string) => {
      setInputError(null);
      setInput(value);
    },
    [setInput],
  );

  // Voice input — append transcribed text to current input
  const {
    isListening: isVoiceListening,
    isSupported: isVoiceSupported,
    error: voiceError,
    interimTranscript,
    toggleListening: handleVoiceToggle,
  } = useVoiceInput({
    lang: VOICE_LANG[voiceLang] ?? "en-US",
    onTranscript: (text) => {
      const newBase = baseInputRef.current
        ? `${baseInputRef.current} ${text}`
        : text;
      baseInputRef.current = newBase;
      setInput(newBase);
    },
  });

  useEffect(() => {
    if (!isVoiceListening && !interimTranscript) {
      baseInputRef.current = uiState.input;
    }
  }, [uiState.input, isVoiceListening, interimTranscript]);

  const displayInput =
    isVoiceListening && interimTranscript
      ? baseInputRef.current
        ? `${baseInputRef.current} ${interimTranscript}`
        : interimTranscript
      : uiState.input;
  const cappedDisplayInput = displayInput;
  inputLengthRef.current = cappedDisplayInput.length;

  // Custom toggle that captures current input as base when starting
  const toggleVoiceListening = useCallback(() => {
    if (!isVoiceListening) {
      // Starting - capture current input as base
      baseInputRef.current = uiState.input;
    }
    handleVoiceToggle();
  }, [isVoiceListening, uiState.input, handleVoiceToggle]);

  // ============================================================================
  // Refs
  // ============================================================================

  // Create a ref to control stream interruption
  const shouldInterruptRef = useRef(false);

  // File input ref for triggering file selection
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Textarea ref for auto-focus
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Track previous loading state to detect completion of AI response
  const prevIsLoadingRef = useRef(false);

  // ============================================================================
  // User Information
  // ============================================================================

  // userId: gerado localmente (sem autenticação por agora)
  const userId = useUserId();

  // Não há mais cliente SDK — o vectora-client usa fetch nativo

  // Memoize user metadata (usado por subcomponentes)
  const userEmail = useMemo(() => userId || null, [userId]);
  const userName = useMemo(
    () => (userId ? `User ${userId.slice(0, 8)}` : null),
    [userId],
  );

  // ============================================================================
  // Custom Hooks
  // ============================================================================

  const { processStream, processResume } = useStreamHandler({
    threadId,
    setMessages,
    agentConfig,
    shouldInterruptRef,
    userId,
    userEmail,
    userName,
  });

  // E2 — HITL: retoma execução pausada após decisão do usuário
  const handleHitlDecision = useCallback(
    async (
      messageId: string,
      interruptId: string,
      decision: "approve" | "reject" | `edit:${string}`,
    ) => {
      uiDispatch({ type: "START_SEND" });
      try {
        const { assistantContent } = await processResume(
          { thread_id: threadId, interrupt_id: interruptId, decision },
          messageId,
        );
        if (assistantContent && onThreadUpdate) {
          onThreadUpdate(
            threadId,
            customTitle || "Continuação",
            truncate(assistantContent, 100),
          );
        }
      } catch (error) {
        console.error("Erro ao retomar após HITL:", error);
      } finally {
        uiDispatch({ type: "FINISH_SEND" });
      }
    },
    [processResume, threadId, onThreadUpdate, customTitle, uiDispatch],
  );

  const {
    feedbackComment,
    showCommentInput,
    handleFeedback,
    handleSubmitComment,
    handleCancelComment,
    handleToggleComment,
    setFeedbackComment,
  } = useFeedback({
    messages,
    setMessages,
  });

  // ============================================================================
  // Effects
  // ============================================================================

  // Restore draft when switching threads
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Check if there's an initial message (from ticket page, etc.)
    // If so, let that take precedence on first load
    if (initialMessage && !uiState.hasAutoSent) {
      return;
    }

    const draft = localStorage.getItem(`draft-${threadId}`);
    if (draft) {
      setLimitedInput(draft);
    } else {
      // Clear input when switching to thread with no draft
      setLimitedInput("");
    }
  }, [threadId, initialMessage, uiState.hasAutoSent, setLimitedInput]);

  // Track if we've sent a message on the current thread to skip unnecessary reloads
  const hasSentMessageRef = useRef<string | null>(null);

  // Load conversation history when threadId changes
  useEffect(() => {
    // Capture the current threadId to prevent race conditions
    const currentThreadId = threadId;

    const loadThreadHistory = async () => {
      // Skip loading for new threads - they don't exist in backend yet
      if (isNewThread) {
        console.log("New thread detected - skipping backend load");
        setMessages([]);
        uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
        return;
      }

      // Skip reload if we just sent a message on this thread - client state is authoritative
      // This prevents race conditions where history reload overwrites trace URLs
      if (hasSentMessageRef.current === currentThreadId) {
        console.log("Skipping reload - we just sent a message on this thread");
        uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
        return;
      }

      if (!VECTORA_API_URL) {
        console.error(
          "Missing NEXT_PUBLIC_VECTORA_API_URL; cannot load thread history",
        );
        uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
        return;
      }

      // UX-18 — se a aba fechou/recarregou no meio de uma resposta, a marca
      // em localStorage (ver use-stream-handler.ts) ainda está presente;
      // avisamos o usuário de que a resposta anterior pode ter sido cortada.
      if (consumeInterruptedFlag(currentThreadId)) {
        // `translate` (não o `t` do useT()) — evita acrescentar dependência
        // de hook a este efeito só por causa de um toast condicional.
        useToastStore.getState().warning(translate("chat.stream_interrupted"));
      }

      try {
        console.log("Loading thread history for:", currentThreadId);
        const { messages: historyMessages } = await getHistory(
          currentThreadId,
        ).catch((err) => {
          const msg = err instanceof Error ? err.message : String(err);
          if (msg.includes("404")) {
            console.log("Thread not found (404)");
            onThreadNotFound?.();
          } else {
            console.error("Error fetching thread history:", err);
          }
          return { messages: [] };
        });

        if (historyMessages.length === 0) {
          setMessages([]);
          uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
          return;
        }

        const convertedMessages: Message[] = historyMessages
          .map(
            (msg, idx) =>
              ({
                id: `history-${currentThreadId}-${idx}`,
                role: msg.role === "human" ? "user" : "assistant",
                content: msg.content,
                timestamp: msg.created_at
                  ? new Date(msg.created_at)
                  : new Date(),
              }) as Message,
          )
          .filter((msg) => msg.content.trim().length > 0);

        console.log(
          `SUCCESS: Loaded ${convertedMessages.length} messages from thread history`,
        );

        if (currentThreadId === threadId) {
          setMessages(convertedMessages);
          uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
        } else {
          console.log(
            `Discarding messages for ${currentThreadId} - now on ${threadId}`,
          );
        }
      } catch (error) {
        console.error("Unexpected error loading thread history:", error);
        uiDispatch({ type: "SET_LOADING_THREAD", payload: false });
      }
    };

    console.log("Thread ID changed to:", threadId);

    // Stale-while-revalidate: se já temos cache pra esta thread, renderiza
    // instantâneo e refetch em background SEM loading state (evita flash vazio).
    // Sem cache: comportamento legacy (loading + fetch).
    //
    // IMPORTANTE: lemos o cache via `getState()` (não reativo) para não
    // adicionar `hasCachedMessages` como dep — caso contrário o effect
    // re-roda toda vez que o cache muda, causando re-fetch em loop.
    const hasCached =
      (useThreadsStore.getState().cache[threadId]?.messages.length ?? 0) > 0;
    uiDispatch({ type: "SET_LOADING_THREAD", payload: !hasCached });

    // Clear the "sent message" flag if we're switching to a completely different thread
    // (but keep it if it's the same thread - that's the case we want to skip reload)
    if (hasSentMessageRef.current && hasSentMessageRef.current !== threadId) {
      hasSentMessageRef.current = null;
    }

    // Load new thread immediately
    loadThreadHistory();
  }, [threadId, uiDispatch, isNewThread, setMessages, onThreadNotFound]);

  // Auto-focus textarea when loading completes and userId is available
  useEffect(() => {
    if (!uiState.isLoadingThread && userId && textareaRef.current) {
      // Small delay to ensure DOM is ready
      const timeoutId = setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [uiState.isLoadingThread, userId]);

  // Auto-focus textarea after AI finishes responding
  useEffect(() => {
    // Detect transition from loading (true) to not loading (false)
    const wasLoading = prevIsLoadingRef.current;
    const isCurrentlyLoading = uiState.isLoading || uiState.isRegenerating;

    // Update the ref for next render
    prevIsLoadingRef.current = isCurrentlyLoading;

    // Focus only when transitioning from loading to not loading
    if (
      wasLoading &&
      !isCurrentlyLoading &&
      userId &&
      textareaRef.current &&
      messages.length > 0
    ) {
      // Small delay to ensure DOM is ready and smooth transition
      const timeoutId = setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [uiState.isLoading, uiState.isRegenerating, userId, messages.length]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  // Process a single message (used for both immediate send and queue processing)
  const processMessage = useCallback(
    async (content: string, files: ImageAttachment[], userMessage: Message) => {
      uiDispatch({ type: "START_SEND" });
      shouldInterruptRef.current = false;
      hasSentMessageRef.current = threadId;

      try {
        const assistantMessageId = generateMessageId();
        const { assistantContent } = await processStream(
          content,
          assistantMessageId,
          files,
        );

        if (onThreadUpdate && assistantContent) {
          const firstUserMsg =
            messages.find((m) => m.role === "user") || userMessage;
          const title =
            customTitle ||
            truncate(firstUserMsg.content, 60) ||
            "New conversation";
          const messageCount = messages.length + 2;
          onThreadUpdate(
            threadId,
            title,
            truncate(assistantContent, 100),
            undefined,
            messageCount,
          );
        }
      } catch (error) {
        console.error("Error streaming from LangGraph:", error);
        const errorMsg =
          error instanceof Error
            ? error.message
            : "Failed to connect to the agent";
        const errorMessage = createUserMessage(errorMsg);
        errorMessage.role = "assistant";
        // M5 — marcado para exibir botão de retry no MessageItem
        errorMessage.isError = true;

        setMessages((prev) => [...prev, errorMessage]);

        if (onThreadUpdate) {
          const messageCount = messages.length + 2;
          onThreadUpdate(
            threadId,
            customTitle ||
              truncate(userMessage.content, 60) ||
              "New conversation",
            truncate(errorMessage.content, 100),
            undefined,
            messageCount,
          );
        }
      } finally {
        uiDispatch({ type: "FINISH_SEND" });
      }
    },
    [
      threadId,
      onThreadUpdate,
      processStream,
      messages,
      customTitle,
      uiDispatch,
      setMessages,
    ],
  );

  // Process queued messages one by one
  const processQueue = useCallback(async () => {
    if (isProcessingQueueRef.current || messageQueueRef.current.length === 0)
      return;

    isProcessingQueueRef.current = true;
    const nextMessage = messageQueueRef.current.shift()!;

    // Remove from queue display and add to chat
    setQueuedMessagesDisplay((prev) =>
      prev.filter((m) => m.id !== nextMessage.userMessage.id),
    );
    setMessages((prev) => [...prev, nextMessage.userMessage]);

    await processMessage(
      nextMessage.content,
      nextMessage.files,
      nextMessage.userMessage,
    );

    isProcessingQueueRef.current = false;

    // Process next in queue if any
    if (messageQueueRef.current.length > 0) {
      processQueue();
    }
  }, [processMessage, setMessages]);

  // Process queue when AI finishes responding
  useEffect(() => {
    const wasLoading = prevIsLoadingRef.current;
    const isCurrentlyLoading = uiState.isLoading || uiState.isRegenerating;

    // When loading finishes and there are queued messages, process them
    if (
      wasLoading &&
      !isCurrentlyLoading &&
      messageQueueRef.current.length > 0
    ) {
      processQueue();
    }
  }, [uiState.isLoading, uiState.isRegenerating, processQueue]);

  // Auto-send initial message (for ?q= URL param)
  useEffect(() => {
    const trimmedMessage = initialMessage?.trim();
    if (
      !trimmedMessage ||
      uiState.hasAutoSent ||
      uiState.isLoadingThread ||
      !userId
    ) {
      return;
    }

    uiDispatch({ type: "SET_AUTO_SENT", payload: true });

    if (autoSend) {
      const userMessage = createUserMessage(trimmedMessage);
      setMessages((prev) => [...prev, userMessage]);
      processMessage(trimmedMessage, [], userMessage)
        .then(() => onInitialMessageSent?.())
        .catch((error) => {
          console.error("Failed to auto-send initial message:", error);
          onInitialMessageSent?.(); // Clear URL param even on error to prevent retry loops
        });
    } else {
      // Just populate input (existing behavior for ticket page, etc.)
      setLimitedInput(trimmedMessage);
    }
  }, [
    initialMessage,
    autoSend,
    uiState.hasAutoSent,
    uiState.isLoadingThread,
    userId,
    setLimitedInput,
    uiDispatch,
    processMessage,
    onInitialMessageSent,
    setMessages,
  ]);

  // Dispatch de slash commands (Bloco H) — executa ações locais cuja
  // funcionalidade já existe, sem enviar a mensagem ao agente.
  const dispatchSlash = useCallback(
    (name: string, arg: string) => {
      const addSystemMsg = (content: string) => {
        setMessages((prev) => [
          ...prev,
          {
            id: generateMessageId(),
            role: "assistant",
            content,
            timestamp: new Date(),
          },
        ]);
      };

      if (name === "help") {
        const lines = SLASH_COMMANDS.map(
          (c) => `- \`${c.usage}\` — ${t(c.descKey)}`,
        ).join("\n");
        addSystemMsg(`${t("slash.help_intro")}\n\n${lines}`);
        return;
      }
      if (name === "clear") {
        router.push("/");
        return;
      }
      if (name === "model") {
        const models = getAllowedModels();
        if (!arg) {
          addSystemMsg(
            t("slash.model_usage", {
              models: models.map((m) => getModelDisplayName(m)).join(", "),
            }),
          );
          return;
        }
        const term = arg.toLowerCase();
        const found = models.find(
          (m) =>
            m.toLowerCase().includes(term) ||
            getModelDisplayName(m).toLowerCase().includes(term),
        );
        if (found && onAgentConfigChange && agentConfig) {
          onAgentConfigChange({ ...agentConfig, model: found });
          addSystemMsg(
            t("slash.model_changed", { model: getModelDisplayName(found) }),
          );
        } else {
          addSystemMsg(t("slash.model_not_found", { name: arg }));
        }
      }
    },
    [setMessages, router, t, onAgentConfigChange, agentConfig],
  );

  // Handler de seleção no AtMentionMenu: substitui @query pelo @path escolhido.
  const handleAtMentionSelect = useCallback(
    (path: string, startIdx: number, endIdx: number) => {
      const cur = uiState.input;
      const suffix = path.endsWith("/") ? "" : " ";
      const next =
        cur.slice(0, startIdx) + "@" + path + suffix + cur.slice(endIdx);
      setLimitedInput(next);
      if (!path.endsWith("/")) {
        setTimeout(() => textareaRef.current?.focus(), 10);
      }
    },
    [uiState.input, setLimitedInput],
  );

  // Resolve tokens @path no conteúdo da mensagem antes de enviar ao agente.
  // Busca o conteúdo de cada arquivo referenciado e o prepende como bloco de
  // contexto — o usuário vê @tokens na UI, mas o agente recebe o conteúdo real.
  const resolveAtMentions = useCallback(
    async (content: string): Promise<string> => {
      const mentionRegex = /@([^\s@]+)/g;
      const paths: string[] = [];
      let m: RegExpExecArray | null;
      while ((m = mentionRegex.exec(content)) !== null) {
        paths.push(m[1]);
      }
      if (paths.length === 0) return content;

      const ws = useWorkspacesStore.getState().getActive();
      if (!ws) return content;

      const results = await Promise.allSettled(
        paths.map(async (p) => {
          const qs = new URLSearchParams({ path: p });
          const res = await fetch(
            `/workspaces/${encodeURIComponent(ws.id)}/file?${qs}`,
          );
          if (!res.ok) return null;
          const data = await res.json().catch(() => null);
          if (!data || data.kind === "binary") return null;
          return { path: p, content: String(data.content ?? "") };
        }),
      );

      const blocks = results
        .filter(
          (r): r is PromiseFulfilledResult<{ path: string; content: string }> =>
            r.status === "fulfilled" && r.value !== null,
        )
        .map(
          ({ value: { path, content: fc } }) =>
            `\`\`\`\n// @${path}\n${fc}\n\`\`\``,
        );

      if (blocks.length === 0) return content;
      return `${blocks.join("\n\n")}\n\n${content}`;
    },
    [],
  );

  const handleSend = useCallback(async () => {
    if (inputLocked) {
      return;
    }
    if (!uiState.input.trim() && attachedFiles.length === 0) {
      return;
    }

    if (!userId) {
      return;
    }

    // Slash command? Executa localmente e não envia ao agente.
    const parsed = parseSlashCommand(uiState.input);
    if (parsed && isKnownCommand(parsed.name)) {
      setInput("");
      setInputError(null);
      clearFiles();
      dispatchSlash(parsed.name, parsed.arg);
      return;
    }

    const rawInput = uiState.input;
    const userMessage = createUserMessage(rawInput);
    if (attachedFiles.length > 0) {
      userMessage.images = attachedFiles;
    }

    // Resolve @path tokens antes de enviar — preserva display original na UI.
    const resolvedInput = await resolveAtMentions(rawInput);
    const currentInput = resolvedInput;
    const currentFiles = [...attachedFiles];

    // Clear input and files immediately
    setInput("");
    setInputError(null);
    clearFiles();

    // If currently loading, queue the message (don't show in chat yet)
    if (uiState.isLoading || uiState.isRegenerating) {
      const queuedItem = {
        content: currentInput,
        files: currentFiles,
        userMessage,
      };
      messageQueueRef.current.push(queuedItem);
      setQueuedMessagesDisplay((prev) => [
        ...prev,
        { content: currentInput, id: userMessage.id },
      ]);
      return;
    }

    // Show message in chat and process immediately
    const previousMessages = messages;
    setMessages((prev) => [...prev, userMessage]);

    // F.2.5 — Otimismo da sidebar: avisa o pai já no envio da primeira
    // mensagem, com lastMessage vazio. handleThreadUpdate adiciona a
    // thread otimisticamente; o título da IA é gerado depois (no
    // segundo onThreadUpdate, ao final do stream). Sem isso, a sidebar
    // só descobria a thread quando a resposta da IA terminava.
    if (previousMessages.length === 0 && onThreadUpdate) {
      const optimisticTitle =
        customTitle || truncate(currentInput, 60) || "New conversation";
      onThreadUpdate(threadId, optimisticTitle, "", undefined, 1);
    }

    await processMessage(currentInput, currentFiles, userMessage);

    // Check if anything was queued while processing
    if (messageQueueRef.current.length > 0) {
      processQueue();
    }
  }, [
    uiState.input,
    uiState.isLoading,
    uiState.isRegenerating,
    attachedFiles,
    userId,
    customTitle,
    messages,
    onThreadUpdate,
    threadId,
    setInput,
    clearFiles,
    processMessage,
    processQueue,
    dispatchSlash,
    resolveAtMentions,
    setMessages,
    inputLocked,
  ]);

  const handleStop = useCallback(async () => {
    console.log("User requested stop");
    uiDispatch({ type: "SET_STOPPING", payload: true });
    shouldInterruptRef.current = true;
  }, [uiDispatch]);

  const handleRegenerate = useCallback(async () => {
    if (uiState.isLoading || uiState.isRegenerating) return;

    const lastUserMessage = messages
      .toReversed()
      .find((m) => m.role === "user");
    if (!lastUserMessage) return;

    const messagesUpToLastUser = messages.slice(
      0,
      messages.findIndex((m) => m.id === lastUserMessage.id) + 1,
    );
    setMessages(messagesUpToLastUser);
    uiDispatch({ type: "START_REGENERATE" });
    shouldInterruptRef.current = false;

    try {
      const assistantMessageId = generateMessageId();
      const { assistantContent } = await processStream(
        lastUserMessage.content,
        assistantMessageId,
      );

      if (onThreadUpdate && assistantContent) {
        const firstUserMsg = messagesUpToLastUser.find(
          (m) => m.role === "user",
        );
        const title =
          customTitle ||
          (firstUserMsg
            ? truncate(firstUserMsg.content, 60)
            : "New conversation");
        const messageCount = messagesUpToLastUser.length + 1;
        onThreadUpdate(
          threadId,
          title,
          truncate(assistantContent, 100),
          undefined,
          messageCount,
        );
      }
    } catch (error) {
      console.error("Error regenerating:", error);
      const errorMessage = createUserMessage(
        `Error: ${error instanceof Error ? error.message : "Failed to regenerate response"}`,
      );
      errorMessage.role = "assistant";
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      uiDispatch({ type: "FINISH_REGENERATE" });
    }
  }, [
    uiState.isLoading,
    uiState.isRegenerating,
    messages,
    processStream,
    onThreadUpdate,
    threadId,
    uiDispatch,
    setMessages,
    customTitle,
  ]);

  const handleEditAndRerun = useCallback(
    async (messageId: string, newContent: string) => {
      console.log(
        "Edit and rerun from message:",
        messageId,
        "new content:",
        newContent.slice(0, 50),
      );

      if (uiState.isLoading || uiState.isRegenerating) return;

      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      const messagesUpToEdit = messages.slice(0, messageIndex);
      const updatedMessage = {
        ...messages[messageIndex],
        content: newContent,
      };

      setMessages([...messagesUpToEdit, updatedMessage]);
      uiDispatch({ type: "SET_LOADING", payload: true });
      shouldInterruptRef.current = false;

      try {
        const assistantMessageId = generateMessageId();
        console.log(
          "Rerunning from edited message with assistantMessageId:",
          assistantMessageId,
        );
        const { assistantContent } = await processStream(
          newContent,
          assistantMessageId,
        );

        if (onThreadUpdate && assistantContent) {
          const firstUserMsg =
            messagesUpToEdit.find((m) => m.role === "user") || updatedMessage;
          const title =
            customTitle ||
            truncate(firstUserMsg.content, 60) ||
            "New conversation";
          const messageCount = messagesUpToEdit.length + 2;
          onThreadUpdate(
            threadId,
            title,
            truncate(assistantContent, 100),
            undefined,
            messageCount,
          );
        }
      } catch (error) {
        console.error("Error rerunning from edit:", error);
        const errorMessage = createUserMessage(
          `Error: ${error instanceof Error ? error.message : "Failed to rerun from edit"}`,
        );
        errorMessage.role = "assistant";
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        uiDispatch({ type: "SET_LOADING", payload: false });
        uiDispatch({ type: "SET_STOPPING", payload: false });
      }
    },
    [
      uiState.isLoading,
      uiState.isRegenerating,
      messages,
      processStream,
      onThreadUpdate,
      threadId,
      uiDispatch,
      setMessages,
      customTitle,
    ],
  );

  const handleCopy = async (content: string, messageId: string) => {
    await navigator.clipboard.writeText(content);
    uiDispatch({ type: "SET_COPIED_ID", payload: messageId });
    setTimeout(
      () => uiDispatch({ type: "SET_COPIED_ID", payload: null }),
      2000,
    );
  };

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (userId) {
          handleSend();
        }
      }
    },
    [userId, handleSend],
  );

  const handleFileButtonClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, []);

  // F.4.1 — paste grande vira anexo. Mantém UX do ChatGPT/Claude:
  // texto curto cola normal; texto longo (> LARGE_PASTE_THRESHOLD)
  // entra como `pasted-<N>.txt` na grid de anexos. Imagens continuam
  // sendo capturadas pelo handlePaste do useFileUpload.
  const handleInputPaste = useCallback(
    async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const pastedText = e.clipboardData?.getData("text") ?? "";
      if (pastedText.length > LARGE_PASTE_THRESHOLD) {
        e.preventDefault();
        const blob = new Blob([pastedText], { type: "text/plain" });
        const fileName = `pasted-${Date.now()}.txt`;
        const file = new File([blob], fileName, { type: "text/plain" });
        await processFiles([file]);
        return;
      }
      // Texto curto: deixa o browser inserir; o handlePaste do
      // useFileUpload ainda intercepta imagens do clipboard.
      await handlePaste(e);
    },
    [handlePaste, processFiles],
  );

  // ============================================================================
  // Computed Values
  // ============================================================================

  // Check if this is a new chat (no messages yet)
  const isNewChat = messages.length === 0 && !uiState.isLoadingThread;

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <>
      <style>{scrollbarStyles}</style>
      <main className="h-full flex flex-col overflow-hidden relative">
        {isNewChat ? (
          <EmptyStateHeader />
        ) : (
          <MessageList
            messages={messages}
            showToolCalls={showToolCalls}
            isRegenerating={uiState.isRegenerating}
            isLoadingThread={uiState.isLoadingThread}
            copiedId={uiState.copiedId}
            onCopy={handleCopy}
            onRegenerate={handleRegenerate}
            onEditAndRerun={handleEditAndRerun}
            feedbackComment={feedbackComment}
            showCommentInput={showCommentInput}
            onFeedback={handleFeedback}
            onSubmitComment={handleSubmitComment}
            onCancelComment={handleCancelComment}
            onToggleComment={handleToggleComment}
            setFeedbackComment={setFeedbackComment}
            onHitlDecision={handleHitlDecision}
            threadId={threadId}
            onRetry={handleRegenerate}
            workspaceId={activeWorkspaceId}
          />
        )}

        <ChatInput
          input={cappedDisplayInput}
          onInputChange={setLimitedInput}
          onAtMentionSelect={handleAtMentionSelect}
          onSend={handleSend}
          onKeyDown={handleKeyDown}
          isLoading={uiState.isLoading}
          isStopping={uiState.isStopping}
          onStop={handleStop}
          userId={userId}
          attachedFiles={attachedFiles}
          uploadError={uploadError}
          inputError={inputError}
          isDragging={isDragging}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onPaste={handleInputPaste}
          onRemoveFile={removeFile}
          onFileButtonClick={handleFileButtonClick}
          fileInputRef={fileInputRef}
          onFileSelect={handleFileSelect}
          textareaRef={textareaRef}
          isVoiceListening={isVoiceListening}
          isVoiceSupported={isVoiceSupported}
          onVoiceToggle={toggleVoiceListening}
          voiceError={voiceError}
          queuedMessages={queuedMessagesDisplay}
          modelId={agentConfig?.model}
          tokensUsed={estimateTokens(
            messages.map((m) =>
              typeof m.content === "string" ? m.content : "",
            ),
          )}
          agentConfig={agentConfig}
          onAgentConfigChange={onAgentConfigChange}
          dropHintExpanded={isNewChat}
        />
      </main>
    </>
  );
}
