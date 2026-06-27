"use client";

/**
 * Workbench "Segundo Plano" — rotina/heartbreak/webhook da session atual.
 *
 * Lista as tarefas em segundo plano da session (toggle, rodar agora, remover),
 * um formulário de criação e o log de execuções com link para a thread-resultado.
 * Atualiza ao vivo via SSE de webhooks (eventos `background_run.*`).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Loader2, Plus, Play, Trash2, ExternalLink } from "lucide-react";

import {
  useBackgroundTasks,
  type BackgroundKind,
  type CreateTaskInput,
  type TriggerType,
} from "@/lib/hooks/use-background-tasks";
import { useWebhookEvents } from "@/lib/hooks/use-webhook-events";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { Switch } from "@/components/ui/switch";
import { m } from "@/lib/paraglide/messages";

interface DraftState {
  kind: BackgroundKind;
  name: string;
  instruction: string;
  trigger_type: TriggerType;
  cron_expr: string;
  provider: string;
  events: string;
}

const EMPTY_DRAFT: DraftState = {
  kind: "routine",
  name: "",
  instruction: "",
  trigger_type: "interval",
  cron_expr: "0 9 * * *",
  provider: "github",
  events: "push",
};

function statusLabel(status: string): string {
  if (status === "done") return m.background_status_done();
  if (status === "error") return m.background_status_error();
  return m.background_status_running();
}

export function BackgroundTab({ threadId }: { threadId: string }) {
  const navigate = useNavigate();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const {
    tasks,
    runs,
    loading,
    refetch,
    createTask,
    toggleTask,
    deleteTask,
    runTask,
  } = useBackgroundTasks(threadId);

  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [submitting, setSubmitting] = useState(false);

  // Revalida ao receber um evento de run em segundo plano via SSE.
  const onWebhook = useCallback(
    (evt: { provider: string }) => {
      if (evt.provider === "background") void refetch();
    },
    [refetch],
  );
  useWebhookEvents(onWebhook);

  const handleCreate = async () => {
    if (!draft.name.trim() || !draft.instruction.trim()) return;
    setSubmitting(true);
    try {
      const trigger_config: Record<string, unknown> =
        draft.trigger_type === "interval"
          ? { cron_expr: draft.cron_expr.trim() }
          : draft.trigger_type === "webhook"
            ? {
                provider: draft.provider.trim(),
                events: draft.events
                  .split(",")
                  .map((e) => e.trim())
                  .filter(Boolean),
              }
            : {};
      const input: CreateTaskInput = {
        kind: draft.kind,
        name: draft.name.trim(),
        instruction: draft.instruction.trim(),
        trigger_type: draft.trigger_type,
        trigger_config,
        workspace_id: workspace?.id ?? null,
      };
      const ok = await createTask(input);
      if (ok) {
        setDraft(EMPTY_DRAFT);
        setShowForm(false);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const runsByTask = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of runs) map.set(r.task_id, (map.get(r.task_id) ?? 0) + 1);
    return map;
  }, [runs]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-3 space-y-4 text-xs">
      <div className="flex justify-start">
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          data-testid="background-new-task"
        >
          <Plus className="w-3 h-3" />
          {m.background_new_task()}
        </button>
      </div>

      {showForm && (
        <div className="border border-border/60 rounded-md p-2 space-y-2">
          <div className="flex gap-2">
            <select
              value={draft.kind}
              onChange={(e) =>
                setDraft({ ...draft, kind: e.target.value as BackgroundKind })
              }
              className="flex-1 bg-background border border-border/60 rounded px-1 py-1"
              aria-label={m.background_kind()}
            >
              <option value="routine">{m.background_kind_routine()}</option>
              <option value="heartbreak">
                {m.background_kind_heartbreak()}
              </option>
            </select>
            <select
              value={draft.trigger_type}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  trigger_type: e.target.value as TriggerType,
                })
              }
              className="flex-1 bg-background border border-border/60 rounded px-1 py-1"
              aria-label={m.background_trigger()}
            >
              <option value="interval">
                {m.background_trigger_interval()}
              </option>
              <option value="webhook">{m.background_trigger_webhook()}</option>
              <option value="manual">{m.background_trigger_manual()}</option>
            </select>
          </div>
          <input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder={m.background_field_name()}
            className="w-full bg-background border border-border/60 rounded px-2 py-1"
          />
          <textarea
            value={draft.instruction}
            onChange={(e) =>
              setDraft({ ...draft, instruction: e.target.value })
            }
            placeholder={m.background_field_instruction()}
            rows={2}
            className="w-full bg-background border border-border/60 rounded px-2 py-1 resize-none"
          />
          {draft.trigger_type === "interval" && (
            <input
              value={draft.cron_expr}
              onChange={(e) =>
                setDraft({ ...draft, cron_expr: e.target.value })
              }
              placeholder={m.background_field_cron()}
              className="w-full bg-background border border-border/60 rounded px-2 py-1 font-mono"
            />
          )}
          {draft.trigger_type === "webhook" && (
            <div className="flex gap-2">
              <input
                value={draft.provider}
                onChange={(e) =>
                  setDraft({ ...draft, provider: e.target.value })
                }
                placeholder={m.background_field_provider()}
                className="flex-1 bg-background border border-border/60 rounded px-2 py-1"
              />
              <input
                value={draft.events}
                onChange={(e) => setDraft({ ...draft, events: e.target.value })}
                placeholder={m.background_field_events()}
                className="flex-1 bg-background border border-border/60 rounded px-2 py-1"
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowForm(false)}
              className="px-2 py-1 rounded text-muted-foreground hover:bg-muted/50"
            >
              {m.background_cancel()}
            </button>
            <button
              onClick={() => void handleCreate()}
              disabled={submitting}
              className="px-2 py-1 rounded bg-primary text-primary-foreground disabled:opacity-50"
              data-testid="background-create"
            >
              {submitting ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                m.background_create()
              )}
            </button>
          </div>
        </div>
      )}

      {tasks.length === 0 ? (
        <p className="text-muted-foreground">{m.background_empty()}</p>
      ) : (
        <ul className="space-y-2" data-testid="background-task-list">
          {tasks.map((t) => (
            <li
              key={t.id}
              className="border border-border/60 rounded-md p-2 space-y-1"
              data-testid="background-task-item"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium truncate">{t.name}</span>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => void runTask(t.id)}
                    title={m.background_run_now()}
                    className="p-1 text-muted-foreground hover:text-foreground"
                    data-testid="background-run-now"
                  >
                    <Play className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => void deleteTask(t.id)}
                    title={m.background_delete()}
                    className="p-1 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                  <Switch
                    checked={t.enabled}
                    onCheckedChange={(v) => void toggleTask(t.id, v)}
                    aria-label={
                      t.enabled ? m.background_active() : m.background_paused()
                    }
                  />
                </div>
              </div>
              <p className="text-muted-foreground truncate">{t.instruction}</p>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                <span className="px-1 rounded bg-muted/60">
                  {t.kind === "routine"
                    ? m.background_kind_routine()
                    : m.background_kind_heartbreak()}
                </span>
                <span className="px-1 rounded bg-muted/60">
                  {t.trigger_type === "interval"
                    ? m.background_trigger_interval()
                    : t.trigger_type === "webhook"
                      ? m.background_trigger_webhook()
                      : m.background_trigger_manual()}
                </span>
                <span>
                  {m.background_last_run()}:{" "}
                  {t.last_run_at ?? m.background_never()}
                </span>
                {runsByTask.has(t.id) && <span>· {runsByTask.get(t.id)}×</span>}
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-2">
        <span className="font-medium">{m.background_runs_title()}</span>
        {runs.length === 0 ? (
          <p className="text-muted-foreground">{m.background_no_runs()}</p>
        ) : (
          <ul className="space-y-1" data-testid="background-run-list">
            {runs.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between gap-2 border border-border/40 rounded px-2 py-1"
              >
                <div className="min-w-0">
                  <span
                    className={
                      r.status === "error"
                        ? "text-destructive"
                        : r.status === "done"
                          ? "text-emerald-500"
                          : "text-amber-500"
                    }
                  >
                    {statusLabel(r.status)}
                  </span>
                  <span className="text-muted-foreground ml-2 truncate">
                    {r.summary ?? ""}
                  </span>
                </div>
                {r.run_thread_id && (
                  <button
                    onClick={() =>
                      void navigate({
                        to: "/session/$threadId",
                        params: { threadId: r.run_thread_id as string },
                      })
                    }
                    title={m.background_open_thread()}
                    className="p-1 text-muted-foreground hover:text-foreground shrink-0"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
