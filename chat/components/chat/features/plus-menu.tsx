"use client";

/**
 * PlusMenu (R3)
 *
 * Substitui o botão único de anexo por um menu popover:
 *   - Adicionar arquivos ou fotos  → fluxo de upload existente
 *   - Adicionar pasta              → trust dialog do workspace
 *   - Comandos de barra            → insere "/" no input (opcional)
 */

import { useEffect, useRef, useState } from "react";
import {
  Database,
  FolderPlus,
  Paperclip,
  Plug,
  Plus,
  Share2,
  Slash,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { useSettingsDialogStore } from "@/lib/stores/settings-dialog-store";
import { WorkspaceTrustDialog } from "@/components/sidebar/workspace-trust-dialog";

interface PlusMenuProps {
  disabled?: boolean;
  onAddFiles: (e: React.MouseEvent) => void;
  /** Insere "/" no input para disparar o autocomplete de comandos (opcional). */
  onSlashCommands?: () => void;
}

export function PlusMenu({
  disabled,
  onAddFiles,
  onSlashCommands,
}: PlusMenuProps) {
  const t = useT();
  const openSettings = useSettingsDialogStore((s) => s.openAt);
  const pushDraft = useChatInputStore((s) => s.pushDraft);
  const [open, setOpen] = useState(false);
  const [trustOpen, setTrustOpen] = useState(false);
  const [ingestOpen, setIngestOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <Button
        onClick={() => setOpen((o) => !o)}
        variant="ghost"
        size="sm"
        disabled={disabled}
        className="group h-9 w-9 p-0 mb-0.5 rounded-full bg-muted/50 hover:bg-primary/10 text-muted-foreground hover:text-primary border-0 flex-shrink-0 transition-all duration-200 hover:scale-105 active:scale-95"
        type="button"
        aria-label="+"
        aria-expanded={open}
      >
        <Plus className="w-4.5 h-4.5" />
      </Button>

      {open && (
        <div className="absolute left-0 bottom-11 z-50 w-60 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-bottom-2">
          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
            onClick={(e) => {
              setOpen(false);
              onAddFiles(e);
            }}
          >
            <Paperclip className="w-4 h-4 shrink-0 text-muted-foreground" />
            {t("plus.add_files")}
          </button>

          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
            onClick={() => {
              setOpen(false);
              setTrustOpen(true);
            }}
          >
            <FolderPlus className="w-4 h-4 shrink-0 text-muted-foreground" />
            {t("plus.add_folder")}
          </button>

          {/* Abre o directory browser real (mesmo do trust). Ao confirmar,
              encaminha o path para o input como prompt — o agente delega
              para a tool ingest_docs. */}
          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
            onClick={() => {
              setOpen(false);
              setIngestOpen(true);
            }}
          >
            <Database className="w-4 h-4 shrink-0 text-muted-foreground" />
            {t("plus.ingest_folder")}
          </button>

          {onSlashCommands && (
            <button
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
              onClick={() => {
                setOpen(false);
                onSlashCommands();
              }}
            >
              <Slash className="w-4 h-4 shrink-0 text-muted-foreground" />
              {t("plus.slash_commands")}
            </button>
          )}

          <div className="border-t border-border/60 my-1" />

          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
            onClick={() => {
              setOpen(false);
              openSettings("integracoes");
            }}
          >
            <Share2 className="w-4 h-4 shrink-0 text-muted-foreground" />
            {t("plus.connectors")}
          </button>

          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
            onClick={() => {
              setOpen(false);
              openSettings("plugins");
            }}
          >
            <Plug className="w-4 h-4 shrink-0 text-muted-foreground" />
            {t("plus.plugins")}
          </button>
        </div>
      )}

      <WorkspaceTrustDialog open={trustOpen} onOpenChange={setTrustOpen} />
      <WorkspaceTrustDialog
        open={ingestOpen}
        onOpenChange={setIngestOpen}
        mode="ingest"
        onConfirmPath={(path) => {
          pushDraft(t("plus.ingest_prompt", { path }));
        }}
      />
    </div>
  );
}
