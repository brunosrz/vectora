"use client";

/**
 * DiffTab — diff do workspace ativo.
 *
 * Estado vive no workbench-store (slice `diff`), cacheado por workspace:
 * resumo (lista de arquivos modificados), arquivos com hunks abertos e os
 * hunks já carregados. Revalidação via `useWorkbenchSWR`.
 */

import { ChevronDown, ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

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
    `/workspaces/${encodeURIComponent(workspaceId)}/git/diff`,
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
    `/workspaces/${encodeURIComponent(workspaceId)}/git/diff/file?${qs}`,
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
  "?": "text-muted-foreground",
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
  const clearPending = useWorkbenchStore((s) => s.clearPending);

  // Abrir/revalidar a aba consome a pendência de atualização.
  useEffect(() => {
    if (wsId) clearPending(wsId, "diff");
  }, [wsId, fetchedAt, clearPending]);

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

  return <DiffGroups workspaceId={wsId} summary={summary} t={t} />;
}

// ---------------------------------------------------------------------------
// DiffGroups — agrupa em "Staged" e "Modificados / Não rastreados". Um arquivo
// com XY=MM (staged E unstaged) aparece nos dois grupos.
// ---------------------------------------------------------------------------

function DiffGroups({
  workspaceId,
  summary,
  t,
}: {
  workspaceId: string;
  summary: DiffSummary;
  t: ReturnType<typeof useT>;
}) {
  const { staged, unstaged } = useMemo(() => {
    const stagedFiles: DiffFile[] = [];
    const unstagedFiles: DiffFile[] = [];
    for (const f of summary.files) {
      if (f.staged_change) stagedFiles.push(f);
      if (f.unstaged_change || f.untracked) unstagedFiles.push(f);
    }
    return { staged: stagedFiles, unstaged: unstagedFiles };
  }, [summary.files]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1.5 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <span className="text-xs text-muted-foreground">
          {t("workbench.diff.files_badge", { n: summary.files.length })}
        </span>
        <span className="text-xs font-mono">
          <span className="text-green-500">+{summary.total_additions}</span>{" "}
          <span className="text-destructive">−{summary.total_deletions}</span>
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <DiffGroup
          label={t("workbench.diff.group_staged")}
          tone="text-green-500"
          workspaceId={workspaceId}
          files={staged}
        />
        <DiffGroup
          label={t("workbench.diff.group_unstaged")}
          tone="text-amber-500"
          workspaceId={workspaceId}
          files={unstaged}
        />
      </div>
    </div>
  );
}

function DiffGroup({
  label,
  tone,
  workspaceId,
  files,
}: {
  label: string;
  tone: string;
  workspaceId: string;
  files: DiffFile[];
}) {
  const [open, setOpen] = useState(true);

  if (files.length === 0) return null;

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-2 py-1 text-[10px] font-medium uppercase tracking-wide hover:bg-muted/30 text-left"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground" />
        )}
        <span className={tone}>{label}</span>
        <span className="text-muted-foreground">({files.length})</span>
      </button>
      {open &&
        files.map((f) => (
          <FileRow key={f.path} workspaceId={workspaceId} file={f} />
        ))}
    </div>
  );
}
