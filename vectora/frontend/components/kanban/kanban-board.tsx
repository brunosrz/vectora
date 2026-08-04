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

import { useEffect, useRef, useState } from "react";

import { m } from "@/lib/paraglide/messages";

function NewTaskForm({
  threadId,
  onCreated,
}: {
  threadId: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [instruction, setInstruction] = useState("");

  const criar = () => {
    if (!name.trim() || !instruction.trim()) return;
    void fetch(`/sessions/${threadId}/background/tasks`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind: "routine",
        name: name.trim(),
        instruction: instruction.trim(),
        trigger_type: "manual",
      }),
    }).then(() => {
      setName("");
      setInstruction("");
      setOpen(false);
      onCreated();
    });
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-primary hover:underline mb-2"
      >
        {m.kanban_new_task()}
      </button>
    );
  }

  return (
    <div className="mb-3 max-w-sm rounded-md border bg-card p-3 space-y-2">
      <div>
        <label
          htmlFor="kanban-new-name"
          className="text-[10px] text-muted-foreground"
        >
          {m.kanban_task_name()}
        </label>
        <input
          id="kanban-new-name"
          aria-label={m.kanban_task_name()}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded border bg-background px-2 py-1 text-xs"
        />
      </div>
      <div>
        <label
          htmlFor="kanban-new-instruction"
          className="text-[10px] text-muted-foreground"
        >
          {m.kanban_task_instruction()}
        </label>
        <textarea
          id="kanban-new-instruction"
          aria-label={m.kanban_task_instruction()}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          className="w-full rounded border bg-background px-2 py-1 text-xs min-h-[60px]"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={criar}
          className="text-xs px-2 py-1 rounded bg-primary text-primary-foreground"
        >
          {m.kanban_create()}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="text-xs px-2 py-1 rounded text-muted-foreground hover:underline"
        >
          {m.kanban_action_cancel()}
        </button>
      </div>
    </div>
  );
}

//: Atualização em tempo real vem por push (SSE, ver `useKanbanSse` abaixo).
//: Este polling é só reconciliação de baixa frequência — cobre o evento
//: perdido numa reconexão de rede — não a via principal de atualização.
const POLL_INTERVAL_MS = 30000;

//: Canal SSE genérico de webhooks (`backend/api/handlers/webhooks.py`),
//: reaproveitado em vez de um endpoint dedicado ao Kanban — o provider
//: `"kanban"` no payload é o que distingue estes eventos dos demais.
const SSE_URL = "/webhook/events";
const SSE_RECONNECT_DELAY_MS = 3000;

export interface KanbanTask {
  id: string;
  name: string;
  status: string;
  block_kind: string | null;
  block_reason: string | null;
  blocked_by?: string[];
}

interface KanbanSseEventData {
  task_id: string;
  status: string;
  block_kind: string | null;
  block_reason: string | null;
}

interface WebhookSseEvent {
  type: string;
  provider: string;
  event_type: string;
  data: KanbanSseEventData;
}

const COLUNAS: { status: string; label: () => string }[] = [
  { status: "todo", label: () => m.kanban_column_todo() },
  { status: "ready", label: () => m.kanban_column_ready() },
  { status: "running", label: () => m.kanban_column_running() },
  { status: "blocked", label: () => m.kanban_column_blocked() },
  { status: "done", label: () => m.kanban_column_done() },
];

