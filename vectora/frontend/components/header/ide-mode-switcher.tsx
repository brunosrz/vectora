"use client";

import { MessageSquare, Code2 } from "lucide-react";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { m } from "@/lib/paraglide/messages";

export function IdeModeSwitch() {
  const chatMode = useSettingsStore((s) => s.chatMode);
  const ideMode = useSettingsStore((s) => s.ideMode);
  const setIdeMode = useSettingsStore((s) => s.setIdeMode);

  if (chatMode) return null;

  return (
    <div
      role="group"
      aria-label={m.ide_mode_switcher_label()}
      className="flex rounded-lg border border-border/40 overflow-hidden"
    >
      <button
        type="button"
        onClick={() => {
          if (ideMode) setIdeMode(false);
        }}
        aria-pressed={!ideMode}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
          !ideMode
            ? "bg-muted text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
        }`}
      >
        <MessageSquare className="w-3.5 h-3.5" />
        {m.ide_mode_assistente()}
      </button>
      <div className="w-px bg-border/40 self-stretch" />
      <button
        type="button"
        onClick={() => {
          if (!ideMode) setIdeMode(true);
        }}
        aria-pressed={ideMode}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
          ideMode
            ? "bg-muted text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
        }`}
      >
        <Code2 className="w-3.5 h-3.5" />
        {m.ide_mode_ide()}
      </button>
    </div>
  );
}
