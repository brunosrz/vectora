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

"use client"

import { useCallback, useRef } from "react"
import type { Message, ToolCall } from "../../types"
import {
  streamChat,
  resumeChat,
  type StreamEvent,
  type ChatConfig,
} from "../../api/vectora-client"
import {
  ensureMessageExists,
  updateMessageInList,
} from "../../utils/chat"
import type { AgentConfig } from "@/components/layout/agent-settings"

// ============================================================================
// Types
// ============================================================================

interface UseStreamHandlerProps {
  /** Não utilizado (mantido para compatibilidade com chat-interface.tsx) */
  client?: unknown
  threadId: string
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  agentConfig?: AgentConfig
  shouldInterruptRef?: React.MutableRefObject<boolean>
  /** Não utilizado (LangSmith removido) */
  userId?: string | null
  userEmail?: string | null
  userName?: string | null
}

interface UseStreamHandlerReturn {
  processStream: (
    userContent: string,
    assistantMessageId: string,
    images?: unknown[]
  ) => Promise<{ assistantContent: string; runId: string | undefined }>
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
  const abortRef = useRef<AbortController | null>(null)

  const processStream = useCallback(
    async (
      userContent: string,
      assistantMessageId: string,
      _images?: unknown[]
    ): Promise<{ assistantContent: string; runId: string | undefined }> => {
      // Cancela stream anterior se ainda em andamento
      abortRef.current?.abort()
      const abort = new AbortController()
      abortRef.current = abort

      // Garante que a mensagem do assistente existe no estado
      setMessages((prev) =>
        ensureMessageExists(prev, assistantMessageId, "assistant", "")
      )

      let assistantContent = ""
      let resolvedRunId: string | undefined

      // Monta config da request
      const config: ChatConfig = {}
      if (agentConfig?.model) config.model = agentConfig.model

      try {
        const events = streamChat(
          {
            thread_id: threadId,
            content: userContent,
            config,
          },
          abort.signal
        )

        for await (const event of events) {
          // Interrupção solicitada pelo usuário
          if (shouldInterruptRef?.current) {
            abort.abort()
            break
          }

          await handleEvent(event, assistantMessageId, setMessages, (text) => {
            assistantContent += text
          })

          if (event.type === "done") {
            resolvedRunId = event.run_id || undefined
            break
          }
          if (event.type === "error") {
            throw new Error(event.message || "Stream error")
          }
        }
      } catch (err: unknown) {
        if ((err as { name?: string }).name === "AbortError") {
          // Interrompido pelo usuário — não é um erro
        } else {
          const msg = err instanceof Error ? err.message : String(err)
          setMessages((prev) =>
            updateMessageInList(prev, assistantMessageId, (m) => ({
              ...m,
              content: assistantContent || `Erro no stream: ${msg}`,
            }))
          )
        }
      }

      return { assistantContent, runId: resolvedRunId }
    },
    [threadId, setMessages, agentConfig, shouldInterruptRef]
  )

  return { processStream }
}

// ============================================================================
// Event handler
// ============================================================================

async function handleEvent(
  event: StreamEvent,
  assistantMessageId: string,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  onToken: (text: string) => void
): Promise<void> {
  switch (event.type) {
    case "token": {
      onToken(event.content)
      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          content:
            (typeof m.content === "string" ? m.content : "") + event.content,
        }))
      )
      break
    }

    case "tool_call": {
      let args: Record<string, unknown> = {}
      try {
        args = JSON.parse(event.args_json)
      } catch {
        args = { _raw: event.args_json }
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
      }

      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          toolCalls: [...(m.toolCalls ?? []), toolCall],
        }))
      )
      break
    }

    case "tool_result": {
      let output: unknown
      try {
        output = JSON.parse(event.content_json)
      } catch {
        output = event.content_json
      }

      setMessages((prev) =>
        updateMessageInList(prev, assistantMessageId, (m) => ({
          ...m,
          toolCalls: (m.toolCalls ?? []).map((tc) =>
            tc.id === event.tool_call_id
              ? { ...tc, output, isError: event.is_error }
              : tc
          ),
        }))
      )
      break
    }

    // node / ui_metrics / hitl: atualmente apenas loggados
    case "node":
    case "ui_metrics":
    case "hitl":
      break

    default:
      break
  }
}
