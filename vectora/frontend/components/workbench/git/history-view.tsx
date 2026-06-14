"use client";

/**
 * HistoryView — aba "Histórico" do painel Git (antiga aba Log).
 *
 * Lista os últimos commits; clique expande o diff do commit. Clique direito
 * abre menu: copiar SHA, ver diff, checkout, reverter.
 */

import { ChevronDown, ChevronRight, GitBranch, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useT } from "@/lib/i18n";
import {
  apiCheckout,
  apiRevert,
  fetchCommitDiff,
  fetchGitLog,
  type GitLogCommit,
} from "./api";
import { useContextMenu, type ContextMenuItem } from "./git-context-menu";

function formatDate(raw: string): string {
  try {
    const d = new Date(raw);
    return `${String(d.getDate()).padStart(2, "0")}/${String(
      d.getMonth() + 1,
    ).padStart(2, "0")}/${d.getFullYear()}`;
  } catch {
    return raw.slice(0, 10);
  }
}

function CommitRow({
  workspaceId,
  commit,
  onContextMenu,
}: {
  workspaceId: string;
  commit: GitLogCommit;
  onContextMenu: (e: React.MouseEvent, commit: GitLogCommit) => void;
}) {
  const [open, setOpen] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const handleToggle = useCallback(async () => {
    const next = !open;
    setOpen(next);
    if (next && diff === null) {
      setDiffLoading(true);
      const d = await fetchCommitDiff(workspaceId, commit.sha);
      setDiffLoading(false);
      setDiff(d);
    }
  }, [open, diff, workspaceId, commit.sha]);

  return (
    <div
      className="border-b border-border/40 last:border-0"
      onContextMenu={(e) => onContextMenu(e, commit)}
    >
      <button
        onClick={handleToggle}
        className="w-full flex items-start gap-2 px-2 py-1.5 text-xs hover:bg-muted/30 text-left"
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
              {formatDate(commit.date)}
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

export function HistoryView({
  workspaceId,
  onChanged,
}: {
  workspaceId: string;
  /** Chamado após checkout/revert para o pai revalidar branch/diff. */
  onChanged: () => void;
}) {
  const t = useT();
  const menu = useContextMenu();
  const [data, setData] = useState<{
    branch: string;
    commits: GitLogCommit[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    setLoading(true);
    void fetchGitLog(workspaceId).then((d) => {
      setLoading(false);
      setData(d);
    });
  }, [workspaceId]);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, commit: GitLogCommit) => {
      const items: ContextMenuItem[] = [
        {
          label: t("workbench.git.ctx_copy_sha"),
          onSelect: () => void navigator.clipboard.writeText(commit.sha),
        },
        {
          label: t("workbench.git.ctx_checkout"),
          onSelect: () =>
            void apiCheckout(workspaceId, commit.sha).then(onChanged),
        },
        {
          label: t("workbench.git.ctx_revert"),
          danger: true,
          onSelect: () =>
            void apiRevert(workspaceId, commit.sha).then(onChanged),
        },
      ];
      menu.open(e, items);
    },
    [workspaceId, t, onChanged, menu],
  );

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!data || data.commits.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-8 px-4">
        {t("workbench.git.history_empty")}
      </p>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {menu.element}
      <div className="px-2 py-1 border-b border-border/60 bg-muted/10 flex items-center gap-1.5">
        <GitBranch className="w-3 h-3 text-muted-foreground" />
        <span className="text-[10px] font-mono text-muted-foreground">
          {data.branch}
        </span>
        <span className="text-[10px] text-muted-foreground ml-auto">
          {t("workbench.git.commits_count", { n: data.commits.length })}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {data.commits.map((c) => (
          <CommitRow
            key={c.sha}
            workspaceId={workspaceId}
            commit={c}
            onContextMenu={handleContextMenu}
          />
        ))}
      </div>
    </div>
  );
}
