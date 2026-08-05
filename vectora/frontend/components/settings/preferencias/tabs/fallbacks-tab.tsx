"use client";

/**
 * FallbacksTab — ordem de fallback de modelos LLM.
 *
 * Extraído de `preferencias-tab.tsx` (aba "Geral") pra aba própria — é uma
 * preferência cross-provider (a ordem vale pra qualquer provider ativo), não
 * config de um gateway específico, então não se encaixa em Provider Routing
 * (Ambiente) nem faz sentido misturado com tema/idioma/font-scale em "Geral".
 */

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  getAllowedModels,
  getModelDisplayName,
  getModelProvider,
  type ModelOption,
} from "@/lib/config/deployment-config";
import { ProviderIcon } from "@/components/icons/provider-icons";
import { m } from "@/lib/paraglide/messages";

async function fetchFallbackOrder(): Promise<string[]> {
  const res = await fetch("/admin/model/fallback-order");
  if (!res.ok) return [];
  const data = (await res.json()) as { fallback_order: string[] };
  return data.fallback_order ?? [];
}

async function saveFallbackOrder(order: string[]): Promise<void> {
  await fetch("/admin/model/fallback-order", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order }),
  });
}

export function FallbacksTab() {
  const [order, setOrder] = useState<string[]>([]);
  const [addModel, setAddModel] = useState<string>("");

  useEffect(() => {
    fetchFallbackOrder()
      .then(setOrder)
      .catch(() => setOrder([]));
  }, []);

  const persist = useCallback(async (next: string[]) => {
    setOrder(next);
    await saveFallbackOrder(next);
  }, []);

  const moveUp = (i: number) => {
    if (i === 0) return;
    const next = [...order];
    [next[i - 1], next[i]] = [next[i], next[i - 1]];
    persist(next);
  };

  const moveDown = (i: number) => {
    if (i === order.length - 1) return;
    const next = [...order];
    [next[i], next[i + 1]] = [next[i + 1], next[i]];
    persist(next);
  };

  const remove = (i: number) => {
    persist(order.filter((_, idx) => idx !== i));
  };

  const add = () => {
    if (!addModel || order.includes(addModel)) return;
    persist([...order, addModel]);
    setAddModel("");
  };

  const available = getAllowedModels().filter((mid) => !order.includes(mid));

  return (
    <div className="space-y-2">
      <Label>{m.prefs_fallback_order_title()}</Label>
      <p className="text-xs text-muted-foreground">
        {m.prefs_fallback_order_help()}
      </p>

      {order.length === 0 ? (
        <p className="text-xs text-muted-foreground italic py-1">
          {m.prefs_fallback_order_empty()}
        </p>
      ) : (
        <ul className="space-y-1">
          {order.map((mid, i) => (
            <li
              key={mid}
              className="flex items-center gap-2 rounded-md border border-border px-2 py-1.5 bg-muted/30 text-sm"
            >
              <ProviderIcon
                provider={getModelProvider(mid as ModelOption)}
                className="w-3.5 h-3.5 shrink-0 text-muted-foreground"
              />
              <span className="flex-1 truncate">
                {getModelDisplayName(mid as ModelOption) || mid}
              </span>
              <button
                onClick={() => moveUp(i)}
                disabled={i === 0}
                title={m.prefs_fallback_order_move_up()}
                aria-label={m.prefs_fallback_order_move_up()}
                className="p-1 rounded hover:bg-muted disabled:opacity-30"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => moveDown(i)}
                disabled={i === order.length - 1}
                title={m.prefs_fallback_order_move_down()}
                aria-label={m.prefs_fallback_order_move_down()}
                className="p-1 rounded hover:bg-muted disabled:opacity-30"
              >
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => remove(i)}
                title={m.prefs_fallback_order_remove()}
                aria-label={m.prefs_fallback_order_remove()}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {available.length > 0 && (
        <div className="flex gap-2 pt-1">
          <Select value={addModel} onValueChange={setAddModel}>
            <SelectTrigger className="flex-1 h-8 text-xs">
              <SelectValue
                placeholder={m.prefs_fallback_order_add_placeholder()}
              />
            </SelectTrigger>
            <SelectContent>
              {available.map((mid) => (
                <SelectItem key={mid} value={mid} className="text-xs">
                  {getModelDisplayName(mid as ModelOption) || mid}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            className="h-8 px-3 text-xs shrink-0"
            onClick={add}
            disabled={!addModel}
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            {m.prefs_fallback_order_add()}
          </Button>
        </div>
      )}
    </div>
  );
}
