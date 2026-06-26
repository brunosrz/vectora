/**
 * useOlderMessages — carrega mensagens antigas via IntersectionObserver (FASE 4.1).
 *
 * Observa um elemento sentinel no topo da lista. Quando fica visível e há
 * mensagens mais antigas (hasMore=true), faz fetch de 50 mensagens mais
 * antigas e chama onOlderLoaded com o resultado.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  HistoryMessage,
  PagedHistoryResponse,
} from "@/lib/api/vectora-client";
import { getHistoryPage } from "@/lib/api/vectora-client";

const PAGE_SIZE = 50;

export interface UseOlderMessagesResult {
  hasMore: boolean;
  isLoadingOlder: boolean;
  olderMessages: HistoryMessage[];
}

/**
 * @param threadId  ID da thread
 * @param sentinelRef  ref para o elemento sentinel no topo da lista
 * @param currentCount  número de mensagens atualmente carregadas (para calcular offset)
 * @param initialHasMore  se há mensagens mais antigas (do GetHistory inicial)
 */
export function useOlderMessages(
  threadId: string,
  sentinelRef: React.RefObject<Element | null>,
  currentCount: number,
  initialHasMore = false,
): UseOlderMessagesResult {
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [olderMessages, setOlderMessages] = useState<HistoryMessage[]>([]);
  const isLoadingRef = useRef(false);
  const offsetRef = useRef(0);

  // Sincroniza hasMore quando initialHasMore muda (ex.: após carregamento inicial)
  useEffect(() => {
    setHasMore(initialHasMore);
  }, [initialHasMore, threadId]);

  // Reset ao mudar de thread
  useEffect(() => {
    setHasMore(initialHasMore);
    setOlderMessages([]);
    offsetRef.current = 0;
  }, [threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadOlder = useCallback(async () => {
    if (!hasMore || isLoadingRef.current) return;

    isLoadingRef.current = true;
    setIsLoadingOlder(true);

    try {
      const offset = offsetRef.current + currentCount;
      const page: PagedHistoryResponse = await getHistoryPage(
        threadId,
        PAGE_SIZE,
        offset,
      );
      offsetRef.current += page.messages.length;
      setHasMore(page.has_more);
      setOlderMessages((prev) => [...page.messages, ...prev]);
    } catch {
      // falha silenciosa — usuário pode rolar de novo para tentar
    } finally {
      isLoadingRef.current = false;
      setIsLoadingOlder(false);
    }
  }, [threadId, hasMore, currentCount]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasMore) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          loadOlder();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [sentinelRef, hasMore, loadOlder]);

  return { hasMore, isLoadingOlder, olderMessages };
}
