"use client";

/**
 * CommandBar (R1)
 *
 * Barra de contexto acima do input: indicador de execução (Local), seletor de
 * workspace, estado git da branch, seletor de worktree e o modo de permissão.
 * Reúne componentes já existentes num único cabeçalho da área de input.
 */

import { useEffect, useState } from "react";
import { GitBranch, Monitor, Plug } from "lucide-react";

import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useSettingsDialogStore } from "@/lib/stores/settings-dialog-store";
import { useT } from "@/lib/i18n";
import { PermissionModeMenu } from "./permission-mode-menu";

function LocalChip() {
  const t = useT();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  // "Local" = sem sessão autenticada (CLI/root local); senão mostra a conta.
  const label = isAuthenticated ? "Server" : t("commandbar.local");
  return (
    <span
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-muted-foreground select-none"
      title={t("commandbar.local_tip")}
    >
      <Monitor className="w-3.5 h-3.5 shrink-0" />
      {label}
    </span>
  );
}

function WorktreeChip() {
  const t = useT();
  const active = useWorkspacesStore((s) => s.getActive());
  const [worktrees, setWorktrees] = useState<
    { path: string; branch: string | null }[]
  >([]);

  useEffect(() => {
    if (!active?.is_git_repo) {
      setWorktrees([]);
      return;
    }
    let cancelled = false;
    fetch(
      `/api/workspaces/worktrees?workspace_id=${encodeURIComponent(active.id)}`,
    )
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d?.worktrees) setWorktrees(d.worktrees);
      })
      .catch(() => {
        /* silencioso */
      });
    return () => {
      cancelled = true;
    };
  }, [active?.id, active?.is_git_repo]);

  // Só exibe quando há worktrees além da principal.
  if (worktrees.length <= 1) return null;

  return (
    <span
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-muted-foreground select-none"
      title={t("commandbar.worktree")}
    >
      <GitBranch className="w-3.5 h-3.5 shrink-0" />
      {worktrees.length}
    </span>
  );
}

function PluginsChip() {
  const openSettings = useSettingsDialogStore((s) => s.openAt);
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/plugins")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && typeof d?.total === "number") setCount(d.total);
      })
      .catch(() => {
        /* silencioso */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (count === 0) return null;

  return (
    <button
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors select-none"
      onClick={() => openSettings("plugins")}
      title="MCP"
    >
      <Plug className="w-3.5 h-3.5 shrink-0" />
      {count}
    </button>
  );
}

export function CommandBar() {
  return (
    <div className="flex items-center gap-1 flex-wrap mb-1.5 px-1">
      <LocalChip />
      <WorktreeChip />
      <PluginsChip />
      <div className="flex-1" />
      <PermissionModeMenu />
    </div>
  );
}
