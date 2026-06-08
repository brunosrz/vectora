"use client";

/**
 * FilesTab — explorador de arquivos do workspace ativo.
 *
 * Estado vive no workbench-store (slice `files`), sobrevivendo a remount:
 * árvore expandida e entradas carregadas, arquivo aberto + conteúdo, filtro
 * de busca. Arquivos fixados ("pin") persistem por threadId via `pinnedFiles`.
 *
 * Funcionalidades: toolbar (novo arquivo/pasta, refresh), criação inline na
 * árvore, delete em hover (arquivo e pasta) e botão @ que injeta o caminho
 * como @mention no chat.
 */

import {
  AtSign,
  ChevronRight,
  File,
  FilePlus,
  FolderClosed,
  FolderPlus,
  Loader2,
  Pin,
  PinOff,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import { useDelayedLoading } from "@/lib/hooks/use-delayed-loading";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type DiffSummary,
  type FileContent,
  type FileEntry,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { FileTreeSkeleton } from "./file-tree-skeleton";

// ---------------------------------------------------------------------------
// Badge de status git — derivado do diff porcelain por join client-side.
// ---------------------------------------------------------------------------

const GIT_BADGE_TONE: Record<string, string> = {
  M: "text-amber-500",
  A: "text-green-500",
  D: "text-destructive",
  R: "text-blue-400",
  "?": "text-muted-foreground",
};

/** Normaliza separadores para "/" (backend devolve POSIX). */
function norm(path: string): string {
  return path.replace(/\\/g, "/");
}

function GitBadge({ status }: { status?: string }) {
  if (!status) return null;
  return (
    <span
      className={`w-3 text-center font-bold shrink-0 text-[10px] ${
        GIT_BADGE_TONE[status] ?? "text-muted-foreground"
      }`}
      title={status}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

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

async function fetchDiffSummary(
  workspaceId: string,
): Promise<DiffSummary | null> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/diff`,
  );
  if (!res.ok) return null;
  return res.json();
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

async function apiFsCreate(
  workspaceId: string,
  type: "file" | "dir",
  path: string,
): Promise<boolean> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/fs/${type}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    },
  );
  return res.ok;
}

async function apiFsDelete(
  workspaceId: string,
  path: string,
  permanent = false,
): Promise<boolean> {
  const qs = new URLSearchParams({ path });
  if (permanent) qs.set("permanent", "true");
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/fs?${qs}`,
    { method: "DELETE" },
  );
  return res.ok;
}

// ---------------------------------------------------------------------------
// Estado de criação inline
// ---------------------------------------------------------------------------

interface CreatingState {
  type: "file" | "dir";
  parentDir: string; // path relativo do diretório onde criar
}

// ---------------------------------------------------------------------------
// FileItem
// ---------------------------------------------------------------------------

function FileItem({
  threadId,
  entry,
  depth,
  status,
  onOpenFile,
  onAddToContext,
  onDelete,
}: {
  threadId: string;
  entry: FileEntry;
  depth: number;
  status?: string;
  onOpenFile: (path: string) => void;
  onAddToContext?: (path: string) => void;
  onDelete: (path: string, name: string, permanent?: boolean) => void;
}) {
  const pinned = useWorkbenchStore((s) => s.isPinned(threadId, entry.path));
  const togglePinned = useWorkbenchStore((s) => s.togglePinned);
  const t = useT();

  return (
    <div
      tabIndex={0}
      className="group flex items-center px-2 py-0.5 text-xs hover:bg-muted/50 rounded-sm focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
      style={{ paddingLeft: 8 + (depth + 1) * 12 }}
      onKeyDown={(e) => {
        if (e.key === "Delete") {
          e.preventDefault();
          onDelete(entry.path, entry.name, e.shiftKey);
        }
      }}
    >
      <span className="w-3" />
      <File className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
      <button
        onClick={() => onOpenFile(entry.path)}
        className="flex-1 text-left truncate text-foreground/80 hover:text-foreground ml-1"
      >
        {entry.name}
      </button>
      <GitBadge status={status} />

      {/* Ações em hover */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {onAddToContext && (
          <button
            onClick={() => onAddToContext(entry.path)}
            className="p-0.5 rounded text-muted-foreground hover:text-foreground"
            aria-label={t("workbench.files.add_context")}
            title={t("workbench.files.add_context")}
          >
            <AtSign className="w-3 h-3" />
          </button>
        )}
        <button
          onClick={(e) => onDelete(entry.path, entry.name, e.shiftKey)}
          className="p-0.5 rounded text-muted-foreground hover:text-destructive"
          aria-label={t("workbench.files.delete")}
          title={`${t("workbench.files.delete")} (Shift: permanente)`}
        >
          <Trash2 className="w-3 h-3" />
        </button>
        <button
          onClick={() => togglePinned(threadId, entry.path)}
          className={`p-0.5 rounded ${
            pinned
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-label={
            pinned ? t("workbench.files.unpin") : t("workbench.files.pin")
          }
          title={pinned ? t("workbench.files.unpin") : t("workbench.files.pin")}
        >
          <Pin className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// InlineCreateInput — input que aparece na árvore para digitar nome
// ---------------------------------------------------------------------------

function InlineCreateInput({
  placeholder,
  onConfirm,
  onCancel,
  depth,
}: {
  placeholder: string;
  onConfirm: (name: string) => void;
  onCancel: () => void;
  depth: number;
}) {
  const [value, setValue] = useState("");

  return (
    <div
      className="flex items-center px-2 py-0.5"
      style={{ paddingLeft: 8 + (depth + 1) * 12 }}
    >
      <input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim()) {
            onConfirm(value.trim());
          } else if (e.key === "Escape") {
            onCancel();
          }
        }}
        onBlur={() => onCancel()}
        placeholder={placeholder}
        className="flex-1 text-xs bg-background border border-primary/60 rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-primary/40 font-mono"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// DirNode
// ---------------------------------------------------------------------------

interface DirNodeProps {
  threadId: string;
  workspaceId: string;
  path: string;
  name: string;
  depth: number;
  filter: string;
  statusByPath: Map<string, string>;
  onOpenFile: (path: string) => void;
  onAddToContext?: (path: string) => void;
  onDelete: (path: string, name: string, permanent?: boolean) => void;
  creating: CreatingState | null;
  onInlineCreate: (name: string) => void;
  onCancelCreate: () => void;
  onRequestCreate: (type: "file" | "dir", parentDir: string) => void;
}

function DirNode({
  threadId,
  workspaceId,
  path,
  name,
  depth,
  filter,
  statusByPath,
  onOpenFile,
  onAddToContext,
  onDelete,
  creating,
  onInlineCreate,
  onCancelCreate,
  onRequestCreate,
}: DirNodeProps) {
  const t = useT();
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

  // UX-9 — skeleton só na raiz (primeira carga da árvore); subpastas usam o
  // spinner inline de "…" para não competir visualmente com o nó pai.
  const showRootSkeleton = useDelayedLoading(
    depth === 0 && expanded && !entries,
  );

  const visible = useMemo(() => {
    if (!filter || !entries) return entries ?? [];
    const f = filter.toLowerCase();
    return entries.filter((e) => e.name.toLowerCase().includes(f));
  }, [entries, filter]);

  // Verifica se o inline create input deve aparecer neste diretório
  const showCreateHere =
    creating !== null && creating.parentDir === path && expanded;

  return (
    <div>
      {depth > 0 && (
        <div
          tabIndex={0}
          className="group flex items-center px-2 py-0.5 text-xs text-foreground/80 hover:bg-muted/50 rounded-sm focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
          onKeyDown={(e) => {
            if (e.key === "Delete") {
              e.preventDefault();
              onDelete(path, name, e.shiftKey);
            }
          }}
        >
          <button
            onClick={() => toggleExpanded(workspaceId, path)}
            className="flex items-center gap-1 flex-1 min-w-0"
            style={{ paddingLeft: depth * 12 }}
          >
            <ChevronRight
              className={`w-3 h-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
            />
            <FolderClosed className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate">{name}</span>
          </button>

          {/* Ações em hover na pasta */}
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            {onAddToContext && (
              <button
                onClick={() => onAddToContext(path)}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                title={t("workbench.files.add_context")}
              >
                <AtSign className="w-3 h-3" />
              </button>
            )}
            <button
              onClick={(e) => onDelete(path, name, e.shiftKey)}
              className="p-0.5 rounded text-muted-foreground hover:text-destructive"
              title={`${t("workbench.files.delete")} (Shift: permanente)`}
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {expanded && (
        <div>
          {!entries && depth === 0 ? (
            showRootSkeleton && <FileTreeSkeleton />
          ) : !entries ? (
            <div
              className="flex items-center gap-2 text-xs text-muted-foreground py-1"
              style={{ paddingLeft: 8 + (depth + 1) * 12 }}
            >
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>…</span>
            </div>
          ) : null}

          {/* Input de criação inline */}
          {showCreateHere && (
            <InlineCreateInput
              placeholder={
                creating!.type === "file"
                  ? t("workbench.files.creating_file")
                  : t("workbench.files.creating_folder")
              }
              onConfirm={onInlineCreate}
              onCancel={onCancelCreate}
              depth={depth}
            />
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
                  statusByPath={statusByPath}
                  onOpenFile={onOpenFile}
                  onAddToContext={onAddToContext}
                  onDelete={onDelete}
                  creating={creating}
                  onInlineCreate={onInlineCreate}
                  onCancelCreate={onCancelCreate}
                  onRequestCreate={onRequestCreate}
                />
              ) : (
                <FileItem
                  key={entry.path}
                  threadId={threadId}
                  entry={entry}
                  depth={depth}
                  status={statusByPath.get(norm(entry.path))}
                  onOpenFile={onOpenFile}
                  onAddToContext={onAddToContext}
                  onDelete={onDelete}
                />
              ),
            )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PinnedSection
// ---------------------------------------------------------------------------

function PinnedSection({
  threadId,
  onOpenFile,
  onAddToContext,
}: {
  threadId: string;
  onOpenFile: (path: string) => void;
  onAddToContext?: (path: string) => void;
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
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              {onAddToContext && (
                <button
                  onClick={() => onAddToContext(path)}
                  className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                  title={t("workbench.files.add_context")}
                >
                  <AtSign className="w-3 h-3" />
                </button>
              )}
              <button
                onClick={() => togglePinned(threadId, path)}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label={t("workbench.files.unpin")}
                title={t("workbench.files.unpin")}
              >
                <PinOff className="w-3 h-3" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

const EMPTY_PINNED: string[] = [];

// ---------------------------------------------------------------------------
// FilesTab principal
// ---------------------------------------------------------------------------

interface FilesTabProps {
  threadId: string;
  /** Adicionar arquivo/pasta ao contexto do chat como @mention. */
  onAddToContext?: (path: string) => void;
}

export function FilesTab({ threadId, onAddToContext }: FilesTabProps) {
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
  const invalidateFiles = useWorkbenchStore((s) => s.invalidateFiles);

  // Badges M/A/D na árvore: join client-side com o diff porcelain.
  const diffSummary = useWorkbenchStore((s) => s.getDiff(wsId).summary);
  const diffFetchedAt = useWorkbenchStore(
    (s) => s.getDiff(wsId).summaryFetchedAt,
  );
  const setDiffSummary = useWorkbenchStore((s) => s.setDiffSummary);
  const clearPending = useWorkbenchStore((s) => s.clearPending);

  // Abrir/revalidar a aba consome a pendência de atualização.
  useEffect(() => {
    if (wsId) clearPending(wsId, "files");
  }, [wsId, diffFetchedAt, clearPending]);

  const statusByPath = useMemo(() => {
    const m = new Map<string, string>();
    for (const f of diffSummary?.files ?? []) m.set(norm(f.path), f.status);
    return m;
  }, [diffSummary]);

  useWorkbenchSWR({
    key: `files-diff-badges:${wsId}`,
    hasCache: diffSummary !== null,
    isStale: Date.now() - diffFetchedAt > WORKBENCH_STALE_MS,
    revalidate: async () => {
      if (!wsId) return;
      const data = await fetchDiffSummary(wsId);
      if (data) setDiffSummary(wsId, data);
    },
    skip: !wsId,
  });

  // Estado de criação inline
  const [creating, setCreating] = useState<CreatingState | null>(null);

  const handleOpenFile = useCallback(
    (path: string) => {
      if (!wsId) return;
      setOpenFile(wsId, path);
    },
    [wsId, setOpenFile],
  );

  // Refresh: invalida cache e força re-fetch
  const handleRefresh = useCallback(() => {
    if (!wsId) return;
    invalidateFiles(wsId);
  }, [wsId, invalidateFiles]);

  // Criar arquivo ou pasta
  const handleRequestCreate = useCallback(
    (type: "file" | "dir", parentDir: string) => {
      setCreating({ type, parentDir });
    },
    [],
  );

  const handleInlineCreate = useCallback(
    async (name: string) => {
      if (!wsId || !creating) return;
      setCreating(null);
      const relPath = creating.parentDir
        ? `${creating.parentDir}/${name}`
        : name;
      const ok = await apiFsCreate(wsId, creating.type, relPath);
      if (ok) invalidateFiles(wsId);
    },
    [wsId, creating, invalidateFiles],
  );

  const handleCancelCreate = useCallback(() => {
    setCreating(null);
  }, []);

  // Deletar arquivo/pasta com confirmação; permanent=true vai para o lixo permanente
  const handleDelete = useCallback(
    async (path: string, name: string, permanent = false) => {
      if (!wsId) return;
      const label = permanent
        ? `Deletar permanentemente "${name}"? Esta ação não pode ser desfeita.`
        : `Mover "${name}" para a Lixeira?`;
      // eslint-disable-next-line no-alert
      if (!window.confirm(label)) return;
      const ok = await apiFsDelete(wsId, path, permanent);
      if (ok) {
        invalidateFiles(wsId);
        if (openPath === path) setOpenFile(wsId, null);
      }
    },
    [wsId, openPath, invalidateFiles, setOpenFile],
  );

  // Ctrl+N → novo arquivo na raiz; Ctrl+Shift+N → nova pasta na raiz
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;
      if (e.key === "N" || e.key === "n") {
        if (e.shiftKey) {
          e.preventDefault();
          handleRequestCreate("dir", "");
        } else {
          e.preventDefault();
          handleRequestCreate("file", "");
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleRequestCreate]);

  // SWR para o conteúdo do arquivo aberto
  useWorkbenchSWR({
    key: `file:${wsId}:${openPath ?? ""}`,
    hasCache: openContent !== undefined,
    isStale: false,
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
      {/* Toolbar VS Code-like */}
      <div className="flex items-center gap-0.5 px-2 py-1 border-b border-border/60 bg-muted/10">
        <span className="text-[10px] font-medium text-muted-foreground truncate flex-1 select-none">
          {workspace.name}
        </span>
        <button
          onClick={() => handleRequestCreate("file", "")}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title={t("workbench.files.new_file")}
          aria-label={t("workbench.files.new_file")}
        >
          <FilePlus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleRequestCreate("dir", "")}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title={t("workbench.files.new_folder")}
          aria-label={t("workbench.files.new_folder")}
        >
          <FolderPlus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleRefresh}
          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title={t("workbench.files.refresh")}
          aria-label={t("workbench.files.refresh")}
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

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
        <PinnedSection
          threadId={threadId}
          onOpenFile={handleOpenFile}
          onAddToContext={onAddToContext}
        />

        {/* Input de criação na raiz */}
        {creating && creating.parentDir === "" && (
          <InlineCreateInput
            placeholder={
              creating.type === "file"
                ? t("workbench.files.creating_file")
                : t("workbench.files.creating_folder")
            }
            onConfirm={handleInlineCreate}
            onCancel={handleCancelCreate}
            depth={0}
          />
        )}

        <DirNode
          threadId={threadId}
          workspaceId={wsId}
          path=""
          name={workspace.name}
          depth={0}
          filter={filter}
          statusByPath={statusByPath}
          onOpenFile={handleOpenFile}
          onAddToContext={onAddToContext}
          onDelete={handleDelete}
          creating={creating}
          onInlineCreate={handleInlineCreate}
          onCancelCreate={handleCancelCreate}
          onRequestCreate={handleRequestCreate}
        />
      </div>

      {/* Viewer */}
      {showViewer && (
        <div className="border-t border-border/60 max-h-[50%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground">
              {openPath ?? "…"}
            </span>
            <div className="flex items-center gap-1 shrink-0">
              {onAddToContext && openPath && (
                <button
                  onClick={() => onAddToContext(openPath)}
                  className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                  title={t("workbench.files.add_context")}
                >
                  <AtSign className="w-3 h-3" />
                </button>
              )}
              <button
                onClick={() => setOpenFile(wsId, null)}
                className="text-muted-foreground hover:text-foreground px-1"
                title={t("workbench.close")}
              >
                ×
              </button>
            </div>
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
