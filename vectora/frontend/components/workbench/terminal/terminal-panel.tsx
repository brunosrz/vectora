"use client";

/**
 * TerminalPanel — container de terminais: tabs por instância, botão de abrir
 * novo e fechar. Cada aba renderiza um XtermView ligado ao seu próprio PTY no
 * backend (identificado por terminal_id).
 */

import { Plug, Plus, ShieldCheck, TerminalSquare, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  useTerminalsStore,
  type TerminalInstance,
} from "@/lib/stores/terminals-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { XtermView } from "./xterm-view";
import { m } from "@/lib/paraglide/messages";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface SandboxStatus {
  enabled: boolean;
  diagnostic: string | null;
}

const SANDBOX_DIAGNOSTIC_MESSAGE: Record<string, () => string> = {
  no_workspace: m.terminal_sandbox_diagnostic_no_workspace,
  no_vectora_toml: m.terminal_sandbox_diagnostic_no_vectora_toml,
  sandbox_disabled_in_config:
    m.terminal_sandbox_diagnostic_sandbox_disabled_in_config,
  wsl_not_installed: m.terminal_sandbox_diagnostic_wsl_not_installed,
  no_general_purpose_distro:
    m.terminal_sandbox_diagnostic_no_general_purpose_distro,
  distro_missing_shell: m.terminal_sandbox_diagnostic_distro_missing_shell,
};

/** Consulta `GET /workspaces/{id}/sandbox/status` — reflete se o worker
 * jailado (AI Jail) está ativo pra essa workspace, e por quê não quando
 * desabilitado. `null` enquanto carrega (não mostra nenhum dos dois
 * avisos até saber de verdade). */
