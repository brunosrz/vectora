/**
 * useWorkbenchSWR — stale-while-revalidate genérico para o workbench (T11.6).
 *
 * Padrão: o componente passa uma chave + fetcher + função "tem cache" + função
 * "stale". O hook dispara o fetcher imediatamente se não houver cache; caso
 * contrário, dispara silenciosamente em segundo plano se a entrada estiver
 * stale. O componente lê o cache do store normalmente.
 *
 * Igual ao threads-store: a verdade vive no backend; o cache é "best effort"
 * para renderização instantânea ao trocar de aba/sessão.
 */

import { useEffect, useRef } from "react";

interface SWROptions {
  /** Chave única — quando muda, dispara nova validação. */
  key: string;
  /** True se já existe cache renderizável. */
  hasCache: boolean;
  /** True se a entrada cacheada está obsoleta. */
  isStale: boolean;
  /** Função que faz o fetch e atualiza o store. */
  revalidate: () => Promise<void> | void;
  /** Pular o hook (ex.: workspace ausente). */
  skip?: boolean;
}

export function useWorkbenchSWR({
  key,
  hasCache,
  isStale,
  revalidate,
  skip = false,
}: SWROptions) {
  // Deduplicação de validações concorrentes para a mesma chave.
  const inFlight = useRef<Record<string, boolean>>({});

  useEffect(() => {
    if (skip) return;
    // Sem cache → fetch imediato. Com cache stale → refetch em background.
    if (hasCache && !isStale) return;
    if (inFlight.current[key]) return;
    inFlight.current[key] = true;
    Promise.resolve(revalidate()).finally(() => {
      inFlight.current[key] = false;
    });
    // Não incluímos `revalidate` nas deps — sua identidade muda a cada render
    // mesmo quando o que importa (a chave) é estável.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, hasCache, isStale, skip]);
}
