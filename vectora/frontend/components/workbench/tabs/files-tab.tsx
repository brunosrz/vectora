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
  AppWindow,
  AtSign,
  ChevronRight,
  FilePlus,
  Filter,
  FolderClosed,
  FolderPlus,
  History,
  Loader2,
  Pencil,
  Pin,
  PinOff,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FileIcon } from "@/components/icons/file-icon";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import { useDelayedLoading } from "@/lib/hooks/use-delayed-loading";
import { useToastStore } from "@/lib/stores/toast-store";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type DiffSummary,
  type FileEntry,
} from "@/lib/stores/workbench-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useWindowsStore } from "@/lib/stores/windows-store";
import { fetchFile, apiUpdateFile } from "@/lib/api/fs-files";
import { VerticalSplit } from "@/components/layout/vertical-split";
import { getMediaKind, MediaView } from "@/components/workbench/file-viewer";
import { MarkdownView } from "@/components/workbench/markdown-view";
import { FileTreeSkeleton } from "./file-tree-skeleton";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { m } from "@/lib/paraglide/messages";

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

async function apiFsMove(
  workspaceId: string,
  fromPath: string,
  toPath: string,
): Promise<{ ok: boolean; message?: string }> {
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/fs/move`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_path: fromPath, to_path: toPath }),
    },
  );
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, message: data.message };
}

// ---------------------------------------------------------------------------
// A.5 — Busca de texto em arquivos
// ---------------------------------------------------------------------------

interface SearchHit {
  path: string;
  line_number: number;
  line_text: string;
}

interface SearchResult {
  hits: SearchHit[];
  truncated: boolean;
}

async function apiFsSearch(
  workspaceId: string,
  query: string,
  path = "",
): Promise<SearchResult | null> {
  const qs = new URLSearchParams({ q: query });
  if (path) qs.set("path", path);
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/fs/search?${qs}`,
  );
  if (!res.ok) return null;
  return res.json() as Promise<SearchResult>;
}

// ---------------------------------------------------------------------------
// A.6 — Histórico de arquivo (git log/file + git show)
// ---------------------------------------------------------------------------

interface FileLogEntry {
  sha: string;
  sha_short: string;
  author: string;
  date: string; // ISO 8601
  message: string;
}

interface FileLogResponse {
  path: string;
  entries: FileLogEntry[];
}

interface ShowFileAtRevResponse {
  path: string;
  sha: string;
  content: string | null;
  binary: boolean;
  truncated: boolean;
}

async function apiFsGitLogFile(
  workspaceId: string,
  path: string,
  n = 50,
): Promise<FileLogResponse | null> {
  const qs = new URLSearchParams({ path, n: String(n) });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/log/file?${qs}`,
  );
  if (!res.ok) return null;
  return res.json() as Promise<FileLogResponse>;
}

async function apiFsGitShow(
  workspaceId: string,
  sha: string,
  path: string,
): Promise<ShowFileAtRevResponse | null> {
  const qs = new URLSearchParams({ sha, path });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/git/show?${qs}`,
  );
  if (!res.ok) return null;
  return res.json() as Promise<ShowFileAtRevResponse>;
}

