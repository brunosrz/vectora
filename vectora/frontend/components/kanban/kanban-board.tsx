"use client";

/**
 * Board do 3º modo de interface — feature pública (promovida da flag
 * dev-only `enableKanbanMode` na Sprint 7 do plano 0.1.11).
 *
 * Cinco colunas fixas, sempre visíveis (mesmo com 0 tasks — colunas vazias
 * não são bug, são o estado normal de um board recém-criado). `triage` fica
 * fora das colunas principais (dropzone própria, ver `TriageDropzone`);
 * `archived` só aparece quando o filtro "mostrar arquivadas" está ativo.
 *
 * Drag-and-drop só nas transições seguras (`DRAG_TRANSITIONS`), reaproveitando
 * os mesmos endpoints dos botões explícitos — nunca uma chamada nova. `*→running`
 * (exclusivo do claim atômico do scheduler) e `*→done` (só a run terminando de
 * verdade decide) nunca disparam chamada nenhuma: o board os recusa antes de
 * qualquer fetch, e o backend (`kanban.manual_transition`) recusaria de novo se
 * o frontend tentasse.
 */

import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  useDraggable,
  useDroppable,
  type DragEndEvent,
} from "@dnd-kit/core";

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
  //: "tenant" do card — já existia no backend (`workspace_id`), só não
  //: chegava até aqui.
  workspace_id?: string | null;
  //: "assignee" do card — perfil de agente atribuído.
  agent_profile_id?: string | null;
  //: "low" | "normal" | "high" | "urgent" — sinal visual, não afeta ordem
  //: real de claim.
  priority?: string;
}

const PRIORITY_CLASS: Record<string, string> = {
  low: "text-muted-foreground",
  normal: "text-muted-foreground",
  high: "text-amber-600 dark:text-amber-400",
  urgent: "text-destructive",
};

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

//: Pares acionáveis por drag-and-drop — espelha
//: `backend/scheduling/kanban.py::MANUAL_TRANSITIONS`. `running` e `done`
//: nunca aparecem como alvo: são exclusivos do claim atômico do scheduler e
//: da run terminando de verdade, respectivamente. O backend recusa de novo
//: se este mapa algum dia divergir — esta cópia é só pra recusar o drop
//: antes de qualquer chamada de rede.
const DRAG_TRANSITIONS: Record<string, string[]> = {
  todo: ["ready", "triage"],
  ready: ["triage"],
  blocked: ["ready"],
};

function isDragAllowed(from: string, to: string): boolean {
  return (DRAG_TRANSITIONS[from] ?? []).includes(to);
}

