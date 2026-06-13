/**
 * Message Types
 *
 * Type definitions for chat messages and related structures.
 */

import type { ToolCall } from "./tools";
import type { SubgraphOutput } from "./tools";
import type { UsageMetadata } from "./metadata";
import type { ImageAttachment } from "./images";

/**
 * Represents a chat message from either user or assistant.
 * Contains metadata for streaming, tool calls, feedback, and tracing.
 */
export interface Message {
  // Core properties
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;

  // Image attachments
  images?: ImageAttachment[];

  // Tool execution
  toolCalls?: ToolCall[];
  subgraphOutputs?: SubgraphOutput[];

  // Thinking/streaming state
  isThinking?: boolean;
  thinkingSteps?: string[];
  thinkingStartTime?: number;
  thinkingDuration?: number;

  // Bloco D — Reasoning Reveal
  /** Raciocínio do orchestrator (ThinkingEvent) */
  thinking?: {
    reason: string;
    action: string;
    delegate_to?: string | null;
    task_query?: string | null;
  };
  /** Label semântico do nó atualmente em execução (D2) */
  currentNodeLabel?: string;
  /** Durações por nó, acumuladas durante o stream (D3) */
  nodeDurations?: { node: string; label: string; duration_ms: number }[];

  // LangSmith tracing
  runId?: string;
  shareUrl?: string; // Public LangSmith trace share URL
  usageMetadata?: UsageMetadata;

  // User feedback
  feedback?: "positive" | "negative" | null;
  feedbackId?: string;
  feedbackComment?: string;

  // Interruption tracking
  wasInterrupted?: boolean;

  // M5 — Optimistic UI / error retry
  /** Mensagem é uma falha de stream — exibe botão de retry */
  isError?: boolean;

  // C.28 — RAG citations
  /** Fontes RAG retornadas durante a resposta, para renderizar referências [N]. */
  ragCitations?: Array<{ index: number; source: string; chunk: string }>;

  // Bloco E — HITL em Chat
  /** Preenchido quando o stream pausa para aprovação humana. */
  hitlPending?: {
    toolName: string;
    argsJson: string;
    interruptId: string;
    /** Razão para a ação (exibida no painel). */
    reasoning?: string;
    /** Preview diff unified para file_write/file_edit. */
    diffPreview?: string;
    /** Caminhos de arquivo afetados. */
    affectedPaths?: string[];
    /** Modo de permissão ativo (default/yolo/…). */
    permissionMode?: string;
  };
}
