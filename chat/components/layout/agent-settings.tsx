"use client";

/**
 * AgentSettings → "Chat Settings" — Bloco L1
 *
 * Dialog acessível via ⚙️ no header. Escopo: sessão/chat atual.
 *
 * Removidos: Agent Type, Recursion Limit (eram placeholders não funcionais).
 * Adicionados:
 *   - Toggle "Mostrar tool calls no chat"
 *   - Toggle "Confirmar ações destrutivas" (HITL antecipado)
 *   - Seletor de verbosidade: Concisa / Normal / Detalhada
 * Mantidos: seletor de modelo, atalhos de teclado.
 */

import { useEffect, useState } from "react";
import { Settings, Keyboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { getAllowedModels, getModelDisplayName, isModelAllowed, getDefaultModel, type ModelOption } from "@/lib/config/deployment-config";
import { useSettingsStore, type Verbosity } from "@/lib/stores/settings-store";

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

const VERBOSITY_OPTIONS: { value: Verbosity; label: string }[] = [
  { value: "concise", label: "Concisa" },
  { value: "normal", label: "Normal" },
  { value: "detailed", label: "Detalhada" },
];

export function AgentSettings({ config, onConfigChange, onShowShortcuts, forceShowTooltip, open, onOpenChange }: AgentSettingsProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  const { showToolCalls, requireHitl, verbosity, setShowToolCalls, setRequireHitl, setVerbosity } = useSettingsStore();

  const allowedModels = getAllowedModels();

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
              <Button variant="ghost" size="sm" className="hover:bg-muted/70 hover:text-foreground" aria-label="Configurações do chat">
                <Settings className="w-4 h-4" />
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">Configurações do chat</p>
          </TooltipContent>
        </Tooltip>

        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Configurações do Chat</DialogTitle>
            <DialogDescription>Personaliza o comportamento desta sessão de chat.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-5 py-2">
            {/* Modelo */}
            <div className="grid gap-2">
              <Label htmlFor="model">Modelo</Label>
              <Select value={config.model} onValueChange={(model) => onConfigChange({ ...config, model })}>
                <SelectTrigger id="model">
                  <SelectValue placeholder="Selecionar modelo" />
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
              <Label htmlFor="verbosity">Verbosidade das respostas</Label>
              <Select value={verbosity} onValueChange={(v) => setVerbosity(v as Verbosity)}>
                <SelectTrigger id="verbosity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VERBOSITY_OPTIONS.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Ferramentas */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Ferramentas</p>

              {/* Mostrar tool calls */}
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <Label htmlFor="show-tool-calls" className="text-sm font-normal cursor-pointer">
                    Mostrar tool calls no chat
                  </Label>
                  <p className="text-xs text-muted-foreground">Exibe as chamadas de ferramentas durante a resposta.</p>
                </div>
                <Switch id="show-tool-calls" checked={showToolCalls} onCheckedChange={setShowToolCalls} />
              </div>

              {/* Confirmar ações destrutivas */}
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <Label htmlFor="require-hitl" className="text-sm font-normal cursor-pointer">
                    Confirmar ações destrutivas
                  </Label>
                  <p className="text-xs text-muted-foreground">Pede confirmação antes de executar ferramentas irreversíveis (escrita de arquivo, terminal, etc).</p>
                </div>
                <Switch id="require-hitl" checked={requireHitl} onCheckedChange={setRequireHitl} />
              </div>
            </div>
          </div>

          {/* Atalhos */}
          {onShowShortcuts && (
            <div className="border-t pt-3 mt-0">
              <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground" onClick={onShowShortcuts}>
                <Keyboard className="w-4 h-4" />
                Ver atalhos de teclado
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
