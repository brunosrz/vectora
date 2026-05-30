"use client";

/**
 * PermissionModeMenu (R2)
 *
 * Chip + dropdown com os 5 modos de permissão. A escolha persiste no
 * settings-store (campo permissionMode) e é enviada em cada request como
 * config.permission_mode, consumida pelo hitl_check no backend.
 */

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, ShieldCheck } from "lucide-react";

import {
  useSettingsStore,
  PERMISSION_MODES,
  type PermissionMode,
} from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";

/** Cor do chip por modo — quanto mais permissivo, mais "quente". */
const MODE_TONE: Record<PermissionMode, string> = {
  ask: "text-muted-foreground",
  accept_edits: "text-blue-400",
  plan: "text-violet-400",
  auto: "text-amber-400",
  bypass: "text-orange-500",
};

export function PermissionModeMenu() {
  const t = useT();
  const mode = useSettingsStore((s) => s.permissionMode);
  const setMode = useSettingsStore((s) => s.setPermissionMode);

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs hover:bg-muted/50 transition-colors select-none ${MODE_TONE[mode]}`}
        title={t("permission.title")}
        aria-expanded={open}
      >
        <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
        <span className="font-medium">{t(`permission.mode.${mode}`)}</span>
        <ChevronDown className="w-3 h-3 shrink-0" />
      </button>

      {open && (
        <div className="absolute left-0 bottom-9 z-50 w-72 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-bottom-2">
          <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("permission.title")}
          </div>
          {PERMISSION_MODES.map((m) => (
            <button
              key={m}
              className="w-full flex items-start gap-2 px-3 py-2 text-sm hover:bg-accent text-left transition-colors"
              onClick={() => {
                setMode(m);
                setOpen(false);
              }}
            >
              <span className="w-4 shrink-0 pt-0.5">
                {m === mode && <Check className="w-4 h-4 text-primary" />}
              </span>
              <span className="min-w-0">
                <span className={`block font-medium ${MODE_TONE[m]}`}>
                  {t(`permission.mode.${m}`)}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {t(`permission.desc.${m}`)}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
