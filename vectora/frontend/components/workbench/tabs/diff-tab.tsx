"use client";

/**
 * DiffTab — diff do workspace ativo.
 *
 * Estado vive no workbench-store (slice `diff`), cacheado por workspace:
 * resumo (lista de arquivos modificados), arquivos com hunks abertos e os
 * hunks já carregados. Revalidação via `useWorkbenchSWR`.
 */

import {
  Archive,
  ChevronDown,
  ChevronRight,
  Copy,
  GitBranch,
  GitCommit,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import { useDelayedLoading } from "@/lib/hooks/use-delayed-loading";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type DiffFile,
  type DiffHunk,
  type DiffSummary,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { DiffSkeleton } from "./diff-skeleton";

// ---------------------------------------------------------------------------
// A.7 — Git Log: tipos e funções de API
// ---------------------------------------------------------------------------

interface GitLogCommit {
  sha: string;
  sha_short: string;
  author: string;
  date: string;
  message: string;
  refs: string[];
}

interface GitLogData {
  branch: string;
  commits: GitLogCommit[];
}

async function fetchGitLog(workspaceId: string): Promise<GitLogData | null> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/log?n=50`,
  );
  if (!res.ok) return null;
  return res.json() as Promise<GitLogData>;
}

async function fetchCommitDiff(
  workspaceId: string,
  sha: string,
): Promise<string | null> {
  const qs = new URLSearchParams({ sha });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/commit/diff?${qs}`,
  );
  if (!res.ok) return null;
  const data = await res.json();
  return (data.diff as string) ?? null;
}

async function apiRevertCommit(
  workspaceId: string,
  sha: string,
): Promise<{ status: string; message: string }> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/revert`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sha, no_commit: true }),
    },
  );
  const data = await res.json().catch(() => ({ status: "error", message: "" }));
  return data as { status: string; message: string };
}

async function apiCompareRefs(
  workspaceId: string,
  base: string,
  head: string,
): Promise<{ diff: string; truncated: boolean } | null> {
  const qs = new URLSearchParams({ base, head });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/compare?${qs}`,
  );
  if (!res.ok) return null;
  return res.json();
}

// ---------------------------------------------------------------------------
// A.15 — Stage / unstage / discard / commit inline
// ---------------------------------------------------------------------------

async function apiGitAction(
  workspaceId: string,
  action: "stage" | "unstage" | "discard",
  path: string,
): Promise<boolean> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/${action}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    },
  );
  return res.ok;
}

async function apiGitCommitInline(
  workspaceId: string,
  message: string,
  dryRunHooks = false,
): Promise<{ status: string; message: string }> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/commit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, dry_run_hooks: dryRunHooks }),
    },
  );
  const data = await res.json().catch(() => ({ status: "error", message: "" }));
  return data as { status: string; message: string };
}

