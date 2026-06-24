"use client";

import { useCallback, useEffect, useState } from "react";

export interface GraphStatus {
  status: "not_built" | "running" | "done" | "error" | "unknown" | "queued";
  node_count?: number | null;
  edge_count?: number | null;
  error?: string | null;
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

export function useGraph(workspaceId: string | null | undefined) {
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
    const id = setInterval(fetchStatus, 3000);
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

  return { status, report, loading, build, fetchStatus, getHtmlUrl };
}
