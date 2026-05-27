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

  // Bloco E — HITL em Chat
  /** Preenchido quando o stream pausa para aprovação humana. */
  hitlPending?: {
    toolName: string;
    argsJson: string;
    interruptId: string;
  };
}
