"use client";

import Image from "next/image";
import { Menu, Settings } from "lucide-react";

import { ContextualHelp } from "./contextual-help";
import { GitStatusBadge } from "./git-status-badge";
import { UserMenu } from "./user-menu";
import { WorkbenchToggle } from "@/components/workbench/workbench-toggle";
import { Button } from "@/components/ui/button";
import { useSettingsDialogStore } from "@/lib/stores/settings-dialog-store";
import { useT } from "@/lib/i18n";

interface HeaderProps {
  showToolCalls?: boolean;
  onToggleToolCalls?: () => void;
  onShowShortcuts?: () => void;
  onOpenSidebar?: () => void;
}

export function Header({ onShowShortcuts, onOpenSidebar }: HeaderProps) {
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
          <ContextualHelp onShowShortcuts={onShowShortcuts} />
          <UserMenu />
          <WorkbenchToggle />
          <Button
            variant="ghost"
            size="sm"
            className="hover:bg-muted/70 hover:text-foreground"
            aria-label={t("settings.chat.tooltip")}
            title={t("settings.chat.tooltip")}
            onClick={() =>
              useSettingsDialogStore.getState().openAt("preferencias")
            }
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
