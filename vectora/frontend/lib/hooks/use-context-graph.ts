"use client";

import { useCallback, useEffect, useState } from "react";

export interface GraphStatus {
  status:
    | "not_built"
    | "running"
    | "done"
    | "error"
    | "unknown"
    | "queued"
    | "paused";
  node_count?: number | null;
  edge_count?: number | null;
  error?: string | null;
  step?: number | null;
  step_total?: number | null;
  step_label?: string | null;
  files_total?: number | null;
  files_done?: number | null;
  files_list?: string[] | null;
}

export interface GraphReport {
  report: string;
}

function base(workspaceId: string): string {
  return `/workspaces/${encodeURIComponent(workspaceId)}/context-graph`;
}

async function asJson<T>(res: Response, fallback: T): Promise<T> {
  if (!res.ok) return fallback;
  try {
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export function useContextGraph(workspaceId: string | null | undefined) {
  const [status, setStatus] = useState<GraphStatus>({ status: "unknown" });
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(`${base(workspaceId)}/status`).catch(() => null);
    if (!res) return;
    const data = await asJson<GraphStatus>(res, { status: "unknown" });
    setStatus(data);
  }, [workspaceId]);

  const fetchReport = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(`${base(workspaceId)}/report`).catch(() => null);
    if (!res || !res.ok) return;
    const data = await asJson<GraphReport>(res, { report: "" });
    if (data.report) setReport(data.report);
  }, [workspaceId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (status.status === "done") fetchReport();
  }, [status.status, fetchReport]);

  useEffect(() => {
    if (status.status !== "running") return;
    const id = setInterval(fetchStatus, 1500);
    return () => clearInterval(id);
  }, [status.status, fetchStatus]);

  const build = useCallback(
    async (opts: { model?: string; mode?: string; update?: boolean } = {}) => {
      if (!workspaceId) return;
      setLoading(true);
      setStatus({ status: "queued" });
      const res = await fetch(`${base(workspaceId)}/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: opts.model ?? "",
          mode: opts.mode ?? "semantic",
          update: opts.update ?? false,
        }),
      }).catch(() => null);
      setLoading(false);
      if (res?.ok) {
        setStatus({ status: "running" });
      }
    },
    [workspaceId],
  );

  const getHtmlUrl = useCallback(() => {
    if (!workspaceId) return null;
    return `${base(workspaceId)}/html`;
  }, [workspaceId]);

  const queryAffected = useCallback(
    async (nodeQuery: string, depth = 2): Promise<string> => {
      if (!workspaceId) return "";
      try {
        const res = await fetch(`${base(workspaceId)}/affected`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ node_query: nodeQuery, depth }),
        });
        if (!res.ok) return "";
        const data = await res.json();
        return (data as { answer?: string }).answer ?? "";
      } catch {
        return "";
      }
    },
    [workspaceId],
  );

  const update = useCallback(
    async (opts: { model?: string } = {}) => {
      await build({ ...opts, update: true });
    },
    [build],
  );

  const cancel = useCallback(async () => {
    if (!workspaceId) return;
    await fetch(`${base(workspaceId)}/build`, { method: "DELETE" }).catch(
      () => null,
    );
    setStatus({ status: "not_built" });
  }, [workspaceId]);

  return {
    status,
    report,
    loading,
    build,
    update,
    cancel,
    queryAffected,
    fetchStatus,
    getHtmlUrl,
  };
}
