"use client";

/**
 * FileEditor — editor de código (Monaco) usado pelas janelas flutuantes.
 *
 * Carrega o conteúdo do `GET /file`, edita com syntax highlighting e tema
 * VSCode (dark/light conforme o theme do app) e salva via `PUT /fs/file` com
 * `expected_sha256` (conflito otimista → HTTP 412). Mídia e arquivos
 * truncados/binários caem no `FileViewer` read-only.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import MonacoEditor, { type OnMount } from "@monaco-editor/react";
import { useTheme } from "next-themes";
import { Loader2, Save } from "lucide-react";

import { languageFromPath } from "@/lib/monaco/setup";
import { fetchFile, apiUpdateFile } from "@/lib/api/fs-files";
import type { FileContent } from "@/lib/stores/workbench-store";
import { useToastStore } from "@/lib/stores/toast-store";
import { useT } from "@/lib/i18n";
import { getMediaKind, FileViewer } from "@/components/workbench/file-viewer";

export function FileEditor({
  workspaceId,
  path,
}: {
  workspaceId: string;
  path: string;
}) {
  const t = useT();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme !== "light";
  const media = getMediaKind(path);

  const [file, setFile] = useState<FileContent | null>(null);
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const shaRef = useRef<string | null>(null);

  const dirty = file?.content !== undefined && value !== file.content;
  const readOnly =
    file?.kind === "binary" || file?.truncated || file?.sha256 == null;

  useEffect(() => {
    if (media) return;
    let cancelled = false;
    setLoading(true);
    fetchFile(workspaceId, path)
      .then((data) => {
        if (cancelled) return;
        setFile(data);
        setValue(data?.content ?? "");
        shaRef.current = data?.sha256 ?? null;
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, path, media]);

  const handleSave = useCallback(async () => {
    if (!file || file.content === undefined || readOnly || saving) return;
    setSaving(true);
    const result = await apiUpdateFile(
      workspaceId,
      path,
      value,
      shaRef.current,
    );
    setSaving(false);
    if (result.ok) {
      shaRef.current = result.sha256;
      setFile((prev) => (prev ? { ...prev, content: value } : prev));
      return;
    }
    useToastStore
      .getState()
      .error(
        result.conflict
          ? t("workbench.files.conflict_title")
          : t("workbench.files.save_error"),
        { description: result.message },
      );
  }, [file, readOnly, saving, workspaceId, path, value, t]);

  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        void handleSave();
      });
    },
    [handleSave],
  );

  if (media) {
    return <FileViewer workspaceId={workspaceId} path={path} />;
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (file?.kind === "binary") {
    return <FileViewer workspaceId={workspaceId} path={path} />;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-7 shrink-0 items-center justify-between border-b border-border/60 bg-muted/30 px-2">
        <span className="flex items-center gap-1.5 truncate text-[11px] font-mono text-muted-foreground">
          {dirty && (
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
              title={t("workbench.files.unsaved")}
            />
          )}
          {path}
        </span>
        {!readOnly && (
          <button
            onClick={() => void handleSave()}
            disabled={!dirty || saving}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-40 disabled:hover:bg-transparent"
            title={t("workbench.files.save")}
          >
            {saving ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Save className="h-3 w-3" />
            )}
            {t("workbench.files.save")}
          </button>
        )}
      </div>
      <div className="min-h-0 flex-1">
        <MonacoEditor
          value={value}
          language={languageFromPath(path)}
          theme={isDark ? "vs-dark" : "vs"}
          onChange={(v) => setValue(v ?? "")}
          onMount={handleMount}
          options={{
            readOnly,
            fontSize: 13,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: "off",
          }}
          loading={
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          }
        />
      </div>
      {file?.truncated && (
        <p className="shrink-0 border-t border-border/60 px-2 py-1 text-[10px] text-muted-foreground">
          {t("workbench.files.read_only_truncated")}
        </p>
      )}
    </div>
  );
}
