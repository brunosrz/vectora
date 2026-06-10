"use client";

import Image from "next/image";
import { ExternalLink, Menu } from "lucide-react";
import { useCallback, useState } from "react";

import { AgentSettings, type AgentConfig } from "./agent-settings";
import { ContextualHelp } from "./contextual-help";
import { GitStatusBadge } from "./git-status-badge";
import { QuotaGauge } from "./quota-gauge";
import { UserMenu } from "./user-menu";
import { WorkbenchToggle } from "@/components/workbench/workbench-toggle";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";

interface VscodeOption {
  strategy: string;
  label: string;
  url: string;
}

/** Botão "Abrir no VS Code" — opções dependem do workspace ativo (Bloco I.6/A.x). */
function VscodeMenu({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<VscodeOption[]>([]);

  const handleOpen = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(
      `/workspaces/${encodeURIComponent(workspaceId)}/vscode-options`,
    );
    if (res.ok) {
      const data = await res.json();
      setOptions((data.options as VscodeOption[]) ?? []);
    }
    setOpen((v) => !v);
  }, [workspaceId]);

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
        title={t("workbench.open_vscode")}
        aria-label={t("workbench.open_vscode")}
      >
        <ExternalLink className="w-4 h-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-popover border border-border/60 rounded-md shadow-lg py-1 min-w-[200px]">
            {options.length === 0 ? (
              <p className="px-3 py-1.5 text-xs text-muted-foreground">
                {t("workbench.open_vscode_unavailable")}
              </p>
            ) : (
              options.map((opt) => (
                <a
                  key={opt.strategy}
                  href={opt.url}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-muted/40 transition-colors"
                >
                  <ExternalLink className="w-3 h-3 text-muted-foreground shrink-0" />
                  {opt.label}
                </a>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

interface HeaderProps {
  showToolCalls?: boolean;
  onToggleToolCalls?: () => void;
  agentConfig?: AgentConfig;
  onAgentConfigChange?: (config: AgentConfig) => void;
  onShowShortcuts?: () => void;
  forceShowTooltip?: number;
  showSettingsDialog?: boolean;
  onSettingsDialogChange?: (open: boolean) => void;
  onOpenSidebar?: () => void;
}

export function Header({
  agentConfig,
  onAgentConfigChange,
  onShowShortcuts,
  forceShowTooltip,
  showSettingsDialog,
  onSettingsDialogChange,
  onOpenSidebar,
}: HeaderProps) {
  const t = useT();
  const wsId = useWorkspacesStore((s) => s.getActive())?.id ?? "";
  return (
    <header className="border-b border-border/60 bg-background h-16 flex items-center">
      <div className="flex items-center justify-between w-full px-4 sm:px-6">
        <div className="flex items-center gap-2">
          {/* Hamburger só em mobile — reabre o sidebar como overlay. */}
          {onOpenSidebar && (
            <button
              type="button"
              onClick={onOpenSidebar}
              aria-label={t("sidebar.open")}
              className="md:hidden -ml-1 mr-1 inline-flex items-center justify-center w-10 h-10 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          <Image
            src="/vectora.svg"
            alt="Vectora"
            width={28}
            height={28}
            priority
            className="h-7 w-7"
          />
          <span
            className="text-xl font-semibold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-aeonik-mono)" }}
          >
            Vectora
          </span>
        </div>

        <div className="flex items-center gap-3">
          <GitStatusBadge />
          <QuotaGauge />
          <ContextualHelp onShowShortcuts={onShowShortcuts} />
          <UserMenu />
          {wsId && <VscodeMenu workspaceId={wsId} />}
          <WorkbenchToggle />
          {agentConfig && onAgentConfigChange && (
            <AgentSettings
              config={agentConfig}
              onConfigChange={onAgentConfigChange}
              onShowShortcuts={onShowShortcuts}
              forceShowTooltip={forceShowTooltip}
              open={showSettingsDialog}
              onOpenChange={onSettingsDialogChange}
            />
          )}
        </div>
      </div>
    </header>
  );
}
