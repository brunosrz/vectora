/**
 * Thread Management Hook — Vectora
 *
 * Gerencia threads de conversa via REST API do Vectora (FastAPI).
 * Substitui a versão baseada no LangGraph SDK.
 *
 * Features:
 * - Auto-carrega threads na inicialização
 * - Operações CRUD (create, read, delete)
 * - Updates otimistas para UX instantânea
 */

"use client";

import { useState, useEffect } from "react";
import {
  listThreads,
  getThread as fetchThread,
  deleteThread as deleteThreadApi,
  updateThread as updateThreadApi,
  type Thread as VectoraThread,
} from "../../api/vectora-client";
import { logger } from "../../utils/logger";
import { THREAD_FETCH_LIMIT } from "../../constants/features";
import { useToastStore } from "@/lib/stores/toast-store";
// Alias — este módulo já usa `t` como nome de variável local para threads
// (ex.: `raw.map((t) => ...)`); evita colisão com a tradução fora de hooks.
import { withRetry } from "@/lib/utils/fetch-retry";
import { m } from "@/lib/paraglide/messages";

// ============================================================================
// Types
// ============================================================================

export interface ClientProfile {
  id: string;
  label?: string;
  avatarColor?: string;
}

export interface ThreadMetadata {
  user_id: string;
  title?: string;
  lastMessage?: string;
  client?: ClientProfile;
  [key: string]: unknown;
}

/** Thread no formato esperado pelos componentes (compatível com a API antiga). */
export interface Thread {
  thread_id: string;
  created_at: string;
  updated_at: string;
  metadata: ThreadMetadata;
  values?: Record<string, unknown>;
  /** Workspace físico associado à sessão (P3 — sidebar pasta=workspace). */
  workspace_id?: string;
  /** Modo da sessão: "chat" | "dev" (default "dev"). */
  mode?: string;
}

// ---------------------------------------------------------------------------
// Conversão VectoraThread → Thread (compatibilidade de interface)
// ---------------------------------------------------------------------------

function toThread(t: VectoraThread, userId: string): Thread {
  return {
    thread_id: t.id,
    created_at: t.created_at,
    updated_at: t.updated_at,
    metadata: { user_id: userId, title: t.title ?? "" },
    workspace_id: t.workspace_id,
    mode: t.mode ?? "dev",
  };
}

// ============================================================================
// Hook
// ============================================================================

export function useThreads(userId: string | undefined) {
  const [isLoading, setIsLoading] = useState(false);
  const [threads, setThreads] = useState<Thread[]>([]);

  // Auto-carrega threads quando userId estiver disponível
  useEffect(() => {
    if (typeof window === "undefined" || !userId) return;
    getUserThreads(userId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // --------------------------------------------------------------------------
  // Fetch
  // --------------------------------------------------------------------------

  const getUserThreads = async (id: string, silent = false): Promise<void> => {
    if (!silent) setIsLoading(true);
    try {
      // UX-17 — leitura idempotente: retenta em 5xx/queda de rede antes de
      // admitir falha (a sidebar ficaria vazia por uma instabilidade passageira).
      const { threads: raw } = await withRetry(() =>
        listThreads(THREAD_FETCH_LIMIT),
      );
      const mapped = raw.map((t) => toThread(t, id));
      setThreads(mapped);
    } catch (error) {
      logger.error("useThreads: erro ao buscar threads:", error);
      setThreads([]);
      // UX-7 — falha visível (sidebar ficaria vazia sem explicação alguma).
      useToastStore.getState().error(m.threads_error_list());
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  const getThreadById = async (id: string): Promise<Thread | null> => {
    try {
      const t = await fetchThread(id);
      return toThread(t, userId ?? "");
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      if (msg.includes("404")) {
        logger.debug(`useThreads: thread ${id} não encontrada (404)`);
        return null;
      }
      logger.error("useThreads: erro ao buscar thread:", error);
      return null;
    }
  };

  // --------------------------------------------------------------------------
  // Update metadata (otimista, sem persistência extra — título fica local)
  // --------------------------------------------------------------------------

  const updateThreadMetadata = async (
    threadId: string,
    metadata: Partial<ThreadMetadata>,
  ): Promise<void> => {
    // Update otimista imediato
    setThreads((prev) =>
      prev.map((t) =>
        t.thread_id === threadId
          ? {
              ...t,
              updated_at: new Date().toISOString(),
              metadata: { ...t.metadata, ...metadata },
            }
          : t,
      ),
    );
    // Persiste title no backend para sobreviver a restarts
    if (metadata.title !== undefined) {
      try {
        await updateThreadApi(threadId, { title: metadata.title });
      } catch (error) {
        logger.error("useThreads: erro ao persistir title da thread:", error);
        // UX-7 — o título mudou na UI (otimista) mas não foi salvo; o
        // usuário precisa saber que vai reverter no próximo reload.
        useToastStore.getState().error(m.threads_error_rename());
      }
    }
  };

  // --------------------------------------------------------------------------
  // Optimistic add
  // --------------------------------------------------------------------------

  const addOptimisticThread = (thread: Thread): void => {
    setThreads((prev) => {
      if (prev.some((t) => t.thread_id === thread.thread_id)) return prev;
      return [thread, ...prev];
    });
  };

  // --------------------------------------------------------------------------
  // Delete
  // --------------------------------------------------------------------------

  const deleteThread = async (
    id: string,
    onDeleteCurrent?: () => void,
  ): Promise<void> => {
    // Update otimista
    setThreads((prev) => prev.filter((t) => t.thread_id !== id));

    try {
      await deleteThreadApi(id);
      logger.info("useThreads: thread deletada:", id);
      onDeleteCurrent?.();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      if (msg.includes("404")) return; // Já deletada
      logger.error("useThreads: erro ao deletar thread:", error);
      // UX-7 — sem isso o item simplesmente reaparece e o usuário não
      // entende por quê.
      useToastStore.getState().error(m.threads_error_delete());
      // Reverte update otimista
      if (userId) await getUserThreads(userId);
    }
  };

  // --------------------------------------------------------------------------
  // Return
  // --------------------------------------------------------------------------

  return {
    isLoading,
    threads,
    getThreadById,
    setThreads,
    getUserThreads,
    updateThreadMetadata,
    deleteThread,
    addOptimisticThread,
  };
}
