"use client";

/**
 * ContextualHelp — Botão "?" com dicas adaptadas ao estado do workspace.
 *
 * Renderiza um DropdownMenu com até 5 dicas rápidas baseadas no contexto:
 *   - Sem workspace → como adicionar uma pasta
 *   - Com workspace sem git → sugestão de git init
 *   - Com workspace git → dicas do workbench (diff, log, stash)
 *   - Sempre: link para os atalhos de teclado
 */

import { HelpCircle } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";

interface ContextualHelpProps {
  onShowShortcuts?: () => void;
}

export function ContextualHelp({ onShowShortcuts }: ContextualHelpProps) {
  const t = useT();
  const activeId = useWorkspacesStore((s) => s.active_id);
  const workspaces = useWorkspacesStore((s) => s.workspaces);
  const active = workspaces.find((w) => w.id === activeId);

  const hasWorkspace = !!active;
  const isGit = active?.is_git_repo ?? false;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={t("help.title")}
          className="inline-flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="text-xs font-semibold text-muted-foreground">
          {t("help.title")}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Tips — pointer-events-none so they're read-only */}
        {!hasWorkspace && (
          <DropdownMenuItem className="pointer-events-none text-xs text-foreground/80 whitespace-normal py-2">
            💡 {t("help.tip_no_workspace")}
          </DropdownMenuItem>
        )}

        {hasWorkspace && !isGit && (
          <DropdownMenuItem className="pointer-events-none text-xs text-foreground/80 whitespace-normal py-2">
            📁 {t("help.tip_no_git")}
          </DropdownMenuItem>
        )}

        {hasWorkspace && isGit && (
          <>
            <DropdownMenuItem className="pointer-events-none text-xs text-foreground/80 whitespace-normal py-2">
              🌿 {t("help.tip_git_diff")}
            </DropdownMenuItem>
            <DropdownMenuItem className="pointer-events-none text-xs text-foreground/80 whitespace-normal py-2">
              📦 {t("help.tip_git_stash")}
            </DropdownMenuItem>
          </>
        )}

        <DropdownMenuItem className="pointer-events-none text-xs text-foreground/80 whitespace-normal py-2">
          💬 {t("help.tip_slash_commands")}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={onShowShortcuts}
          className="text-xs cursor-pointer"
        >
          ⌨️ {t("help.view_shortcuts")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
