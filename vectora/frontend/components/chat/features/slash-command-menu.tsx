"use client";

/**
 * SlashCommandMenu (Bloco H)
 *
 * Popup de autocomplete exibido ao digitar "/" no início do input. Lista os
 * comandos registrados; selecionar preenche o input com o comando (o envio é
 * tratado pelo dispatch no chat-interface).
 */

import { Slash } from "lucide-react";

import {
  filterCommands,
  isSlashQuery,
  type SlashCommand,
} from "@/lib/constants/slash-commands";
import { useT } from "@/lib/i18n";

interface SlashCommandMenuProps {
  input: string;
  onSelect: (command: SlashCommand) => void;
}

export function SlashCommandMenu({ input, onSelect }: SlashCommandMenuProps) {
  const t = useT();

  // Só aparece enquanto o usuário ainda escolhe o comando (sem espaço/arg).
  if (!isSlashQuery(input)) return null;
  const commands = filterCommands(input);
  if (commands.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 mb-2 w-80 rounded-lg border border-border bg-background shadow-xl py-1 z-50 animate-in fade-in slide-in-from-bottom-2">
      <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
        <Slash className="w-3 h-3" />
        {t("slash.title")}
      </div>
      {commands.map((cmd) => (
        <button
          key={cmd.name}
          type="button"
          onMouseDown={(e) => {
            // onMouseDown (não onClick) evita blur do textarea antes da seleção.
            e.preventDefault();
            onSelect(cmd);
          }}
          className="w-full flex items-center justify-between gap-3 px-3 py-2 text-sm hover:bg-accent text-left transition-colors"
        >
          <span className="font-mono text-foreground">{cmd.usage}</span>
          <span className="text-xs text-muted-foreground truncate">
            {t(cmd.descKey)}
          </span>
        </button>
      ))}
    </div>
  );
}
