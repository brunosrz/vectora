"use client";

/**
 * ContextMeter (R5)
 *
 * Rodapé do input com dois indicadores:
 *   - Janela de contexto: tokens estimados da thread vs context_window do modelo
 *   - Uso do plano: requisições consumidas na janela de rate limit (GET /auth/usage)
 */

import { useEffect, useState } from "react";

import { formatTokens } from "@/lib/utils/tokens";
import {
  getContextWindow,
  type ModelOption,
} from "@/lib/config/deployment-config";
import { useT } from "@/lib/i18n";

interface PlanUsage {
  used: number;
  limit: number;
  remaining: number;
  window_seconds: number;
  reset_in_seconds: number;
}

interface ContextMeterProps {
  /** Tokens estimados já usados na thread atual. */
  tokensUsed: number;
  /** Modelo ativo — define o tamanho da janela de contexto. */
  modelId: string;
}

export function ContextMeter({ tokensUsed, modelId }: ContextMeterProps) {
  const t = useT();
  const [usage, setUsage] = useState<PlanUsage | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/usage")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d && typeof d.used === "number") setUsage(d);
      })
      .catch(() => {
        /* silencioso — medidor de plano some se indisponível */
      });
    return () => {
      cancelled = true;
    };
    // Revalida quando a contagem de tokens muda (ou seja, após uma resposta).
  }, [tokensUsed]);

  const window = getContextWindow(modelId as ModelOption);
  const pct = Math.min(100, Math.round((tokensUsed / window) * 100));

  return (
    <div className="flex items-center gap-3 text-[11px] text-muted-foreground/70">
      <span title={t("meter.context_window")}>
        {formatTokens(tokensUsed)} / {formatTokens(window)} ({pct}%)
      </span>
      {usage && (
        <>
          <span className="text-muted-foreground/40">·</span>
          <span title={t("meter.plan_usage")}>
            {usage.used}/{usage.limit} {t("meter.requests")}
            {usage.used > 0 && usage.reset_in_seconds > 0 && (
              <>
                {" "}
                · {t("meter.resets_in")} {Math.ceil(usage.reset_in_seconds)}s
              </>
            )}
          </span>
        </>
      )}
    </div>
  );
}
