"use client";

/**
 * ModelSelector
 *
 * Chip de modelo — vive ao lado do `WorkspaceSelector` no rodapé do
 * composer. Reaproveita o MESMO padrão visual do seletor de workspace
 * (botão compacto + dropdown em popover com lista rolável, item ativo
 * marcado com `Check`, descrição secundária abaixo do nome) — o Vectora
 * não deve ter dois "estilos" de seletor coexistindo (ver
 * `workspace-selector.tsx`).
 */

import { useEffect, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

import { ProviderIcon } from "@/components/icons/provider-icons";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  getAllowedModels,
  getModelDisplayName,
  getModelProvider,
  type ModelOption,
} from "@/lib/config/deployment-config";
import { m } from "@/lib/paraglide/messages";

interface ModelSelectorProps {
  value: string;
  onChange: (model: string) => void;
  compact?: boolean;
}

export function ModelSelector({
  value,
  onChange,
  compact = false,
}: ModelSelectorProps) {
  const allowedModels = getAllowedModels();
  const [open, setOpen] = useState(false);
  // Providers com API key configurada (backend). null = ainda não carregado →
  // mostra todos; lista vazia/erro também cai no fallback de mostrar todos para
  // nunca travar o usuário sem opções.
  const [configuredProviders, setConfiguredProviders] = useState<
    string[] | null
  >(null);

  useEffect(() => {
    if (typeof fetch === "undefined") return;
    let alive = true;
    fetch("/models/providers")
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { providers?: string[] } | null) => {
        if (alive && Array.isArray(data?.providers))
          setConfiguredProviders(data.providers);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Esconde modelos cujo provider não tem credencial. Mantém sempre o modelo
  // ativo visível (mesmo sem key) para não sumir com a seleção atual.
  const visibleModels =
    configuredProviders && configuredProviders.length > 0
      ? allowedModels.filter(
          (model) =>
            model === value ||
            configuredProviders.includes(getModelProvider(model)),
        )
      : allowedModels;

  const activeLabel = getModelDisplayName(value as ModelOption) || value;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className={
            compact
              ? "flex items-center gap-1.5 h-7 px-2 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors select-none min-w-0 max-w-[160px]"
              : "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm text-foreground/80 hover:text-foreground hover:bg-muted/50 transition-colors select-none max-w-[200px]"
          }
          title={m.model_select_title()}
        >
          <ProviderIcon
            provider={getModelProvider(value as ModelOption)}
            className={`shrink-0 text-muted-foreground ${compact ? "w-3.5 h-3.5" : "w-4 h-4"}`}
          />
          <span className="truncate font-medium">{activeLabel}</span>
          <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground [&_svg]:opacity-70" />
        </button>
      </PopoverTrigger>

      {/* Portal (via PopoverContent) — escapa de qualquer ancestral com
          overflow/stacking context próprio (composer, split-pane do
          workbench). Sem isso o dropdown ficava cortado/atrás da sidebar
          de ícones do workbench quando o chat renderizava num painel
          estreito. */}
      <PopoverContent
        align="start"
        side={compact ? "top" : "bottom"}
        sideOffset={6}
        className="z-50 w-72 rounded-lg border border-border bg-background shadow-xl p-0 py-1"
      >
        <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {m.model_select_title()}
        </div>

        <div className="max-h-72 overflow-y-auto">
          {visibleModels.map((model) => (
            <button
              key={model}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent text-left transition-colors"
              onClick={() => {
                onChange(model);
                setOpen(false);
              }}
            >
              {model === value ? (
                <Check className="w-4 h-4 shrink-0 text-primary" />
              ) : (
                <ProviderIcon
                  provider={getModelProvider(model)}
                  className="w-4 h-4 shrink-0 text-muted-foreground"
                />
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium text-foreground">
                  {getModelDisplayName(model)}
                </span>
              </span>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
