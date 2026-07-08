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
    // h-16: mesma altura fixa do header principal (components/header/header.tsx)
    // — com padding em vez de altura fixa, a linha divisória desalinhava
    // entre sidebar e área principal quando a sidebar estava expandida.
    <div className="h-16 px-2 flex items-center border-b border-border/40">
      <div className="flex items-center justify-between w-full">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              aria-label={m.sidebar_collapse()}
              className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors duration-150 rounded-md"
            >
              <PanelLeftClose className="w-4 h-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">{m.sidebar_collapse()}</TooltipContent>
        </Tooltip>

        <span className="text-xs font-medium text-muted-foreground/70 uppercase tracking-widest select-none">
          {m.sidebar_title()}
        </span>

        <div className="w-7" />
      </div>
    </div>
  );
});
