"use client";

/**
 * PreferenciasTab — preferências do usuário no Settings Dialog.
 *
 * - Tema: seletor unificado (sistema / claro / escuro / presets / customizada)
 * - Idioma: en / es / pt (settings-store + i18n)
 * - System prompt personalizado + blocos de treinamento
 */

import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
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
import { Switch } from "@/components/ui/switch";
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  FONT_SCALE_MIN,
  FONT_SCALE_MAX,
  MONACO_FONT_SIZE_MIN,
  MONACO_FONT_SIZE_MAX,
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
  return id === "light" || id.endsWith("-light") ? "light" : "dark";
}

/** Rótulo do tema selecionado, resolvido explicitamente (não deixado pro
 * registro interno do Radix Select) — sem isso o trigger mostra vazio no
 * primeiro paint, antes do `SelectItem` correspondente montar. */
export function themeLabel(id: string): string {
  if (id === "system") return m.prefs_theme_system();
  if (id === "custom") return m.prefs_theme_palette_custom();
  return THEME_PRESETS.find((preset) => preset.id === id)?.label ?? id;
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
    { key: "sidebar", labelKey: "prefs.custom_color.sidebar" },
    { key: "userBubble", labelKey: "prefs.custom_color.user_bubble" },
  ];

/** Toggle de auto-update (Electron) + botão de checagem manual — a checagem
 * manual funciona independente do toggle (dispara `checkForUpdates()` sob
 * demanda mesmo com o automático desligado). Invisível no navegador/modo
 * servidor: `window.vectora` só existe dentro do app desktop. */
function AutoUpdateSection({
  autoUpdateEnabled,
  setAutoUpdateEnabled,
}: {
  autoUpdateEnabled: boolean;
  setAutoUpdateEnabled: (v: boolean) => void;
}) {
  const [checking, setChecking] = useState(false);

  if (typeof window === "undefined" || !window.vectora) return null;

  const handleCheckNow = () => {
    setChecking(true);
    window.vectora?.checkForUpdate?.();
    setTimeout(() => setChecking(false), 3000);
  };

  return (
    <div className="space-y-3">
      <Label>{m.prefs_auto_update_section()}</Label>
      <div className="flex items-center justify-between gap-3">
        <div>
          <Label htmlFor="auto-update-toggle" className="cursor-pointer">
            {m.prefs_auto_update_toggle()}
          </Label>
          <p className="text-xs text-muted-foreground">
            {m.prefs_auto_update_toggle_hint()}
          </p>
        </div>
        <Switch
          id="auto-update-toggle"
          checked={autoUpdateEnabled}
          onCheckedChange={setAutoUpdateEnabled}
        />
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={handleCheckNow}
        disabled={checking}
      >
        {checking
          ? m.prefs_auto_update_checking()
          : m.prefs_auto_update_check_now()}
      </Button>
    </div>
  );
}

/** Fuso horário do usuário — o scheduler já usava `user_timezone` para
 * converter "toda segunda às 9h" no UTC de armazenamento; sem este seletor a
 * config só existia por API e "9h" virava 9h UTC pra todo mundo. */
