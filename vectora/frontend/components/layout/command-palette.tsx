"use client";

/**
 * CommandPalette — buscador de ações acessível via Ctrl+K / ⌘K.
 *
 * Lista comandos predefinidos (nova conversa, configurações, workbench…) e
 * filtra pelo texto digitado. Navegação por ↑↓ + Enter, fecha no Esc.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PaletteCommand {
  id: string;
  /** Rótulo exibido na lista. */
  label: string;
  /** Categoria (agrupamento visual). */
  category: string;
  /** Função executada ao selecionar. */
  run: () => void;
  /** Atalho exibido à direita (opcional). */
  shortcut?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: PaletteCommand[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CommandPalette({
  open,
  onOpenChange,
  commands,
}: CommandPaletteProps) {
  const t = useT();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Filtra por query (case-insensitive, busca em label + category).
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q),
    );
  }, [commands, query]);

  // Reset ao abrir.
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      // Foco adiado para o próximo frame (Dialog precisa montar primeiro).
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Mantém activeIndex dentro dos limites quando o filtro muda.
  useEffect(() => {
    setActiveIndex((i) =>
      filtered.length === 0 ? 0 : Math.min(i, filtered.length - 1),
    );
  }, [filtered.length]);

  // Scroll do item ativo para a viewport.
  useEffect(() => {
    const li = listRef.current?.children[activeIndex] as
      | HTMLElement
      | undefined;
    li?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const execute = useCallback(
    (cmd: PaletteCommand) => {
      onOpenChange(false);
      // Executa após fechar para não colidir com o foco do Dialog.
      setTimeout(() => cmd.run(), 50);
    },
    [onOpenChange],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % Math.max(filtered.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(
        (i) =>
          (i - 1 + Math.max(filtered.length, 1)) % Math.max(filtered.length, 1),
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = filtered[activeIndex];
      if (cmd) execute(cmd);
    }
    // Esc fecha via Dialog (onOpenChange)
  }

  // Agrupa por categoria para exibição.
  const grouped = useMemo(() => {
    const map: Record<string, PaletteCommand[]> = {};
    for (const cmd of filtered) {
      (map[cmd.category] ??= []).push(cmd);
    }
    return map;
  }, [filtered]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-0 gap-0 overflow-hidden">
        <DialogHeader className="sr-only">
          <DialogTitle>{t("palette.title")}</DialogTitle>
          <DialogDescription>{t("palette.description")}</DialogDescription>
        </DialogHeader>

        {/* Input de busca */}
        <div className="flex items-center border-b border-border px-4 py-3 gap-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="shrink-0 text-muted-foreground"
            aria-hidden
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder={t("palette.placeholder")}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            aria-label={t("palette.title")}
            aria-autocomplete="list"
            role="combobox"
            aria-expanded={filtered.length > 0}
            aria-activedescendant={
              filtered[activeIndex]
                ? `palette-cmd-${filtered[activeIndex].id}`
                : undefined
            }
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label={t("palette.clear")}
            >
              ✕
            </button>
          )}
        </div>

        {/* Lista de comandos */}
        <ul
          ref={listRef}
          role="listbox"
          aria-label={t("palette.title")}
          className="max-h-80 overflow-y-auto py-1"
        >
          {filtered.length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-muted-foreground">
              {t("palette.no_results")}
            </li>
          ) : (
            Object.entries(grouped).map(([category, cmds]) => {
              // Calcula o índice global do primeiro comando desta categoria.
              const firstIdx = filtered.indexOf(cmds[0]!);
              return (
                <li key={category} role="presentation">
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                    {category}
                  </div>
                  <ul role="presentation">
                    {cmds.map((cmd, i) => {
                      const globalIdx = firstIdx + i;
                      const isActive = globalIdx === activeIndex;
                      return (
                        <li
                          key={cmd.id}
                          id={`palette-cmd-${cmd.id}`}
                          role="option"
                          aria-selected={isActive}
                          onClick={() => execute(cmd)}
                          onMouseEnter={() => setActiveIndex(globalIdx)}
                          className={`flex items-center justify-between mx-1 px-3 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                            isActive
                              ? "bg-primary/15 text-foreground"
                              : "text-foreground/80 hover:bg-muted/50"
                          }`}
                        >
                          <span>{cmd.label}</span>
                          {cmd.shortcut && (
                            <kbd className="ml-auto text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded border border-border">
                              {cmd.shortcut}
                            </kbd>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </li>
              );
            })
          )}
        </ul>

        {/* Rodapé — dica de navegação */}
        <div className="flex items-center gap-4 border-t border-border px-4 py-2 text-[10px] text-muted-foreground/60 select-none">
          <span>↑↓ {t("palette.hint_navigate")}</span>
          <span>↵ {t("palette.hint_run")}</span>
          <span>Esc {t("palette.hint_close")}</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
