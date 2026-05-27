/**
 * Vectora API Client
 *
 * Cliente que conecta ao backend FastAPI do Vectora.
 * Substitui o LangGraph SDK — usa fetch nativo para SSE e REST.
 *
 * Endpoints base: NEXT_PUBLIC_VECTORA_API_URL (default: http://localhost:8080)
 */

import { VECTORA_API_URL } from "@/lib/constants/api";

// ============================================================================
// Types — espelham os schemas do vectora/api/schemas.py
// ============================================================================

export interface ChatConfig {
  model?: string;
  llm_provider?: string;
  recursion_limit?: number;
  workspace_id?: string;
}

/** Tipo semântico do attachment — espelha AttachmentKind do backend. */
export type AttachmentKind = "image" | "pdf" | "code" | "text";

/**
 * Arquivo anexado a uma mensagem.
 * ``base64_data`` é o conteúdo puro em base64, sem prefixo data URL.
 */
export interface Attachment {
  kind: AttachmentKind;
  name: string;
  mime_type: string;
  base64_data: string;
}

export interface StreamChatRequest {
  thread_id?: string;
  content: string;
  config?: ChatConfig;
  /** Arquivos anexados à mensagem (F1 — multimodal). */
  attachments?: Attachment[];
}

export interface ResumeChatRequest {
  thread_id: string;
  interrupt_id: string;
  decision: "approve" | "reject" | `edit:${string}`;
}

/** Evento discriminado pelo campo `type` */
export type StreamEvent =
  | { type: "thread"; thread_id: string }
  | { type: "token"; content: string; node?: string }
  | {
      type: "tool_call";
      tool_name: string;
      tool_call_id: string;
      args_json: string;
      render_hint?: string;
      category?: string;
      destructive?: boolean;
      icon?: string;
    }
  | {
      type: "tool_result";
      tool_call_id: string;
      content_json: string;
      is_error?: boolean;
    }
  | {
      type: "thinking";
      reason: string;
      action: string;
      delegate_to?: string | null;
      task_query?: string | null;
    }
  | {
      type: "node";
      node: string;
      status: "started" | "finished";
      duration_ms?: number;
      node_label?: string;
    }
  | {
      type: "ui_metrics";
      last_node?: string;
      last_node_ms?: number;
      rag_hits?: number;
      rag_misses?: number;
      tool_calls?: Record<string, number>;
    }
  | { type: "hitl"; tool_name: string; args_json: string; interrupt_id: string }
  | { type: "error"; message: string; code?: string }
  | { type: "done"; thread_id: string; run_id?: string };

export interface Thread {
  id: string;
  created_at: string;
  updated_at: string;
  title?: string;
}

export interface HistoryMessage {
  role: "human" | "assistant";
  content: string;
  created_at?: string;
}

// ============================================================================
// Token refresh automático
// ============================================================================

/**
 * Tenta renovar o access token via /api/auth/refresh (proxy Hono).
 *
 * Chamado automaticamente quando qualquer endpoint retorna 401.
 * O proxy Hono repassa os cookies corretamente, garantindo que o
 * refresh token seja enviado ao backend e que os novos cookies sejam
 * definidos no browser antes de retornar.
 *
 * @returns true se o refresh foi bem-sucedido
 */
async function _tryRefreshToken(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Redireciona para login quando o refresh falha.
 * No-op em SSR (sem window).
 */
function _redirectToLogin(): void {
  if (typeof window !== "undefined") {
    window.location.href = "/auth/signin";
  }
}

// ============================================================================
// Chat streaming
// ============================================================================

/**
 * Inicia ou continua um chat via SSE streaming.
 *
 * Se o backend retornar 401 (token expirado), renova o access token
 * automaticamente via /api/auth/refresh e retenta uma vez antes de
 * redirecionar para /auth/signin.
 *
 * @yields StreamEvent — eventos tipados (token, tool_call, done, etc.)
 */
export async function* streamChat(
  request: StreamChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const url = `${VECTORA_API_URL}/vectora.chat.v1.ChatService/StreamChat`;

  const doFetch = () =>
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
      signal,
    });

  let response = await doFetch();

  // Refresh automático quando o access token expira (TTL: 15 min)
  if (response.status === 401) {
    const refreshed = await _tryRefreshToken();
    if (!refreshed) {
      _redirectToLogin();
      throw new Error("StreamChat: sessão expirada. Faça login novamente.");
    }
    response = await doFetch();
  }

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");
    throw new Error(`StreamChat failed (${response.status}): ${text}`);
  }

  yield* _readSSEStream(response.body);
}

/**
 * Retoma uma execução pausada (HITL).
 */
export async function* resumeChat(
  request: ResumeChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const url = `${VECTORA_API_URL}/vectora.chat.v1.ChatService/ResumeChat`;

  const doFetch = () =>
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
      signal,
    });

  let response = await doFetch();

  if (response.status === 401) {
    const refreshed = await _tryRefreshToken();
    if (!refreshed) {
      _redirectToLogin();
      throw new Error("ResumeChat: sessão expirada. Faça login novamente.");
    }
    response = await doFetch();
  }

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");
    throw new Error(`ResumeChat failed (${response.status}): ${text}`);
  }

  yield* _readSSEStream(response.body);
}

// ============================================================================
// Thread management
// ============================================================================

async function _post<T>(
  path: string,
  body: object,
  isRetry = false,
): Promise<T> {
  const response = await fetch(`${VECTORA_API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (response.status === 401 && !isRetry) {
    const refreshed = await _tryRefreshToken();
    if (refreshed) return _post(path, body, true);
    _redirectToLogin();
    throw new Error(`${path}: sessão expirada. Faça login novamente.`);
  }
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`${path} failed (${response.status}): ${text}`);
  }
  return response.json();
}

export const createThread = (): Promise<Thread> =>
  _post("/vectora.chat.v1.ThreadService/CreateThread", {});

export const getThread = (thread_id: string): Promise<Thread> =>
  _post("/vectora.chat.v1.ThreadService/GetThread", { thread_id });

export const listThreads = (limit = 50): Promise<{ threads: Thread[] }> =>
  _post("/vectora.chat.v1.ThreadService/ListThreads", { limit });

export const deleteThread = (thread_id: string): Promise<{}> =>
  _post("/vectora.chat.v1.ThreadService/DeleteThread", { thread_id });

export const updateThread = (
  thread_id: string,
  updates: { title?: string },
): Promise<Thread> =>
  _post("/vectora.chat.v1.ThreadService/UpdateThread", {
    thread_id,
    title: updates.title ?? "",
  });

export const getHistory = (
  thread_id: string,
): Promise<{ messages: HistoryMessage[] }> =>
  _post("/vectora.chat.v1.ThreadService/GetHistory", { thread_id });

// ============================================================================
// SSE parser interno
// ============================================================================

async function* _readSSEStream(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<StreamEvent> {
  const decoder = new TextDecoder();
  const reader = body.getReader();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Processar linhas completas
      const lines = buffer.split("\n");
      // A última linha pode estar incompleta — guardar no buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const json = line.slice(6).trim();
        if (!json || json === "[DONE]") continue;

        try {
          const event: StreamEvent = JSON.parse(json);
          yield event;
          if (event.type === "done" || event.type === "error") return;
        } catch {
          // Linha malformada — ignorar
          console.warn("[vectora-client] SSE parse error:", json);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
