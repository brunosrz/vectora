"use client";

/**
 * WorkspaceTrustDialog (Q6)
 *
 * Fluxo de "trust folder": directory browser para escolher uma pasta,
 * confirmação explícita de confiança (explica os guard rails de escopo) e
 * checkbox para inicializar git se a pasta ainda não for um repositório.
 *
 * Ao confiar, registra a pasta como workspace ativo via store.create().
 */

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, Folder, FolderOpen, GitBranch } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useWorkspacesStore,
  type BrowseResult,
} from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";

interface WorkspaceTrustDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WorkspaceTrustDialog({
  open,
  onOpenChange,
}: WorkspaceTrustDialogProps) {
  const t = useT();
  const browse = useWorkspacesStore((s) => s.browse);
  const create = useWorkspacesStore((s) => s.create);

  const [listing, setListing] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [gitInit, setGitInit] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(
    async (path?: string) => {
      setLoading(true);
      const result = await browse(path);
      if (result) setListing(result);
      setLoading(false);
    },
    [browse],
  );

  useEffect(() => {
    if (open) {
      setListing(null);
      setGitInit(true);
      void load();
    }
  }, [open, load]);

  const handleConfirm = async () => {
    if (!listing) return;
    setSubmitting(true);
    const ws = await create(listing.path, { trust: true, git_init: gitInit });
    setSubmitting(false);
    if (ws) onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("workspace.trust_title")}</DialogTitle>
          <DialogDescription>{t("workspace.trust_desc")}</DialogDescription>
        </DialogHeader>

        {/* Caminho atual */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground font-mono truncate">
          <FolderOpen className="w-4 h-4 shrink-0 text-primary" />
          <span className="truncate">{listing?.path ?? "…"}</span>
        </div>

        {/* Directory browser */}
        <ScrollArea className="h-64 rounded-md border border-border">
          <div className="p-1">
            {listing?.parent && (
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent text-left transition-colors"
                onClick={() => load(listing.parent!)}
                disabled={loading}
              >
                <ChevronLeft className="w-4 h-4 shrink-0 text-muted-foreground" />
                {t("workspace.browse_up")}
              </button>
            )}

            {listing && listing.entries.length === 0 && (
              <p className="px-3 py-4 text-sm text-muted-foreground text-center">
                {t("workspace.browse_empty")}
              </p>
            )}

            {listing?.entries.map((entry) => (
              <button
                key={entry.path}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent text-left transition-colors"
                onClick={() => load(entry.path)}
                disabled={loading}
              >
                <Folder className="w-4 h-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{entry.name}</span>
              </button>
            ))}
          </div>
        </ScrollArea>

        {/* git init opt-in */}
        <label className="flex items-center gap-2 text-sm text-foreground/80 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={gitInit}
            onChange={(e) => setGitInit(e.target.checked)}
            className="rounded border-border"
          />
          <GitBranch className="w-4 h-4 shrink-0 text-muted-foreground" />
          {t("workspace.git_init_label")}
        </label>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("workspace.cancel")}
          </Button>
          <Button onClick={handleConfirm} disabled={!listing || submitting}>
            {t("workspace.trust_confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
