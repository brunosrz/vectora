"use client";

/**
 * FilesTab (T6 + T11.2 + T10.2 pin)
 *
 * Estado vive no workbench-store (slice `files`):
 *   - árvore expandida e entradas já carregadas → sobrevivem a remount
 *   - arquivo aberto + conteúdo → mesmo
 *   - filtro de busca → idem
 *
 * T10.2 — Pin de arquivo (persistido por threadId via `pinnedFiles`):
 *   - Seção "Fixados" no topo quando há pins
 *   - Botão pin/unpin aparece em hover no item file
 *
 * SWR via `useWorkbenchSWR`: render imediato do cache + revalidação
 * silenciosa quando stale. A verdade vive no backend.
 */

import {
  ChevronRight,
  File,
  FolderClosed,
  Loader2,
  Pin,
  PinOff,
  Search,
} from "lucide-react";
import { useCallback, useMemo } from "react";

import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type FileContent,
  type FileEntry,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

async function fetchTree(
  workspaceId: string,
  path: string,
): Promise<FileEntry[] | null> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/tree?${qs}`,
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.entries ?? [];
}

async function fetchFile(
  workspaceId: string,
  path: string,
): Promise<FileContent | null> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/file?${qs}`,
  );
  if (!res.ok) return null;
  return res.json();
}

/** Linha de arquivo na árvore — com botão pin/unpin em hover. */
function FileItem({
  threadId,
  entry,
  depth,
  onOpenFile,
}: {
  threadId: string;
  entry: FileEntry;
  depth: number;
  onOpenFile: (path: string) => void;
}) {
  const pinned = useWorkbenchStore((s) => s.isPinned(threadId, entry.path));
  const togglePinned = useWorkbenchStore((s) => s.togglePinned);
  const t = useT();
  return (
    <div
      className="group flex items-center px-2 py-0.5 text-xs hover:bg-muted/50 rounded-sm"
      style={{ paddingLeft: 8 + (depth + 1) * 12 }}
    >
      <span className="w-3" />
      <File className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
      <button
        onClick={() => onOpenFile(entry.path)}
        className="flex-1 text-left truncate text-foreground/80 hover:text-foreground ml-1"
      >
        {entry.name}
      </button>
      <button
        onClick={() => togglePinned(threadId, entry.path)}
        className={`shrink-0 p-0.5 rounded ${
          pinned
            ? "text-primary"
            : "text-muted-foreground/0 group-hover:text-muted-foreground hover:text-foreground"
        }`}
        aria-label={
          pinned ? t("workbench.files.unpin") : t("workbench.files.pin")
        }
        title={pinned ? t("workbench.files.unpin") : t("workbench.files.pin")}
      >
        {pinned ? <Pin className="w-3 h-3" /> : <Pin className="w-3 h-3" />}
      </button>
    </div>
  );
}

interface DirNodeProps {
  threadId: string;
  workspaceId: string;
  path: string;
  name: string;
  depth: number;
  filter: string;
  onOpenFile: (path: string) => void;
}

