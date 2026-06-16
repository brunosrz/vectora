"use client";

import { useState } from "react";

import {
  formatTokens,
  usageBarColor,
  usageLevel,
  usageRingColor,
} from "@/lib/utils/usage";
import {
  getContextWindow,
  type ModelOption,
} from "@/lib/config/deployment-config";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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

const RING_RADIUS = 8;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

function UsageRing({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct));
  const offset = RING_CIRCUMFERENCE * (1 - clamped / 100);
  const color = usageRingColor(usageLevel(pct));
  return (
    <svg
      viewBox="0 0 20 20"
      className="h-[18px] w-[18px] -rotate-90"
      aria-hidden
    >
      <circle
        cx="10"
        cy="10"
        r={RING_RADIUS}
        fill="none"
        strokeWidth="2.5"
        stroke="currentColor"
        className="text-muted-foreground/20"
      />
      <circle
        cx="10"
        cy="10"
        r={RING_RADIUS}
        fill="none"
        strokeWidth="2.5"
        strokeLinecap="round"
        stroke="currentColor"
        strokeDasharray={RING_CIRCUMFERENCE}
        strokeDashoffset={offset}
        className={`${color} transition-all duration-300`}
      />
    </svg>
  );
}

export function UsagePopover({ tokensUsed, modelId }: UsagePopoverProps) {
  const contextWindow = getContextWindow(modelId as ModelOption);
  const pct = contextWindow > 0 ? (tokensUsed / contextWindow) * 100 : 0;
  const [open, setOpen] = useState(false);

  const valueLabel = `${formatTokens(tokensUsed)} / ${formatTokens(
    contextWindow,
  )} (${pct.toFixed(0)}%)`;

  return (
    <div className="relative">
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="flex items-center justify-center p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
              aria-haspopup="dialog"
              aria-expanded={open}
              aria-label={`Janela de contexto: ${valueLabel}`}
            >
              <UsageRing pct={pct} />
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="z-[100] font-mono text-xs">
            {valueLabel}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

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
