"use client";

/**
 * FilesTab (T6) — file tree do workspace ativo.
 *
 * Pequena árvore lazy-expanded com filtro/busca no topo. Viewer inline
 * read-only para arquivos selecionados (reusa CodeBlockViewer).
 */

import {
  ChevronRight,
  File,
  FolderClosed,
  Loader2,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

interface Entry {
  name: string;
  path: string;
  kind: "dir" | "file";
  size?: number;
}

interface TreeResponse {
  path: string;
  entries: Entry[];
}

interface FileResponse {
  path: string;
  kind: "text" | "binary";
  content?: string;
  size: number;
  truncated?: boolean;
}

async function fetchTree(
  workspaceId: string,
  path: string,
): Promise<TreeResponse | null> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/tree?${qs}`,
  );
  if (!res.ok) return null;
  return res.json();
}

async function fetchFile(
  workspaceId: string,
  path: string,
): Promise<FileResponse | null> {
  const qs = new URLSearchParams({ path });
  const res = await fetch(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/file?${qs}`,
  );
  if (!res.ok) return null;
  return res.json();
}

interface DirNodeProps {
  workspaceId: string;
  path: string;
  name: string;
  depth: number;
  filter: string;
  onOpenFile: (path: string) => void;
}

function DirNode({
  workspaceId,
  path,
  name,
  depth,
  filter,
  onOpenFile,
}: DirNodeProps) {
  const [open, setOpen] = useState(depth === 0);
  const [entries, setEntries] = useState<Entry[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchTree(workspaceId, path);
    setEntries(data?.entries ?? []);
    setLoading(false);
  }, [workspaceId, path]);

  useEffect(() => {
    if (open && entries === null) void load();
  }, [open, entries, load]);

  // refetch quando o workspace muda
  useEffect(() => {
    setEntries(null);
    setOpen(depth === 0);
  }, [workspaceId, depth]);

  const visible = useMemo(() => {
    if (!filter || !entries) return entries ?? [];
    const f = filter.toLowerCase();
    return entries.filter((e) => e.name.toLowerCase().includes(f));
  }, [entries, filter]);

  return (
    <div>
      {depth > 0 && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center gap-1 px-2 py-0.5 text-xs text-foreground/80 hover:bg-muted/50 rounded-sm"
          style={{ paddingLeft: 8 + depth * 12 }}
        >
          <ChevronRight
            className={`w-3 h-3 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
          />
          <FolderClosed className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{name}</span>
        </button>
      )}
      {open && (
        <div>
          {loading && (
            <div
              className="flex items-center gap-2 text-xs text-muted-foreground py-1"
              style={{ paddingLeft: 8 + (depth + 1) * 12 }}
            >
              <Loader2 className="w-3 h-3 animate-spin" />
              {/* não traduzido — string interna mínima */}
              <span>…</span>
            </div>
          )}
          {!loading &&
            visible.map((entry) =>
              entry.kind === "dir" ? (
                <DirNode
                  key={entry.path}
                  workspaceId={workspaceId}
                  path={entry.path}
                  name={entry.name}
                  depth={depth + 1}
                  filter={filter}
                  onOpenFile={onOpenFile}
                />
              ) : (
                <button
                  key={entry.path}
                  onClick={() => onOpenFile(entry.path)}
                  className="w-full flex items-center gap-1 px-2 py-0.5 text-xs text-foreground/80 hover:bg-muted/50 rounded-sm text-left"
                  style={{ paddingLeft: 8 + (depth + 1) * 12 }}
                >
                  <span className="w-3" />
                  <File className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{entry.name}</span>
                </button>
              ),
            )}
        </div>
      )}
    </div>
  );
}

interface FilesTabProps {
  threadId: string;
}

export function FilesTab(_props: FilesTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const [filter, setFilter] = useState("");
  const [openFile, setOpenFile] = useState<FileResponse | null>(null);
  const [loadingFile, setLoadingFile] = useState(false);

  const handleOpenFile = useCallback(
    async (path: string) => {
      if (!workspace) return;
      setLoadingFile(true);
      const data = await fetchFile(workspace.id, path);
      setOpenFile(data);
      setLoadingFile(false);
    },
    [workspace],
  );

  if (!workspace) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-muted-foreground p-4 text-center">
        {t("workbench.files.no_workspace")}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Busca */}
      <div className="px-2 py-1.5 border-b border-border/60">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={t("workbench.files.filter")}
            className="h-7 text-xs pl-7"
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        <DirNode
          workspaceId={workspace.id}
          path=""
          name={workspace.name}
          depth={0}
          filter={filter}
          onOpenFile={handleOpenFile}
        />
      </div>

      {/* Viewer */}
      {(openFile || loadingFile) && (
        <div className="border-t border-border/60 max-h-[50%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground">
              {openFile?.path ?? "…"}
            </span>
            <button
              onClick={() => setOpenFile(null)}
              className="text-muted-foreground hover:text-foreground px-1"
              title={t("workbench.close")}
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-auto p-2">
            {loadingFile ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : openFile?.kind === "binary" ? (
              <p className="text-xs text-muted-foreground">
                {t("workbench.files.binary", { size: openFile.size })}
              </p>
            ) : (
              <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                {openFile?.content ?? ""}
              </pre>
            )}
            {openFile?.truncated && (
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
