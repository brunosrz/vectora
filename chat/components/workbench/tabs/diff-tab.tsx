"use client";

/**
 * DiffTab (T7 + T11.3) — diff do workspace ativo.
 *
 * Estado vive no workbench-store (slice `diff`):
 *   - resumo (lista de arquivos modificados) → cacheado por workspace
 *   - arquivos com hunks abertos → idem
 *   - hunks já carregados → idem
 * SWR via `useWorkbenchSWR`.
 */

import { ChevronDown, ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { useCallback } from "react";

import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type DiffFile,
  type DiffHunk,
  type DiffSummary,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

async function fetchDiff(workspaceId: string): Promise<DiffSummary | null> {
  const res = await fetch(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/git/diff`,
  );
  if (!res.ok) return null;
  return res.json();
}

async function fetchDiffFile(
  workspaceId: string,
  path: string,
): Promise<DiffHunk[] | null> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/git/diff/file?${qs}`,
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.hunks ?? [];
}

const STATUS_TONE: Record<DiffFile["status"], string> = {
  M: "text-amber-500",
  A: "text-green-500",
  D: "text-destructive",
  R: "text-blue-400",
};

function HunkView({ hunk }: { hunk: DiffHunk }) {
  return (
    <pre className="text-[11px] font-mono leading-tight bg-muted/30 rounded-sm px-2 py-1 overflow-x-auto">
      <span className="text-muted-foreground">{hunk.header}</span>
      {"\n"}
      {hunk.lines.map((line, i) => {
        const tone = line.startsWith("+")
          ? "text-green-500"
          : line.startsWith("-")
            ? "text-destructive"
            : "text-foreground/80";
        return (
          <span key={i} className={tone}>
            {line}
            {"\n"}
          </span>
        );
      })}
    </pre>
  );
}

function FileRow({
  workspaceId,
  file,
}: {
  workspaceId: string;
  file: DiffFile;
}) {
  const open = useWorkbenchStore((s) =>
    s.getDiff(workspaceId).openFiles.includes(file.path),
  );
  const hunks = useWorkbenchStore(
    (s) => s.getDiff(workspaceId).hunksByFile[file.path],
  );
  const fetchedAt = useWorkbenchStore(
    (s) => s.getDiff(workspaceId).fileFetchedAt[file.path] ?? 0,
  );
  const setDiffOpenFile = useWorkbenchStore((s) => s.setDiffOpenFile);
  const setDiffHunks = useWorkbenchStore((s) => s.setDiffHunks);

  const revalidate = useCallback(async () => {
    const h = await fetchDiffFile(workspaceId, file.path);
    if (h) setDiffHunks(workspaceId, file.path, h);
  }, [workspaceId, file.path, setDiffHunks]);

  useWorkbenchSWR({
    key: `diff:${workspaceId}:${file.path}`,
    hasCache: Array.isArray(hunks),
    isStale: Date.now() - fetchedAt > WORKBENCH_STALE_MS,
    revalidate,
    skip: !open,
  });

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        onClick={() => setDiffOpenFile(workspaceId, file.path, !open)}
        className="w-full flex items-center gap-2 px-2 py-1.5 text-xs hover:bg-muted/30 text-left"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground" />
        )}
        <span
          className={`w-4 text-center font-bold shrink-0 ${STATUS_TONE[file.status]}`}
        >
          {file.status}
        </span>
        <span className="flex-1 truncate font-mono">{file.path}</span>
        <span className="text-green-500 shrink-0">+{file.additions}</span>
        <span className="text-destructive shrink-0">−{file.deletions}</span>
      </button>
      {open && (
        <div className="px-3 pb-2 space-y-1">
          {!hunks && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
          {hunks?.map((h, i) => (
            <HunkView key={i} hunk={h} />
          ))}
        </div>
      )}
    </div>
  );
}

interface DiffTabProps {
  threadId: string;
}

export function DiffTab(_props: DiffTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  const summary = useWorkbenchStore((s) => s.getDiff(wsId).summary);
  const fetchedAt = useWorkbenchStore((s) => s.getDiff(wsId).summaryFetchedAt);
  const setDiffSummary = useWorkbenchStore((s) => s.setDiffSummary);

  useWorkbenchSWR({
    key: `diff-summary:${wsId}`,
    hasCache: summary !== null,
    isStale: Date.now() - fetchedAt > WORKBENCH_STALE_MS,
    revalidate: async () => {
      if (!wsId) return;
      const data = await fetchDiff(wsId);
      if (data) setDiffSummary(wsId, data);
    },
    skip: !wsId,
  });

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground p-4 text-center">
        {t("workbench.diff.no_workspace")}
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!summary.is_git_repo) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
        <GitBranch className="w-6 h-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          {t("workbench.diff.not_git")}
        </p>
      </div>
    );
  }

  if (summary.files.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
        <p className="text-xs text-muted-foreground">
          {t("workbench.diff.clean")}
        </p>
        <p className="text-[10px] text-muted-foreground/60">
          {t("workbench.diff.clean_hint")}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1.5 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <span className="text-xs text-muted-foreground">
          {t("workbench.diff.summary", { n: summary.files.length })}
        </span>
        <span className="text-xs font-mono">
          <span className="text-green-500">+{summary.total_additions}</span>{" "}
          <span className="text-destructive">−{summary.total_deletions}</span>
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {summary.files.map((f) => (
          <FileRow key={f.path} workspaceId={wsId} file={f} />
        ))}
      </div>
    </div>
  );
}
