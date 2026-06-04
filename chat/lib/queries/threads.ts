/**
 * TanStack Query hooks para threads.
 *
 * Substitui o padrão useState+useEffect em use-threads.ts. Cache compartilhado
 * via QueryClient: todas as instâncias de useThreadsQuery() lêem o mesmo dado
 * sem fazer fetches duplicados. Invalidação propagada automaticamente após
 * create/delete/update.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from "@tanstack/react-query";
import {
  listThreads,
  createThread,
  deleteThread,
  updateThread,
  type Thread as VectoraThread,
} from "@/lib/api/vectora-client";
import type { Thread } from "@/lib/hooks/threads";
import { THREAD_FETCH_LIMIT } from "@/lib/constants/features";

// Chave estável para o cache — toda query de threads usa esta lista.
export const threadsQueryKey = ["threads"] as const;

// ---------------------------------------------------------------------------
// Conversão VectoraThread → Thread (formato do Sidebar)
// ---------------------------------------------------------------------------

function toSidebarThread(t: VectoraThread, userId: string): Thread {
  return {
    thread_id: t.id,
    created_at: t.created_at,
    updated_at: t.updated_at,
    metadata: { user_id: userId, title: t.title ?? "" },
  };
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/** Lista de threads do usuário, convertida para o formato do Sidebar. */
export function useThreadsQuery(
  userId: string | undefined,
): UseQueryResult<Thread[], Error> {
  return useQuery({
    queryKey: threadsQueryKey,
    queryFn: () => listThreads(THREAD_FETCH_LIMIT),
    select: (data) => data.threads.map((t) => toSidebarThread(t, userId ?? "")),
    enabled: !!userId,
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Cria uma nova thread e invalida o cache. */
export function useCreateThread(): UseMutationResult<
  VectoraThread,
  Error,
  void
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createThread,
    onSuccess: () => qc.invalidateQueries({ queryKey: threadsQueryKey }),
  });
}

/** Deleta uma thread com update otimista + rollback em erro. */
export function useDeleteThread(): UseMutationResult<
  Record<string, never>,
  Error,
  string
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteThread,
    onMutate: async (threadId) => {
      await qc.cancelQueries({ queryKey: threadsQueryKey });
      const prev = qc.getQueryData<{ threads: VectoraThread[] }>(
        threadsQueryKey,
      );
      qc.setQueryData<{ threads: VectoraThread[] }>(threadsQueryKey, (old) => ({
        threads: old?.threads.filter((t) => t.id !== threadId) ?? [],
      }));
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(threadsQueryKey, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: threadsQueryKey }),
  });
}

/** Atualiza título da thread com invalidação. */
export function useUpdateThread(): UseMutationResult<
  VectoraThread,
  Error,
  { id: string; updates: { title?: string } }
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, updates }) => updateThread(id, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: threadsQueryKey }),
  });
}
