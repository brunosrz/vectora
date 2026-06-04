/**
 * Banner único de licença que aparece abaixo do header.
 *
 * Estados visuais derivados de ``GET /license/status``:
 * - **laranja** — sem token configurado ou pagamento em atraso (`past_due`).
 * - **amarelo** — trial expira em ≤7 dias.
 * - **vermelho** — licença expirada/revogada (bloqueia input no chat
 *   via prop `onBlockingChange`).
 * - **oculto** — licença ativa e fora da janela de aviso.
 *
 * Click em "Configurar" abre Settings → Administração → Configurações;
 * "Renovar"/"Assinar" abre o Customer Portal via ``POST /license/portal``
 * em nova aba (web) ou ``window.vectora.openExternal`` (desktop Electron).
 */

import { useEffect, useState } from "react";
import { AlertTriangle, Clock, ShieldAlert, X } from "lucide-react";

import { useT } from "@/lib/i18n";
import { useLicenseStatus } from "@/lib/hooks/use-license-status";
import { useSettingsDialogStore } from "@/lib/stores/settings-dialog-store";

interface LicenseBannerProps {
  /** Se true, banner ocupa toda a largura abaixo do header. */
  fullWidth?: boolean;
  /** Notifica o pai quando o banner está em estado bloqueante (vermelho). */
  onBlockingChange?: (blocking: boolean) => void;
}

type Severity = "warning" | "danger" | "critical" | null;

interface BannerSpec {
  severity: Severity;
  icon: typeof AlertTriangle;
  message: string;
  cta: { label: string; action: "configure" | "portal" } | null;
}

const TRIAL_WARN_DAYS = 7;

export function LicenseBanner({
  fullWidth = true,
  onBlockingChange,
}: LicenseBannerProps) {
  const t = useT();
  const { status } = useLicenseStatus();
  const openSettings = useSettingsDialogStore((s) => s.openAt);
  const [dismissed, setDismissed] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  const spec = computeSpec(status, t);

  useEffect(() => {
    onBlockingChange?.(spec.severity === "critical");
  }, [spec.severity, onBlockingChange]);

  if (!spec.severity || dismissed) return null;

  async function handlePortal() {
    if (portalLoading) return;
    setPortalLoading(true);
    try {
      const res = await fetch("/license/portal", { method: "POST" });
      if (!res.ok) {
        // Sem assinatura ativa → manda pro site de pricing.
        void openUrl("https://vectora.company/pricing");
        return;
      }
      const data = (await res.json()) as { url?: string };
      if (data.url) void openUrl(data.url);
    } finally {
      setPortalLoading(false);
    }
  }

  const Icon = spec.icon;
  const colorClass = SEVERITY_COLORS[spec.severity];

  return (
    <div
      role="status"
      className={`${colorClass} ${fullWidth ? "w-full" : ""} px-4 py-2 text-xs flex items-center gap-2 border-b`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="flex-1 min-w-0">{spec.message}</span>
      {spec.cta && (
        <button
          type="button"
          onClick={
            spec.cta.action === "configure"
              ? () => openSettings("admin", "config")
              : handlePortal
          }
          disabled={portalLoading}
          className="ml-2 px-2 py-0.5 rounded border border-current/40 hover:bg-current/10 transition-colors disabled:opacity-50"
        >
          {portalLoading ? "…" : spec.cta.label}
        </button>
      )}
      {spec.severity !== "critical" && (
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label={t("license.dismiss")}
          className="ml-1 p-0.5 rounded hover:bg-current/10"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

const SEVERITY_COLORS: Record<Exclude<Severity, null>, string> = {
  warning:
    "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
  danger:
    "bg-orange-500/15 text-orange-700 dark:text-orange-300 border-orange-500/30",
  critical: "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30",
};

function openUrl(url: string): Promise<void> {
  if (typeof window !== "undefined" && window.vectora?.openExternal) {
    return window.vectora.openExternal(url);
  }
  window.open(url, "_blank", "noopener,noreferrer");
  return Promise.resolve();
}

function computeSpec(
  status: ReturnType<typeof useLicenseStatus>["status"],
  t: ReturnType<typeof useT>,
): BannerSpec {
  if (!status || status.status === "offline") {
    return { severity: null, icon: AlertTriangle, message: "", cta: null };
  }
  if (!status.configured) {
    return {
      severity: "danger",
      icon: AlertTriangle,
      message: t("license.banner.unconfigured"),
      cta: { label: t("license.banner.configure"), action: "configure" },
    };
  }
  if (status.status === "expired" || status.status === "revoked") {
    return {
      severity: "critical",
      icon: ShieldAlert,
      message: t("license.banner.expired"),
      cta: { label: t("license.banner.renew"), action: "portal" },
    };
  }
  if (status.status === "past_due") {
    return {
      severity: "danger",
      icon: AlertTriangle,
      message: t("license.banner.past_due"),
      cta: { label: t("license.banner.manage"), action: "portal" },
    };
  }
  if (
    (status.status === "trial" || status.status === "trialing") &&
    status.days_remaining <= TRIAL_WARN_DAYS
  ) {
    return {
      severity: "warning",
      icon: Clock,
      message: t("license.banner.trial_ending", {
        n: status.days_remaining,
      }),
      cta: { label: t("license.banner.subscribe"), action: "portal" },
    };
  }
  return { severity: null, icon: AlertTriangle, message: "", cta: null };
}
