"use client";

/**
 * AgentSettings — dialog "Chat Settings" acessível via ⚙️ no header.
 * Escopo: sessão/chat atual.
 *
 * Controles: seletor de modelo, verbosidade, tema, idioma,
 * toggles de tool calls e confirmação de ações destrutivas, atalhos de teclado.
 */

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Settings, Keyboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  getAllowedModels,
  getModelDisplayName,
  isModelAllowed,
  getDefaultModel,
  type ModelOption,
} from "@/lib/config/deployment-config";
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  type Verbosity,
  type Theme,
  type Lang,
  type ReasoningEffort,
} from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// AgentConfig — mantido para retrocompatibilidade; agentType e recursionLimit
// estão deprecados e serão removidos gradualmente dos consumidores.
// ---------------------------------------------------------------------------

export interface AgentConfig {
  model: string;
  /** @deprecated — não tem efeito; remover dos consumidores */
  recursionLimit?: number;
  /** @deprecated — não tem efeito; remover dos consumidores */
  agentType?: string;
  repos?: string[];
}

interface AgentSettingsProps {
  config: AgentConfig;
  onConfigChange: (config: AgentConfig) => void;
  onShowShortcuts?: () => void;
  forceShowTooltip?: number;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

const VERBOSITY_VALUES: Verbosity[] = ["concise", "normal", "detailed"];
const THEME_VALUES: Theme[] = ["system", "light", "dark"];
const EFFORT_VALUES: ReasoningEffort[] = ["low", "medium", "high", "max"];

export function AgentSettings({
  config,
  onConfigChange,
  onShowShortcuts,
  forceShowTooltip,
  open,
  onOpenChange,
}: AgentSettingsProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const t = useT();
  const { setTheme: setNextTheme } = useTheme();

  const {
    showToolCalls,
    verbosity,
    theme,
    language,
    reasoningEffort,
    fastMode,
    setShowToolCalls,
    setVerbosity,
    setTheme,
    setLanguage,
    setReasoningEffort,
    setFastMode,
  } = useSettingsStore();

  const allowedModels = getAllowedModels();

  const handleThemeChange = (value: Theme) => {
    setTheme(value);
    setNextTheme(value);
  };

  // Força tooltip ao receber forceShowTooltip
  useEffect(() => {
    if (forceShowTooltip && forceShowTooltip > 0) {
      setTooltipOpen(true);
      const timer = setTimeout(() => setTooltipOpen(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [forceShowTooltip]);

  // Valida modelo salvo; reseta para default se não permitido
  useEffect(() => {
    if (!isModelAllowed(config.model as ModelOption)) {
      const defaultModel = getDefaultModel();
      onConfigChange({ ...config, model: defaultModel });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <TooltipProvider delayDuration={0}>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <Tooltip open={tooltipOpen} onOpenChange={setTooltipOpen}>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="hover:bg-muted/70 hover:text-foreground"
                aria-label={t("settings.chat.tooltip")}
              >
                <Settings className="w-4 h-4" />
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">{t("settings.chat.tooltip")}</p>
          </TooltipContent>
        </Tooltip>

        <DialogContent className="sm:max-w-[400px] max-h-[85vh] flex flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>{t("settings.chat.title")}</DialogTitle>
            <DialogDescription>
              {t("settings.chat.description")}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-5 py-2 overflow-y-auto pr-1 flex-1 min-h-0">
            {/* Modelo */}
            <div className="grid gap-2">
              <Label htmlFor="model">{t("settings.chat.model")}</Label>
              <Select
                value={config.model}
                onValueChange={(model) => onConfigChange({ ...config, model })}
              >
                <SelectTrigger id="model">
                  <SelectValue
                    placeholder={t("settings.chat.model_placeholder")}
                  />
                </SelectTrigger>
                <SelectContent>
                  {allowedModels.map((modelId) => (
                    <SelectItem key={modelId} value={modelId}>
                      {getModelDisplayName(modelId)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Verbosidade */}
            <div className="grid gap-2">
              <Label htmlFor="verbosity">{t("settings.chat.verbosity")}</Label>
              <Select
                value={verbosity}
                onValueChange={(v) => setVerbosity(v as Verbosity)}
              >
                <SelectTrigger id="verbosity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VERBOSITY_VALUES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {t(`settings.chat.verbosity.${value}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Esforço de raciocínio (R4) */}
            <div className="grid gap-2">
              <Label htmlFor="effort">{t("effort.title")}</Label>
              <Select
                value={reasoningEffort}
                onValueChange={(v) => setReasoningEffort(v as ReasoningEffort)}
                disabled={fastMode}
              >
                <SelectTrigger id="effort">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EFFORT_VALUES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {t(`effort.${value}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex items-center justify-between gap-4 pt-1">
                <div className="space-y-0.5">
                  <Label
                    htmlFor="fast-mode"
                    className="text-sm font-normal cursor-pointer"
                  >
                    {t("effort.fast_mode")}
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    {t("effort.fast_mode_desc")}
                  </p>
                </div>
                <Switch
                  id="fast-mode"
                  checked={fastMode}
                  onCheckedChange={setFastMode}
                />
              </div>
            </div>

            {/* Tema */}
            <div className="grid gap-2">
              <Label htmlFor="chat-theme">{t("prefs.theme")}</Label>
              <Select value={theme} onValueChange={handleThemeChange}>
                <SelectTrigger id="chat-theme">
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
            <div className="grid gap-2">
              <Label htmlFor="chat-language">{t("prefs.language")}</Label>
              <Select
                value={language}
                onValueChange={(v) => setLanguage(v as Lang)}
              >
                <SelectTrigger id="chat-language">
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

            {/* Ferramentas */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {t("settings.chat.tools_section")}
              </p>

              {/* Mostrar tool calls */}
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
            </div>
          </div>

          {/* Atalhos */}
          {onShowShortcuts && (
            <div className="border-t pt-3 mt-0">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
                onClick={onShowShortcuts}
              >
                <Keyboard className="w-4 h-4" />
                {t("settings.chat.keyboard_shortcuts")}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
