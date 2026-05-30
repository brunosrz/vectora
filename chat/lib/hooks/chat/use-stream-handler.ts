/**
 * Stream Handler Hook — Vectora
 *
 * Gerencia streaming de respostas do agente Vectora via SSE.
 * Substitui o hook baseado no LangGraph SDK pelo cliente SSE nativo.
 *
 * Eventos tratados:
 * - token      → acumula texto da resposta
 * - tool_call  → adiciona tool call inline na mensagem
 * - tool_result → atualiza output da tool call
 * - hitl       → pausa para aprovação humana
 * - done       → finaliza stream
 * - error      → propaga erro ao caller
 */

"use client";

import { useCallback, useRef } from "react";
import type { Message, ToolCall, ImageAttachment } from "../../types";
import {
  streamChat,
  resumeChat,
  type StreamEvent,
  type ChatConfig,
  type ResumeChatRequest,
} from "../../api/vectora-client";
import {
  ensureMessageExists,
  updateMessageInList,
  toApiAttachments,
} from "../../utils/chat";
import type { AgentConfig } from "@/components/layout/agent-settings";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

// ============================================================================
// Types
// ============================================================================

interface UseStreamHandlerProps {
  /** Não utilizado (mantido para compatibilidade com chat-interface.tsx) */
  client?: unknown;
  threadId: string;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  agentConfig?: AgentConfig;
  shouldInterruptRef?: React.MutableRefObject<boolean>;
  /** Não utilizado (LangSmith removido) */
  userId?: string | null;
  userEmail?: string | null;
  userName?: string | null;
}

interface UseStreamHandlerReturn {
  processStream: (
    userContent: string,
    assistantMessageId: string,
    images?: ImageAttachment[],
  ) => Promise<{ assistantContent: string; runId: string | undefined }>;
  /** Retoma uma execução pausada por HITL (approve / reject / edit:<json>). */
  processResume: (
    request: ResumeChatRequest,
    assistantMessageId: string,
  ) => Promise<{ assistantContent: string }>;
}

// ============================================================================
// Hook
// ============================================================================

