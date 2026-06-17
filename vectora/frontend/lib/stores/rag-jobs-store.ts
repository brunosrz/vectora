import { create } from "zustand";

/**
 * rag-jobs-store — acompanha jobs de indexação RAG disparados pela UI.
 *
 * `start()` chama `POST /workspaces/{id}/rag/ingest` e passa a pollar
 * `GET /rag/jobs/{job_id}` até concluir. O modal de indexação e a aba Memory
 * leem daqui, então a indexação continua visível mesmo após "Minimizar".
 */

export type RagJobStatus =
  | "starting"
  | "indexing"
  | "done"
  | "failed"
  | "no_files";

export interface RagJob {
  jobId: string;
  workspaceId: string;
  path: string;
  total: number;
  processed: number;
  failed: number;
  status: RagJobStatus;
}

interface RagJobsState {
  jobs: Record<string, RagJob>;
  /** Dispara a indexação; retorna o jobId (ou null em falha) e inicia o poll. */
  start: (
    workspaceId: string,
    path: string,
    fileTypes: "code" | "markdown" | "all",
  ) => Promise<string | null>;
  /** Remove um job da lista (não cancela o processamento no backend). */
  dismiss: (jobId: string) => void;
}

const POLL_MS = 1200;
const timers: Record<string, ReturnType<typeof setInterval>> = {};

function stopPoll(jobId: string) {
  const t = timers[jobId];
  if (t) {
    clearInterval(t);
    delete timers[jobId];
  }
}

export const useRagJobsStore = create<RagJobsState>((set) => ({
  jobs: {},

  start: async (workspaceId, path, fileTypes) => {
    let data: {
      job_id: string;
      total_chunks: number;
      status: string;
    };
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(workspaceId)}/rag/ingest`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ path, file_types: fileTypes }),
        },
      );
      if (!res.ok) return null;
      data = await res.json();
    } catch {
      return null;
    }

    const jobId = data.job_id;
    set((s) => ({
      jobs: {
        ...s.jobs,
        [jobId]: {
          jobId,
          workspaceId,
          path,
          total: data.total_chunks ?? 0,
          processed: 0,
          failed: 0,
          status: data.status === "no_files" ? "no_files" : "indexing",
        },
      },
    }));

    if (data.status === "no_files") return jobId;

    const poll = async () => {
      try {
        const res = await fetch(
          `/workspaces/${encodeURIComponent(workspaceId)}/rag/jobs/${encodeURIComponent(jobId)}`,
          { credentials: "include" },
        );
        if (!res.ok) return;
        const st = (await res.json()) as {
          total: number;
          processed: number;
          failed: number;
          status: RagJobStatus;
        };
        set((s) => {
          const prev = s.jobs[jobId];
          if (!prev) return s;
          return {
            jobs: {
              ...s.jobs,
              [jobId]: {
                ...prev,
                total: st.total,
                processed: st.processed,
                failed: st.failed,
                status: st.status,
              },
            },
          };
        });
        if (st.status === "done" || st.status === "failed") stopPoll(jobId);
      } catch {
        // mantém o poll; falha transitória de rede
      }
    };
    timers[jobId] = setInterval(() => void poll(), POLL_MS);
    void poll();
    return jobId;
  },

  dismiss: (jobId) => {
    stopPoll(jobId);
    set((s) => {
      const next = { ...s.jobs };
      delete next[jobId];
      return { jobs: next };
    });
  },
}));
