"use client";

import { useState } from "react";

import { formatTokens, usageBarColor, usageLevel } from "@/lib/utils/usage";
import {
  getContextWindow,
  type ModelOption,
} from "@/lib/config/deployment-config";

interface UsagePopoverProps {
  tokensUsed: number;
  modelId: string;
}

function UsageBar({ pct }: { pct: number }) {
  const color = usageBarColor(usageLevel(pct));
  return (
    <div className="h-1 rounded-full bg-muted/60 overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-300`}
        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
      />
    </div>
  );
}

export function UsagePopover({ tokensUsed, modelId }: UsagePopoverProps) {
  const contextWindow = getContextWindow(modelId as ModelOption);
  const pct = contextWindow > 0 ? (tokensUsed / contextWindow) * 100 : 0;
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-muted/40 font-mono"
        aria-haspopup="dialog"
        aria-expanded={open}
        title="Janela de contexto"
      >
        {formatTokens(tokensUsed)}/{formatTokens(contextWindow)} (
        {pct.toFixed(0)}%)
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            role="dialog"
            className="absolute right-0 bottom-full mb-2 z-50 w-72 rounded-lg border border-border/60 bg-background shadow-xl p-3 space-y-2"
          >
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Janela de contexto</span>
              <span className="font-mono text-foreground/90">
                {formatTokens(tokensUsed)} / {formatTokens(contextWindow)} (
                {pct.toFixed(0)}%)
              </span>
            </div>
            <UsageBar pct={pct} />
            <p className="text-[11px] text-muted-foreground pt-1">{modelId}</p>
          </div>
        </>
      )}
    </div>
  );
}
