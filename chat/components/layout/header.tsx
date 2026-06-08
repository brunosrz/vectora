"use client";

import Image from "next/image";
import { Menu } from "lucide-react";

import { AgentSettings, type AgentConfig } from "./agent-settings";
import { GitStatusBadge } from "./git-status-badge";
import { UserMenu } from "./user-menu";
import { WorkbenchToggle } from "@/components/workbench/workbench-toggle";
import { useT } from "@/lib/i18n";

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
          <UserMenu />
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
