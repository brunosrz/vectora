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
import { stripMarkdownEnvelope } from "../../utils/string/markdown-envelope";
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
// Streaming rendering
// ============================================================================

// Cede controle ao scheduler do browser para que React consiga commitar
// atualizações de estado e o browser pinte entre tokens.
//
// Problema raiz: reader.read() resolve como microtask quando há dados
// bufferizados — o loop for-await processa todos os tokens sem nunca ceder ao
// event loop. requestAnimationFrame não dispara enquanto microtasks estão
// rodando. scheduler.yield() (Chromium/Electron) cede sem delay artificial;
// MessageChannel é o fallback (sub-milissegundo, sem o delay mínimo de 4ms
// do setTimeout).
function yieldToBrowser(): Promise<void> {
  type Sched = { yield: () => Promise<void> };
  const sched = (globalThis as { scheduler?: Sched }).scheduler;
  if (typeof sched?.yield === "function") return sched.yield();
  return new Promise<void>((resolve) => {
    const { port1, port2 } = new MessageChannel();
    port1.addEventListener(
      "message",
      () => {
        port1.close();
        resolve();
      },
      { once: true },
    );
    port1.start();
    port2.postMessage(null);
    port2.close();
  });
}

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
export function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError) return true;
  const errMsg = err instanceof Error ? err.message : String(err);
  return /failed to fetch|network ?error|load failed|ECONNRESET|ECONNREFUSED/i.test(
    errMsg,
  );
}

/**
 * Mensagem amigável (localizada) para um erro de aplicação reportado pelo
 * backend via evento `error`. O backend classifica em códigos estáveis
 * (`RATE_LIMIT`, `AUTH`, `STREAM_ERROR`) — aqui mapeamos para i18n. Erros de
 * limite/quota do provedor (ex.: 429 do Gemini) não vazam o JSON cru.
 */
export function streamErrorMessage(code?: string): string {
  switch (code) {
    case "RATE_LIMIT":
      return msg.chat_error_rate_limit();
    case "AUTH":
      return msg.chat_error_auth();
    case "TIMEOUT":
      return msg.chat_error_timeout();
    case "MODEL_NO_VISION":
      return msg.chat_error_model_no_vision();
    default:
      return msg.chat_error_generic();
  }
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
  // A UI sempre mostra uma mensagem genérica localizada (nunca o erro cru
  // pro usuário) — mas sem isso, a causa real (status HTTP, "failed to
  // fetch", etc.) some completamente. Loga no console pra dar pra
  // diagnosticar via DevTools (Ctrl+Shift+I, inclusive no build desktop).
  console.error("[chat] queda de transporte no stream:", err);
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
  /** Troca automática de provider por quota — atualiza model selector + toast. */
  onModelSwitched?: (fromModel: string, toModel: string) => void;
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
  /**
   * Aborta o stream em andamento IMEDIATAMENTE (não espera o próximo evento
   * SSE chegar). Bug: `handleStop` só setava `shouldInterruptRef.current`,
   * checado unicamente dentro do `for await` do loop de eventos — se o
   * modelo está "pensando" sem produzir token nenhum, o cancelamento não
   * tinha efeito nenhum até o servidor mandar alguma coisa.
   */
  abort: () => void;
}

// ============================================================================
// Hook
// ============================================================================

