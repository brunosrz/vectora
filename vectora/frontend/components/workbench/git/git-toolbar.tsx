"use client";

/**
 * GitToolbar — barra de ações do painel Git (estilo GitHub Desktop).
 *
 * - Branch (dropdown): branch atual + trocar / criar / comparar-merge /
 *   worktrees.
 * - Sync (botão adaptativo): Pull N · Push N · Fetch conforme ahead/behind.
 * - Pull requests (dropdown): lista abertos + criar PR.
 *
 * Tudo o que antes eram 6 sub-abas de texto cabe aqui em ícones/dropdowns,
 * eliminando o overflow horizontal da barra antiga.
 */

import { GitBranch, GitPullRequest, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";
import { apiCheckout, apiSync, type GitBranches, type GitStatus } from "./api";

function syncLabel(
  t: ReturnType<typeof useT>,
  status: GitStatus | null,
): { label: string; action: "fetch" | "pull" | "push" } {
  if (status && status.behind > 0) {
    return {
      label: t("workbench.git.sync_pull", { n: status.behind }),
      action: "pull",
    };
  }
  if (status && status.ahead > 0) {
    return {
      label: t("workbench.git.sync_push", { n: status.ahead }),
      action: "push",
    };
  }
  return { label: t("workbench.git.sync_fetch"), action: "fetch" };
}

export function GitToolbar({
  workspaceId,
  status,
  branches,
  onCompare,
  onOpenStash,
  onOpenWorktrees,
  onOpenPR,
  onChanged,
}: {
  workspaceId: string;
  status: GitStatus | null;
  branches: GitBranches | null;
  onCompare: () => void;
  onOpenStash: () => void;
  onOpenWorktrees: () => void;
  onOpenPR: (head: string) => void;
  onChanged: () => void;
}) {
  const t = useT();
  const [creating, setCreating] = useState(false);
  const [newBranch, setNewBranch] = useState("");
  const [syncing, setSyncing] = useState(false);

  const current = status?.branch || branches?.current || "—";
  const others = (branches?.branches ?? []).filter((b) => b !== current);
  const sync = syncLabel(t, status);

  const handleCheckout = useCallback(
    async (ref: string, create = false) => {
      await apiCheckout(workspaceId, ref, create);
      onChanged();
    },
    [workspaceId, onChanged],
  );

  const handleCreate = useCallback(async () => {
    if (!newBranch.trim()) return;
    await handleCheckout(newBranch.trim(), true);
    setNewBranch("");
    setCreating(false);
  }, [newBranch, handleCheckout]);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await apiSync(workspaceId, sync.action);
      onChanged();
    } finally {
      setSyncing(false);
    }
  }, [workspaceId, sync.action, onChanged]);

  return (
    <div className="shrink-0 border-b border-border/60">
      <div className="flex items-center gap-1 px-2 py-1.5">
        {/* Branch dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex items-center gap-1.5 min-w-0 max-w-[55%] px-2 py-1 rounded-md text-xs hover:bg-muted/50 transition-colors"
              title={t("tooltip.git_branch")}
              aria-label={t("tooltip.git_branch")}
            >
              <GitBranch className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate font-mono">{current}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[200px]">
            <DropdownMenuLabel>
              {t("workbench.git.branch_menu")}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {others.length === 0 ? (
              <DropdownMenuItem disabled>
                {t("workbench.git.branch_empty")}
              </DropdownMenuItem>
            ) : (
              others.map((b) => (
                <DropdownMenuItem
                  key={b}
                  onSelect={() => void handleCheckout(b)}
                  className="font-mono text-xs"
                >
                  {b}
                </DropdownMenuItem>
              ))
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => setCreating(true)}>
              {t("workbench.git.branch_create")}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onCompare}>
              {t("workbench.git.branch_compare")}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onOpenWorktrees}>
              {t("workbench.git.branch_worktrees")}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onOpenStash}>
              {t("workbench.git.stash_view")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="flex-1" />

        {/* Sync */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => void handleSync()}
              disabled={syncing}
              aria-label={sync.label}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-xs hover:bg-muted/50 disabled:opacity-50 transition-colors shrink-0"
            >
              {syncing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5 text-muted-foreground" />
              )}
              <span className="hidden sm:inline">{sync.label}</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{sync.label}</TooltipContent>
        </Tooltip>

        {/* PR */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => onOpenPR(current)}
              aria-label={t("tooltip.git_pr")}
              className="flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors shrink-0"
            >
              <GitPullRequest className="w-3.5 h-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{t("tooltip.git_pr")}</TooltipContent>
        </Tooltip>
      </div>

      {/* Linha de criação de branch (inline, aparece sob demanda) */}
      {creating && (
        <div className="flex items-center gap-1.5 px-2 pb-1.5">
          <input
            autoFocus
            value={newBranch}
            onChange={(e) => setNewBranch(e.target.value)}
            placeholder={t("workbench.git.branch_create_placeholder")}
            className="flex-1 text-xs font-mono bg-background border border-border/60 rounded px-1.5 py-0.5 outline-none focus:border-primary min-w-0"
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCreate();
              if (e.key === "Escape") setCreating(false);
            }}
          />
          <button
            onClick={() => void handleCreate()}
            className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20"
          >
            {t("workbench.git.branch_create").replace("…", "")}
          </button>
        </div>
      )}
    </div>
  );
}
