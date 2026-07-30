"use client";

import { Bot, Code2 } from "lucide-react";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { m } from "@/lib/paraglide/messages";

interface IdeModeProps {
  show?: boolean;
}

export function IdeModeSwitch({ show = false }: IdeModeProps) {
  const uiMode = useSettingsStore((s) => s.uiMode);
  const setUiMode = useSettingsStore((s) => s.setUiMode);

  if (!show) return null;

  return (
    <div
      role="group"
      aria-label={m.ide_mode_switcher_label()}
      className="flex rounded-lg border border-border/40 overflow-hidden"
    >
      <button
        type="button"
        onClick={() => {
          if (uiMode !== "assistant") setUiMode("assistant");
        }}
        aria-pressed={uiMode === "assistant"}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
          uiMode === "assistant"
            ? "bg-muted text-foreground font-medium"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
        }`}
      >
        <Bot className="w-3.5 h-3.5" />
        {m.ide_mode_assistente()}
      </button>
      <div className="w-px bg-border/40 self-stretch" />
      <button
        type="button"
        onClick={() => {
          if (uiMode !== "ide") setUiMode("ide");
        }}
        aria-pressed={uiMode === "ide"}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors ${
          uiMode === "ide"
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
