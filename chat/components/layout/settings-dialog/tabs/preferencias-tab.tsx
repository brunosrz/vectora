"use client";

/**
 * PreferenciasTab — Bloco L2 / L3 / L4
 *
 * - Tema: dark / light / system (via next-themes + settings-store)
 * - Limite de histórico de mensagens
 * - System prompt personalizado (L4)
 */

import { useTheme } from "next-themes";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { useSettingsStore, type Theme } from "@/lib/stores/settings-store";

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: "system", label: "Sistema (automático)" },
  { value: "light", label: "Claro" },
  { value: "dark", label: "Escuro" },
];

export function PreferenciasTab() {
  const { setTheme: setNextTheme } = useTheme();
  const { theme, historyLimit, customSystemPrompt, setTheme, setHistoryLimit, setCustomSystemPrompt } = useSettingsStore();

  const handleThemeChange = (value: Theme) => {
    setTheme(value);
    setNextTheme(value);
  };

  return (
    <div className="space-y-6">
      {/* Tema */}
      <div className="space-y-2">
        <Label htmlFor="theme">Tema da interface</Label>
        <Select value={theme} onValueChange={handleThemeChange}>
          <SelectTrigger id="theme">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {THEME_OPTIONS.map(({ value, label }) => (
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
          <Label htmlFor="history-limit">Limite do histórico</Label>
          <span className="text-sm text-muted-foreground tabular-nums">{historyLimit} mensagens</span>
        </div>
        <Slider id="history-limit" min={10} max={200} step={10} value={[historyLimit]} onValueChange={([v]) => setHistoryLimit(v)} className="w-full" />
        <p className="text-xs text-muted-foreground">Número máximo de mensagens exibidas por thread (padrão: 50).</p>
      </div>

      {/* System prompt personalizado — L4 */}
      <div className="space-y-2">
        <Label htmlFor="custom-prompt">Instrução personalizada</Label>
        <Textarea id="custom-prompt" placeholder="Ex: Responda sempre em bullet points. Seja conciso." value={customSystemPrompt} onChange={(e) => setCustomSystemPrompt(e.target.value)} rows={4} className="resize-none text-sm" />
        <p className="text-xs text-muted-foreground">Texto prefixado ao system prompt do agente em todas as conversas. Deixe em branco para usar o comportamento padrão.</p>
      </div>
    </div>
  );
}