// ---------------------------------------------------------------------------

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
  onRefresh,
}: {
  workspaceId: string;
  file: DiffFile;
  onRefresh?: () => void;
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

  const [discardOpen, setDiscardOpen] = useState(false);

  const handleAction = useCallback(
    async (action: "stage" | "unstage" | "discard") => {
      if (action === "discard") {
        setDiscardOpen(true);
        return;
      }
      await apiGitAction(workspaceId, action, file.path);
      onRefresh?.();
    },
    [workspaceId, file.path, onRefresh],
  );

  const handleConfirmDiscard = useCallback(async () => {
    setDiscardOpen(false);
    await apiGitAction(workspaceId, "discard", file.path);
    onRefresh?.();
  }, [workspaceId, file.path, onRefresh]);

  return (
    <>
      {/* Dialog de confirmação de discard (Radix, não window.confirm) */}
      <Dialog open={discardOpen} onOpenChange={setDiscardOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Descartar alterações?</DialogTitle>
            <DialogDescription>
              As alterações em{" "}
              <span className="font-mono text-foreground">{file.path}</span>{" "}
              serão perdidas permanentemente.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button
              onClick={() => setDiscardOpen(false)}
              className="px-3 py-1.5 text-xs rounded-md border border-border/60 hover:bg-muted/40"
            >
              Cancelar
            </button>
            <button
              onClick={() => void handleConfirmDiscard()}
              className="px-3 py-1.5 text-xs rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Descartar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <div className="border-b border-border/40 last:border-0 group">
        <div className="flex items-center">
          <button
            onClick={() => setDiffOpenFile(workspaceId, file.path, !open)}
            className="flex-1 flex items-center gap-2 px-2 py-1.5 text-xs hover:bg-muted/30 text-left min-w-0"
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
          {/* Botões inline A.15: +stage / −unstage / ↩discard */}
          <div className="flex items-center gap-0.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            {file.unstaged_change || file.untracked ? (
              <button
                onClick={() => void handleAction("stage")}
                title="Stage"
                className="p-0.5 text-green-500 hover:text-green-400 text-[10px] font-bold"
              >
                +
              </button>
            ) : null}
            {file.staged_change ? (
              <button
                onClick={() => void handleAction("unstage")}
                title="Unstage"
                className="p-0.5 text-amber-500 hover:text-amber-400 text-[10px] font-bold"
              >
                −
              </button>
            ) : null}
            {file.unstaged_change && !file.untracked ? (
              <button
                onClick={() => void handleAction("discard")}
                title="Descartar alterações"
                className="p-0.5 text-destructive hover:text-red-400 text-[10px]"
              >
                ↩
              </button>
            ) : null}
          </div>
        </div>
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
    </>
  );
}

// ---------------------------------------------------------------------------
// A.7 — CommitRow: linha de commit com diff expandível e ações
// ---------------------------------------------------------------------------