export function useStreamHandler({
  threadId,
  setMessages,
  agentConfig,
  shouldInterruptRef,
}: UseStreamHandlerProps): UseStreamHandlerReturn {
  // AbortController para interromper o stream quando shouldInterruptRef === true
  const abortRef = useRef<AbortController | null>(null);

  const processStream = useCallback(
    async (
      userContent: string,
      assistantMessageId: string,
      images?: ImageAttachment[],
    ): Promise<{ assistantContent: string; runId: string | undefined }> => {
      // Cancela stream anterior se ainda em andamento
      abortRef.current?.abort();
      const abort = new AbortController();
      abortRef.current = abort;

      // Garante que a mensagem do assistente existe no estado
      const thinkingStartTime = Date.now();
      const baseAssistantMessage: Message = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isThinking: true,
        thinkingStartTime,
      };
      setMessages((prev) =>
        ensureMessageExists(prev, assistantMessageId, baseAssistantMessage),
      );

      let assistantContent = "";
      let resolvedRunId: string | undefined;

      // Monta config da request
      const config: ChatConfig = {};
      if (agentConfig?.model) config.model = agentConfig.model;
      const customSystemPrompt = useSettingsStore.getState().customSystemPrompt;
      if (customSystemPrompt) config.custom_system_prompt = customSystemPrompt;
      const activeWorkspaceId = useWorkspacesStore.getState().active_id;
      if (activeWorkspaceId) config.workspace_id = activeWorkspaceId;
      const settings = useSettingsStore.getState();
      config.permission_mode = settings.permissionMode;
      // Modo rápido força esforço mínimo; senão usa o nível escolhido.
      config.reasoning_effort = settings.fastMode
        ? "low"
        : settings.reasoningEffort;

      // Converte ImageAttachment[] → Attachment[] para a API (F1)
      const attachments =
        images && images.length > 0 ? toApiAttachments(images) : undefined;

      // M2 — Token buffering: acumula tokens dentro de um animation frame (≤16ms)
      // e faz um único setMessages por frame. Evita layout thrashing em modelos
      // rápidos como Gemini Flash (100+ tokens/s → 6+ setMessages por frame sem buffer).
      let pendingTokenBatch = "";
      let flushScheduled = false;

      const scheduleTokenFlush = () => {
        if (flushScheduled) return;
        flushScheduled = true;
        requestAnimationFrame(() => {
          if (!pendingTokenBatch) {
            flushScheduled = false;
            return;
          }
          const batch = pendingTokenBatch;
          pendingTokenBatch = "";
          flushScheduled = false;
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: (typeof m.content === "string" ? m.content : "") + batch,
            })),
          );
        });
      };

      // Flush imediato (antes de eventos não-token, e ao final do stream)
      const flushNow = () => {
        if (!pendingTokenBatch) return;
        const batch = pendingTokenBatch;
        pendingTokenBatch = "";
        flushScheduled = false;
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            content: (typeof m.content === "string" ? m.content : "") + batch,
          })),
        );
      };

      try {
        const events = streamChat(
          {
            thread_id: threadId,
            content: userContent,
            config,
            ...(attachments && attachments.length > 0 && { attachments }),
          },
          abort.signal,
        );

        for await (const event of events) {
          // Interrupção solicitada pelo usuário
          if (shouldInterruptRef?.current) {
            abort.abort();
            break;
          }

          if (event.type === "token") {
            // Acumula tokens — serão flushed em batch no próximo animation frame
            assistantContent += event.content;
            pendingTokenBatch += event.content;
            scheduleTokenFlush();
            continue;
          }

          // Antes de qualquer evento não-token: flush tokens pendentes
          // para garantir que o conteúdo de texto está atualizado antes
          // de eventos que dependem do estado (ex: tool_call, done)
          flushNow();

          await handleEvent(event, assistantMessageId, setMessages, threadId);

          if (event.type === "done") {
            resolvedRunId = event.run_id || undefined;
            break;
          }
          if (event.type === "error") {
            throw new Error(event.message || "Stream error");
          }
        }

        // Flush final — tokens do último frame ainda pendentes
        flushNow();
      } catch (err: unknown) {
        if ((err as { name?: string }).name === "AbortError") {
          // Interrompido pelo usuário — não é um erro; encerra o thinking timer
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              isThinking: false,
              thinkingDuration:
                m.thinkingStartTime !== undefined
                  ? Date.now() - m.thinkingStartTime
                  : undefined,
            })),
          );
        } else {
          const msg = err instanceof Error ? err.message : String(err);
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || `Erro no stream: ${msg}`,
              isThinking: false,
              thinkingDuration:
                m.thinkingStartTime !== undefined
                  ? Date.now() - m.thinkingStartTime
                  : undefined,
            })),
          );
        }
      } finally {
        // Defesa em profundidade: garante que o spinner sempre encerra
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) =>
            m.isThinking
              ? {
                  ...m,
                  isThinking: false,
                  thinkingDuration:
                    m.thinkingStartTime !== undefined
                      ? Date.now() - m.thinkingStartTime
                      : undefined,
                }
              : m,
          ),
        );
      }

      return { assistantContent, runId: resolvedRunId };
    },
    [threadId, setMessages, agentConfig, shouldInterruptRef],
  );

  // ---------------------------------------------------------------------------
  // processResume — retoma stream após aprovação/rejeição HITL
  // ---------------------------------------------------------------------------
  const processResume = useCallback(
    async (
      request: ResumeChatRequest,
      assistantMessageId: string,
    ): Promise<{ assistantContent: string }> => {
      // Limpa hitlPending e reativa o spinner de thinking
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          hitlPending: undefined,
          isThinking: true,
          thinkingStartTime: Date.now(),
        })),
      );

      let assistantContent = "";

      // M2 — mesmo buffering de tokens usado em processStream
      let pendingTokenBatch = "";
      let flushScheduled = false;

      const scheduleTokenFlush = () => {
        if (flushScheduled) return;
        flushScheduled = true;
        requestAnimationFrame(() => {
          if (!pendingTokenBatch) {
            flushScheduled = false;
            return;
          }
          const batch = pendingTokenBatch;
          pendingTokenBatch = "";
          flushScheduled = false;
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: (typeof m.content === "string" ? m.content : "") + batch,
            })),
          );
        });
      };

      const flushNow = () => {
        if (!pendingTokenBatch) return;
        const batch = pendingTokenBatch;
        pendingTokenBatch = "";
        flushScheduled = false;
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            content: (typeof m.content === "string" ? m.content : "") + batch,
          })),
        );
      };

      try {
        const events = resumeChat(request, abortRef.current?.signal);

        for await (const event of events) {
          if (shouldInterruptRef?.current) {
            abortRef.current?.abort();
            break;
          }

          if (event.type === "token") {
            assistantContent += event.content;
            pendingTokenBatch += event.content;
            scheduleTokenFlush();
            continue;
          }

          flushNow();
          await handleEvent(event, assistantMessageId, setMessages, threadId);

          if (event.type === "done") break;
          if (event.type === "error")
            throw new Error(event.message || "Resume error");
        }

        flushNow();
      } catch (err: unknown) {
        if ((err as { name?: string }).name !== "AbortError") {
          const msg = err instanceof Error ? err.message : String(err);
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || `Erro ao retomar: ${msg}`,
              isThinking: false,
            })),
          );
        }
      } finally {
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) =>
            m.isThinking
              ? {
                  ...m,
                  isThinking: false,
                  thinkingDuration:
                    m.thinkingStartTime !== undefined
                      ? Date.now() - m.thinkingStartTime
                      : undefined,
                }
              : m,
          ),
        );
      }

      return { assistantContent };
    },
    [threadId, setMessages, shouldInterruptRef],
  );

  return { processStream, processResume };
}

