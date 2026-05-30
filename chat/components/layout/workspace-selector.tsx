"use client";

/**
 * WorkspaceSelector (Q6)
 *
 * Chip de pasta no header. Mostra o workspace ativo e, ao clicar, abre um
 * dropdown com a lista de workspaces conhecidos (com indicador de confiança)
 * e a opção de adicionar uma nova pasta via trust dialog.
 */

import { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  FolderGit2,
  FolderOpen,
  Plus,
  ShieldCheck,
} from "lucide-react";

import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";
import { WorkspaceTrustDialog } from "./workspace-trust-dialog";

export function WorkspaceSelector() {
  const t = useT();
  const workspaces = useWorkspacesStore((s) => s.workspaces);
  const activeId = useWorkspacesStore((s) => s.active_id);
  const hydrate = useWorkspacesStore((s) => s.hydrate);
  const setActive = useWorkspacesStore((s) => s.setActive);

  const [open, setOpen] = useState(false);
  const [trustOpen, setTrustOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Hidrata no boot
  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  // Fecha ao clicar fora
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const active =
    workspaces.find((w) => w.id === activeId) ?? workspaces[0] ?? null;

  return (
    <>
      <div className="relative" ref={ref}>
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm text-foreground/80 hover:text-foreground hover:bg-muted/50 transition-colors select-none max-w-[200px]"
          title={active?.cwd ?? t("workspace.select_title")}
          aria-expanded={open}
        >
          {active?.is_git_repo ? (
            <FolderGit2 className="w-4 h-4 shrink-0 text-primary" />
          ) : (
            <FolderOpen className="w-4 h-4 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate font-medium">
            {active?.name ?? t("workspace.add_folder")}
          </span>
          <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        </button>

        {open && (
          <div className="absolute left-0 top-10 z-50 w-72 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-top-2">
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t("workspace.select_title")}
            </div>

            <div className="max-h-72 overflow-y-auto">
              {workspaces.length === 0 && (
                <p className="px-3 py-2 text-sm text-muted-foreground">
                  {t("workspace.no_workspaces")}
                </p>
              )}

              {workspaces.map((w) => (
                <button
                  key={w.id}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent text-left transition-colors"
                  onClick={() => {
                    void setActive(w.id);
                    setOpen(false);
                  }}
                >
                  {w.id === active?.id ? (
                    <Check className="w-4 h-4 shrink-0 text-primary" />
                  ) : w.is_git_repo ? (
                    <FolderGit2 className="w-4 h-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FolderOpen className="w-4 h-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-foreground">
                      {w.name}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground font-mono">
                      {w.cwd}
                    </span>
                  </span>
                  {w.trusted ? (
                    <span
                      className="flex items-center gap-1 text-xs text-green-500 shrink-0"
                      title={t("workspace.trusted")}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground shrink-0">
                      {t("workspace.untrusted")}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="border-t border-border/60 mt-1 pt-1">
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
                onClick={() => {
                  setOpen(false);
                  setTrustOpen(true);
                }}
              >
                <Plus className="w-4 h-4 shrink-0 text-muted-foreground" />
                {t("workspace.add_folder")}
              </button>
            </div>
          </div>
        )}
      </div>

      <WorkspaceTrustDialog open={trustOpen} onOpenChange={setTrustOpen} />
    </>
  );
}