function CommitRow({
  workspaceId,
  commit,
}: {
  workspaceId: string;
  commit: GitLogCommit;
}) {
  const [open, setOpen] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleToggle = useCallback(async () => {
    const next = !open;
    setOpen(next);
    if (next && diff === null) {
      setDiffLoading(true);
      const d = await fetchCommitDiff(workspaceId, commit.sha);
      setDiffLoading(false);
      setDiff(d ?? "");
    }
  }, [open, diff, workspaceId, commit.sha]);

  const handleCopy = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      void navigator.clipboard.writeText(commit.sha).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
    },
    [commit.sha],
  );

  const date = (() => {
    try {
      const d = new Date(commit.date);
      return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
    } catch {
      return commit.date.slice(0, 10);
    }
  })();

  return (
    <div className="border-b border-border/40 last:border-0">
      <button
        onClick={handleToggle}
        className="w-full flex items-start gap-2 px-2 py-1.5 text-xs hover:bg-muted/30 text-left group"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground mt-0.5" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="font-mono text-[10px] text-primary shrink-0">
              {commit.sha_short}
            </span>
            <span className="text-[10px] text-muted-foreground shrink-0">
              {date}
            </span>
            {commit.refs.map((ref) => (
              <span
                key={ref}
                className="text-[9px] px-1 py-px rounded bg-primary/10 text-primary shrink-0 truncate max-w-[80px]"
                title={ref}
              >
                {ref}
              </span>
            ))}
          </div>
          <p className="truncate text-foreground/90">{commit.message}</p>
          <p className="text-[10px] text-muted-foreground truncate mt-0.5">
            {commit.author.split("<")[0].trim()}
          </p>
        </div>
        {/* Ações: copiar SHA + revert */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            onClick={handleCopy}
            className="p-0.5 text-muted-foreground hover:text-foreground"
            title="Copiar SHA"
          >
            {copied ? (
              <GitCommit className="w-3 h-3 text-green-500" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
          <button
            onClick={async (e) => {
              e.stopPropagation();
              const r = await apiRevertCommit(workspaceId, commit.sha);
              if (r.status !== "ok") {
                // silently ignore — toast seria ideal mas está fora do scope aqui
              }
            }}
            className="p-0.5 text-muted-foreground hover:text-amber-500"
            title="Reverter commit"
          >
            <ChevronDown className="w-3 h-3 rotate-180" />
          </button>
        </div>
      </button>
      {open && (
        <div className="px-3 pb-2">
          {diffLoading ? (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          ) : (
            <pre className="text-[10px] font-mono whitespace-pre-wrap break-all bg-muted/30 rounded-sm px-2 py-1 overflow-x-auto max-h-64 overflow-y-auto">
              {diff ?? ""}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// GitLogView: lista de commits para uma workspace
function GitLogView({ workspaceId }: { workspaceId: string }) {
  const [logData, setLogData] = useState<GitLogData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    setLoading(true);
    void fetchGitLog(workspaceId).then((data) => {
      setLoading(false);
      setLogData(data);
    });
  }, [workspaceId]);

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!logData || logData.commits.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-8 px-4">
        Nenhum commit encontrado.
      </p>
    );
  }
  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1 border-b border-border/60 bg-muted/10 flex items-center gap-1.5">
        <GitBranch className="w-3 h-3 text-muted-foreground" />
        <span className="text-[10px] font-mono text-muted-foreground">
          {logData.branch}
        </span>
        <span className="text-[10px] text-muted-foreground ml-auto">
          {logData.commits.length} commits
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {logData.commits.map((c) => (
          <CommitRow key={c.sha} workspaceId={workspaceId} commit={c} />
        ))}
      </div>
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
  const [logView, setLogView] = useState<
    "changes" | "log" | "stash" | "conflicts" | "compare" | "worktrees"
  >("changes");

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

  // UX-9 — só exibe o skeleton se o carregamento levar mais que 100ms
  // (cache quente resolve quase instantâneo; evita o "flash").
  const showSkeleton = useDelayedLoading(summary === null && Boolean(wsId));

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground p-4 text-center">
        {t("workbench.diff.no_workspace")}
      </div>
    );
  }

  if (!summary) {
    // Sem skeleton nos primeiros 100ms — cache quente costuma resolver antes
    // disso, e mostrar+esconder um placeholder em sequência pisca mais do que
    // simplesmente esperar o conteúdo real aparecer.
    return showSkeleton ? <DiffSkeleton /> : <div className="h-full" />;
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

  return (
    <div className="h-full flex flex-col">
      {/* Barra de abas Changes | Log */}
      <div className="flex shrink-0 border-b border-border/60">
        <button
          onClick={() => setLogView("changes")}
          aria-pressed={logView === "changes"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "changes"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_changes")}
        </button>
        <button
          onClick={() => setLogView("log")}
          aria-pressed={logView === "log"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "log"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_log")}
        </button>
        <button
          onClick={() => setLogView("stash")}
          aria-pressed={logView === "stash"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "stash"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_stash")}
        </button>
        <button
          onClick={() => setLogView("conflicts")}
          aria-pressed={logView === "conflicts"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "conflicts"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_conflicts")}
        </button>
        <button
          onClick={() => setLogView("compare")}
          aria-pressed={logView === "compare"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "compare"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_compare")}
        </button>
        <button
          onClick={() => setLogView("worktrees")}
          aria-pressed={logView === "worktrees"}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${
            logView === "worktrees"
              ? "border-b-2 border-primary text-foreground -mb-px"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("workbench.diff.tab_worktrees")}
        </button>
      </div>
      {/* Conteúdo */}
      <div className="flex-1 min-h-0">
        {logView === "log" ? (
          <GitLogView workspaceId={wsId} />
        ) : logView === "stash" ? (
          <StashView workspaceId={wsId} />
        ) : logView === "conflicts" ? (
          <ConflictView workspaceId={wsId} />
        ) : logView === "compare" ? (
          <CompareView workspaceId={wsId} />
        ) : logView === "worktrees" ? (
          <WorktreeView workspaceId={wsId} />
        ) : summary.files.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
            <p className="text-xs text-muted-foreground">
              {t("workbench.diff.clean")}
            </p>
            <p className="text-[10px] text-muted-foreground/60">
              {t("workbench.diff.clean_hint")}
            </p>
          </div>
        ) : (
          <DiffGroups workspaceId={wsId} summary={summary} t={t} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// A.14 — WorktreeView: lista worktrees e cria nova
// ---------------------------------------------------------------------------

interface WorktreeEntry {
  path: string;
  branch?: string;
  head?: string;
}

async function apiFetchWorktrees(
  workspaceId: string,
): Promise<WorktreeEntry[]> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/worktrees`,
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.worktrees as WorktreeEntry[]) ?? [];
}

async function apiCreateWorktree(
  workspaceId: string,
  name: string,
  branch?: string,
): Promise<boolean> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/worktrees`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, name, branch }),
    },
  );
  return res.ok;
}

function WorktreeView({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [entries, setEntries] = useState<WorktreeEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [newName, setNewName] = useState("");
  const [newBranch, setNewBranch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const r = await apiFetchWorktrees(workspaceId);
    setLoading(false);
    setEntries(r);
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    await apiCreateWorktree(
      workspaceId,
      newName.trim(),
      newBranch.trim() || undefined,
    );
    setNewName("");
    setNewBranch("");
    void load();
  }, [workspaceId, newName, newBranch, load]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1.5 border-b border-border/60 bg-muted/10 flex flex-col gap-1">
        <div className="flex items-center gap-1.5">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("workbench.diff.worktree_name_placeholder")}
            className="flex-1 text-xs bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0"
          />
          <input
            value={newBranch}
            onChange={(e) => setNewBranch(e.target.value)}
            placeholder={t("workbench.diff.worktree_branch_placeholder")}
            className="flex-1 text-xs bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0 font-mono"
          />
          <button
            onClick={handleCreate}
            className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 shrink-0"
          >
            {t("workbench.diff.worktree_create")}
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-8 px-4">
            {t("workbench.diff.worktree_empty")}
          </p>
        ) : (
          entries.map((w, i) => (
            <div
              key={i}
              className="px-3 py-2 border-b border-border/40 last:border-0"
            >
              <p
                className="text-xs font-mono text-foreground truncate"
                title={w.path}
              >
                {w.path.split(/[\\/]/).pop()}
              </p>
              <p className="text-[10px] text-muted-foreground truncate">
                {w.path}
              </p>
              {w.branch && (
                <p className="text-[10px] text-primary font-mono mt-0.5">
                  {w.branch}
                </p>
              )}
              {w.head && (
                <p className="text-[10px] text-muted-foreground font-mono">
                  {w.head}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// A.12 — CompareView: diff entre dois refs
// ---------------------------------------------------------------------------

function CompareView({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [base, setBase] = useState("HEAD~1");
  const [head, setHead] = useState("HEAD");
  const [diff, setDiff] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [truncated, setTruncated] = useState(false);

  const handleCompare = useCallback(async () => {
    if (!base.trim() || !head.trim()) return;
    setLoading(true);
    const r = await apiCompareRefs(workspaceId, base.trim(), head.trim());
    setLoading(false);
    if (r) {
      setDiff(r.diff);
      setTruncated(r.truncated);
    }
  }, [workspaceId, base, head]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-2 py-1.5 border-b border-border/60 flex items-center gap-1.5 bg-muted/10">
        <input
          value={base}
          onChange={(e) => setBase(e.target.value)}
          placeholder="base (e.g. HEAD~1)"
          className="flex-1 text-xs bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0 font-mono"
        />
        <span className="text-[10px] text-muted-foreground">…</span>
        <input
          value={head}
          onChange={(e) => setHead(e.target.value)}
          placeholder="head (e.g. HEAD)"
          className="flex-1 text-xs bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0 font-mono"
        />
        <button
          onClick={handleCompare}
          className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 shrink-0"
        >
          {t("workbench.diff.compare_run")}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : diff === null ? (
          <p className="text-xs text-muted-foreground text-center py-8 px-4">
            {t("workbench.diff.compare_hint")}
          </p>
        ) : (
          <>
            {truncated && (
              <p className="text-[10px] text-amber-500 px-3 pt-1.5">
                {t("workbench.diff.compare_truncated")}
              </p>
            )}
            <pre className="text-[10px] font-mono whitespace-pre-wrap break-all bg-muted/20 m-2 rounded p-2 overflow-x-auto">
              {diff || t("workbench.diff.compare_no_diff")}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}

// A.9 — ConflictView: lista arquivos conflitantes com resolução ours/theirs
// ---------------------------------------------------------------------------

interface ConflictFile {
  path: string;
}

async function apiListConflicts(workspaceId: string): Promise<ConflictFile[]> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/conflicts`,
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.files as ConflictFile[]) ?? [];
}

async function apiResolveConflict(
  workspaceId: string,
  path: string,
  resolution: "ours" | "theirs" | "content",
  content?: string,
): Promise<boolean> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/resolve-conflict`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, resolution, content }),
    },
  );
  return res.ok;
}

function ConflictView({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [files, setFiles] = useState<ConflictFile[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const f = await apiListConflicts(workspaceId);
    setLoading(false);
    setFiles(f);
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const resolve = useCallback(
    async (path: string, resolution: "ours" | "theirs") => {
      await apiResolveConflict(workspaceId, path, resolution);
      void load();
    },
    [workspaceId, load],
  );

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-8 px-4">
        {t("workbench.diff.conflicts_none")}
      </p>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {files.map((f) => (
        <div
          key={f.path}
          className="border-b border-border/40 last:border-0 px-3 py-2"
        >
          <p
            className="text-xs font-mono text-amber-500 truncate mb-1.5"
            title={f.path}
          >
            {f.path}
          </p>
          <div className="flex gap-1.5">
            <button
              onClick={() => void resolve(f.path, "ours")}
              className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
            >
              {t("workbench.diff.conflicts_ours")}
            </button>
            <button
              onClick={() => void resolve(f.path, "theirs")}
              className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 hover:bg-purple-500/20"
            >
              {t("workbench.diff.conflicts_theirs")}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// A.8 — StashView: lista de stashes com push/pop/drop
// ---------------------------------------------------------------------------

interface StashEntry {
  index: number;
  label: string;
}

async function apiStash(
  workspaceId: string,
  action: string,
  opts: { name?: string; index?: number } = {},
): Promise<{ action: string; entries: StashEntry[]; message: string } | null> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/stash`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...opts }),
    },
  );
  if (!res.ok) return null;
  return res.json();
}

function StashView({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [entries, setEntries] = useState<StashEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [newName, setNewName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const r = await apiStash(workspaceId, "list");
    setLoading(false);
    if (r) setEntries(r.entries);
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handlePush = useCallback(async () => {
    await apiStash(workspaceId, "push", { name: newName || undefined });
    setNewName("");
    void load();
  }, [workspaceId, newName, load]);

  const handlePop = useCallback(async () => {
    await apiStash(workspaceId, "pop");
    void load();
  }, [workspaceId, load]);

  const handleDrop = useCallback(
    async (index: number) => {
      await apiStash(workspaceId, "drop", { index });
      void load();
    },
    [workspaceId, load],
  );

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="px-2 py-1.5 border-b border-border/60 flex items-center gap-1.5 bg-muted/10">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t("workbench.diff.stash_name_placeholder")}
          className="flex-1 text-xs bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0"
          onKeyDown={(e) => {
            if (e.key === "Enter") void handlePush();
          }}
        />
        <button
          onClick={handlePush}
          title={t("workbench.diff.stash_push")}
          className="p-1 rounded hover:bg-muted/40 text-muted-foreground hover:text-foreground"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
        {entries.length > 0 && (
          <button
            onClick={handlePop}
            title={t("workbench.diff.stash_pop")}
            className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20"
          >
            {t("workbench.diff.stash_pop")}
          </button>
        )}
      </div>
      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-8 px-4">
            {t("workbench.diff.stash_empty")}
          </p>
        ) : (
          entries.map((e) => (
            <div
              key={e.index}
              className="flex items-center gap-2 px-3 py-1.5 border-b border-border/40 last:border-0 group"
            >
              <Archive className="w-3 h-3 text-muted-foreground shrink-0" />
              <span className="flex-1 truncate text-xs">{e.label}</span>
              <button
                onClick={() => void handleDrop(e.index)}
                title={t("workbench.diff.stash_drop")}
                className="p-0.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
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
  const invalidateDiff = useWorkbenchStore((s) => s.invalidateDiff);
  const [commitMsg, setCommitMsg] = useState("");
  const [committing, setCommitting] = useState(false);
  const [hookResult, setHookResult] = useState<{
    status: "ok" | "fail" | null;
    output: string;
  }>({ status: null, output: "" });

  const handleRefresh = useCallback(() => {
    invalidateDiff(workspaceId);
  }, [workspaceId, invalidateDiff]);

  const handleCheckHooks = useCallback(async () => {
    setCommitting(true);
    setHookResult({ status: null, output: "" });
    try {
      const result = await apiGitCommitInline(
        workspaceId,
        commitMsg.trim() || " ",
        true,
      );
      if (result.status === "hooks_ok") {
        setHookResult({ status: "ok", output: result.message ?? "" });
      } else {
        setHookResult({ status: "fail", output: result.message ?? "" });
      }
    } finally {
      setCommitting(false);
    }
  }, [workspaceId, commitMsg]);

  const handleCommit = useCallback(async () => {
    if (!commitMsg.trim()) return;
    setCommitting(true);
    setHookResult({ status: null, output: "" });
    try {
      const result = await apiGitCommitInline(workspaceId, commitMsg.trim());
      if (result.status === "ok") {
        setCommitMsg("");
        handleRefresh();
      }
    } finally {
      setCommitting(false);
    }
  }, [workspaceId, commitMsg, handleRefresh]);

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
      <div className="flex-1 overflow-y-auto min-h-0">
        <DiffGroup
          label={t("workbench.diff.group_staged")}
          tone="text-green-500"
          workspaceId={workspaceId}
          files={staged}
          onRefresh={handleRefresh}
        />
        <DiffGroup
          label={t("workbench.diff.group_unstaged")}
          tone="text-amber-500"
          workspaceId={workspaceId}
          files={unstaged}
          onRefresh={handleRefresh}
        />
      </div>
      {/* Painel de commit A.15 + A.16 */}
      <div className="border-t border-border/60 p-2 flex flex-col gap-1.5 bg-muted/10 shrink-0">
        <textarea
          value={commitMsg}
          onChange={(e) => setCommitMsg(e.target.value)}
          placeholder={t("workbench.diff.commit_placeholder")}
          rows={2}
          className="w-full resize-none rounded-md border border-border/60 bg-background px-2 py-1 text-xs font-mono placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
              void handleCommit();
            }
          }}
        />
        {/* Resultado dos hooks A.16 */}
        {hookResult.status !== null && (
          <div
            className={`rounded-md px-2 py-1 text-[10px] font-mono whitespace-pre-wrap break-all ${
              hookResult.status === "ok"
                ? "bg-green-500/10 text-green-500"
                : "bg-destructive/10 text-destructive"
            }`}
          >
            {hookResult.status === "ok"
              ? t("workbench.diff.hooks_ok")
              : t("workbench.diff.hooks_failed")}
            {hookResult.output ? `\n${hookResult.output}` : ""}
          </div>
        )}
        <div className="flex gap-1.5">
          <button
            onClick={() => void handleCheckHooks()}
            disabled={committing}
            className="flex items-center justify-center gap-1 py-1 px-2 text-xs rounded-md border border-border/60 hover:bg-muted/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title={t("workbench.diff.check_hooks")}
          >
            {committing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <span className="text-[10px]">⚙</span>
            )}
            {t("workbench.diff.check_hooks")}
          </button>
          <button
            onClick={() => void handleCommit()}
            disabled={!commitMsg.trim() || committing}
            className="flex flex-1 items-center justify-center gap-1.5 py-1 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {committing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <GitCommit className="w-3 h-3" />
            )}
            {t("workbench.diff.commit_button")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DiffGroup({
  label,
  tone,
  workspaceId,
  files,
  onRefresh,
}: {
  label: string;
  tone: string;
  workspaceId: string;
  files: DiffFile[];
  onRefresh?: () => void;
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
          <FileRow
            key={f.path}
            workspaceId={workspaceId}
            file={f}
            onRefresh={onRefresh}
          />
        ))}
    </div>
  );
}
