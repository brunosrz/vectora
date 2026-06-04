import { createFileRoute, redirect } from "@tanstack/react-router";
import { queryClient } from "../router";
import { threadsQueryKey } from "@/lib/queries/threads";
import { listThreads, createThread } from "@/lib/api/vectora-client";

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

    // Nenhuma thread — cria uma nova e redireciona.
    const thread = await createThread();
    await queryClient.invalidateQueries({ queryKey: threadsQueryKey });
    throw redirect({
      to: "/session/$threadId",
      params: { threadId: thread.id },
    } as unknown as Parameters<typeof redirect>[0]);
  },
  component: () => (
    <main className="flex-1 flex items-center justify-center p-8">
      <div className="text-sm text-muted-foreground">Carregando...</div>
    </main>
  ),
});
