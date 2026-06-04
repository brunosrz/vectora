import { createFileRoute } from "@tanstack/react-router";

/**
 * `/` — entrada do app. Por enquanto exibe uma tela mínima que confirma
 * que o Vite + TanStack Router estão funcionando.
 *
 * Quando os componentes de chat forem migrados, o `beforeLoad` aqui
 * redireciona para a última sessão ativa do usuário (via
 * `chat/lib/stores/threads-store`).
 */
export const Route = createFileRoute("/" as never)({
  component: IndexComponent,
});

function IndexComponent() {
  return (
    <main className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md text-center space-y-3">
        <h1 className="text-2xl font-semibold">Vectora</h1>
        <p className="text-sm text-muted-foreground">
          SPA Vite ativa. Os componentes do chat (ChatInterface, Workbench,
          Sidebar) ainda usam o entry-point antigo — esta página será
          substituída pelo chat completo quando as rotas forem portadas.
        </p>
        <p className="text-xs text-muted-foreground/60">
          Backend FastAPI em <code>/auth</code>, <code>/vectora.chat.v1/*</code>
          , <code>/license/status</code> etc.
        </p>
      </div>
    </main>
  );
}
