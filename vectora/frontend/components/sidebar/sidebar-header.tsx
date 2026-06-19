"use client";

import { memo } from "react";
import { PanelLeftClose } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { m } from "@/lib/paraglide/messages";

interface SidebarHeaderProps {
  onToggle: () => void;
}

export const SidebarHeader = memo(function SidebarHeader({
  onToggle,
}: SidebarHeaderProps) {
  return (
    <div className="px-3 pt-[13px] pb-[14px] border-b border-border/60 bg-gradient-to-r from-sidebar-accent/20 via-sidebar-accent/10 to-transparent">
      <div className="flex items-center justify-between">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              aria-label={m.sidebar_collapse()}
              className="hover:bg-sidebar-primary/10 hover:text-sidebar-primary transition-all duration-200 shadow-depth-xs hover:shadow-depth-hover rounded-lg"
            >
              <PanelLeftClose className="w-5 h-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">{m.sidebar_collapse()}</TooltipContent>
        </Tooltip>
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          {m.sidebar_title()}
        </span>
      </div>
    </div>
  );
});