function TaskCard({
  task,
  threadId,
  onChanged,
}: {
  task: KanbanTask;
  threadId: string;
  onChanged: () => void;
}) {
  const base = `/sessions/${threadId}/background/tasks/${task.id}`;

  const desbloquear = () => {
    void fetch(`${base}/unblock`, {
      method: "POST",
      credentials: "include",
    }).then(onChanged);
  };
  const rodarAgora = () => {
    void fetch(`${base}/run`, { method: "POST", credentials: "include" }).then(
      onChanged,
    );
  };
  const cancelar = () => {
    void fetch(base, { method: "DELETE", credentials: "include" }).then(
      onChanged,
    );
  };

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
      <div className="flex gap-2 pt-0.5">
        {task.status === "ready" && (
          <button
            onClick={rodarAgora}
            className="text-[10px] text-primary hover:underline"
          >
            {m.kanban_action_run_now()}
          </button>
        )}
        {task.status === "blocked" && (
          <button
            onClick={desbloquear}
            className="text-[10px] text-primary hover:underline"
          >
            {m.kanban_action_unblock()}
          </button>
        )}
        {task.status !== "done" && (
          <button
            onClick={cancelar}
            className="text-[10px] text-muted-foreground hover:underline"
          >
            {m.kanban_action_cancel()}
          </button>
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({ threadId }: { threadId: string }) {
  const [tasks, setTasks] = useState<KanbanTask[]>([]);

  const carregar = () => {
    let cancelado = false;
    void fetch(`/sessions/${threadId}/background/tasks`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        // A resposta real é `list[TaskOut]` (array puro) — não um envelope
        // `{tasks: [...]}`. Um formato inesperado degrada pro board vazio
        // em vez de lançar.
        if (!cancelado) setTasks(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        // Board vazio é melhor que tela de erro — as tarefas seguem
        // rodando, só a visualização não carregou.
      });
    return () => {
      cancelado = true;
    };
  };

  useEffect(carregar, [threadId]);

  // Ref sempre com a versão mais recente de `carregar` — o interval abaixo
  // só precisa ser recriado quando `threadId` muda, não a cada render.
  const carregarRef = useRef(carregar);
  carregarRef.current = carregar;

  // Pausa o polling com a aba oculta — evita chamada de fundo desnecessária
  // quando o usuário está em outra aba/app. Agora é só reconciliação de
  // baixa frequência: a atualização principal chega via SSE abaixo.
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") carregarRef.current();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [threadId]);

  // Aplica um evento de mudança de status a um card específico, sem
  // refazer o fetch do board inteiro. Task ainda desconhecida localmente
  // (ex.: criada por outra sessão/processo) cai no fallback de `carregar`.
  const aplicarEventoSse = (data: KanbanSseEventData) => {
    // Checa contra o `tasks` do último render (via ref abaixo), não dentro
    // do updater funcional: `setTasks` não roda o updater de forma
    // síncrona, então ler o resultado logo depois de chamá-lo é uma corrida
    // — o card entra em `carregarRef.current()` mesmo quando já existe.
    if (!tasks.some((t) => t.id === data.task_id)) {
      carregarRef.current();
      return;
    }
    setTasks((atual) =>
      atual.map((t) =>
        t.id === data.task_id
          ? {
              ...t,
              status: data.status,
              block_kind: data.block_kind,
              block_reason: data.block_reason,
            }
          : t,
      ),
    );
  };
  const aplicarEventoSseRef = useRef(aplicarEventoSse);
  aplicarEventoSseRef.current = aplicarEventoSse;

  // Push via SSE reaproveitando o canal genérico de webhooks. Reconecta
  // manualmente em vez de confiar só no auto-retry do EventSource — dá
  // controle do delay e faz a reconexão ser determinística em teste.
  useEffect(() => {
    let cancelado = false;
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const conectar = () => {
      if (cancelado) return;
      es = new EventSource(SSE_URL);
      es.addEventListener("message", (ev: MessageEvent<string>) => {
        try {
          const parsed = JSON.parse(ev.data) as Partial<WebhookSseEvent>;
          if (parsed.provider !== "kanban" || !parsed.data?.task_id) return;
          aplicarEventoSseRef.current(parsed.data);
        } catch {
          // Evento malformado não pode derrubar a conexão — o polling de
          // reconciliação cobre o que se perder aqui.
        }
      });
      es.addEventListener("error", () => {
        es?.close();
        if (!cancelado)
          reconnectTimer = setTimeout(conectar, SSE_RECONNECT_DELAY_MS);
      });
    };
    conectar();

    return () => {
      cancelado = true;
      es?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [threadId]);

  // `triage`/`archived` não têm coluna: mostrá-los junto encheria o board de
  // cards que não são o fluxo ativo.
  const visiveis = tasks.filter((t) =>
    COLUNAS.some((c) => c.status === t.status),
  );

  return (
    <div className="flex-1 min-h-0 overflow-x-auto p-4">
      <NewTaskForm threadId={threadId} onCreated={carregar} />
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
                    <TaskCard
                      key={task.id}
                      task={task}
                      threadId={threadId}
                      onChanged={carregar}
                    />
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
