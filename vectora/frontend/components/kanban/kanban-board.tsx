"use client";

/**
 * Board do 3º modo de interface (dev-only, ver `enableKanbanMode`).
 *
 * Cinco colunas fixas. `triage` e `archived` existem no modelo mas ficam
 * fora daqui: sete colunas viram ruído visual, e essas duas não são o
 * fluxo do dia a dia.
 *
 * Sem drag-and-drop nesta primeira leva. Arrastar um card tem efeito real
 * no agente — "Done → Ready" reabriria uma tarefa concluída — então as
 * ações ficam em botões explícitos, reaproveitando os endpoints que já
 * existem.
 */

import { useEffect, useState } from "react";

import { m } from "@/lib/paraglide/messages";

export interface KanbanTask {
  id: string;
  name: string;
  status: string;
  block_kind: string | null;
  block_reason: string | null;
  blocked_by?: string[];
}

const COLUNAS: { status: string; label: () => string }[] = [
  { status: "todo", label: () => m.kanban_column_todo() },
  { status: "ready", label: () => m.kanban_column_ready() },
  { status: "running", label: () => m.kanban_column_running() },
  { status: "blocked", label: () => m.kanban_column_blocked() },
  { status: "done", label: () => m.kanban_column_done() },
];

function TaskCard({ task }: { task: KanbanTask }) {
  return (
    <div className="rounded-md border bg-card px-2.5 py-2 space-y-1">
      <p className="text-xs font-medium leading-snug">{task.name}</p>
      {/* Dependência aparece como badge, não como linha desenhada: a v1 não
          precisa de grafo pra dizer "espera aquele outro". */}
      {task.blocked_by?.length ? (
        <p className="text-[10px] text-muted-foreground">
          {m.kanban_blocked_by()}: {task.blocked_by.join(", ")}
        </p>
      ) : null}
      {task.block_reason ? (
        <p className="text-[10px] text-amber-600 dark:text-amber-400">
          {task.block_reason}
        </p>
      ) : null}
    </div>
  );
}

export function KanbanBoard({ threadId }: { threadId: string }) {
  const [tasks, setTasks] = useState<KanbanTask[]>([]);

  useEffect(() => {
    let cancelado = false;
    void fetch(`/sessions/${threadId}/background/tasks`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : { tasks: [] }))
      .then((data) => {
        if (!cancelado) setTasks(data.tasks ?? []);
      })
      .catch(() => {
        // Board vazio é melhor que tela de erro — as tarefas seguem
        // rodando, só a visualização não carregou.
      });
    return () => {
      cancelado = true;
    };
  }, [threadId]);

  // `triage`/`archived` não têm coluna: mostrá-los junto encheria o board de
  // cards que não são o fluxo ativo.
  const visiveis = tasks.filter((t) =>
    COLUNAS.some((c) => c.status === t.status),
  );

  return (
    <div className="flex-1 min-h-0 overflow-x-auto p-4">
      {visiveis.length === 0 ? (
        <p className="text-xs text-muted-foreground">{m.kanban_empty()}</p>
      ) : (
        <div className="flex gap-3 min-w-max h-full">
          {COLUNAS.map((coluna) => {
            const daColuna = visiveis.filter((t) => t.status === coluna.status);
            return (
              <div
                key={coluna.status}
                className="w-60 shrink-0 flex flex-col gap-2"
                data-testid={`kanban-col-${coluna.status}`}
              >
                <div className="flex items-center justify-between px-1">
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    {coluna.label()}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {daColuna.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {daColuna.map((task) => (
                    <TaskCard key={task.id} task={task} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