async function patchStatus(
  threadId: string,
  taskId: string,
  status: string,
): Promise<void> {
  await fetch(`/sessions/${threadId}/background/tasks/${taskId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

async function unblockTaskRequest(
  threadId: string,
  taskId: string,
): Promise<void> {
  await fetch(`/sessions/${threadId}/background/tasks/${taskId}/unblock`, {
    method: "POST",
    credentials: "include",
  });
}

async function bulkArchive(threadId: string, taskIds: string[]): Promise<void> {
  await fetch(`/sessions/${threadId}/background/tasks/bulk`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_ids: taskIds, action: "archive" }),
  });
}

/** Aplica (ou recusa) uma transição de drag-and-drop. `false` sem chamada de
 * rede nenhuma quando o par não está em `DRAG_TRANSITIONS` — o card volta
 * pro lugar porque o estado local nunca mudou. `blocked→ready` reaproveita o
 * mesmo endpoint do botão "Desbloquear"; os demais pares usam `PATCH` de
 * status, mesma rota que valida a transição em `kanban.manual_transition`. */
export async function applyDragTransition(
  threadId: string,
  task: KanbanTask,
  targetStatus: string,
): Promise<boolean> {
  if (targetStatus === task.status) return false;
  if (!isDragAllowed(task.status, targetStatus)) return false;
  if (task.status === "blocked" && targetStatus === "ready") {
    await unblockTaskRequest(threadId, task.id);
  } else {
    await patchStatus(threadId, task.id, targetStatus);
  }
  return true;
}

function TaskCard({
  task,
  threadId,
  selected,
  onToggleSelect,
  onChanged,
}: {
  task: KanbanTask;
  threadId: string;
  selected: boolean;
  onToggleSelect: (shiftKey: boolean) => void;
  onChanged: () => void;
}) {
  const base = `/sessions/${threadId}/background/tasks/${task.id}`;
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: task.id });

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

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: isDragging ? 10 : undefined,
      }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="rounded-md border bg-card px-2.5 py-2 space-y-1"
    >
      <div className="flex items-start gap-1.5">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => {}}
          onClick={(e) => {
            e.preventDefault();
            onToggleSelect(e.shiftKey);
          }}
          aria-label={m.kanban_select_task()}
          className="mt-0.5 shrink-0"
        />
        <p
          className="text-xs font-medium leading-snug flex-1 cursor-grab active:cursor-grabbing"
          {...attributes}
          {...listeners}
        >
          {task.name}
        </p>
      </div>
      {(task.priority && task.priority !== "normal") ||
      task.workspace_id ||
      task.agent_profile_id ? (
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px]">
          {task.priority && task.priority !== "normal" && (
            <span
              className={`font-medium uppercase ${PRIORITY_CLASS[task.priority] ?? "text-muted-foreground"}`}
            >
              {task.priority}
            </span>
          )}
          {task.workspace_id && (
            <span className="text-muted-foreground/70">
              {m.kanban_tenant_label({ id: task.workspace_id })}
            </span>
          )}
          {task.agent_profile_id && (
            <span className="text-muted-foreground/70">
              {m.kanban_assignee_label({ id: task.agent_profile_id })}
            </span>
          )}
        </div>
      ) : null}
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

function Column({
  status,
  label,
  count,
  children,
}: {
  status: string;
  label: string;
  count: number;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div
      ref={setNodeRef}
      className={`w-60 shrink-0 flex flex-col gap-2 rounded-md ${
        isOver ? "bg-accent/40" : ""
      }`}
      data-testid={`kanban-col-${status}`}
    >
      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <span className="text-[10px] text-muted-foreground">{count}</span>
      </div>
      <div className="space-y-2">
        {count === 0 ? (
          <p className="px-1 text-[10px] text-muted-foreground/60">
            {m.kanban_column_empty()}
          </p>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

//: Alvo de drop pra "esconder/adiar" (`todo`/`ready` → `triage`) — não é uma
//: coluna do board (triage não faz parte do fluxo ativo, ver comentário no
//: topo do arquivo), só uma faixa fina que aceita o drop.
function TriageDropzone() {
  const { setNodeRef, isOver } = useDroppable({ id: "triage" });

  return (
    <div
      ref={setNodeRef}
      className={`mb-2 rounded-md border border-dashed px-2 py-1.5 text-[10px] text-muted-foreground ${
        isOver ? "bg-accent/40 border-primary" : ""
      }`}
    >
      {m.kanban_triage_dropzone()}
    </div>
  );
}

export function KanbanBoard({ threadId }: { threadId: string }) {
  const [tasks, setTasks] = useState<KanbanTask[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [lastSelectedId, setLastSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tenantFilter, setTenantFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [showArchived, setShowArchived] = useState(false);

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

  // `triage` nunca tem coluna (dropzone própria); `archived` só entra
  // quando o filtro "mostrar arquivadas" está ativo.
  const colunasAtivas = showArchived
    ? [
        ...COLUNAS,
        { status: "archived", label: () => m.kanban_column_archived() },
      ]
    : COLUNAS;

  const tenants = Array.from(
    new Set(tasks.map((t) => t.workspace_id).filter((v): v is string => !!v)),
  ).toSorted();
  const assignees = Array.from(
    new Set(
      tasks.map((t) => t.agent_profile_id).filter((v): v is string => !!v),
    ),
  ).toSorted();

  const buscaLower = search.trim().toLowerCase();
  const visiveis = tasks.filter((t) => {
    if (!colunasAtivas.some((c) => c.status === t.status)) return false;
    if (buscaLower && !t.name.toLowerCase().includes(buscaLower)) return false;
    if (tenantFilter && t.workspace_id !== tenantFilter) return false;
    if (assigneeFilter && t.agent_profile_id !== assigneeFilter) return false;
    return true;
  });

  const toggleSelect = (taskId: string, shiftKey: boolean) => {
    setSelected((atual) => {
      const next = new Set(atual);
      if (shiftKey && lastSelectedId) {
        // Range simples na ordem em que os cards visíveis aparecem — não
        // precisa respeitar coluna, só a ordem visual do board.
        const ids = visiveis.map((t) => t.id);
        const de = ids.indexOf(lastSelectedId);
        const ate = ids.indexOf(taskId);
        if (de !== -1 && ate !== -1) {
          const [ini, fim] = de < ate ? [de, ate] : [ate, de];
          for (const id of ids.slice(ini, fim + 1)) next.add(id);
        } else {
          next.add(taskId);
        }
      } else if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
    setLastSelectedId(taskId);
  };

  const arquivarSelecionadas = () => {
    const ids = Array.from(selected);
    void bulkArchive(threadId, ids).then(() => {
      setSelected(new Set());
      carregar();
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const task = tasks.find((t) => t.id === active.id);
    if (!task) return;
    const targetStatus = String(over.id);
    void applyDragTransition(threadId, task, targetStatus).then((aplicado) => {
      if (aplicado) carregar();
    });
  };

  return (
    <div className="flex-1 min-h-0 overflow-x-auto p-4">
      <NewTaskForm threadId={threadId} onCreated={carregar} />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={m.kanban_filter_search_placeholder()}
          aria-label={m.kanban_filter_search_label()}
          className="w-40 rounded border bg-background px-2 py-1 text-xs"
        />
        {tenants.length > 0 && (
          <select
            value={tenantFilter}
            onChange={(e) => setTenantFilter(e.target.value)}
            aria-label={m.kanban_filter_tenant_all()}
            className="rounded border bg-background px-2 py-1 text-xs"
          >
            <option value="">{m.kanban_filter_tenant_all()}</option>
            {tenants.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        )}
        {assignees.length > 0 && (
          <select
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            aria-label={m.kanban_filter_assignee_all()}
            className="rounded border bg-background px-2 py-1 text-xs"
          >
            <option value="">{m.kanban_filter_assignee_all()}</option>
            {assignees.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        )}
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />
          {m.kanban_filter_show_archived()}
        </label>
      </div>
      {selected.size > 0 && (
        <div className="mb-3 flex items-center gap-3 rounded-md border bg-card px-3 py-1.5">
          <span className="text-xs">
            {m.kanban_selection_count({ n: selected.size })}
          </span>
          <button
            onClick={arquivarSelecionadas}
            className="text-xs text-primary hover:underline"
          >
            {m.kanban_action_archive()}
          </button>
        </div>
      )}
      {tasks.length === 0 && (
        <p className="mb-2 text-xs text-muted-foreground">{m.kanban_empty()}</p>
      )}
      <DndContext onDragEnd={handleDragEnd}>
        <TriageDropzone />
        <div className="flex gap-3 min-w-max h-full">
          {colunasAtivas.map((coluna) => {
            const daColuna = visiveis.filter((t) => t.status === coluna.status);
            return (
              <Column
                key={coluna.status}
                status={coluna.status}
                label={coluna.label()}
                count={daColuna.length}
              >
                {daColuna.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    threadId={threadId}
                    selected={selected.has(task.id)}
                    onToggleSelect={(shiftKey) =>
                      toggleSelect(task.id, shiftKey)
                    }
                    onChanged={carregar}
                  />
                ))}
              </Column>
            );
          })}
        </div>
      </DndContext>
    </div>
  );
}
