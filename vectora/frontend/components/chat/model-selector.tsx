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

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

import { useT } from "@/lib/i18n";
import { ProviderIcon } from "@/components/icons/provider-icons";
import {
  getAllowedModels,
  getModelDisplayName,
  getModelProvider,
  type ModelOption,
} from "@/lib/config/deployment-config";

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
  const t = useT();
  const allowedModels = getAllowedModels();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const activeLabel = getModelDisplayName(value as ModelOption) || value;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={
          compact
            ? "flex items-center gap-1.5 h-7 px-2 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors select-none min-w-0 max-w-[160px]"
            : "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm text-foreground/80 hover:text-foreground hover:bg-muted/50 transition-colors select-none max-w-[200px]"
        }
        title={t("model.select_title")}
        aria-expanded={open}
      >
        <ProviderIcon
          provider={getModelProvider(value as ModelOption)}
          className={`shrink-0 text-muted-foreground ${compact ? "w-3.5 h-3.5" : "w-4 h-4"}`}
        />
        <span className="truncate font-medium">{activeLabel}</span>
        <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground [&_svg]:opacity-70" />
      </button>

      {open && (
        <div
          className={`absolute left-0 z-50 w-72 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-top-2 ${
            compact ? "bottom-9" : "top-10"
          }`}
        >
          <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {t("model.select_title")}
          </div>

          <div className="max-h-72 overflow-y-auto">
            {allowedModels.map((model) => (
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
        </div>
      )}
    </div>
  );
}