export function useStreamHandler({
  threadId,
  setMessages,
  agentConfig,
  shouldInterruptRef,
  onModelSwitched,
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

      // activeId rastreia a bolha corrente; muda ao receber message_break.
      let activeId = assistantMessageId;

      let assistantContent = "";
      let resolvedRunId: string | undefined;
      // UX-15 — primeiro evento recebido = conexão SSE estabelecida
      let sseConnected = false;

      // Monta config da request
      const config: ChatConfig = {};
      if (agentConfig?.model) config.model = agentConfig.model;
      const customSystemPrompt = useSettingsStore.getState().customSystemPrompt;
      if (customSystemPrompt) config.custom_system_prompt = customSystemPrompt;
      const settings = useSettingsStore.getState();
      // Modo Chat: conversacional puro, sem workspace/folders.
      config.chat_mode = settings.chatMode;
      const activeWorkspaceId = useWorkspacesStore.getState().active_id;
      if (!settings.chatMode && activeWorkspaceId)
        config.workspace_id = activeWorkspaceId;
      config.permission_mode = settings.permissionMode;
      config.reasoning_effort = settings.reasoningEffort;

      // Converte ImageAttachment[] → Attachment[] para a API (F1)
      const attachments =
        images && images.length > 0 ? toApiAttachments(images) : undefined;

      // needsSeparator: true após message_break — próximo token recebe "\n\n"
      // de separação (só quando há conteúdo prévio na bolha).
      let needsSeparator = false;

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
            assistantContent += event.content;
            const token = event.content;
            const sep = needsSeparator ? "\n\n" : "";
            needsSeparator = false;
            setMessages((prev) =>
              updateMessageInList(prev, activeId, (m) => {
                const cur = typeof m.content === "string" ? m.content : "";
                return { ...m, content: cur + (cur && sep ? sep : "") + token };
              }),
            );
            // Cede ao scheduler do browser para que o token apareça na tela
            // antes do próximo ser processado (streaming visível letra a letra).
            await yieldToBrowser();
            continue;
          }

          // Fallback automático de provider por quota: atualiza model selector + toast
          if (event.type === "model_switched") {
            onModelSwitched?.(event.from_model, event.to_model);
            continue;
          }

          // Quebra de segmento: o backend mudou de nó emissor de tokens.
          // stripMarkdownEnvelope aqui é defensivo (no-op na maioria das
          // respostas — o modelo não é mais instruído a envelopar em fence),
          // só entra em ação se algum provider insistir em envelopar por
          // conta própria. Seta separador para o próximo segmento. Continua
          // na MESMA bolha — sem nova mensagem.
          if (event.type === "message_break") {
            setMessages((prev) =>
              updateMessageInList(prev, activeId, (m) => {
                const current = typeof m.content === "string" ? m.content : "";
                return { ...m, content: stripMarkdownEnvelope(current) };
              }),
            );
            assistantContent = stripMarkdownEnvelope(assistantContent);
            needsSeparator = true;
            continue;
          }

          await handleEvent(event, activeId, setMessages, threadId);

          if (event.type === "done") {
            resolvedRunId = event.run_id || undefined;
            break;
          }
          if (event.type === "error") {
            // Erro de aplicação reportado pelo backend (ex.: 429/quota do
            // provedor). Em vez de exibir o JSON cru como se fosse a resposta
            // da IA, mostramos uma mensagem limpa e localizada (por código) e
            // marcamos isError para habilitar o retry. Encerra o loop sem
            // throw — o catch fica reservado a quedas de transporte.
            const friendly = streamErrorMessage(event.code);
            setMessages((prev) =>
              updateMessageInList(prev, activeId, (m) => ({
                ...m,
                content: friendly,
                isError: true,
                isThinking: false,
                thinkingDuration:
                  m.thinkingStartTime !== undefined
                    ? Date.now() - m.thinkingStartTime
                    : undefined,
              })),
            );
            break;
          }
        }
      } catch (err: unknown) {
        if ((err as { name?: string }).name === "AbortError") {
          // Interrompido pelo usuário — não é um erro; encerra o thinking timer
          setMessages((prev) =>
            updateMessageInList(prev, activeId, (m) => ({
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
          // Queda de transporte: preserva qualquer conteúdo parcial já
          // recebido; sem conteúdo, mostra mensagem genérica localizada e
          // marca isError (retry), nunca o texto cru da exceção.
          setMessages((prev) =>
            updateMessageInList(prev, activeId, (m) => ({
              ...m,
              content: assistantContent || streamErrorMessage(undefined),
              isError: !assistantContent,
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
        // Defesa em profundidade: garante que o spinner sempre encerra na bolha ativa
        setMessages((prev) =>
          updateMessageInList(prev, activeId, (m) =>
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
    [threadId, setMessages, agentConfig, shouldInterruptRef, onModelSwitched],
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
            setMessages((prev) =>
              updateMessageInList(prev, assistantMessageId, (m) => ({
                ...m,
                content:
                  (typeof m.content === "string" ? m.content : "") +
                  event.content,
              })),
            );
            await yieldToBrowser();
            continue;
          }

          await handleEvent(event, assistantMessageId, setMessages, threadId);

          if (event.type === "done") break;
          if (event.type === "error") {
            const friendly = streamErrorMessage(event.code);
            setMessages((prev) =>
              updateMessageInList(prev, assistantMessageId, (m) => ({
                ...m,
                content: friendly,
                isError: true,
                isThinking: false,
              })),
            );
            break;
          }
        }
      } catch (err: unknown) {
        if ((err as { name?: string }).name !== "AbortError") {
          // UX-15 — mesma distinção transporte vs. aplicação do processStream
          announceSSEDropped(err);
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || streamErrorMessage(undefined),
              isError: !assistantContent,
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

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { processStream, processResume, abort };
}

// ============================================================================
// Event handler
// ============================================================================

// handleEvent processa todos os eventos exceto "token"
// (tokens são aplicados via setMessages diretamente nos loops)
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

    // Streaming ao vivo da tool `terminal` — chega enquanto o comando ainda
    // roda (antes do tool_result). Só existe uma tool `terminal` ativa por
    // vez (backend/services/terminal_stream.py garante isso); anexa na
    // última tool call desse tipo que ainda não tem output.
    case "terminal_line": {
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => {
          const calls = m.toolCalls ?? [];
          const idx = calls.findLastIndex(
            (tc) =>
              tc.renderHint === "terminal_output" && tc.output === undefined,
          );
          if (idx === -1) return m;
          const updated = [...calls];
          updated[idx] = {
            ...updated[idx],
            liveOutputLines: [
              ...(updated[idx].liveOutputLines ?? []),
              event.line,
            ],
          };
          return { ...m, toolCalls: updated };
        }),
      );
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

    case "tool_activity": {
      if (event.elapsed_ms === null) {
        // Tool iniciou: mostrar na status line
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            activeTool: {
              name: event.tool_name,
              argsPreview: event.args_preview,
            },
          })),
        );
      } else {
        const elapsedMs = event.elapsed_ms;
        const tcId = event.tool_call_id;
        // Tool terminou: enriquecer ToolCall com elapsed + atualizar status line
        setMessages((prev) =>
          updateMessageInList(prev, assistantMessageId, (m) => ({
            ...m,
            activeTool: {
              name: event.tool_name,
              argsPreview: event.args_preview,
              elapsedMs,
            },
            // Enriquece o ToolCall correspondente com o elapsed_ms
            toolCalls: (m.toolCalls ?? []).map((tc) =>
              tc.id === tcId ? { ...tc, elapsedMs } : tc,
            ),
          })),
        );
        // Limpa o indicador após 800ms para o usuário ver o tempo
        setTimeout(() => {
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) =>
              m.activeTool?.name === event.tool_name
                ? { ...m, activeTool: null }
                : m,
            ),
          );
        }, 800);
      }
      break;
    }

    case "workbench_invalidate": {
      const ws = useWorkspacesStore.getState().getActive();
      if (ws) {
        const tabs = event.tabs as string[];
        if (tabs.includes("files"))
          useWorkbenchStore.getState().invalidateFiles(ws.id);
        if (tabs.includes("diff"))
          useWorkbenchStore.getState().invalidateDiff(ws.id);
        if (tabs.includes("plan") && threadId)
          useWorkbenchStore.getState().invalidatePlan(threadId);
        if (tabs.includes("tasks") || tabs.includes("files"))
          useWorkbenchStore.getState().markPending(ws.id);
      }
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
