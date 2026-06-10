"use client";

/**
 * ChatParamsMenu — menu compacto de parâmetros de geração.
 *
 * Agrupa Verbosidade, Esforço de raciocínio e Modo-rápido no rodapé do
 * composer, ao lado do seletor de modelo e do PermissionModeMenu. Esses
 * controles definem "como a próxima resposta será gerada" e pertencem
 * ao fluxo de composição, não às preferências persistentes do usuário
 * (Tema/Idioma), que ficam no Settings completo (Settings → Preferências).
 */

import { useEffect, useRef, useState } from "react";
import { SlidersHorizontal } from "lucide-react";

import {
  useSettingsStore,
  type Verbosity,
  type ReasoningEffort,
} from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const VERBOSITY_VALUES: Verbosity[] = ["concise", "normal", "detailed"];
const EFFORT_VALUES: ReasoningEffort[] = ["low", "medium", "high", "max"];

export function ChatParamsMenu() {
  const t = useT();
  const {
    verbosity,
    reasoningEffort,
    fastMode,
    setVerbosity,
    setReasoningEffort,
    setFastMode,
  } = useSettingsStore();

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onOutsideClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onOutsideClick);
    return () => document.removeEventListener("mousedown", onOutsideClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors select-none"
        title={t("chat_params.title")}
        aria-expanded={open}
        aria-haspopup="true"
        type="button"
      >
        <SlidersHorizontal className="w-3.5 h-3.5 shrink-0" />
      </button>

      {open && (
        <div className="absolute right-0 bottom-9 z-50 w-64 rounded-lg border border-border bg-background shadow-xl p-3 space-y-4 animate-in fade-in slide-in-from-bottom-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("chat_params.title")}
          </p>

          {/* Verbosidade */}
          <div className="grid gap-1.5">
            <Label htmlFor="cp-verbosity" className="text-xs">
              {t("settings.chat.verbosity")}
            </Label>
            <Select
              value={verbosity}
              onValueChange={(v) => setVerbosity(v as Verbosity)}
            >
              <SelectTrigger id="cp-verbosity" className="h-7 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VERBOSITY_VALUES.map((v) => (
                  <SelectItem key={v} value={v} className="text-xs">
                    {t(`settings.chat.verbosity.${v}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Esforço de raciocínio */}
          <div className="grid gap-1.5">
            <Label htmlFor="cp-effort" className="text-xs">
              {t("effort.title")}
            </Label>
            <Select
              value={reasoningEffort}
              onValueChange={(v) => setReasoningEffort(v as ReasoningEffort)}
              disabled={fastMode}
            >
              <SelectTrigger id="cp-effort" className="h-7 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EFFORT_VALUES.map((v) => (
                  <SelectItem key={v} value={v} className="text-xs">
                    {t(`effort.${v}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Modo rápido */}
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-0.5 min-w-0">
              <Label
                htmlFor="cp-fast-mode"
                className="text-xs font-normal cursor-pointer"
              >
                {t("effort.fast_mode")}
              </Label>
              <p className="text-xs text-muted-foreground leading-tight">
                {t("effort.fast_mode_desc")}
              </p>
            </div>
            <Switch
              id="cp-fast-mode"
              checked={fastMode}
              onCheckedChange={setFastMode}
            />
          </div>
        </div>
      )}
    </div>
  );
}
