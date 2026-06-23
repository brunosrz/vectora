"use client";

/**
 * Hook das tarefas em segundo plano de uma session (rotina/heartbreak/webhook).
 *
 * CRUD + histórico de execuções, scoped por `threadId`. O backend é a fonte de
 * verdade (CLAUDE.md §8): toda mutação refaz o fetch. Atualizações ao vivo das
 * runs chegam via SSE de webhooks (`use-webhook-events`), tratadas pelo painel.
 */

import { useCallback, useEffect, useState } from "react";

export type BackgroundKind = "routine" | "heartbreak";
export type TriggerType = "interval" | "webhook" | "manual";

export interface BackgroundTask {
  id: string;
  session_id: string;
  workspace_id: string | null;
  kind: BackgroundKind;
  name: string;
  instruction: string;
  trigger_type: TriggerType;
  trigger_config: Record<string, unknown>;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface BackgroundRun {
  id: string;
  task_id: string;
  run_thread_id: string | null;
  trigger_source: string;
  status: "running" | "done" | "error";
  summary: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface CreateTaskInput {
  kind: BackgroundKind;
  name: string;
  instruction: string;
  trigger_type: TriggerType;
  trigger_config?: Record<string, unknown>;
  workspace_id?: string | null;
}

function base(threadId: string): string {
  return `/sessions/${encodeURIComponent(threadId)}/background`;
}

async function asJson<T>(res: Response, fallback: T): Promise<T> {
  if (!res.ok) return fallback;
  try {
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export function useBackgroundTasks(threadId: string): {
  tasks: BackgroundTask[];
  runs: BackgroundRun[];
  loading: boolean;
  refetch: () => Promise<void>;
  createTask: (input: CreateTaskInput) => Promise<boolean>;
  toggleTask: (id: string, enabled: boolean) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  runTask: (id: string) => Promise<void>;
} {
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [runs, setRuns] = useState<BackgroundRun[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    const [t, r] = await Promise.all([
      fetch(`${base(threadId)}/tasks`).then((res) =>
        asJson<BackgroundTask[]>(res, []),
      ),
      fetch(`${base(threadId)}/runs`).then((res) =>
        asJson<BackgroundRun[]>(res, []),
      ),
    ]);
    setTasks(t);
    setRuns(r);
    setLoading(false);
  }, [threadId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const createTask = useCallback(
    async (input: CreateTaskInput): Promise<boolean> => {
      const res = await fetch(`${base(threadId)}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trigger_config: {}, ...input }),
      });
      if (res.ok) await refetch();
      return res.ok;
    },
    [threadId, refetch],
  );

  const toggleTask = useCallback(
    async (id: string, enabled: boolean): Promise<void> => {
      await fetch(`${base(threadId)}/tasks/${encodeURIComponent(id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      await refetch();
    },
    [threadId, refetch],
  );

  const deleteTask = useCallback(
    async (id: string): Promise<void> => {
      await fetch(`${base(threadId)}/tasks/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      await refetch();
    },
    [threadId, refetch],
  );

  const runTask = useCallback(
    async (id: string): Promise<void> => {
      await fetch(`${base(threadId)}/tasks/${encodeURIComponent(id)}/run`, {
        method: "POST",
      });
      // A run é assíncrona; o painel revalida ao receber o SSE, mas refazemos
      // o fetch já para refletir o estado 'running'.
      await refetch();
    },
    [threadId, refetch],
  );

  return {
    tasks,
    runs,
    loading,
    refetch,
    createTask,
    toggleTask,
    deleteTask,
    runTask,
  };
}
