"use client";

/**
 * DiffTab (T7) — diff do workspace ativo.
 *
 * Cabeçalho com contagem +N -M, lista de arquivos modificados com
 * status (M/A/D/R) e expand inline dos hunks.
 */

import { ChevronDown, ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useT } from "@/lib/i18n";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

interface DiffHunk {
  header: string;
  lines: string[];
}

interface DiffFile {
  path: string;
  status: "M" | "A" | "D" | "R";
  additions: number;
  deletions: number;
  hunks?: DiffHunk[];
}

interface DiffResponse {
  is_git_repo: boolean;
  total_additions: number;
  total_deletions: number;
  files: DiffFile[];
}

async function fetchDiff(workspaceId: string): Promise<DiffResponse | null> {
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
  const [open, setOpen] = useState(false);
  const [hunks, setHunks] = useState<DiffHunk[] | null>(file.hunks ?? null);
  const [loading, setLoading] = useState(false);

  const handleToggle = useCallback(async () => {
    setOpen((o) => !o);
    if (!hunks) {
      setLoading(true);
      const h = await fetchDiffFile(workspaceId, file.path);
      setHunks(h ?? []);
      setLoading(false);
    }
  }, [hunks, workspaceId, file.path]);

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        onClick={handleToggle}
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
          {loading && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
          {!loading &&
            (hunks ?? []).map((h, i) => <HunkView key={i} hunk={h} />)}
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
  const [data, setData] = useState<DiffResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!workspace) return;
    let cancelled = false;
    setLoading(true);
    void fetchDiff(workspace.id).then((d) => {
      if (!cancelled) {
        setData(d);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [workspace]);

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground p-4 text-center">
        {t("workbench.diff.no_workspace")}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data?.is_git_repo) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
        <GitBranch className="w-6 h-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          {t("workbench.diff.not_git")}
        </p>
      </div>
    );
  }

  if (data.files.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
        <p className="text-xs text-muted-foreground">
          {t("workbench.diff.clean")}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1.5 border-b border-border/60 flex items-center justify-between bg-muted/20">
        <span className="text-xs text-muted-foreground">
          {t("workbench.diff.summary", { n: data.files.length })}
        </span>
        <span className="text-xs font-mono">
          <span className="text-green-500">+{data.total_additions}</span>{" "}
          <span className="text-destructive">−{data.total_deletions}</span>
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {data.files.map((f) => (
          <FileRow key={f.path} workspaceId={workspace.id} file={f} />
        ))}
      </div>
    </div>
  );
}
