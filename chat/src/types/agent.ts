import { type Message } from "@langchain/langgraph-sdk";
import {
  type UIMessage,
  type RemoveUIMessage,
} from "@langchain/langgraph-sdk/react-ui";

/** ui_metrics — D1.5 State-Sync Observability */
export interface UIMetrics {
  last_node?: string;
  last_node_ms?: number;
  total_tokens_session?: number;
  rag_hits?: number;
  rag_misses?: number;
  tool_calls?: Record<string, number>;
  workspace_id?: string;
  manifest_version?: number;
}

/** StateType — Contrato de estado do LangGraph v2 */
export interface StateType {
  messages: Message[];
  ui?: UIMessage[];
  /** Métricas de observabilidade — atualizadas pelos nós do grafo */
  ui_metrics?: UIMetrics;
  [key: string]: unknown;
}

/** Configuração do Agent — parâmetros de conexão */
export interface AgentConfig {
  apiUrl: string;
  assistantId: string;
  apiKey?: string;
}

export interface StreamUpdateType {
  messages?: Message[] | Message | string;
  ui?: (UIMessage | RemoveUIMessage)[] | UIMessage | RemoveUIMessage;
  ui_metrics?: UIMetrics;
}

export type CustomEventType = UIMessage | RemoveUIMessage;

/** Tool Result Types — D1.1-D1.2 Discovery & Render Hints */

export interface SearchResult {
  content?: string;
  text?: string;
  page_content?: string;
  metadata?: {
    source?: string;
    collection?: string;
    workspace_id?: string;
    origin?: string;
    [key: string]: any;
  };
  score?: number;
  relevance_score?: number;
}

export interface WebSearchResult {
  url: string;
  title: string;
  content: string;
  raw_content?: string;
  score?: number;
}

export interface QueueProgress {
  status:
    | "fire_and_forget"
    | "processing"
    | "completed"
    | "error"
    | "quota_error"
    | "queued";
  queue_id?: string;
  id?: string;
  queue_ids?: string[];
  total?: number;
  count?: number;
  processed?: number;
  success_count?: number;
  message?: string;
  indexed?: number;
  failed?: number;
  collection?: string;
}

export interface WorkspaceDescribeResult {
  status: string;
  workspace_id?: string;
  name?: string;
  manifest?: string;
  summary?: string;
  content?: string;
  message?: string;
}

export interface CoderResult {
  status: "success" | "error";
  files_created?: string[];
  files_modified?: string[];
  commands_executed?: string[];
  diffs?: Record<string, string>;
  error?: string;
}

export interface ParallelResult {
  results: Record<string, any>;
  metadata?: Record<string, any>;
}
