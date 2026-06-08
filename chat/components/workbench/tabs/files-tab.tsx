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
  Pencil,
  Pin,
  PinOff,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import { useDelayedLoading } from "@/lib/hooks/use-delayed-loading";
import { useToastStore } from "@/lib/stores/toast-store";
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

type SaveFileResult =
  | { ok: true; sha256: string | null }
  | { ok: false; conflict: boolean; message?: string };

async function apiUpdateFile(
  workspaceId: string,
  path: string,
  content: string,
  expectedSha256: string | null,
): Promise<SaveFileResult> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/workspaces/${encodeURIComponent(workspaceId)}/fs/file?${qs}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, expected_sha256: expectedSha256 }),
    },
  );
  if (res.status === 412) {
    return { ok: false, conflict: true };
  }
  let data: { status?: string; message?: string; sha256?: string | null } = {};
  try {
    data = await res.json();
  } catch {
    // resposta sem corpo JSON — segue com `data` vazio
  }
  if (!res.ok || data.status !== "ok") {
    return { ok: false, conflict: false, message: data.message };
  }
  return { ok: true, sha256: data.sha256 ?? null };
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
  onRename,
}: {
  threadId: string;
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
  const t = useT();
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
      className="group flex items-center px-2 py-0.5 text-xs hover:bg-muted/50 rounded-sm focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
      style={{ paddingLeft: 8 + (depth + 1) * 12 }}
      onKeyDown={(e) => {
        if (e.key === "Delete" && !renaming) {
          e.preventDefault();
          onDelete(entry.path, entry.name, e.shiftKey);
        }
      }}
    >
      <span className="w-3" />
      <File className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
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
          placeholder={t("workbench.files.rename_placeholder")}
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
          title={onRename ? t("workbench.files.rename") : undefined}
        >
          {entry.name}
        </button>
      )}
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
        {onRename && !renaming && (
          <button
            onClick={() => {
              setRenameValue(entry.name);
              setRenaming(true);
            }}
            className="p-0.5 rounded text-muted-foreground hover:text-foreground"
            aria-label={t("workbench.files.rename")}
            title={t("workbench.files.rename")}
          >
            <Pencil className="w-3 h-3" />
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
  const t = useT();
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
            ? t("workbench.files.rename_exists")
            : t("workbench.files.rename_error");
        useToastStore.getState().error(msg);
      }
      await revalidate();
    },
    [workspaceId, revalidate, t],
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
              style={{ paddingLeft: depth * 12 + 4 }}
              placeholder={t("workbench.files.rename_placeholder")}
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
              style={{ paddingLeft: depth * 12 }}
            >
              <ChevronRight
                className={`w-3 h-3 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
              />
              <FolderClosed className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{name}</span>
            </button>
          )}

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
            {onRename && !renamingDir && (
              <button
                onClick={() => {
                  setRenameDirValue(name);
                  setRenamingDir(true);
                }}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground"
                title={t("workbench.files.rename")}
              >
                <Pencil className="w-3 h-3" />
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
                  onRename={handleChildRename}
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

  // ── Editor inline (A.1): rascunho local + dirty-tracking ────────────────
  const [draft, setDraft] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [pendingNav, setPendingNav] = useState<
    { kind: "open"; path: string } | { kind: "close" } | null
  >(null);

  const dirty = draft !== null && draft !== (openContent?.content ?? "");
  const editable =
    openContent?.kind === "text" &&
    !openContent.truncated &&
    openContent.sha256 != null;

  // ── Busca em conteúdo (A.5) ─────────────────────────────────────────────
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null);
  const [searching, setSearching] = useState(false);
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

  // Trocar de arquivo limpa o rascunho (cada arquivo tem seu próprio ciclo).
  useEffect(() => {
    setDraft(null);
  }, [openPath]);

  const handleOpenFile = useCallback(
    (path: string) => {
      if (!wsId) return;
      if (dirty) {
        setPendingNav({ kind: "open", path });
        return;
      }
      setOpenFile(wsId, path);
    },
    [wsId, dirty, setOpenFile],
  );

  const handleCloseViewer = useCallback(() => {
    if (!wsId) return;
    if (dirty) {
      setPendingNav({ kind: "close" });
      return;
    }
    setOpenFile(wsId, null);
  }, [wsId, dirty, setOpenFile]);

  const handleConfirmDiscardNav = useCallback(() => {
    if (!wsId || !pendingNav) return;
    setDraft(null);
    if (pendingNav.kind === "open") setOpenFile(wsId, pendingNav.path);
    else setOpenFile(wsId, null);
    setPendingNav(null);
  }, [wsId, pendingNav, setOpenFile]);

  const handleSaveFile = useCallback(async () => {
    if (!wsId || !openPath || draft === null || !openContent) return;
    setSaving(true);
    const result = await apiUpdateFile(
      wsId,
      openPath,
      draft,
      openContent.sha256 ?? null,
    );
    setSaving(false);
    if (result.ok) {
      setFileContent(wsId, openPath, {
        ...openContent,
        content: draft,
        sha256: result.sha256,
        truncated: false,
      });
      setDraft(null);
      return;
    }
    if (result.conflict) {
      setConflictOpen(true);
      return;
    }
    useToastStore
      .getState()
      .error(t("workbench.files.save_error"), { description: result.message });
  }, [wsId, openPath, draft, openContent, setFileContent, t]);

  const handleReloadFile = useCallback(async () => {
    if (!wsId || !openPath) return;
    setConflictOpen(false);
    setDraft(null);
    const data = await fetchFile(wsId, openPath);
    if (data) setFileContent(wsId, openPath, data);
  }, [wsId, openPath, setFileContent]);

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
        {/* Toggle de busca em conteúdo (A.5) */}
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
          title={t("workbench.files.search_in_files")}
          aria-label={t("workbench.files.search_in_files")}
          aria-pressed={searchMode}
        >
          <Search className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Filtro de nomes ou busca em conteúdo */}
      {searchMode ? (
        <div className="px-2 py-1.5 border-b border-border/60">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <Input
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("workbench.files.search_placeholder")}
              className="h-7 text-xs pl-7 pr-6"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSearchResults(null);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                title={t("workbench.files.cancel")}
              >
                <X className="w-3 h-3" />
              </button>
            )}
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
              placeholder={t("workbench.files.filter")}
              className="h-7 text-xs pl-7"
            />
          </div>
        </div>
      )}

      {/* Árvore de arquivos ou resultados de busca */}
      <div className="flex-1 overflow-y-auto py-1">
        {searchMode ? (
          <div className="px-1">
            {searchResults !== null && searchResults.hits.length === 0 && (
              <p className="text-[10px] text-muted-foreground text-center py-4">
                {t("workbench.files.search_no_results")}
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
                {t("workbench.files.search_truncated")}
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
          </>
        )}
      </div>

      {/* Viewer */}
      {showViewer && (
        <div className="border-t border-border/60 max-h-[50%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground flex items-center gap-1.5">
              {openPath ?? "…"}
              {dirty && (
                <span
                  className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0"
                  title={t("workbench.files.unsaved")}
                />
              )}
            </span>
            <div className="flex items-center gap-1 shrink-0">
              {dirty && (
                <>
                  <button
                    onClick={() => setDraft(null)}
                    className="px-1.5 py-0.5 rounded text-muted-foreground hover:text-foreground"
                  >
                    {t("workbench.files.discard")}
                  </button>
                  <button
                    onClick={handleSaveFile}
                    disabled={saving}
                    className="px-1.5 py-0.5 rounded text-primary hover:text-primary/80 font-medium flex items-center gap-1"
                  >
                    {saving && <Loader2 className="w-3 h-3 animate-spin" />}
                    {t("workbench.files.save")}
                  </button>
                </>
              )}
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
                onClick={handleCloseViewer}
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
            ) : editable ? (
              <textarea
                value={draft ?? openContent?.content ?? ""}
                onChange={(e) => setDraft(e.target.value)}
                spellCheck={false}
                className="w-full h-full min-h-[160px] resize-none bg-transparent text-xs font-mono leading-relaxed outline-none"
              />
            ) : highlightLine !== null ? (
              // Renderização linha-a-linha com destaque para busca em conteúdo
              <div className="text-xs font-mono leading-relaxed">
                {(openContent?.content ?? "").split("\n").map((line, i) => {
                  const lineNum = i + 1;
                  return (
                    <div
                      key={i}
                      ref={lineNum === highlightLine ? highlightRef : undefined}
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
                {t("workbench.files.read_only_truncated")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Conflito de edição concorrente — 412 do PUT */}
      <Dialog open={conflictOpen} onOpenChange={setConflictOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("workbench.files.conflict_title")}</DialogTitle>
            <DialogDescription>
              {t("workbench.files.conflict_desc")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConflictOpen(false)}>
              {t("workbench.files.cancel")}
            </Button>
            <Button variant="destructive" onClick={handleReloadFile}>
              {t("workbench.files.reload")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Aviso de descarte ao trocar/fechar arquivo com edições pendentes */}
      <Dialog
        open={pendingNav !== null}
        onOpenChange={(open) => {
          if (!open) setPendingNav(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("workbench.files.discard_title")}</DialogTitle>
            <DialogDescription>
              {t("workbench.files.discard_desc")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingNav(null)}>
              {t("workbench.files.cancel")}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDiscardNav}>
              {t("workbench.files.discard")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