function DirNode({
  threadId,
  workspaceId,
  path,
  name,
  depth,
  filter,
  onOpenFile,
}: DirNodeProps) {
  const expanded = useWorkbenchStore((s) =>
    depth === 0 ? true : s.getFiles(workspaceId).expandedDirs.includes(path),
  );
  const entries = useWorkbenchStore(
    (s) => s.getFiles(workspaceId).entriesByDir[path],
  );
  const fetchedAt = useWorkbenchStore(
    (s) => s.getFiles(workspaceId).fetchedAt[path] ?? 0,
  );
  const toggleExpanded = useWorkbenchStore((s) => s.toggleExpanded);
  const setFilesEntries = useWorkbenchStore((s) => s.setFilesEntries);

  const revalidate = useCallback(async () => {
    const data = await fetchTree(workspaceId, path);
    if (data) setFilesEntries(workspaceId, path, data);
  }, [workspaceId, path, setFilesEntries]);

  useWorkbenchSWR({
    key: `files:${workspaceId}:${path}`,
    hasCache: Array.isArray(entries),
    isStale: Date.now() - fetchedAt > WORKBENCH_STALE_MS,
    revalidate,
    skip: !expanded,
  });

  const visible = useMemo(() => {
    if (!filter || !entries) return entries ?? [];
    const f = filter.toLowerCase();
    return entries.filter((e) => e.name.toLowerCase().includes(f));
  }, [entries, filter]);

  return (
    <div>
      {depth > 0 && (
        <button
          onClick={() => toggleExpanded(workspaceId, path)}
          className="w-full flex items-center gap-1 px-2 py-0.5 text-xs text-foreground/80 hover:bg-muted/50 rounded-sm"
          style={{ paddingLeft: 8 + depth * 12 }}
        >
          <ChevronRight
            className={`w-3 h-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
          <FolderClosed className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{name}</span>
        </button>
      )}
      {expanded && (
        <div>
          {!entries && (
            <div
              className="flex items-center gap-2 text-xs text-muted-foreground py-1"
              style={{ paddingLeft: 8 + (depth + 1) * 12 }}
            >
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>…</span>
            </div>
          )}
          {entries &&
            visible.map((entry) =>
              entry.kind === "dir" ? (
                <DirNode
                  key={entry.path}
                  threadId={threadId}
                  workspaceId={workspaceId}
                  path={entry.path}
                  name={entry.name}
                  depth={depth + 1}
                  filter={filter}
                  onOpenFile={onOpenFile}
                />
              ) : (
                <FileItem
                  key={entry.path}
                  threadId={threadId}
                  entry={entry}
                  depth={depth}
                  onOpenFile={onOpenFile}
                />
              ),
            )}
        </div>
      )}
    </div>
  );
}

/** Seção "Fixados" no topo — mostra os pins do thread. */
function PinnedSection({
  threadId,
  onOpenFile,
}: {
  threadId: string;
  onOpenFile: (path: string) => void;
}) {
  const t = useT();
  const pinned = useWorkbenchStore(
    (s) => s.pinnedFiles[threadId] ?? EMPTY_PINNED,
  );
  const togglePinned = useWorkbenchStore((s) => s.togglePinned);

  if (pinned.length === 0) return null;

  return (
    <div className="border-b border-border/40 pb-1 mb-1">
      <div className="px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {t("workbench.files.pinned")}
      </div>
      {pinned.map((path) => {
        const name = path.split(/[/\\]/).pop() ?? path;
        return (
          <div
            key={path}
            className="group flex items-center gap-1 px-2 py-0.5 text-xs hover:bg-muted/50 rounded-sm"
          >
            <Pin className="w-3 h-3 shrink-0 text-primary" />
            <button
              onClick={() => onOpenFile(path)}
              className="flex-1 text-left truncate text-foreground/80 hover:text-foreground"
              title={path}
            >
              {name}
            </button>
            <button
              onClick={() => togglePinned(threadId, path)}
              className="shrink-0 p-0.5 rounded text-muted-foreground/0 group-hover:text-muted-foreground hover:text-foreground"
              aria-label={t("workbench.files.unpin")}
              title={t("workbench.files.unpin")}
            >
              <PinOff className="w-3 h-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

/** Lista vazia estável (evita re-render por nova referência). */
const EMPTY_PINNED: string[] = [];

interface FilesTabProps {
  threadId: string;
}

export function FilesTab({ threadId }: FilesTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  const filter = useWorkbenchStore((s) => s.getFiles(wsId).filter);
  const openPath = useWorkbenchStore((s) => s.getFiles(wsId).openPath);
  const openContent = useWorkbenchStore((s) =>
    openPath ? s.getFiles(wsId).contents[openPath] : undefined,
  );
  const setFilesFilter = useWorkbenchStore((s) => s.setFilesFilter);
  const setOpenFile = useWorkbenchStore((s) => s.setOpenFile);
  const setFileContent = useWorkbenchStore((s) => s.setFileContent);

  const handleOpenFile = useCallback(
    (path: string) => {
      if (!wsId) return;
      setOpenFile(wsId, path);
    },
    [wsId, setOpenFile],
  );

  // Carrega o conteúdo do arquivo aberto via SWR.
  useWorkbenchSWR({
    key: `file:${wsId}:${openPath ?? ""}`,
    hasCache: openContent !== undefined,
    isStale: false, // conteúdo só revalida via invalidate (T11.5)
    revalidate: async () => {
      if (!wsId || !openPath) return;
      const data = await fetchFile(wsId, openPath);
      if (data) setFileContent(wsId, openPath, data);
    },
    skip: !openPath || !wsId,
  });

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground p-4 text-center">
        {t("workbench.files.no_workspace")}
      </div>
    );
  }

  const showViewer = openPath !== null;
  const loadingFile = showViewer && openContent === undefined;

  return (
    <div className="h-full flex flex-col">
      {/* Busca */}
      <div className="px-2 py-1.5 border-b border-border/60">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <Input
            value={filter}
            onChange={(e) => setFilesFilter(wsId, e.target.value)}
            placeholder={t("workbench.files.filter")}
            className="h-7 text-xs pl-7"
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        <PinnedSection threadId={threadId} onOpenFile={handleOpenFile} />
        <DirNode
          threadId={threadId}
          workspaceId={wsId}
          path=""
          name={workspace.name}
          depth={0}
          filter={filter}
          onOpenFile={handleOpenFile}
        />
      </div>

      {/* Viewer */}
      {showViewer && (
        <div className="border-t border-border/60 max-h-[50%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground">
              {openPath ?? "…"}
            </span>
            <button
              onClick={() => setOpenFile(wsId, null)}
              className="text-muted-foreground hover:text-foreground px-1"
              title={t("workbench.close")}
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-auto p-2">
            {loadingFile ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : openContent?.kind === "binary" ? (
              <p className="text-xs text-muted-foreground">
                {t("workbench.files.binary", { size: openContent.size })}
              </p>
            ) : (
              <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                {openContent?.content ?? ""}
              </pre>
            )}
            {openContent?.truncated && (
              <p className="text-[10px] text-muted-foreground mt-2">
                {t("workbench.files.truncated")}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
