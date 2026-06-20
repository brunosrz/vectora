"use client";

import { memo } from "react";
import { PanelLeftClose } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { NewChatButton } from "./new-chat-button";
import { m } from "@/lib/paraglide/messages";

interface SidebarHeaderProps {
  onToggle: () => void;
  onNewChat?: () => void;
}

export const SidebarHeader = memo(function SidebarHeader({
  onToggle,
  onNewChat,
}: SidebarHeaderProps) {
  return (
    <div className="px-2 pt-2 pb-2 border-b border-border/40">
      <div className="flex items-center justify-between">
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

        {onNewChat ? (
          <NewChatButton onClick={onNewChat} />
        ) : (
          <div className="w-7" />
        )}
      </div>
    </div>
  );
});
