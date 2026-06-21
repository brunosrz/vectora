"use client";

import { memo } from "react";
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
    <div className="px-3 py-1.5">
      <button
        onClick={onClick}
        disabled={offline}
        aria-label={label}
        className={`group w-full h-10 inline-flex items-center ${sidebarOnRight ? "justify-end" : "justify-start"} gap-2 pl-3 pr-3 bg-muted/30 hover:bg-muted/60 border border-border/50 hover:border-border/80 rounded-lg text-sm font-medium text-foreground/80 hover:text-foreground transition-colors duration-150 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`shrink-0 text-muted-foreground ${sidebarOnRight ? "order-last" : ""}`}
        >
          <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        </svg>
        {m.sidebar_new_chat()}
      </button>
    </div>
  );
});
