"use client";

import { memo } from "react";
import { BookOpen, Flag } from "lucide-react";
import { m } from "@/lib/paraglide/messages";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { useHydrated } from "@/lib/hooks/use-hydrated";

const LABEL_THRESHOLD = 200;

export const SidebarFooter = memo(function SidebarFooter() {
  const sidebarWidth = useSettingsStore((s) => s.sidebarWidth);
  const hydrated = useHydrated();
  const showLabel = hydrated && sidebarWidth >= LABEL_THRESHOLD;

  return (
    <div className="bg-gradient-to-t from-sidebar-accent/10 via-sidebar-accent/5 to-transparent pt-1.5 pb-0">
      <div className="flex items-center gap-1 px-2 py-1.5">
        <a
          href="https://docs.vectora.company"
          target="_blank"
          rel="noopener noreferrer"
          title={m.sidebar_documentation()}
          className="flex-1 min-w-0 flex items-center gap-1.5 px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/20 transition-colors duration-150"
        >
          <BookOpen className="w-3.5 h-3.5 shrink-0" />
          {showLabel && (
            <span className="text-xs truncate">{m.sidebar_docs()}</span>
          )}
        </a>
        <a
          href="https://vectora.company/issues"
          target="_blank"
          rel="noopener noreferrer"
          title={m.sidebar_feedback()}
          className="flex-1 min-w-0 flex items-center gap-1.5 px-2 py-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/20 transition-colors duration-150"
        >
          <Flag className="w-3.5 h-3.5 shrink-0" />
          {showLabel && (
            <span className="text-xs truncate">{m.sidebar_feedback()}</span>
          )}
        </a>
      </div>
    </div>
  );
});
