"use client";

import { Check, Monitor } from "lucide-react";
import type { BaseThemeColors, ThemePresetDef } from "@/lib/theme/presets";

/** Faixa de 3 swatches (background/primary/accent) — dá pra reconhecer a
 * paleta de relance antes de aplicar, sem precisar ler o label. */
function ThemeSwatch({ colors }: { colors: BaseThemeColors }) {
  return (
    <div
      aria-hidden
      className="flex h-5 w-10 shrink-0 overflow-hidden rounded-sm border border-border/60"
    >
      <span className="flex-1" style={{ background: colors.background }} />
      <span className="flex-1" style={{ background: colors.primary }} />
      <span className="flex-1" style={{ background: colors.accent }} />
    </div>
  );
}

interface ThemePickerOption {
  id: string;
  label: string;
  colors?: BaseThemeColors;
}

export function ThemePicker({
  value,
  onChange,
  presets,
  systemLabel,
  customLabel,
  customColors,
}: {
  value: string;
  onChange: (id: string) => void;
  presets: ThemePresetDef[];
  systemLabel: string;
  customLabel: string;
  customColors: BaseThemeColors;
}) {
  const options: ThemePickerOption[] = [
    { id: "system", label: systemLabel },
    ...presets.map((preset) => ({
      id: preset.id,
      label: preset.label,
      colors: preset.colors,
    })),
    { id: "custom", label: customLabel, colors: customColors },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {options.map((opt) => {
        const isActive = opt.id === value;
        return (
          <button
            key={opt.id}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(opt.id)}
            className={`flex items-center gap-2 rounded-md border p-2 text-left transition-colors ${
              isActive
                ? "border-primary bg-primary/10"
                : "border-border hover:bg-muted/50"
            }`}
          >
            {opt.colors ? (
              <ThemeSwatch colors={opt.colors} />
            ) : (
              <Monitor className="h-5 w-10 shrink-0 rounded-sm border border-border/60 p-1 text-muted-foreground" />
            )}
            <span className="flex-1 truncate text-xs font-medium">
              {opt.label}
            </span>
            {isActive && (
              <Check className="h-3.5 w-3.5 shrink-0 text-primary" />
            )}
          </button>
        );
      })}
    </div>
  );
}
