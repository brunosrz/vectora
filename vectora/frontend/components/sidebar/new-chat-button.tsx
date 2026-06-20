"use client";

import { memo } from "react";
import { SquarePen } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useNetworkStatus } from "@/lib/hooks/use-network-status";
import { m } from "@/lib/paraglide/messages";

interface NewChatButtonProps {
  onClick: () => void;
}

export const NewChatButton = memo(function NewChatButton({
  onClick,
}: NewChatButtonProps) {
  const { offline } = useNetworkStatus();
  const label = offline ? m.network_disabled_offline() : m.sidebar_new_chat();

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          disabled={offline}
          aria-label={label}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <SquarePen className="w-4 h-4" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom">{label}</TooltipContent>
    </Tooltip>
  );
});
