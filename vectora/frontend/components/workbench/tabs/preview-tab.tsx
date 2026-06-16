"use client";

/**
 * PreviewTab — preview de arquivo/media.
 *
 * Reutiliza FileViewer (já mapeia image/vídeo/áudio/pdf).
 * Pode ser aberto via:
 * - Clique em arquivo no Files/Storage tab
 * - Command/shortcut para "Preview Current File"
 * - Artifact preview no Tasks tab
 */

import { useState } from "react";
import { X } from "lucide-react";
import { useT } from "@/lib/i18n";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

interface PreviewTabProps {
  threadId: string;
  /** Arquivo a visualizar (path relativo ao workspace). */
  filePath?: string;
}

export function PreviewTab({
  threadId,
  filePath: initialPath,
}: PreviewTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";
  const [filePath, setFilePath] = useState<string | undefined>(initialPath);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [mimeType, setMimeType] = useState<string | null>(null);

  const loadFile = async (path: string) => {
    if (!wsId) {
      setError(t("workbench.files.no_workspace"));
      return;
    }

    setIsLoading(true);
    setError(null);
    setContent(null);

    try {
      const qs = new URLSearchParams({ path });
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/fs/raw?${qs}`,
      );

      if (!res.ok) {
        setError(`Failed to load: ${res.statusText}`);
        return;
      }

      const mime = res.headers.get("content-type") || "text/plain";
      setMimeType(mime);

      if (
        mime.startsWith("image/") ||
        mime.startsWith("video/") ||
        mime.startsWith("audio/")
      ) {
        // Para mídia, usa blob URL
        const blob = await res.blob();
        setContent(URL.createObjectURL(blob));
      } else if (mime.includes("pdf")) {
        // Para PDF, também usa blob
        const blob = await res.blob();
        setContent(URL.createObjectURL(blob));
      } else {
        // Para texto, lê como string
        setContent(await res.text());
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("workbench.files.read_only_truncated"),
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!filePath) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-6xl">👀</div>
        <p className="text-sm text-muted-foreground">
          Selecione um arquivo para visualizar
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="mb-2 text-sm font-medium">
            {t("input.loading_placeholder")}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-sm text-destructive">{error}</div>
        <button
          onClick={() => loadFile(filePath)}
          className="inline-block rounded bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20"
        >
          {t("workbench.files.refresh")}
        </button>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-sm text-muted-foreground">
          {t("workbench.files.binary")}
        </div>
      </div>
    );
  }

  // Renderiza baseado no tipo MIME
  if (mimeType?.startsWith("image/")) {
    return (
      <div className="h-full flex items-center justify-center p-4 bg-background/50">
        <img
          src={content}
          alt={filePath}
          className="max-w-full max-h-full object-contain"
        />
      </div>
    );
  }

  if (mimeType?.startsWith("video/")) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <video src={content} controls className="max-w-full max-h-full" />
      </div>
    );
  }

  if (mimeType?.startsWith("audio/")) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 p-6">
        <audio src={content} controls className="w-full max-w-md" />
        <p className="text-xs text-muted-foreground">{filePath}</p>
      </div>
    );
  }

  if (mimeType?.includes("pdf")) {
    return (
      <iframe
        src={`${content}#toolbar=0`}
        className="h-full w-full border-0"
        title={filePath}
      />
    );
  }

  // Text/code preview
  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b border-border/60 px-3 py-2 flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground truncate">
          {filePath}
        </p>
      </div>
      <pre className="flex-1 overflow-auto custom-scrollbar p-4 font-mono text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap break-words bg-background/50">
        {content}
      </pre>
    </div>
  );
}
