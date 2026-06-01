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

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, CornerDownLeft, Folder, GitBranch } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useWorkspacesStore,
  type BrowseResult,
} from "@/lib/stores/workspaces-store";
import { useT } from "@/lib/i18n";

interface WorkspaceTrustDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** `trust`: adiciona pasta como workspace confiável (default).
   *  `ingest`: usa o directory browser apenas para escolher a pasta e
   *  encaminha o caminho para o chat indexar via tool ingest_docs. */
  mode?: "trust" | "ingest";
  /** Callback opcional disparado no confirmar — recebe o path absoluto. */
  onConfirmPath?: (path: string) => void;
  /** Pré-navega para esse caminho ao abrir (F.3.5 — quick access). */
  initialPath?: string;
}

export function WorkspaceTrustDialog({
  open,
  onOpenChange,
  mode = "trust",
  onConfirmPath,
  initialPath,
}: WorkspaceTrustDialogProps) {
  const t = useT();
  const create = useWorkspacesStore((s) => s.create);

  const [listing, setListing] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [gitInit, setGitInit] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Evita resetar o input enquanto o usuário digita um path novo —
  // só sincroniza quando a navegação (clique/Enter) muda o listing.path.
  const lastLoadedPathRef = useRef<string | null>(null);

  /** Fetch direto: precisamos distinguir 403 (fora de safe-root) de
   *  outros erros para mostrar mensagem inline. O `browse` do store
   *  achata erros em `null` e perde essa informação. */
  const load = useCallback(async (path?: string) => {
    setLoading(true);
    setError(null);
    try {
      const q = path ? `?path=${encodeURIComponent(path)}` : "";
      const res = await fetch(`/api/workspaces/browse${q}`);
      if (res.status === 403) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Caminho fora das pastas seguras.");
        return;
      }
      if (!res.ok) {
        setError(`Erro ao listar (${res.status}).`);
        return;
      }
      const data = (await res.json()) as BrowseResult;
      setListing(data);
      lastLoadedPathRef.current = data.path;
      setPathInput(data.path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha de rede.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setListing(null);
      setGitInit(true);
      setError(null);
      setPathInput(initialPath ?? "");
      lastLoadedPathRef.current = null;
      void load(initialPath || undefined);
    }
  }, [open, load, initialPath]);

  const handleGo = () => {
    const target = pathInput.trim();
    if (!target || target === lastLoadedPathRef.current) return;
    void load(target);
  };

  const handleConfirm = async () => {
    if (!listing) return;
    if (mode === "ingest") {
      onConfirmPath?.(listing.path);
      onOpenChange(false);
      return;
    }
    setSubmitting(true);
    const ws = await create(listing.path, { trust: true, git_init: gitInit });
    setSubmitting(false);
    if (ws) onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {mode === "ingest"
              ? t("workspace.ingest_title")
              : t("workspace.trust_title")}
          </DialogTitle>
          <DialogDescription>
            {mode === "ingest"
              ? t("workspace.ingest_desc")
              : t("workspace.trust_desc")}
          </DialogDescription>
        </DialogHeader>

        {/* Path editável — Enter ou botão "Ir" navega para o destino.
            Backend recusa (403) se o usuário comum sair das pastas seguras. */}
        <div className="flex items-center gap-1.5">
          <Input
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleGo();
              }
            }}
            placeholder={t("workspace.path_placeholder")}
            spellCheck={false}
            className="h-8 text-xs font-mono"
            disabled={loading}
          />
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 px-2"
            onClick={handleGo}
            disabled={loading || !pathInput.trim()}
            title={t("workspace.go")}
          >
            <CornerDownLeft className="w-3.5 h-3.5" />
          </Button>
        </div>

        {error && (
          <div className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
            {error}
          </div>
        )}

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

        {mode === "trust" && (
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
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("workspace.cancel")}
          </Button>
          <Button onClick={handleConfirm} disabled={!listing || submitting}>
            {mode === "ingest"
              ? t("workspace.ingest_confirm")
              : t("workspace.trust_confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