function TimezoneSection() {
  const [timezone, setTimezone] = useState("");
  const [available, setAvailable] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch("/admin/timezone");
        if (!res.ok || !alive) return;
        const data = (await res.json()) as {
          timezone?: string;
          available?: string[];
        };
        if (!alive) return;
        setTimezone(data.timezone ?? "");
        setAvailable(Array.isArray(data.available) ? data.available : []);
      } catch {
        if (alive) setAvailable([]);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function handleChange(next: string) {
    setError("");
    const previous = timezone;
    setTimezone(next);
    try {
      const res = await fetch("/admin/timezone", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timezone: next }),
      });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      // Reverte a seleção: deixar o valor novo na tela sugeriria que salvou.
      setTimezone(previous);
      setError(m.prefs_timezone_error());
    }
  }

  if (available.length === 0) return null;

  return (
    <div className="space-y-3">
      <Label htmlFor="timezone">{m.prefs_timezone_section()}</Label>
      <p className="text-xs text-muted-foreground">{m.prefs_timezone_hint()}</p>
      <Select value={timezone} onValueChange={(v) => void handleChange(v)}>
        <SelectTrigger id="timezone" className="w-[280px]">
          <SelectValue placeholder={m.prefs_timezone_placeholder()} />
        </SelectTrigger>
        <SelectContent className="max-h-[300px]">
          {available.map((tz) => (
            <SelectItem key={tz} value={tz}>
              {tz}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

/** Aparência — 4 escalas de fonte independentes (UI, chat, markdown, Monaco).
 * Cada uma aplicada só na superfície correspondente (ver __root.tsx e
 * markdown-view.tsx/message-item.tsx/file-editor.tsx). */
export function FontScaleNumberInput({
  id,
  value,
  min,
  max,
  onChange,
}: {
  id: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const [text, setText] = useState(String(value));

  useEffect(() => {
    setText(String(value));
  }, [value]);

  const commit = useCallback(() => {
    const n = Number(text);
    if (text.trim() === "" || Number.isNaN(n)) {
      setText(String(value));
      return;
    }
    const clamped = Math.max(min, Math.min(max, Math.round(n)));
    setText(String(clamped));
    if (clamped !== value) onChange(clamped);
  }, [text, value, min, max, onChange]);

  return (
    <Input
      id={`${id}-number`}
      type="number"
      min={min}
      max={max}
      value={text}
      onChange={(e) => {
        const raw = e.target.value;
        setText(raw);
        const n = Number(raw);
        if (raw.trim() !== "" && !Number.isNaN(n)) onChange(n);
      }}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
      className="h-7 w-16 shrink-0 px-2 text-right text-xs tabular-nums"
    />
  );
}

function FontScaleSection({
  fontScaleUi,
  fontScaleChat,
  fontScaleMarkdown,
  monacoFontSize,
  setFontScaleUi,
  setFontScaleChat,
  setFontScaleMarkdown,
  setMonacoFontSize,
}: {
  fontScaleUi: number;
  fontScaleChat: number;
  fontScaleMarkdown: number;
  monacoFontSize: number;
  setFontScaleUi: (v: number) => void;
  setFontScaleChat: (v: number) => void;
  setFontScaleMarkdown: (v: number) => void;
  setMonacoFontSize: (v: number) => void;
}) {
  const rows: {
    id: string;
    label: string;
    value: number;
    onChange: (v: number) => void;
    min: number;
    max: number;
    step: number;
    unit: string;
  }[] = [
    {
      id: "font-scale-ui",
      label: m.prefs_font_scale_ui(),
      value: fontScaleUi,
      onChange: setFontScaleUi,
      min: FONT_SCALE_MIN,
      max: FONT_SCALE_MAX,
      step: 1,
      unit: "px",
    },
    {
      id: "font-scale-chat",
      label: m.prefs_font_scale_chat(),
      value: fontScaleChat,
      onChange: setFontScaleChat,
      min: FONT_SCALE_MIN,
      max: FONT_SCALE_MAX,
      step: 1,
      unit: "px",
    },
    {
      id: "font-scale-markdown",
      label: m.prefs_font_scale_markdown(),
      value: fontScaleMarkdown,
      onChange: setFontScaleMarkdown,
      min: FONT_SCALE_MIN,
      max: FONT_SCALE_MAX,
      step: 1,
      unit: "px",
    },
    {
      id: "monaco-font-size",
      label: m.prefs_font_size_monaco(),
      value: monacoFontSize,
      onChange: setMonacoFontSize,
      min: MONACO_FONT_SIZE_MIN,
      max: MONACO_FONT_SIZE_MAX,
      step: 1,
      unit: "px",
    },
  ];

  return (
    <div className="space-y-3">
      <Label>{m.prefs_appearance_section()}</Label>
      {rows.map((row) => (
        <div key={row.id} className="flex items-center gap-3">
          <Label htmlFor={row.id} className="flex-1 text-xs font-normal">
            {row.label}
          </Label>
          <input
            id={row.id}
            type="range"
            min={row.min}
            max={row.max}
            step={row.step}
            value={row.value}
            onChange={(e) => row.onChange(Number(e.target.value))}
            className="w-32 accent-primary"
          />
          <FontScaleNumberInput
            id={row.id}
            value={row.value}
            min={row.min}
            max={row.max}
            onChange={row.onChange}
          />
          <span className="w-4 shrink-0 text-left text-xs text-muted-foreground">
            {row.unit}
          </span>
        </div>
      ))}
    </div>
  );
}

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
    showToolCalls,
    setShowToolCalls,
    setCustomSystemPrompt,
    setTrainingInstructions,
    autoUpdateEnabled,
    setAutoUpdateEnabled,
    fontScaleUi,
    fontScaleChat,
    fontScaleMarkdown,
    monacoFontSize,
    setFontScaleUi,
    setFontScaleChat,
    setFontScaleMarkdown,
    setMonacoFontSize,
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
            <SelectValue>{themeLabel(selectedTheme)}</SelectValue>
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
            <SelectValue>
              {SUPPORTED_LANGS.find((l) => l.value === language)?.label ??
                language}
            </SelectValue>
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

      {/* Exibe as chamadas de tool na interface do chat. */}
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="show-tool-calls" className="cursor-pointer">
          {m.settings_chat_show_tool_calls()}
        </Label>
        <Switch
          id="show-tool-calls"
          checked={showToolCalls}
          onCheckedChange={setShowToolCalls}
        />
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

      {/* Aparência — escalas de fonte independentes */}
      <FontScaleSection
        fontScaleUi={fontScaleUi}
        fontScaleChat={fontScaleChat}
        fontScaleMarkdown={fontScaleMarkdown}
        monacoFontSize={monacoFontSize}
        setFontScaleUi={setFontScaleUi}
        setFontScaleChat={setFontScaleChat}
        setFontScaleMarkdown={setFontScaleMarkdown}
        setMonacoFontSize={setMonacoFontSize}
      />

      {/* Auto-update (só desktop) */}
      <AutoUpdateSection
        autoUpdateEnabled={autoUpdateEnabled}
        setAutoUpdateEnabled={setAutoUpdateEnabled}
      />

      {/* Fuso horário usado pelos agendamentos */}
      <TimezoneSection />
    </div>
  );
}