/** Formata data ISO 8601 em string compacta (dd/mm/yyyy). */
function fmtDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  } catch {
    return iso.slice(0, 10);
  }
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
  workspaceId,
  entry,
  depth,
  status,
  onOpenFile,
  onAddToContext,
  onDelete,
  onRename,
}: {
  threadId: string;
  workspaceId: string;
  entry: FileEntry;
  depth: number;
  status?: string;
  onOpenFile: (path: string) => void;
  onAddToContext?: (path: string) => void;
  onDelete: (path: string, name: string, permanent?: boolean) => void;
  onRename?: (oldPath: string, newName: string) => void;
}) {
  const pinned = useWorkbenchStore((s) => s.isPinned(threadId, entry.path));
  const togglePinned = useWorkbenchStore((s) => s.togglePinned);
  const openPath = useWorkbenchStore((s) => s.getFiles(workspaceId).openPath);
  const openWindow = useWindowsStore((s) => s.open);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(entry.name);

  const commitRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== entry.name && onRename) {
      onRename(entry.path, trimmed);
    }
    setRenaming(false);
  };

  return (
    <div
      tabIndex={0}
      role="treeitem"
      aria-selected={openPath === entry.path}
      className="group flex items-center px-2 py-0.5 text-xs hover:bg-muted/50 rounded-sm focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
      style={{ paddingLeft: 8 + depth * 12 }}
      onKeyDown={(e) => {
        if (e.key === "Delete" && !renaming) {
          e.preventDefault();
          onDelete(entry.path, entry.name, e.shiftKey);
        }
      }}
    >
      <span className="w-3" />
      <FileIcon name={entry.name} />
      {renaming ? (
        <input
          autoFocus
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commitRename();
            } else if (e.key === "Escape") {
              setRenaming(false);
              setRenameValue(entry.name);
            }
          }}
          onBlur={commitRename}
          className="flex-1 text-xs bg-background border border-primary/60 rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-primary/40 font-mono ml-1"
          placeholder={m.workbench_files_rename_placeholder()}
        />
      ) : (
        <button
          onClick={() => onOpenFile(entry.path)}
          onDoubleClick={() => {
            if (onRename) {
              setRenameValue(entry.name);
              setRenaming(true);
            }
          }}
          className="flex-1 text-left truncate text-foreground/80 hover:text-foreground ml-1"
          title={onRename ? m.workbench_files_rename() : undefined}
        >
          {entry.name}
        </button>
      )}
      <GitBadge status={status} />

      {/* Ações em hover */}
      <div className="hidden group-hover:flex items-center gap-0.5">
        {onAddToContext && (
          <button
            onClick={() => onAddToContext(entry.path)}
            className="p-0.5 rounded text-muted-foreground hover:text-foreground"
            aria-label={m.workbench_files_add_context()}
            title={m.workbench_files_add_context()}
          >
            <AtSign className="w-3 h-3" />
          </button>
        )}
        <button
          onClick={() => openWindow(workspaceId, entry.path)}
          className="p-0.5 rounded text-muted-foreground hover:text-foreground"
          aria-label={m.window_open_as_window()}
          title={m.window_open_as_window()}
        >
          <AppWindow className="w-3 h-3" />
        </button>
        {onRename && !renaming && (
          <button
            onClick={() => {
              setRenameValue(entry.name);
              setRenaming(true);
            }}
            className="p-0.5 rounded text-muted-foreground hover:text-foreground"
            aria-label={m.workbench_files_rename()}
            title={m.workbench_files_rename()}
          >
            <Pencil className="w-3 h-3" />
          </button>
        )}
        <button
          onClick={(e) => onDelete(entry.path, entry.name, e.shiftKey)}
          className="p-0.5 rounded text-muted-foreground hover:text-destructive"
          aria-label={m.workbench_files_delete()}
          title={`${m.workbench_files_delete()} (Shift: permanente)`}
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
            pinned ? m.workbench_files_unpin() : m.workbench_files_pin()
          }
          title={pinned ? m.workbench_files_unpin() : m.workbench_files_pin()}
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
      style={{ paddingLeft: 8 + depth * 12 }}
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
  /** A.4 — rename/move: callback para renomear esta pasta ou arquivo filho */
  onRename?: (oldPath: string, newName: string) => void;
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
  onRename,
}: DirNodeProps) {
  const [renamingDir, setRenamingDir] = useState(false);
  const [renameDirValue, setRenameDirValue] = useState(name);

  const commitDirRename = () => {
    const trimmed = renameDirValue.trim();
    if (trimmed && trimmed !== name && onRename) {
      onRename(path, trimmed);
    }
    setRenamingDir(false);
  };
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

  // A.4 — rename/move: chamado por FileItem / DirNode filho ao confirmar rename.
  const handleChildRename = useCallback(
    async (oldPath: string, newName: string) => {
      const parentDir = oldPath.includes("/")
        ? oldPath.split("/").slice(0, -1).join("/")
        : "";
      const toPath = parentDir ? `${parentDir}/${newName}` : newName;
      const result = await apiFsMove(workspaceId, oldPath, toPath);
      if (!result.ok) {
        const msg =
          result.message === "Já existe um arquivo ou pasta com esse nome."
            ? m.workbench_files_rename_exists()
            : m.workbench_files_rename_error();
        useToastStore.getState().error(msg);
      }
      await revalidate();
    },
    [workspaceId, revalidate],
  );

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
          role="treeitem"
          aria-expanded={expanded}
          className="group flex items-center px-2 py-0.5 text-xs text-foreground/80 hover:bg-muted/50 rounded-sm focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
          onKeyDown={(e) => {
            if (e.key === "Delete") {
              e.preventDefault();
              onDelete(path, name, e.shiftKey);
            }
          }}
        >
          {renamingDir ? (
            <input
              autoFocus
              value={renameDirValue}
              onChange={(e) => setRenameDirValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  commitDirRename();
                } else if (e.key === "Escape") {
                  setRenamingDir(false);
                  setRenameDirValue(name);
                }
              }}
              onBlur={commitDirRename}
              className="flex-1 text-xs bg-background border border-primary/60 rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-primary/40 font-mono"
              style={{ paddingLeft: (depth - 1) * 12 + 4 }}
              placeholder={m.workbench_files_rename_placeholder()}
            />
          ) : (
            <button
              onClick={() => toggleExpanded(workspaceId, path)}
              onDoubleClick={() => {
                if (onRename && depth > 0) {
                  setRenameDirValue(name);
                  setRenamingDir(true);
                }
              }}
              className="flex items-center gap-1 flex-1 min-w-0"
              style={{ paddingLeft: (depth - 1) * 12 }}
            >
              <ChevronRight
                className={`w-3 h-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
              />
              <FolderClosed className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{name}</span>
            </button>
          )}

          {/* Ações em hover na pasta */}
          <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
            {onAddToContext && (
              <button
                onClick={() => onAddToContext(path)}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                title={m.workbench_files_add_context()}
              >
                <AtSign className="w-3 h-3" />
              </button>
            )}
            {onRename && !renamingDir && (
              <button
                onClick={() => {
                  setRenameDirValue(name);
                  setRenamingDir(true);
                }}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                title={m.workbench_files_rename()}
              >
                <Pencil className="w-3 h-3" />
              </button>
            )}
            <button
              onClick={(e) => onDelete(path, name, e.shiftKey)}
              className="p-0.5 rounded text-muted-foreground hover:text-destructive"
              title={`${m.workbench_files_delete()} (Shift: permanente)`}
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
              style={{ paddingLeft: 8 + depth * 12 }}
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
                  ? m.workbench_files_creating_file()
                  : m.workbench_files_creating_folder()
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
                  onRename={handleChildRename}
                />
              ) : (
                <FileItem
                  key={entry.path}
                  threadId={threadId}
                  workspaceId={workspaceId}
                  entry={entry}
                  depth={depth}
                  status={statusByPath.get(norm(entry.path))}
                  onOpenFile={onOpenFile}
                  onAddToContext={onAddToContext}
                  onDelete={onDelete}
                  onRename={handleChildRename}
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
  const pinned = useWorkbenchStore(
    (s) => s.pinnedFiles[threadId] ?? EMPTY_PINNED,
  );
  const togglePinned = useWorkbenchStore((s) => s.togglePinned);

  if (pinned.length === 0) return null;

  return (
    <div className="border-b border-border/40 pb-1 mb-1">
      <div className="px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {m.workbench_files_pinned()}
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
            <div className="hidden group-hover:flex items-center gap-0.5">
              {onAddToContext && (
                <button
                  onClick={() => onAddToContext(path)}
                  className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                  title={m.workbench_files_add_context()}
                >
                  <AtSign className="w-3 h-3" />
                </button>
              )}
              <button
                onClick={() => togglePinned(threadId, path)}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                aria-label={m.workbench_files_unpin()}
                title={m.workbench_files_unpin()}
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
// FileHistoryPanel — lista de commits que tocaram um arquivo (A.6)
// ---------------------------------------------------------------------------

function FileHistoryPanel({
  entries,
  loading,
  selectedSha,
  onSelectSha,
}: {
  entries: FileLogEntry[] | null;
  loading: boolean;
  selectedSha: string | null;
  onSelectSha: (sha: string) => void;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!entries || entries.length === 0) {
    return (
      <p className="text-[10px] text-muted-foreground text-center py-6 px-4">
        Nenhum commit encontrado para este arquivo.
      </p>
    );
  }
  return (
    <div className="px-1 py-1">
      {entries.map((entry) => (
        <button
          key={entry.sha}
          onClick={() => onSelectSha(entry.sha)}
          className={`w-full text-left px-2 py-1.5 rounded mb-0.5 hover:bg-muted/40 transition-colors ${
            selectedSha === entry.sha ? "bg-primary/10 hover:bg-primary/15" : ""
          }`}
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[10px] font-mono text-primary shrink-0">
              {entry.sha_short}
            </span>
            <span className="text-[10px] text-muted-foreground shrink-0">
              {fmtDate(entry.date)}
            </span>
          </div>
          <p className="text-[11px] text-foreground/90 truncate leading-tight">
            {entry.message}
          </p>
          <p className="text-[10px] text-muted-foreground truncate mt-0.5">
            {entry.author.split("<")[0].trim()}
          </p>
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchResultGroup — grupo colapsável de resultados por arquivo (A.5)
// ---------------------------------------------------------------------------

function SearchResultGroup({
  filePath,
  hits,
  onOpenHit,
}: {
  filePath: string;
  hits: SearchHit[];
  onOpenHit: (path: string, lineNumber: number) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const fileName = filePath.split("/").pop() ?? filePath;

  return (
    <div className="mb-0.5">
      <button
        onClick={() => setCollapsed((v) => !v)}
        className="flex items-center gap-1 w-full px-2 py-0.5 hover:bg-muted/40 rounded text-left"
      >
        <ChevronRight
          className={`w-3 h-3 text-muted-foreground shrink-0 transition-transform ${
            collapsed ? "" : "rotate-90"
          }`}
        />
        <span
          className="text-[11px] font-medium truncate flex-1"
          title={filePath}
        >
          {fileName}
        </span>
        <span className="text-[10px] text-muted-foreground shrink-0 tabular-nums">
          {hits.length}
        </span>
      </button>
      {!collapsed && (
        <div className="ml-4">
          {hits.map((hit, i) => (
            <button
              key={i}
              onClick={() => onOpenHit(hit.path, hit.line_number)}
              className="flex items-start gap-2 w-full px-2 py-px hover:bg-muted/40 rounded text-left"
            >
              <span className="text-[10px] text-muted-foreground shrink-0 w-7 text-right leading-relaxed tabular-nums">
                {hit.line_number}
              </span>
              <span className="text-[11px] font-mono text-foreground/80 truncate leading-relaxed">
                {hit.line_text.trimStart()}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FilesTab principal
// ---------------------------------------------------------------------------

interface FilesTabProps {
  threadId: string;
  /** Adicionar arquivo/pasta ao contexto do chat como @mention. */
  onAddToContext?: (path: string) => void;
}

export function FilesTab({ threadId, onAddToContext }: FilesTabProps) {
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
  const viewerHeight = useWorkbenchStore((s) => s.viewerHeight);
  const setViewerHeight = useWorkbenchStore((s) => s.setViewerHeight);
  const openWindow = useWindowsStore((s) => s.open);

  // aria-busy: verdadeiro enquanto a raiz ainda não chegou do servidor.
  const rootEntriesLoaded = useWorkbenchStore(
    (s) => wsId !== "" && Array.isArray(s.getFiles(wsId).entriesByDir[""]),
  );
  const showSkeleton = !rootEntriesLoaded && !!wsId;

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
    const byPath = new Map<string, string>();
    for (const f of diffSummary?.files ?? [])
      byPath.set(norm(f.path), f.status);
    return byPath;
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

  // ── Confirmação de delete (C.12: Radix Dialog, não window.confirm) ───────
  const [deleteConfirm, setDeleteConfirm] = useState<{
    path: string;
    name: string;
    permanent: boolean;
  } | null>(null);

  // ── Busca em conteúdo (A.5) ─────────────────────────────────────────────
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [replaceQuery, setReplaceQuery] = useState("");
  const [replacing, setReplacing] = useState(false);
  // Linha destacada no viewer quando resultado de busca é aberto.
  const [highlightLine, setHighlightLine] = useState<number | null>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  // Scroll automático para a linha destacada quando o arquivo abre.
  useEffect(() => {
    highlightRef.current?.scrollIntoView({ block: "center" });
  }, [openPath, highlightLine]);

  // Busca com debounce de 350ms — dispara quando query muda.
  useEffect(() => {
    if (!searchMode || !wsId) return;
    if (searchQuery.trim().length < 2) {
      setSearchResults(null);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      const res = await apiFsSearch(wsId, searchQuery.trim());
      setSearching(false);
      setSearchResults(res);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery, searchMode, wsId]);

  // Agrupa hits por arquivo para exibição.
  const searchGrouped = useMemo(() => {
    if (!searchResults) return [];
    const map = new Map<string, SearchHit[]>();
    for (const hit of searchResults.hits) {
      const list = map.get(hit.path) ?? [];
      list.push(hit);
      map.set(hit.path, list);
    }
    return Array.from(map.entries());
  }, [searchResults]);

  const handleReplaceAll = useCallback(async () => {
    if (!wsId || !searchQuery.trim() || !replaceQuery || !searchResults) return;
    setReplacing(true);
    try {
      const filePaths = Array.from(
        new Set(searchResults.hits.map((h) => h.path)),
      );
      const fileDatas = await Promise.all(
        filePaths.map((p) => fetchFile(wsId, p)),
      );
      await Promise.all(
        filePaths.map(async (filePath, i) => {
          const fileData = fileDatas[i];
          if (!fileData || fileData.content === undefined) return;
          const updated = fileData.content.replaceAll(
            searchQuery.trim(),
            replaceQuery,
          );
          if (updated === fileData.content) return;
          await apiUpdateFile(wsId, filePath, updated, fileData.sha256 ?? null);
          setFileContent(wsId, filePath, {
            ...fileData,
            content: updated,
            sha256: null,
          });
        }),
      );
      const res = await apiFsSearch(wsId, searchQuery.trim());
      setSearchResults(res);
    } finally {
      setReplacing(false);
    }
  }, [wsId, searchQuery, replaceQuery, searchResults, setFileContent]);

  // ── Histórico de arquivo (A.6) ───────────────────────────────────────────
  const [historyMode, setHistoryMode] = useState(false);
  const [historyPath, setHistoryPath] = useState<string | null>(null);
  const [historyEntries, setHistoryEntries] = useState<FileLogEntry[] | null>(
    null,
  );
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historicSha, setHistoricSha] = useState<string | null>(null);
  const [historicContent, setHistoricContent] =
    useState<ShowFileAtRevResponse | null>(null);
  const [historicLoading, setHistoricLoading] = useState(false);

  // Fecha o histórico quando o arquivo aberto muda (navegação na árvore).
  useEffect(() => {
    if (historyMode && openPath !== historyPath) {
      setHistoryMode(false);
      setHistoryEntries(null);
      setHistoricSha(null);
      setHistoricContent(null);
    }
  }, [openPath, historyMode, historyPath]);

  const handleOpenFile = useCallback(
    (path: string) => {
      if (!wsId) return;
      setOpenFile(wsId, path);
    },
    [wsId, setOpenFile],
  );

  const handleCloseViewer = useCallback(() => {
    if (!wsId) return;
    setOpenFile(wsId, null);
  }, [wsId, setOpenFile]);

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

  // Abre arquivo a partir de um resultado de busca, destacando a linha.
  const handleOpenHit = useCallback(
    (path: string, lineNumber: number) => {
      setHighlightLine(lineNumber);
      handleOpenFile(path);
    },
    [handleOpenFile],
  );

  // Abre o painel de histórico para o arquivo atualmente aberto.
  const handleOpenHistory = useCallback(async () => {
    if (!wsId || !openPath) return;
    setHistoryMode(true);
    setHistoryPath(openPath);
    setHistoryEntries(null);
    setHistoricSha(null);
    setHistoricContent(null);
    setHistoryLoading(true);
    const res = await apiFsGitLogFile(wsId, openPath);
    setHistoryLoading(false);
    setHistoryEntries(res?.entries ?? []);
  }, [wsId, openPath]);

  // Seleciona um commit do histórico e carrega o conteúdo do arquivo naquele ponto.
  const handleSelectHistoricSha = useCallback(
    async (sha: string) => {
      if (!wsId || !historyPath) return;
      setHistoricSha(sha);
      setHistoricLoading(true);
      const res = await apiFsGitShow(wsId, sha, historyPath);
      setHistoricLoading(false);
      setHistoricContent(res);
    },
    [wsId, historyPath],
  );

  // Deletar arquivo/pasta com confirmação via ConfirmDialog (Radix — C.12).
  const handleDelete = useCallback(
    (path: string, name: string, permanent = false) => {
      if (!wsId) return;
      setDeleteConfirm({ path, name, permanent });
    },
    [wsId],
  );

  const handleDeleteConfirmed = useCallback(async () => {
    if (!wsId || !deleteConfirm) return;
    const { path, permanent } = deleteConfirm;
    setDeleteConfirm(null);
    const ok = await apiFsDelete(wsId, path, permanent);
    if (ok) {
      invalidateFiles(wsId);
      if (openPath === path) setOpenFile(wsId, null);
    }
  }, [wsId, deleteConfirm, openPath, invalidateFiles, setOpenFile]);

  // ── Gerenciador de .gitignore (A.10) ─────────────────────────────────────
  const [gitignoreOpen, setGitignoreOpen] = useState(false);
  const [gitignoreDraft, setGitignoreDraft] = useState<string>("");
  const [gitignoreSaving, setGitignoreSaving] = useState(false);
  const [gitignorePreview, setGitignorePreview] = useState<string[]>([]);
  const [previewPattern, setPreviewPattern] = useState("");

  const handleOpenGitignore = useCallback(async () => {
    if (!wsId) return;
    setGitignoreOpen(true);
    const res = await fetch(
      `/workspaces/${encodeURIComponent(wsId)}/fs/gitignore`,
    );
    if (res.ok) {
      const data = await res.json();
      setGitignoreDraft((data.content as string) ?? "");
    }
  }, [wsId]);

  const handleSaveGitignore = useCallback(async () => {
    if (!wsId) return;
    setGitignoreSaving(true);
    const lines = gitignoreDraft.split("\n");
    await fetch(`/workspaces/${encodeURIComponent(wsId)}/fs/gitignore`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lines }),
    });
    setGitignoreSaving(false);
    setGitignoreOpen(false);
  }, [wsId, gitignoreDraft]);

  useEffect(() => {
    if (!previewPattern.trim() || !wsId || !gitignoreOpen) {
      setGitignorePreview([]);
      return;
    }
    const timer = setTimeout(async () => {
      const qs = new URLSearchParams({ pattern: previewPattern.trim() });
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/fs/gitignore-preview?${qs}`,
      );
      if (res.ok) {
        const data = await res.json();
        setGitignorePreview((data.matched as string[]) ?? []);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [previewPattern, wsId, gitignoreOpen]);

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
        {m.workbench_files_no_workspace()}
      </div>
    );
  }

  const showViewer = openPath !== null;
  const loadingFile = showViewer && openContent === undefined;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar VS Code-like */}
      <div className="flex items-center gap-0.5 px-2 py-1 border-b border-border/60 bg-background">
        <span className="text-[10px] font-medium text-muted-foreground truncate flex-1 select-none">
          {workspace.name}
        </span>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => handleRequestCreate("file", "")}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              aria-label={m.tooltip_files_new_file()}
            >
              <FilePlus className="w-3.5 h-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {m.tooltip_files_new_file()}
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => handleRequestCreate("dir", "")}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              aria-label={m.tooltip_files_new_folder()}
            >
              <FolderPlus className="w-3.5 h-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {m.tooltip_files_new_folder()}
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleRefresh}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              aria-label={m.tooltip_files_refresh()}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {m.tooltip_files_refresh()}
          </TooltipContent>
        </Tooltip>
        {/* .gitignore manager (A.10) */}
        {workspace.is_git_repo && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleOpenGitignore}
                className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                aria-label={m.tooltip_files_gitignore()}
              >
                <Filter className="w-3.5 h-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {m.tooltip_files_gitignore()}
            </TooltipContent>
          </Tooltip>
        )}
        {/* Toggle de busca em conteúdo (A.5) */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={() => {
                if (searchMode) {
                  setSearchMode(false);
                  setSearchQuery("");
                  setSearchResults(null);
                  setHighlightLine(null);
                } else {
                  setSearchMode(true);
                }
              }}
              className={`p-1 rounded transition-colors ${
                searchMode
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
              }`}
              aria-label={m.tooltip_files_search()}
              aria-pressed={searchMode}
            >
              <Search className="w-3.5 h-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {m.tooltip_files_search()}
          </TooltipContent>
        </Tooltip>
      </div>

      {/* Filtro de nomes ou busca em conteúdo */}
      {searchMode ? (
        <div className="px-2 py-1.5 border-b border-border/60 space-y-1">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <Input
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              type="search"
              autoComplete="off"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={m.workbench_files_search_placeholder()}
              className="h-7 text-xs pl-7 pr-6"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSearchResults(null);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                title={m.workbench_files_cancel()}
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
          <div className="flex gap-1">
            <div className="relative flex-1">
              <Pencil className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
              <Input
                type="text"
                autoComplete="off"
                value={replaceQuery}
                onChange={(e) => setReplaceQuery(e.target.value)}
                placeholder={m.workbench_files_replace_placeholder()}
                className="h-7 text-xs pl-7"
              />
            </div>
            <button
              onClick={() => void handleReplaceAll()}
              disabled={
                replacing ||
                !searchQuery.trim() ||
                !replaceQuery ||
                !searchResults?.hits.length
              }
              className="shrink-0 px-2 h-7 rounded text-xs bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title={m.workbench_files_replace_all()}
            >
              {replacing ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                m.workbench_files_replace_all()
              )}
            </button>
          </div>
          {searching && (
            <div className="flex justify-center pt-1">
              <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
            </div>
          )}
        </div>
      ) : (
        <div className="px-2 py-1.5 border-b border-border/60">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <Input
              value={filter}
              onChange={(e) => setFilesFilter(wsId, e.target.value)}
              placeholder={m.workbench_files_filter()}
              autoComplete="off"
              className="h-7 text-xs pl-7"
            />
          </div>
        </div>
      )}

      {/* Árvore (topo) + viewer (base) num split vertical arrastável */}
      <VerticalSplit
        className="flex-1"
        showBottom={showViewer}
        bottomSize={viewerHeight}
        onResize={setViewerHeight}
        top={
          <div
            className="h-full overflow-y-auto py-1"
            role="tree"
            aria-label={m.workbench_files_tree_label()}
            aria-busy={showSkeleton}
          >
            {historyMode ? (
              <>
                {/* Cabeçalho do painel de histórico */}
                <div className="flex items-center justify-between px-2 py-1 mb-1 border-b border-border/40">
                  <span className="text-[10px] font-medium text-muted-foreground truncate flex-1">
                    {m.workbench_files_history()}:{" "}
                    {historyPath?.split("/").pop()}
                  </span>
                  <button
                    onClick={() => {
                      setHistoryMode(false);
                      setHistoryEntries(null);
                      setHistoricSha(null);
                      setHistoricContent(null);
                    }}
                    className="p-0.5 text-muted-foreground hover:text-foreground"
                    title={m.workbench_close()}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
                <FileHistoryPanel
                  entries={historyEntries}
                  loading={historyLoading}
                  selectedSha={historicSha}
                  onSelectSha={handleSelectHistoricSha}
                />
              </>
            ) : searchMode ? (
              <div className="px-1">
                {searchResults !== null && searchResults.hits.length === 0 && (
                  <p className="text-[10px] text-muted-foreground text-center py-4">
                    {m.workbench_files_search_no_results()}
                  </p>
                )}
                {searchGrouped.map(([filePath, hits]) => (
                  <SearchResultGroup
                    key={filePath}
                    filePath={filePath}
                    hits={hits}
                    onOpenHit={handleOpenHit}
                  />
                ))}
                {searchResults?.truncated && (
                  <p className="text-[10px] text-muted-foreground px-2 py-1">
                    {m.workbench_files_search_truncated()}
                  </p>
                )}
              </div>
            ) : (
              <>
                <PinnedSection
                  threadId={threadId}
                  onOpenFile={handleOpenFile}
                  onAddToContext={onAddToContext}
                />

                {/* O input de criação na raiz é renderizado pelo DirNode raiz
                (path="", sempre expandido). Renderizar um segundo input aqui
                fazia os dois montarem com autoFocus: o segundo roubava o foco,
                o onBlur do primeiro disparava onCancel e ambos sumiam — era o
                bug dos botões "novo arquivo"/"nova pasta" não funcionarem. */}

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
              </>
            )}
          </div>
        }
        bottom={
          <div className="border-t border-border/60 h-full flex flex-col">
            <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
              <span className="truncate font-mono text-muted-foreground">
                {openPath ?? "…"}
              </span>
              <div className="flex items-center gap-1 shrink-0">
                {onAddToContext && openPath && (
                  <button
                    onClick={() => onAddToContext(openPath)}
                    className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                    title={m.workbench_files_add_context()}
                  >
                    <AtSign className="w-3 h-3" />
                  </button>
                )}
                {/* Botão de histórico — só para workspaces git (A.6) */}
                {workspace.is_git_repo && openPath && (
                  <button
                    onClick={handleOpenHistory}
                    className={`p-0.5 rounded transition-colors ${
                      historyMode
                        ? "text-primary"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    title={m.workbench_files_history()}
                    aria-pressed={historyMode}
                  >
                    <History className="w-3 h-3" />
                  </button>
                )}
                {openPath && (
                  <button
                    onClick={() => openWindow(wsId, openPath)}
                    className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                    title={m.window_open_as_window()}
                    aria-label={m.window_open_as_window()}
                  >
                    <AppWindow className="w-3 h-3" />
                  </button>
                )}
                <button
                  onClick={handleCloseViewer}
                  className="text-muted-foreground hover:text-foreground px-1"
                  title={m.workbench_close()}
                >
                  ×
                </button>
              </div>
            </div>
            {/* Banner de revisão histórica (A.6) */}
            {historicSha && (
              <div className="flex items-center gap-2 px-2 py-1 bg-amber-500/10 border-b border-amber-500/20 text-[10px]">
                {historicLoading ? (
                  <Loader2 className="w-3 h-3 animate-spin text-muted-foreground shrink-0" />
                ) : (
                  <History className="w-3 h-3 text-amber-500 shrink-0" />
                )}
                <span className="text-muted-foreground truncate flex-1">
                  {m.workbench_files_history_viewing_at()}{" "}
                  <span className="font-mono text-amber-500">
                    {historicSha.slice(0, 7)}
                  </span>
                </span>
                <button
                  onClick={() => {
                    setHistoricSha(null);
                    setHistoricContent(null);
                  }}
                  className="text-muted-foreground hover:text-foreground shrink-0"
                >
                  {m.workbench_files_history_back()}
                </button>
              </div>
            )}
            <div className="flex-1 overflow-auto p-2">
              {!historicSha && openPath && getMediaKind(openPath) ? (
                <MediaView
                  kind={getMediaKind(openPath)!}
                  workspaceId={wsId}
                  path={openPath}
                />
              ) : historicSha && historicLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              ) : historicSha && historicContent ? (
                historicContent.binary ? (
                  <p className="text-xs text-muted-foreground">
                    {m.workbench_files_binary({ size: 0 })}
                  </p>
                ) : (
                  <>
                    <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                      {historicContent.content ?? ""}
                    </pre>
                    {historicContent.truncated && (
                      <p className="text-[10px] text-muted-foreground mt-2">
                        {m.workbench_files_read_only_truncated()}
                      </p>
                    )}
                  </>
                )
              ) : loadingFile ? (
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              ) : openContent?.kind === "binary" ? (
                <p className="text-xs text-muted-foreground">
                  {m.workbench_files_binary({ size: openContent.size })}
                </p>
              ) : openPath?.toLowerCase().match(/\.(md|markdown)$/) &&
                openContent?.content &&
                highlightLine === null ? (
                <MarkdownView content={openContent.content} />
              ) : highlightLine !== null ? (
                // Renderização linha-a-linha com destaque para busca em conteúdo
                <div className="text-xs font-mono leading-relaxed">
                  {(openContent?.content ?? "").split("\n").map((line, i) => {
                    const lineNum = i + 1;
                    return (
                      <div
                        key={i}
                        ref={
                          lineNum === highlightLine ? highlightRef : undefined
                        }
                        className={
                          lineNum === highlightLine
                            ? "bg-yellow-500/20 rounded"
                            : undefined
                        }
                      >
                        <span className="select-none text-muted-foreground inline-block w-8 text-right mr-3 text-[10px]">
                          {lineNum}
                        </span>
                        <span className="whitespace-pre-wrap break-all">
                          {line}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                  {openContent?.content ?? ""}
                </pre>
              )}
              {openContent?.truncated && (
                <p className="text-[10px] text-muted-foreground mt-2">
                  {m.workbench_files_read_only_truncated()}
                </p>
              )}
            </div>
          </div>
        }
      />

      {/* Dialog .gitignore (A.10) */}
      <Dialog
        open={gitignoreOpen}
        onOpenChange={(o) => {
          if (!o) setGitignoreOpen(false);
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{m.workbench_files_gitignore_title()}</DialogTitle>
            <DialogDescription>
              {m.workbench_files_gitignore_desc()}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <textarea
              className="font-mono text-xs bg-muted/30 border border-border/60 rounded p-2 h-48 resize-none outline-none focus:border-primary"
              value={gitignoreDraft}
              onChange={(e) => setGitignoreDraft(e.target.value)}
              spellCheck={false}
            />
            <div className="flex gap-2 items-center">
              <input
                className="flex-1 text-xs bg-background border border-border/60 rounded px-2 py-1 outline-none focus:border-primary"
                placeholder={m.workbench_files_gitignore_preview_placeholder()}
                value={previewPattern}
                onChange={(e) => setPreviewPattern(e.target.value)}
              />
            </div>
            {gitignorePreview.length > 0 && (
              <div className="border border-border/40 rounded p-2 max-h-28 overflow-y-auto">
                <p className="text-[10px] text-muted-foreground mb-1">
                  {m.workbench_files_gitignore_preview_matches({
                    n: gitignorePreview.length,
                  })}
                </p>
                {gitignorePreview.map((f) => (
                  <p
                    key={f}
                    className="text-[10px] font-mono text-foreground/80"
                  >
                    {f}
                  </p>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setGitignoreOpen(false)}
            >
              {m.workbench_files_cancel()}
            </Button>
            <Button
              size="sm"
              disabled={gitignoreSaving}
              onClick={handleSaveGitignore}
            >
              {gitignoreSaving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                m.workbench_files_save()
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmação de delete (Radix Dialog — acessível) */}
      <ConfirmDialog
        open={deleteConfirm !== null}
        title={
          deleteConfirm?.permanent
            ? `Deletar permanentemente "${deleteConfirm.name}"?`
            : `Mover "${deleteConfirm?.name}" para a Lixeira?`
        }
        description={
          deleteConfirm?.permanent
            ? "Esta ação não pode ser desfeita."
            : undefined
        }
        confirmLabel={deleteConfirm?.permanent ? "Deletar" : "Mover"}
        variant={deleteConfirm?.permanent ? "destructive" : "default"}
        onConfirm={handleDeleteConfirmed}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  );
}