// ============================================================================
// Event handler
// ============================================================================

// handleEvent processa todos os eventos exceto "token"
// (tokens são buffered diretamente nos loops de processStream/processResume — M2)
async function handleEvent(
  event: StreamEvent,
  assistantMessageId: string,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  threadId?: string,
): Promise<void> {
  switch (event.type) {
    case "token":
      // tokens handled by caller (buffered via rAF)
      break;

    case "tool_call": {
      let args: Record<string, unknown> = {};
      try {
        args = JSON.parse(event.args_json);
      } catch {
        args = { _raw: event.args_json };
      }

      const toolCall: ToolCall = {
        id: event.tool_call_id,
        name: event.tool_name,
        args,
        output: undefined,
        renderHint: (event.render_hint as ToolCall["renderHint"]) ?? "json",
        category: (event.category as ToolCall["category"]) ?? "general",
        destructive: event.destructive ?? false,
        icon: event.icon ?? "tool",
      };

      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          toolCalls: [...(m.toolCalls ?? []), toolCall],
        })),
      );

      // T11.5 — Invalidate cache do workbench quando a tool muda o disco.
      // Carregamento dinâmico para não acoplar este módulo ao store
      // (importar topo a topo cria ciclo via providers).
      void invalidateWorkbenchFor(event.tool_name, threadId);
      break;
    }

    case "tool_result": {
      let output: unknown;
      try {
        output = JSON.parse(event.content_json);
      } catch {
        output = event.content_json;
      }

      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          toolCalls: (m.toolCalls ?? []).map((tc) =>
            tc.id === event.tool_call_id
              ? { ...tc, output, isError: event.is_error }
              : tc,
          ),
        })),
      );
      break;
    }

    // D1 — ThinkingEvent: raciocínio do orchestrator
    case "thinking": {
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          thinking: {
            reason: event.reason,
            action: event.action,
            delegate_to: event.delegate_to ?? null,
            task_query: event.task_query ?? null,
          },
        })),
      );
      break;
    }

    // D2/D3 — NodeEvent: label semântico + duração por nó
    case "node": {
      if (event.status === "started" && event.node_label) {
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            currentNodeLabel: event.node_label,
          })),
        );
      } else if (
        event.status === "finished" &&
        event.duration_ms != null &&
        event.duration_ms > 0
      ) {
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            currentNodeLabel: undefined,
            nodeDurations: [
              ...(m.nodeDurations ?? []),
              {
                node: event.node,
                label: event.node_label ?? event.node,
                duration_ms: event.duration_ms!,
              },
            ],
          })),
        );
      }
      break;
    }

    case "ui_metrics":
      break;

    // E1 — HITLEvent: pausa do stream para aprovação humana
    case "hitl": {
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          isThinking: false,
          thinkingDuration:
            m.thinkingStartTime !== undefined
              ? Date.now() - m.thinkingStartTime
              : undefined,
          hitlPending: {
            toolName: event.tool_name,
            argsJson: event.args_json,
            interruptId: event.interrupt_id,
          },
        })),
      );
      break;
    }

    default:
      break;
  }
}

// ============================================================================
// Workbench cache invalidation (T11.5)
// ============================================================================
//
// Mapeamento tool_name → caches a invalidar. As tools de filesystem/git/terminal
// mexem no workspace e podem mudar a árvore, o diff e os arquivos abertos.
// `create_artifact` mexe nos artifacts da sessão.

const FILES_DIFF_TOOLS = new Set([
  "file_write",
  "file_edit",
  "terminal",
  "git_commit",
  "git_checkout",
  "git_pull",
  "git_stash",
  "git_worktree",
]);

async function invalidateWorkbenchFor(
  toolName: string,
  threadId: string | undefined,
): Promise<void> {
  // Carregamento dinâmico evita import-order issues entre módulos.
  const [{ useWorkbenchStore }, { useWorkspacesStore }] = await Promise.all([
    import("@/lib/stores/workbench-store"),
    import("@/lib/stores/workspaces-store"),
  ]);

  if (toolName === "create_artifact" && threadId) {
    useWorkbenchStore.getState().invalidatePlan(threadId);
    return;
  }

  if (FILES_DIFF_TOOLS.has(toolName)) {
    const ws = useWorkspacesStore.getState().getActive();
    if (ws) {
      useWorkbenchStore.getState().invalidateFiles(ws.id);
      useWorkbenchStore.getState().invalidateDiff(ws.id);
    }
  }
}
