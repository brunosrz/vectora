"use client";

import { memo } from "react";
import { BookOpen, MessageSquare } from "lucide-react";
import { m } from "@/lib/paraglide/messages";

export const SidebarFooter = memo(function SidebarFooter() {
  return (
    <div className="bg-gradient-to-t from-sidebar-accent/10 via-sidebar-accent/5 to-transparent pt-1.5 pb-0">
      <div className="flex items-center gap-1 px-3 py-1.5">
        <a
          href="https://docs.vectora.company"
          target="_blank"
          rel="noopener noreferrer"
          title={m.sidebar_documentation()}
          className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/20 transition-colors duration-150"
        >
          <BookOpen className="w-3.5 h-3.5" />
        </a>
        <a
          href="https://vectora.company/issues"
          target="_blank"
          rel="noopener noreferrer"
          title={m.sidebar_feedback()}
          className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/20 transition-colors duration-150"
        >
          <MessageSquare className="w-3.5 h-3.5" />
        </a>
      </div>
    </div>
  );
});
