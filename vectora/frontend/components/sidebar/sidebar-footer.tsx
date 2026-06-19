"use client";

import { memo } from "react";
import { BookOpen, MessageSquare } from "lucide-react";
import { m } from "@/lib/paraglide/messages";

export const SidebarFooter = memo(function SidebarFooter() {
  return (
    <div className="bg-gradient-to-t from-sidebar-accent/10 via-sidebar-accent/5 to-transparent pt-2 pb-0 space-y-0">
      <a
        href="https://docs.vectora.company"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 px-4 py-2 text-sm text-sidebar-foreground transition-all duration-300 ease-out hover:bg-sidebar-accent/10 group"
      >
        <div className="h-6 w-6 rounded-full bg-sidebar-primary/20 flex items-center justify-center shadow-sm shrink-0">
          <BookOpen className="w-3 h-3 text-sidebar-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium leading-tight transition-colors duration-300 group-hover:text-sidebar-primary/90">
            {m.sidebar_documentation()}
          </div>
          <div className="text-[10px] text-muted-foreground leading-tight transition-colors duration-300 group-hover:text-muted-foreground/80">
            {m.sidebar_documentation_caption()}
          </div>
        </div>
      </a>

      <a
        href="https://vectora.company/issues"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 px-4 py-2 text-sm text-sidebar-foreground transition-all duration-300 ease-out hover:bg-sidebar-accent/10 group"
      >
        <div className="h-6 w-6 rounded-full bg-sidebar-primary/20 flex items-center justify-center shadow-sm shrink-0">
          <MessageSquare className="w-3 h-3 text-sidebar-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium leading-tight transition-colors duration-300 group-hover:text-sidebar-primary/90">
            {m.sidebar_feedback()}
          </div>
          <div className="text-[10px] text-muted-foreground leading-tight transition-colors duration-300 group-hover:text-muted-foreground/80">
            {m.sidebar_report_issue()}
          </div>
        </div>
      </a>
    </div>
  );
});
