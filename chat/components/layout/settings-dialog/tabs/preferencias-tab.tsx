"use client";

/**
 * PreferenciasTab — preferências do usuário no Settings Dialog.
 *
 * - Tema: dark / light / system (next-themes + settings-store)
 * - Idioma: en / es / pt (settings-store + i18n)
 * - Limite de histórico de mensagens
 * - System prompt personalizado
 */

import { useTheme } from "next-themes";
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
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  type Theme,
  type Lang,
} from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";

const THEME_VALUES: Theme[] = ["system", "light", "dark"];

export function PreferenciasTab() {
  const t = useT();
  const { setTheme: setNextTheme } = useTheme();
  const {
    theme,
    language,
    historyLimit,
    customSystemPrompt,
    setTheme,
    setLanguage,
    setHistoryLimit,
    setCustomSystemPrompt,
  } = useSettingsStore();

  const handleThemeChange = (value: Theme) => {
    setTheme(value);
    setNextTheme(value);
  };

  return (
    <div className="space-y-6">
      {/* Tema */}
      <div className="space-y-2">
        <Label htmlFor="theme">{t("prefs.theme")}</Label>
        <Select value={theme} onValueChange={handleThemeChange}>
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
    </div>
  );
}
