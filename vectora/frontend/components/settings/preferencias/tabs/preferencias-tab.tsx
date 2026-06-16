"use client";

/**
 * PreferenciasTab — preferências do usuário no Settings Dialog.
 *
 * - Tema: seletor unificado (sistema / claro / escuro / presets / customizada)
 * - Idioma: en / es / pt (settings-store + i18n)
 * - System prompt personalizado + blocos de treinamento
 */

import { Plus, Trash2 } from "lucide-react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  type Theme,
  type Lang,
  type SidebarPosition,
} from "@/lib/stores/settings-store";
import {
  THEME_PRESETS,
  DEFAULT_CUSTOM_COLORS,
  type BaseThemeColors,
} from "@/lib/theme/presets";
import { m } from "@/lib/paraglide/messages";
import { mDyn } from "@/lib/i18n-dyn";
/** Deriva o `Theme` (claro/escuro) a partir do id de um preset. */
function themeForPreset(id: string): Theme {
  return id.endsWith("-light") ? "light" : "dark";
}

const CUSTOM_COLOR_FIELDS: { key: keyof BaseThemeColors; labelKey: string }[] =
  [
    { key: "background", labelKey: "prefs.custom_color.background" },
    { key: "foreground", labelKey: "prefs.custom_color.foreground" },
    { key: "card", labelKey: "prefs.custom_color.card" },
    { key: "border", labelKey: "prefs.custom_color.border" },
    { key: "primary", labelKey: "prefs.custom_color.primary" },
    { key: "accent", labelKey: "prefs.custom_color.accent" },
    { key: "muted", labelKey: "prefs.custom_color.muted" },
  ];

export function PreferenciasTab() {
  const {
    theme,
    themePreset,
    customThemeColors,
    language,
    customSystemPrompt,
    trainingInstructions,
    setTheme,
    setThemePreset,
    setCustomThemeColors,
    setLanguage,
    sidebarPosition,
    setSidebarPosition,
    setCustomSystemPrompt,
    setTrainingInstructions,
  } = useSettingsStore();

  const activeCustomColors = customThemeColors ?? DEFAULT_CUSTOM_COLORS;

  const handleCustomColorChange = (
    key: keyof BaseThemeColors,
    value: string,
  ) => {
    setCustomThemeColors({ ...activeCustomColors, [key]: value });
  };

  // Seletor unificado de tema: "system" | "custom" | id de THEME_PRESETS.
  // "default" (sentinela de "sem preset, usa o tema base") é tratado como "system".
  const selectedTheme =
    themePreset === "custom"
      ? "custom"
      : themePreset === "default"
        ? "system"
        : themePreset;

  const handleThemeChange = (value: string) => {
    if (value === "custom") {
      setThemePreset("custom");
      return;
    }
    if (value === "system") {
      setTheme("system");
      setThemePreset("default");
      return;
    }
    setTheme(themeForPreset(value));
    setThemePreset(value);
  };

  const handleAddTrainingBlock = () => {
    setTrainingInstructions([...trainingInstructions, ""]);
  };

  const handleTrainingBlockChange = (index: number, value: string) => {
    setTrainingInstructions(
      trainingInstructions.map((block, i) => (i === index ? value : block)),
    );
  };

  const handleRemoveTrainingBlock = (index: number) => {
    setTrainingInstructions(trainingInstructions.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      {/* Tema — seletor unificado (sistema, presets claros/escuros, custom) */}
      <div className="space-y-2">
        <Label htmlFor="theme">{m.prefs_theme()}</Label>
        <Select value={selectedTheme} onValueChange={handleThemeChange}>
          <SelectTrigger id="theme">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="system">{m.prefs_theme_system()}</SelectItem>
            {THEME_PRESETS.map((preset) => (
              <SelectItem key={preset.id} value={preset.id}>
                {preset.label}
              </SelectItem>
            ))}
            <SelectItem value="custom">
              {m.prefs_theme_palette_custom()}
            </SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {m.prefs_theme_palette_help()}
        </p>

        {themePreset === "custom" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {CUSTOM_COLOR_FIELDS.map(({ key, labelKey }) => (
              <div key={key} className="space-y-1">
                <Label htmlFor={`custom-color-${key}`} className="text-xs">
                  {mDyn(labelKey)}
                </Label>
                <div className="flex items-center gap-2">
                  <input
                    id={`custom-color-${key}`}
                    type="color"
                    value={activeCustomColors[key]}
                    onChange={(e) =>
                      handleCustomColorChange(key, e.target.value)
                    }
                    className="h-8 w-8 shrink-0 cursor-pointer rounded border border-border bg-transparent p-0.5"
                  />
                  <span className="text-[11px] font-mono text-muted-foreground truncate">
                    {activeCustomColors[key]}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Idioma */}
      <div className="space-y-2">
        <Label htmlFor="language">{m.prefs_language()}</Label>
        <Select value={language} onValueChange={(v) => setLanguage(v as Lang)}>
          <SelectTrigger id="language">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SUPPORTED_LANGS.map(({ value, label }) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Posição da sidebar de sessões (workbench no lado oposto) */}
      <div className="space-y-2">
        <Label htmlFor="sidebar-position">{m.prefs_sidebar_position()}</Label>
        <Select
          value={sidebarPosition}
          onValueChange={(v) => setSidebarPosition(v as SidebarPosition)}
        >
          <SelectTrigger id="sidebar-position">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="left">
              {m.prefs_sidebar_position_left()}
            </SelectItem>
            <SelectItem value="right">
              {m.prefs_sidebar_position_right()}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* System prompt personalizado */}
      <div className="space-y-2">
        <Label htmlFor="custom-prompt">{m.prefs_custom_prompt()}</Label>
        <Textarea
          id="custom-prompt"
          placeholder={m.prefs_custom_prompt_placeholder()}
          value={customSystemPrompt}
          onChange={(e) => setCustomSystemPrompt(e.target.value)}
          rows={4}
          className="resize-none text-sm"
        />
        <p className="text-xs text-muted-foreground">
          {m.prefs_custom_prompt_help()}
        </p>
      </div>

      {/* Treinamento — blocos de instrução adicionais */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{m.prefs_training()}</Label>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleAddTrainingBlock}
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            {m.prefs_training_add()}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {m.prefs_training_help()}
        </p>
        {trainingInstructions.map((block, index) => (
          <div key={index} className="flex items-start gap-2">
            <Textarea
              placeholder={m.prefs_training_placeholder()}
              value={block}
              onChange={(e) => handleTrainingBlockChange(index, e.target.value)}
              rows={3}
              className="resize-none text-sm"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2 text-muted-foreground hover:text-destructive shrink-0"
              onClick={() => handleRemoveTrainingBlock(index)}
              title={m.prefs_training_remove()}
              aria-label={m.prefs_training_remove()}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
