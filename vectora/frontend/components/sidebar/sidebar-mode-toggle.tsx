"use client";

import { memo } from "react";
import { LayoutDashboard, MessageSquare } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { m } from "@/lib/paraglide/messages";

export const SidebarModeToggle = memo(function SidebarModeToggle() {
  const chatMode = useSettingsStore((s) => s.chatMode);
  const setChatMode = useSettingsStore((s) => s.setChatMode);

  return (
    <div className="px-3 pb-1.5">
      <div className="flex rounded-lg border border-border/40 overflow-hidden">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => setChatMode(false)}
              aria-pressed={!chatMode}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium transition-colors duration-150 ${
                !chatMode
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5 shrink-0" />
              {m.mode_dev()}
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{m.chat_mode_disable()}</TooltipContent>
        </Tooltip>

        <div className="w-px bg-border/40 self-stretch" />

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => setChatMode(true)}
              aria-pressed={chatMode}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium transition-colors duration-150 ${
                chatMode
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 shrink-0" />
              {m.mode_chat()}
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{m.chat_mode_enable()}</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
});
