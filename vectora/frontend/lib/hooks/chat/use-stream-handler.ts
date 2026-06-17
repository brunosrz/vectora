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
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { useToastStore } from "@/lib/stores/toast-store";
import { useNetworkStore } from "@/lib/hooks/use-network-status";
import {
  markStreamStarted,
  markStreamEnded,
} from "@/lib/utils/stream-interruption";
import { m as msg } from "@/lib/paraglide/messages";

// ============================================================================
// UX-15 — Resiliência de rede: status do SSE
// ============================================================================
//
// Não há `EventSource` aqui — o stream é lido via `fetch().body` (SSE manual,
// ver `vectora-client.ts::readSSEStream`). Por isso "onerror"/"onopen" são
// simulados: marcamos `connected` ao receber o primeiro evento do stream e
// `reconnecting` quando o erro capturado é de transporte (não uma falha de
// aplicação reportada pelo backend via evento `error`).

/** `true` para falhas de rede/conexão (fetch caiu, DNS, timeout de socket). */
function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError) return true;
  const errMsg = err instanceof Error ? err.message : String(err);
  return /failed to fetch|network ?error|load failed|ECONNRESET|ECONNREFUSED/i.test(
    errMsg,
  );
}

/** Marca o stream como conectado; se vínhamos de uma queda, avisa via toast. */
function announceSSEConnected(): void {
  const prev = useNetworkStore.getState().sseStatus;
  if (prev === "reconnecting" || prev === "failed") {
    useToastStore.getState().success(msg.network_sse_reconnected());
  }
  if (prev !== "connected")
    useNetworkStore.getState().setSSEStatus("connected");
}

/** Marca o stream como caído por erro de transporte (badge "Reconectando…"). */
function announceSSEDropped(err: unknown): void {
  if (isNetworkError(err)) {
    useNetworkStore.getState().setSSEStatus("reconnecting");
  }
}

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
      // UX-15 — primeiro evento recebido = conexão SSE estabelecida
      let sseConnected = false;

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

      // UX-18 — marca início; `finally` desmarca por qualquer saída conhecida
      // (done/hitl/error/abort). Se a aba fechar/recarregar no meio, a marca
      // sobrevive e o próximo mount acusa "resposta pode ter sido interrompida".
      markStreamStarted(threadId);

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
          // UX-15 — primeiro evento do stream = conexão SSE de fato estabelecida
          if (!sseConnected) {
            sseConnected = true;
            announceSSEConnected();
          }

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
        // Flush defensivo: tokens acumulados no rAF pendente seriam
        // descartados pelos branches abaixo (que sobrescrevem ou ignoram
        // `content`). Garantir a entrega ANTES de qualquer mutação.
        flushNow();
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
          // UX-15 — distingue queda de transporte (badge "Reconectando…") de
          // erro de aplicação reportado pelo próprio backend via evento `error`.
          announceSSEDropped(err);
          const errMsg = err instanceof Error ? err.message : String(err);
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || `Erro no stream: ${errMsg}`,
              isThinking: false,
              thinkingDuration:
                m.thinkingStartTime !== undefined
                  ? Date.now() - m.thinkingStartTime
                  : undefined,
            })),
          );
        }
      } finally {
        // UX-18 — qualquer saída conhecida do loop desmarca a thread como
        // "streaming em andamento" (só sobra marcado o caso de aba fechada).
        markStreamEnded(threadId);
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
      // UX-15 — primeiro evento recebido = conexão SSE estabelecida
      let sseConnected = false;

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

      // UX-18 — mesma marca de "stream em andamento" do processStream
      markStreamStarted(threadId);

      try {
        const events = resumeChat(request, abortRef.current?.signal);

        for await (const event of events) {
          // UX-15 — primeiro evento do stream = conexão SSE de fato estabelecida
          if (!sseConnected) {
            sseConnected = true;
            announceSSEConnected();
          }

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
        // Defensivo: flush antes de qualquer mutação no branch de erro.
        flushNow();
        if ((err as { name?: string }).name !== "AbortError") {
          // UX-15 — mesma distinção transporte vs. aplicação do processStream
          announceSSEDropped(err);
          const errMsg = err instanceof Error ? err.message : String(err);
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || `Erro ao retomar: ${errMsg}`,
              isThinking: false,
            })),
          );
        }
      } finally {
        // UX-18 — qualquer saída conhecida do loop (done/hitl/error/abort)
        // desmarca a thread como "streaming em andamento"; só sobra marcado
        // o caso em que a aba fechou/recarregou no meio da resposta.
        markStreamEnded(threadId);
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

      // Invalidate cache do workbench quando a tool muda o disco.
      invalidateWorkbenchFor(event.tool_name, threadId);
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

    // C.28 — RAG citations: armazena fontes para renderizar referências [N]
    case "rag_citations": {
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          ragCitations: event.citations,
        })),
      );
      break;
    }

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
            reasoning: event.reasoning,
            diffPreview: event.diff_preview,
            affectedPaths: event.affected_paths,
            permissionMode: event.permission_mode,
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
// Workbench cache invalidation
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

function invalidateWorkbenchFor(
  toolName: string,
  threadId: string | undefined,
): void {
  if (toolName === "create_artifact" && threadId) {
    useWorkbenchStore.getState().invalidatePlan(threadId);
    return;
  }

  if (FILES_DIFF_TOOLS.has(toolName)) {
    const ws = useWorkspacesStore.getState().getActive();
    if (ws) {
      useWorkbenchStore.getState().invalidateFiles(ws.id);
      useWorkbenchStore.getState().invalidateDiff(ws.id);
      // Sinaliza pendência para a aba que não está montada no momento.
      useWorkbenchStore.getState().markPending(ws.id);
    }
  }
}
