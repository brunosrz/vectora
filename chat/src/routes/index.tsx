import { createFileRoute, redirect } from "@tanstack/react-router";
import { queryClient } from "../router";
import { threadsQueryKey } from "@/lib/queries/threads";
import { listThreads } from "@/lib/api/vectora-client";
import { markAsNew } from "@/lib/stores/new-thread-registry";
import { safeRandomUUID } from "@/lib/utils/uuid";

export const Route = createFileRoute("/")({
  loader: async () => {
    // Prefetch da lista de threads para o beforeLoad abaixo.
    await queryClient.ensureQueryData({
      queryKey: threadsQueryKey,
      queryFn: () => listThreads(1),
      staleTime: 30_000,
    });
  },
  beforeLoad: async () => {
    const data = queryClient.getQueryData<{ threads: { id: string }[] }>(
      threadsQueryKey,
    );
    const threads = data?.threads ?? [];

    if (threads.length > 0) {
      throw redirect({
        to: "/session/$threadId",
        params: { threadId: threads[0].id },
      } as unknown as Parameters<typeof redirect>[0]);
    }

    // Nenhuma thread — gera um id local e redireciona, sem persistir no
    // backend ainda (só na primeira mensagem enviada, via StreamChat).
    const id = safeRandomUUID();
    markAsNew(id);
    throw redirect({
      to: "/session/$threadId",
      params: { threadId: id },
    } as unknown as Parameters<typeof redirect>[0]);
  },
  component: () => (
    <main className="flex-1 flex items-center justify-center p-8">
      <div className="text-sm text-muted-foreground">Carregando...</div>
    </main>
  ),
});
