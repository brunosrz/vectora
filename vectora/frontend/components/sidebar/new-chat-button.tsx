"use client";

import { memo } from "react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useNetworkStatus } from "@/lib/hooks/use-network-status";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { m } from "@/lib/paraglide/messages";

interface NewChatButtonProps {
  onClick: () => void;
}

export const NewChatButton = memo(function NewChatButton({
  onClick,
}: NewChatButtonProps) {
  const { offline } = useNetworkStatus();
  const sidebarOnRight = useSettingsStore((s) => s.sidebarPosition === "right");
  const label = offline ? m.network_disabled_offline() : m.sidebar_new_chat();

  return (
    <div className="px-3 pt-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            disabled={offline}
            aria-label={label}
            className={`group w-full inline-flex items-center ${sidebarOnRight ? "justify-end" : "justify-start"} gap-2 px-3 py-2 bg-gradient-to-r from-primary/15 to-primary/5 hover:from-primary/25 hover:to-primary/10 border border-primary/30 hover:border-primary/50 rounded-md text-sm font-medium text-foreground/90 hover:text-foreground transition-all duration-200 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-primary/15 disabled:hover:to-primary/5 disabled:hover:border-primary/30`}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`text-primary ${sidebarOnRight ? "order-last" : ""}`}
            >
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
            </svg>
            {m.sidebar_new_chat()}
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">{label}</TooltipContent>
      </Tooltip>
    </div>
  );
});
