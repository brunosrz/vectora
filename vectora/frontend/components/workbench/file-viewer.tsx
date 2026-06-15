"use client";

/**
 * Viewer de arquivo compartilhado entre o painel docked (files-tab) e as
 * janelas flutuantes (windows). Concentra a detecção de mídia e o render de
 * imagem/vídeo/áudio/pdf a partir do endpoint de bytes crus
 * `GET /workspaces/{id}/fs/raw`. Texto é lido do `GET /file` (truncado).
 */

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useT } from "@/lib/i18n";

export type MediaKind = "image" | "video" | "audio" | "pdf";

const MEDIA_BY_EXT: Record<string, MediaKind> = {
  png: "image",
  jpg: "image",
  jpeg: "image",
  gif: "image",
  webp: "image",
  avif: "image",
  bmp: "image",
  ico: "image",
  svg: "image",
  mp4: "video",
  webm: "video",
  mov: "video",
  mkv: "video",
  m4v: "video",
  ogv: "video",
  mp3: "audio",
  wav: "audio",
  ogg: "audio",
  flac: "audio",
  m4a: "audio",
  aac: "audio",
  pdf: "pdf",
};

/** Tipo de mídia do path (por extensão), ou null para texto/binário comum. */
export function getMediaKind(path: string): MediaKind | null {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return MEDIA_BY_EXT[ext] ?? null;
}

/** URL same-origin dos bytes crus do arquivo (preview de mídia + download). */
export function rawFileUrl(workspaceId: string, path: string): string {
  const qs = new URLSearchParams({ path });
  return `/workspaces/${encodeURIComponent(workspaceId)}/fs/raw?${qs}`;
}

/** Render de mídia (imagem/vídeo/áudio/pdf) a partir do endpoint raw. */
export function MediaView({
  kind,
  workspaceId,
  path,
}: {
  kind: MediaKind;
  workspaceId: string;
  path: string;
}) {
  const src = rawFileUrl(workspaceId, path);
  if (kind === "image") {
    return (
      <div className="flex items-center justify-center h-full w-full overflow-auto p-2">
        <img
          src={src}
          alt={path}
          className="max-w-full max-h-full object-contain"
        />
      </div>
    );
  }
  if (kind === "video") {
    return (
      <div className="flex items-center justify-center h-full w-full bg-black/40">
        <video src={src} controls className="max-w-full max-h-full" />
      </div>
    );
  }
  if (kind === "audio") {
    return (
      <div className="flex items-center justify-center h-full w-full p-4">
        <audio src={src} controls className="w-full max-w-xl" />
      </div>
    );
  }
  // pdf — render nativo do browser via <object> (sem iframe).
  return (
    <object
      data={src}
      type="application/pdf"
      className="w-full h-full"
      aria-label={path}
    >
      <a href={src} className="text-primary hover:underline">
        {path}
      </a>
    </object>
  );
}

interface RawText {
  kind: "text" | "binary";
  content?: string;
  size: number;
  truncated?: boolean;
}

/**
 * Viewer completo e autônomo (read-only) — usado pelas janelas flutuantes.
 * Decide entre mídia (raw) e texto (busca o conteúdo do `GET /file`).
 */
export function FileViewer({
  workspaceId,
  path,
}: {
  workspaceId: string;
  path: string;
}) {
  const t = useT();
  const media = getMediaKind(path);
  const [text, setText] = useState<RawText | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (media) return; // mídia não busca conteúdo de texto
    let cancelled = false;
    setLoading(true);
    const qs = new URLSearchParams({ path });
    fetch(`/workspaces/${encodeURIComponent(workspaceId)}/file?${qs}`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? (r.json() as Promise<RawText>) : null))
      .then((data) => {
        if (!cancelled) setText(data);
      })
      .catch(() => {
        if (!cancelled) setText(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, path, media]);

  if (media) {
    return <MediaView kind={media} workspaceId={workspaceId} path={path} />;
  }
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (text?.kind === "binary") {
    return (
      <div className="p-3 text-xs text-muted-foreground">
        {t("workbench.files.binary", { size: text.size })}{" "}
        <a
          href={rawFileUrl(workspaceId, path)}
          download
          className="text-primary hover:underline"
        >
          {t("workbench.files.download")}
        </a>
      </div>
    );
  }
  return (
    <div className="h-full overflow-auto p-2">
      <pre className="text-xs font-mono whitespace-pre-wrap break-all">
        {text?.content ?? ""}
      </pre>
      {text?.truncated && (
        <p className="text-[10px] text-muted-foreground mt-2">
          {t("workbench.files.read_only_truncated")}
        </p>
      )}
    </div>
  );
}
