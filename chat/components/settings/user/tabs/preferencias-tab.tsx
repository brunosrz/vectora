"use client";

/**
 * PreferenciasTab — preferências do usuário no Settings Dialog.
 *
 * - Tema: dark / light / system (next-themes + settings-store)
 * - Idioma: en / es / pt (settings-store + i18n)
 * - Limite de histórico de mensagens
 * - System prompt personalizado
 */

import { Keyboard } from "lucide-react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  type Theme,
  type Lang,
} from "@/lib/stores/settings-store";
import {
  THEME_PRESETS,
  DEFAULT_CUSTOM_COLORS,
  type BaseThemeColors,
} from "@/lib/theme/presets";
import { useT } from "@/lib/i18n";

const THEME_VALUES: Theme[] = ["system", "light", "dark"];

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
  const t = useT();
  const {
    theme,
    themePreset,
    customThemeColors,
    language,
    historyLimit,
    customSystemPrompt,
    showToolCalls,
    setTheme,
    setThemePreset,
    setCustomThemeColors,
    setLanguage,
    setHistoryLimit,
    setCustomSystemPrompt,
    setShowToolCalls,
  } = useSettingsStore();

  const activeCustomColors = customThemeColors ?? DEFAULT_CUSTOM_COLORS;

  const handleCustomColorChange = (
    key: keyof BaseThemeColors,
    value: string,
  ) => {
    setCustomThemeColors({ ...activeCustomColors, [key]: value });
  };

  return (
    <div className="space-y-6">
      {/* Tema */}
      <div className="space-y-2">
        <Label htmlFor="theme">{t("prefs.theme")}</Label>
        <Select value={theme} onValueChange={(v) => setTheme(v as Theme)}>
          <SelectTrigger id="theme">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {THEME_VALUES.map((value) => (
              <SelectItem key={value} value={value}>
                {t(`prefs.theme.${value}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Paleta de cores — presets inspirados em temas do VS Code + custom */}
      <div className="space-y-2">
        <Label htmlFor="theme-palette">{t("prefs.theme_palette")}</Label>
        <Select value={themePreset} onValueChange={setThemePreset}>
          <SelectTrigger id="theme-palette">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="default">
              {t("prefs.theme_palette.default")}
            </SelectItem>
            {THEME_PRESETS.map((preset) => (
              <SelectItem key={preset.id} value={preset.id}>
                {preset.label}
              </SelectItem>
            ))}
            <SelectItem value="custom">
              {t("prefs.theme_palette.custom")}
            </SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {t("prefs.theme_palette_help")}
        </p>

        {themePreset === "custom" && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {CUSTOM_COLOR_FIELDS.map(({ key, labelKey }) => (
              <div key={key} className="space-y-1">
                <Label htmlFor={`custom-color-${key}`} className="text-xs">
                  {t(labelKey)}
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
        <Label htmlFor="language">{t("prefs.language")}</Label>
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

      {/* Limite de histórico */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="history-limit">{t("prefs.history_limit")}</Label>
          <span className="text-sm text-muted-foreground tabular-nums">
            {historyLimit} {t("prefs.history_limit_unit")}
          </span>
        </div>
        <Slider
          id="history-limit"
          min={10}
          max={200}
          step={10}
          value={[historyLimit]}
          onValueChange={([v]) => setHistoryLimit(v)}
          className="w-full"
        />
        <p className="text-xs text-muted-foreground">
          {t("prefs.history_limit_help")}
        </p>
      </div>

      {/* System prompt personalizado */}
      <div className="space-y-2">
        <Label htmlFor="custom-prompt">{t("prefs.custom_prompt")}</Label>
        <Textarea
          id="custom-prompt"
          placeholder={t("prefs.custom_prompt_placeholder")}
          value={customSystemPrompt}
          onChange={(e) => setCustomSystemPrompt(e.target.value)}
          rows={4}
          className="resize-none text-sm"
        />
        <p className="text-xs text-muted-foreground">
          {t("prefs.custom_prompt_help")}
        </p>
      </div>

      {/* Ferramentas */}
      <div className="space-y-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {t("settings.chat.tools_section")}
        </p>

        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label
              htmlFor="show-tool-calls"
              className="text-sm font-normal cursor-pointer"
            >
              {t("settings.chat.show_tool_calls")}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t("settings.chat.show_tool_calls_hint")}
            </p>
          </div>
          <Switch
            id="show-tool-calls"
            checked={showToolCalls}
            onCheckedChange={setShowToolCalls}
          />
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          onClick={() =>
            window.dispatchEvent(new CustomEvent("open-shortcuts"))
          }
        >
          <Keyboard className="w-4 h-4" />
          {t("settings.chat.keyboard_shortcuts")}
        </Button>
      </div>
    </div>
  );
}
