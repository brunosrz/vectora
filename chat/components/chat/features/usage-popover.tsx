"use client";

/**
 * UsagePopover (K.2.2)
 *
 * Painel flutuante no estilo Claude Code com três medidores: janela de
 * contexto da thread, limite de 5 horas e janela semanal. O trigger é o
 * próprio componente — um chip clicável que mostra contexto+semanal a
 * relance e abre o popover ao clique.
 */

import { useEffect, useState, useCallback } from "react";

import {
  formatTokens,
  formatResetIn,
  usageLevel,
  usageBarColor,
} from "@/lib/utils/usage";
import {
  getContextWindow,
  type ModelOption,
} from "@/lib/config/deployment-config";

interface PlanWindow {
  used: number;
  limit: number;
  remaining: number;
  window_seconds: number;
  reset_in_seconds: number;
}

interface UsageResponse extends PlanWindow {
  five_hour: PlanWindow;
  weekly: PlanWindow;
}

interface UsagePopoverProps {
  tokensUsed: number;
  modelId: string;
}

function UsageBar({ pct }: { pct: number }) {
  const level = usageLevel(pct);
  const color = usageBarColor(level);
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
  const ctxPct = contextWindow > 0 ? (tokensUsed / contextWindow) * 100 : 0;

  const [data, setData] = useState<UsageResponse | null>(null);
  const [open, setOpen] = useState(false);

  const refetch = useCallback(() => {
    fetch("/api/auth/usage")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && typeof d.used === "number") {
          setData(d as UsageResponse);
        }
      })
      .catch(() => {
        /* silencioso — usuário não-autenticado fica sem dados */
      });
  }, []);

  useEffect(() => {
    refetch();
    const id = setInterval(refetch, 30_000);
    return () => clearInterval(id);
  }, [refetch]);

  // Revalida ao reabrir o popover — feedback imediato pós-mensagem.
  useEffect(() => {
    if (open) refetch();
  }, [open, refetch]);

  const fiveHour = data?.five_hour;
  const weekly = data?.weekly;
  const weeklyPct =
    weekly && weekly.limit > 0 ? (weekly.used / weekly.limit) * 100 : 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-muted/40"
        aria-haspopup="dialog"
        aria-expanded={open}
        title="Uso do plano e janela de contexto"
      >
        <span className="font-mono">
          {formatTokens(tokensUsed)}/{formatTokens(contextWindow)} (
          {ctxPct.toFixed(0)}%)
        </span>
        {weekly && (
          <>
            <span className="mx-1.5 opacity-50">·</span>
            <span className="font-mono">{weeklyPct.toFixed(0)}%w</span>
          </>
        )}
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
            className="absolute right-0 bottom-full mb-2 z-50 w-72 rounded-lg border border-border/60 bg-background shadow-xl p-3 space-y-3"
          >
            {/* Janela de contexto */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Janela de contexto
                </span>
                <span className="font-mono text-foreground/90">
                  {formatTokens(tokensUsed)} / {formatTokens(contextWindow)} (
                  {ctxPct.toFixed(0)}%)
                </span>
              </div>
              <UsageBar pct={ctxPct} />
            </div>

            <div className="border-t border-border/40" />

            {/* Uso do plano */}
            <div className="text-xs text-muted-foreground">Uso do plano</div>

            {fiveHour && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground/80">Limite de 5 horas</span>
                  <span className="font-mono text-foreground/90">
                    {Math.round(
                      (fiveHour.used / Math.max(1, fiveHour.limit)) * 100,
                    )}
                    %
                  </span>
                </div>
                <UsageBar
                  pct={(fiveHour.used / Math.max(1, fiveHour.limit)) * 100}
                />
              </div>
            )}

            {weekly && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground/80">
                    Semanal · todos os modelos
                  </span>
                  <span className="font-mono text-foreground/90">
                    {weeklyPct.toFixed(0)}% · reinicia{" "}
                    {formatResetIn(weekly.reset_in_seconds)}
                  </span>
                </div>
                <UsageBar pct={weeklyPct} />
              </div>
            )}

            {!data && (
              <div className="text-[11px] text-muted-foreground italic">
                Carregando uso…
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
