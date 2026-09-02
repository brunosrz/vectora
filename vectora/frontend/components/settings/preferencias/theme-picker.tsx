"use client";

import { Check, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import type { BaseThemeColors, ThemePresetDef } from "@/lib/theme/presets";

/** Luminância relativa aproximada (sRGB) — mesmo cálculo de
 * `lib/theme/presets.ts::contrastFg`, duplicado aqui (função privada lá)
 * só pra decidir a cor do texto do pill de exemplo sem exportar um
 * utilitário novo pro módulo inteiro. */
function relativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim());
  if (!m) return 1;
  const [r, g, b] = [m[1]!, m[2]!, m[3]!].map((h) => parseInt(h, 16) / 255);
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function contrastFg(hex: string): string {
  return relativeLuminance(hex) > 0.5 ? "#0a0a0a" : "#fafafa";
}

/** Card pintado com as cores reais da paleta — barra dupla (primary/accent)
 * + pill de exemplo (userBubble/contrastFg) dá pra reconhecer o tema de
 * relance, sem precisar aplicá-lo primeiro. */
function PaintedCard({
  label,
  colors,
  active,
  onClick,
}: {
  label: string;
  colors: BaseThemeColors;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`group relative flex flex-col overflow-hidden rounded-lg border text-left transition-colors ${
        active
          ? "border-primary ring-1 ring-primary"
          : "border-border hover:border-foreground/30"
      }`}
      style={{ background: colors.background }}
    >
      <div className="flex h-9 w-full" aria-hidden>
        <span className="flex-1" style={{ background: colors.primary }} />
        <span className="flex-1" style={{ background: colors.accent }} />
      </div>
      <div className="flex items-center justify-between gap-2 px-2.5 py-2">
        <span
          className="truncate text-xs font-medium"
          style={{ color: colors.foreground }}
        >
          {label}
        </span>
        <span
          className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium"
          style={{
            background: colors.userBubble,
            color: contrastFg(colors.userBubble),
          }}
          aria-hidden
        >
          Aa
        </span>
      </div>
      {active && (
        <span
          className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground"
          aria-hidden
        >
          <Check className="h-2.5 w-2.5" />
        </span>
      )}
    </button>
  );
}

interface ThemePickerOption {
  id: string;
  label: string;
  colors: BaseThemeColors;
}

export function ThemePicker({
  value,
  onChange,
  presets,
  customLabel,
  customColors,
  searchPlaceholder,
}: {
  value: string;
  onChange: (id: string) => void;
  presets: ThemePresetDef[];
  customLabel: string;
  customColors: BaseThemeColors;
  searchPlaceholder: string;
}) {
  const [query, setQuery] = useState("");

  const options: ThemePickerOption[] = useMemo(
    () => [
      ...presets.map((preset) => ({
        id: preset.id,
        label: preset.label,
        colors: preset.colors,
      })),
      { id: "custom", label: customLabel, colors: customColors },
    ],
    [presets, customLabel, customColors],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((opt) => opt.label.toLowerCase().includes(q));
  }, [options, query]);

  return (
    <div className="space-y-2">
      {/* Busca só ganha espaço quando há paletas suficientes pra valer a
          pena filtrar — poucas opções não precisam de mais um campo pra
          escanear visualmente. */}
      {options.length > 4 && (
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="h-8 pl-7 text-xs"
          />
        </div>
      )}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {filtered.map((opt) => (
          <PaintedCard
            key={opt.id}
            label={opt.label}
            colors={opt.colors}
            active={opt.id === value}
            onClick={() => onChange(opt.id)}
          />
        ))}
      </div>
    </div>
  );
}

/** Toggle Light/Dark/System — separado do grid de paletas: controla só o
 * campo `theme` (claro/escuro/sistema) do store, independente de qual
 * paleta está ativa. Antes "system" era só mais uma entrada do grid de
 * presets, sem opção de forçar claro/escuro sem também trocar de paleta. */
export function ThemeModeToggle({
  value,
  onChange,
  labels,
}: {
  value: "light" | "dark" | "system";
  onChange: (v: "light" | "dark" | "system") => void;
  labels: { system: string; light: string; dark: string };
}) {
  const options: { id: "system" | "light" | "dark"; label: string }[] = [
    { id: "system", label: labels.system },
    { id: "light", label: labels.light },
    { id: "dark", label: labels.dark },
  ];
  return (
    <div
      role="group"
      className="inline-flex rounded-md border border-border p-0.5"
    >
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          aria-pressed={value === opt.id}
          onClick={() => onChange(opt.id)}
          className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
            value === opt.id
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
