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
import { useEnvironmentDialogStore } from "@/lib/stores/environment-dialog-store";
import { VECTORA_API_URL } from "@/lib/constants/api";
import { PermissionModeMenu } from "./permission-mode-menu";
import { m } from "@/lib/paraglide/messages";

/**
 * Hostname abreviado extraído da URL do backend, com porta quando não-padrão.
 * Cai para "server" como rótulo neutro quando a URL é vazia ou inválida.
 */
function serverHostLabel(): string {
  try {
    const u = new URL(VECTORA_API_URL || "http://localhost");
    const isDefaultPort =
      !u.port ||
      (u.protocol === "http:" && u.port === "80") ||
      (u.protocol === "https:" && u.port === "443");
    return isDefaultPort ? u.hostname : `${u.hostname}:${u.port}`;
  } catch {
    return "server";
  }
}

function LocalChip() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  // CLI/root local exibe "Local". Sessão autenticada exibe o hostname real
  // do backend — informativo (distingue localhost vs LAN vs Tailscale).
  const label = isAuthenticated ? serverHostLabel() : m.commandbar_local();
  return (
    <span
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-muted-foreground select-none"
      title={m.commandbar_local_tip()}
    >
      <Monitor className="w-3.5 h-3.5 shrink-0" />
      {label}
    </span>
  );
}

function WorktreeChip() {
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
    fetch(`/workspaces/worktrees?workspace_id=${encodeURIComponent(active.id)}`)
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
      title={m.commandbar_worktree()}
    >
      <GitBranch className="w-3.5 h-3.5 shrink-0" />
      {worktrees.length}
    </span>
  );
}

function PluginsChip() {
  const openEnvironment = useEnvironmentDialogStore((s) => s.openAt);
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetch("/plugins")
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
      onClick={() => openEnvironment("plugins")}
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
