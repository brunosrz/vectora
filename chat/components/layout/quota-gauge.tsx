"use client";

/**
 * QuotaGauge — indicador compacto de uso de requisições no header.
 *
 * Mostra progresso da janela de 5 horas (a mais relevante para o usuário).
 * Verde < 60 %, âmbar 60–85 %, vermelho > 85 %. Tooltip com detalhe semanal
 * e tempo até reset. Oculto quando o backend não retorna dados de quota.
 */

import { useQuery } from "@tanstack/react-query";
import { useT } from "@/lib/i18n";
import { getAuthUsage, type AuthUsage } from "@/lib/api/vectora-client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(used: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

function gaugeColor(p: number): string {
  if (p >= 85) return "bg-destructive";
  if (p >= 60) return "bg-amber-500";
  return "bg-emerald-500";
}

function fmtReset(seconds: number): string {
  if (seconds <= 0) return "agora";
  const m = Math.ceil(seconds / 60);
  if (m < 60) return `${m}min`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h${rm}min` : `${h}h`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function QuotaGauge() {
  const t = useT();

  const { data } = useQuery<AuthUsage>({
    queryKey: ["auth-usage"],
    queryFn: getAuthUsage,
    staleTime: 60_000,
    retry: false,
  });

  if (!data) return null;

  const fh = data.five_hour;
  const wk = data.weekly;
  const p = pct(fh.used, fh.limit);
  const color = gaugeColor(p);
  const resetLabel = fmtReset(fh.reset_in_seconds);

  const tooltipLines = [
    `${t("quota.five_hour")}: ${fh.used}/${fh.limit} (reset em ${resetLabel})`,
    `${t("quota.weekly")}: ${wk.used}/${wk.limit}`,
  ].join("\n");

  return (
    <div
      className="flex items-center gap-1.5 cursor-default"
      title={tooltipLines}
      aria-label={`${t("quota.five_hour")}: ${p}%`}
    >
      {/* Barra compacta */}
      <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${p}%` }}
        />
      </div>
      {/* Texto percentual */}
      <span
        className={`text-[10px] tabular-nums leading-none ${
          p >= 85
            ? "text-destructive"
            : p >= 60
              ? "text-amber-500"
              : "text-muted-foreground/70"
        }`}
      >
        {p}%
      </span>
    </div>
  );
}