function useSandboxStatus(workspaceId: string | undefined): {
  status: SandboxStatus | null;
  refetch: () => void;
} {
  const [status, setStatus] = useState<SandboxStatus | null>(null);

  const refetch = useCallback(() => {
    if (!workspaceId) {
      setStatus(null);
      return;
    }
    fetch(`/workspaces/${encodeURIComponent(workspaceId)}/sandbox/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: SandboxStatus | null) => {
        setStatus(
          data
            ? { enabled: data.enabled, diagnostic: data.diagnostic ?? null }
            : { enabled: false, diagnostic: null },
        );
      })
      .catch(() => {
        setStatus({ enabled: false, diagnostic: null });
      });
  }, [workspaceId]);

  useEffect(() => {
    setStatus(null);
    refetch();
  }, [refetch]);

  return { status, refetch };
}

function SandboxConfigDialog({
  workspaceId,
  diagnostic,
  open,
  onOpenChange,
  onInitDone,
}: {
  workspaceId: string;
  diagnostic: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onInitDone: () => void;
}) {
  const [initializing, setInitializing] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  const message = diagnostic
    ? (SANDBOX_DIAGNOSTIC_MESSAGE[diagnostic]?.() ?? diagnostic)
    : "";

  async function handleInit() {
    setInitializing(true);
    setInitError(null);
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(workspaceId)}/sandbox/init`,
        { method: "POST" },
      );
      if (!res.ok) {
        setInitError(m.terminal_sandbox_init_error());
        return;
      }
      onOpenChange(false);
      onInitDone();
    } catch {
      setInitError(m.terminal_sandbox_init_error());
    } finally {
      setInitializing(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{m.terminal_sandbox_dialog_title()}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">{message}</p>
        {initError && <p className="text-xs text-destructive">{initError}</p>}
        {diagnostic === "no_vectora_toml" && (
          <Button
            size="sm"
            onClick={() => void handleInit()}
            disabled={initializing}
          >
            {m.terminal_sandbox_init_button()}
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface TerminalPanelProps {
  threadId: string;
}

function newId(): string {
  return Math.random().toString(36).slice(2, 14);
}

export function TerminalPanel({ threadId }: TerminalPanelProps) {
  const terminals = useTerminalsStore((s) => s.list(threadId));
  const active = useTerminalsStore((s) => s.active(threadId));
  const open = useTerminalsStore((s) => s.open);
  const close = useTerminalsStore((s) => s.close);
  const setActive = useTerminalsStore((s) => s.setActive);
  const workspace = useWorkspacesStore((s) => s.getActive());
  const { status: sandboxStatus, refetch: refetchSandboxStatus } =
    useSandboxStatus(workspace?.id);
  const [sandboxDialogOpen, setSandboxDialogOpen] = useState(false);

  // Abre 1 terminal automaticamente quando o painel monta sem nenhum.
  // Lê o store inline (não a captura reativa) — Strict Mode roda effects
  // 2× em dev e a captura levaria a abrir 2 shells.
  useEffect(() => {
    const current = useTerminalsStore.getState().list(threadId);
    if (current.length === 0 && workspace?.trusted) {
      open(threadId, {
        id: newId(),
        title: m.terminal_tab_default(),
        workspaceId: workspace.id,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
        {m.terminal_no_workspace()}
      </div>
    );
  }

  if (!workspace.trusted) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground p-4 text-center">
        <Plug className="w-6 h-6" />
        <p className="font-medium">{m.terminal_untrusted_title()}</p>
        <p className="opacity-70">{m.terminal_untrusted_hint()}</p>
      </div>
    );
  }

  const handleNew = () => {
    open(threadId, {
      id: newId(),
      title: m.terminal_tab_default(),
      workspaceId: workspace.id,
    });
  };

  return (
    <div className="h-full flex flex-col bg-sidebar">
      {/* Tabs + ações */}
      <div className="flex items-center gap-1 bg-sidebar border-b border-border/60 px-2 py-1 overflow-x-auto">
        {terminals.map((term) => (
          <button
            key={term.id}
            onClick={() => setActive(threadId, term.id)}
            className={`group flex items-center gap-1.5 pl-2 pr-1 py-1 rounded-md text-xs select-none transition-colors shrink-0 ${
              term.id === active?.id
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            <TerminalSquare className="w-3.5 h-3.5" />
            <span className="truncate max-w-[120px]">{term.title}</span>
            <span
              role="button"
              tabIndex={0}
              className="opacity-0 group-hover:opacity-100 hover:bg-muted-foreground/20 rounded-sm p-0.5"
              onClick={(e) => {
                e.stopPropagation();
                close(threadId, term.id);
              }}
            >
              <X className="w-3 h-3" />
            </span>
          </button>
        ))}
        <button
          onClick={handleNew}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
          title={m.terminal_new()}
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Indicador dinâmico: sandboxed (informativo) vs sem sandbox (aviso,
          acionável via dialog de diagnóstico). sandboxStatus === null
          enquanto o status ainda carrega — não mostra nenhum dos dois até
          saber de verdade. */}
      {sandboxStatus?.enabled === true && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] text-emerald-600 bg-emerald-500/10 border-b border-emerald-500/20">
          <ShieldCheck className="w-3 h-3 shrink-0" />
          {m.terminal_sandbox_active()}
        </div>
      )}
      {sandboxStatus?.enabled === false && (
        <div className="flex items-center gap-2 px-3 py-1.5 text-[10px] text-amber-600 bg-amber-500/10 border-b border-amber-500/20">
          <span>{m.terminal_no_sandbox_warning()}</span>
          <button
            type="button"
            className="underline underline-offset-2 hover:text-amber-500 shrink-0"
            onClick={() => setSandboxDialogOpen(true)}
          >
            {m.terminal_sandbox_configure_link()}
          </button>
        </div>
      )}
      {workspace && (
        <SandboxConfigDialog
          workspaceId={workspace.id}
          diagnostic={sandboxStatus?.diagnostic ?? null}
          open={sandboxDialogOpen}
          onOpenChange={setSandboxDialogOpen}
          onInitDone={refetchSandboxStatus}
        />
      )}

      {/* Body — só renderiza o terminal ativo (poupa CPU; estado fica no PTY) */}
      <div className="flex-1 relative">
        {terminals.map((term) => (
          <div
            key={term.id}
            className="absolute inset-0"
            style={{
              visibility: term.id === active?.id ? "visible" : "hidden",
            }}
          >
            <XtermView
              terminalId={term.id}
              threadId={threadId}
              workspaceId={term.workspaceId}
              onClosed={() => close(threadId, term.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
