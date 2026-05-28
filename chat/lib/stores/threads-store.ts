/**
 * Threads Store — Zustand
 *
 * Cache client-side de mensagens por thread. Resolve o flash vazio que
 * acontecia ao trocar de conversa:
 *
 *   Antes:  click thread → messages = [] → fetch (~500ms) → render
 *   Depois: click thread → render cache instantâneo → revalidate em background
 *
 * Stale-while-revalidate: sempre exibe o cache se existir, e dispara um
 * fetch silencioso para atualizar. O componente nunca vê estado vazio se
 * a thread já foi visitada nesta sessão.
 *
 * Não persiste em localStorage — cache é por sessão de browser (intencional:
 * o backend é a source of truth, queremos invalidar ao recarregar a página).
 */

import { create } from "zustand";
import type { Message } from "@/lib/types";

interface ThreadCacheEntry {
  messages: Message[];
  /** Quando o cache foi populado a partir do backend. */
  fetchedAt: number;
  /** Quando o usuário interagiu pela última vez (envio/recebimento). */
  updatedAt: number;
}

interface ThreadsState {
  /** Cache de mensagens por threadId. */
  cache: Record<string, ThreadCacheEntry>;
  /** Threads cujo refetch em background está em andamento (para deduplicação). */
  revalidating: Record<string, boolean>;

  // ── Reads ────────────────────────────────────────────────────────────────
  /** Retorna o cache da thread (ou undefined se nunca foi vista). */
  getCached: (threadId: string) => ThreadCacheEntry | undefined;

  // ── Writes ───────────────────────────────────────────────────────────────
  /** Sobrescreve o cache de uma thread (após fetch do backend). */
  setMessages: (threadId: string, messages: Message[]) => void;

  /** Substitui as mensagens via updater function. Use em stream updates. */
  patchMessages: (threadId: string, updater: (current: Message[]) => Message[]) => void;

  /** Marca/desmarca revalidação em andamento. */
  setRevalidating: (threadId: string, value: boolean) => void;

  /** Remove uma thread do cache (após delete). */
  invalidate: (threadId: string) => void;

  /** Limpa todo o cache (logout, troca de usuário). */
  clear: () => void;
}

export const useThreadsStore = create<ThreadsState>((set, get) => ({
  cache: {},
  revalidating: {},

  getCached: (threadId) => get().cache[threadId],

  setMessages: (threadId, messages) => {
    const now = Date.now();
    set((state) => ({
      cache: {
        ...state.cache,
        [threadId]: {
          messages,
          fetchedAt: now,
          updatedAt: now,
        },
      },
    }));
  },

  patchMessages: (threadId, updater) => {
    set((state) => {
      const prev = state.cache[threadId];
      const prevMessages = prev?.messages ?? [];
      const next = updater(prevMessages);
      // Identidade preservada se updater retornar o mesmo array.
      if (next === prevMessages && prev) return state;
      const now = Date.now();
      return {
        cache: {
          ...state.cache,
          [threadId]: {
            messages: next,
            fetchedAt: prev?.fetchedAt ?? now,
            updatedAt: now,
          },
        },
      };
    });
  },

  setRevalidating: (threadId, value) => {
    set((state) => {
      if (state.revalidating[threadId] === value) return state;
      const nextRevalidating = { ...state.revalidating };
      if (value) nextRevalidating[threadId] = true;
      else delete nextRevalidating[threadId];
      return { revalidating: nextRevalidating };
    });
  },

  invalidate: (threadId) => {
    set((state) => {
      if (!(threadId in state.cache) && !(threadId in state.revalidating)) return state;
      const nextCache = { ...state.cache };
      const nextRevalidating = { ...state.revalidating };
      delete nextCache[threadId];
      delete nextRevalidating[threadId];
      return { cache: nextCache, revalidating: nextRevalidating };
    });
  },

  clear: () => set({ cache: {}, revalidating: {} }),
}));
