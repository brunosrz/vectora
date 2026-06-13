"use client";

/**
 * Renderiza a fila do `toast-store`. Montado uma vez em `__root.tsx` no
 * topo da árvore. Lê o store, renderiza cards no canto superior-direito
 * (mobile: topo full-width) e dispara `dismiss(id)` quando `duration`
 * expira (se setado) ou quando o usuário clica em `×`.
 *
 * Acessibilidade:
 *   - `role="status"` + `aria-live="polite"` para success/info
 *   - `role="alert"` + `aria-live="assertive"` para warning/error
 */

import { useEffect } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  X,
} from "lucide-react";
import {
  useToastStore,
  type Toast,
  type ToastLevel,
} from "@/lib/stores/toast-store";

const ICONS: Record<ToastLevel, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: AlertCircle,
  info: Info,
};

// Texto escuro no tema claro / claro no tema escuro — texto fixo claro
// (ex.: `text-emerald-100`) ficava ilegível sobre o fundo claro de `.light`.
const LEVEL_STYLES: Record<ToastLevel, { wrapper: string; icon: string }> = {
  success: {
    wrapper:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
    icon: "text-emerald-600 dark:text-emerald-400",
  },
  warning: {
    wrapper:
      "border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-100",
    icon: "text-amber-600 dark:text-amber-400",
  },
  error: {
    wrapper: "border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-100",
    icon: "text-red-600 dark:text-red-400",
  },
  info: {
    wrapper:
      "border-blue-500/30 bg-blue-500/10 text-blue-900 dark:text-blue-100",
    icon: "text-blue-600 dark:text-blue-400",
  },
};

function ToastCard({ toast }: { toast: Toast }) {
  const dismiss = useToastStore((s) => s.dismiss);
  const Icon = ICONS[toast.level];
  const styles = LEVEL_STYLES[toast.level];
  const role =
    toast.level === "error" || toast.level === "warning" ? "alert" : "status";
  const live = role === "alert" ? "assertive" : "polite";

  useEffect(() => {
    if (toast.duration === null || toast.duration === undefined) return;
    const timer = window.setTimeout(() => dismiss(toast.id), toast.duration);
    return () => window.clearTimeout(timer);
  }, [toast.duration, toast.id, dismiss]);

  return (
    <div
      role={role}
      aria-live={live}
      data-toast-level={toast.level}
      data-toast-id={toast.id}
      className={`pointer-events-auto relative w-full max-w-sm rounded-lg border px-4 py-3 shadow-lg backdrop-blur-sm ${styles.wrapper}`}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={`mt-0.5 h-4 w-4 shrink-0 ${styles.icon}`}
          aria-hidden
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium leading-tight">{toast.title}</p>
          {toast.description ? (
            <p className="mt-1 text-xs opacity-80 leading-relaxed">
              {toast.description}
            </p>
          ) : null}
          {toast.action ? (
            <button
              type="button"
              onClick={() => {
                void toast.action!.onClick();
                dismiss(toast.id);
              }}
              className="mt-2 text-xs font-medium underline underline-offset-2 hover:no-underline"
            >
              {toast.action.label}
            </button>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => dismiss(toast.id)}
          aria-label="Fechar notificação"
          className="absolute right-2 top-2 rounded p-1 opacity-60 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-current"
        >
          <X className="h-3 w-3" aria-hidden />
        </button>
      </div>
    </div>
  );
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notificações"
      className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex flex-col items-center gap-2 px-4 sm:right-4 sm:left-auto sm:items-end"
    >
      {toasts.map((t) => (
        <ToastCard key={t.id} toast={t} />
      ))}
    </div>
  );
}
