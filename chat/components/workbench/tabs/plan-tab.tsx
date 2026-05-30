"use client";

/**
 * PlanTab (T8) — lista de artifacts (planos/specs/guias) da sessão.
 *
 * Reusa `ArtifactMetadata` do backend (vectora/types/documents.py). Os
 * artifacts são persistidos pelo agente via `create_artifact` (fs.py) em
 * ~/.vectora/artifacts/<session_id>/<slug>.md.
 */

import { FileText, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useT } from "@/lib/i18n";

interface ArtifactItem {
  title: string;
  path: string;
  session_id: string;
  created_at: string;
  content_preview?: string | null;
}

async function fetchArtifacts(threadId: string): Promise<ArtifactItem[]> {
  const qs = new URLSearchParams({ session_id: threadId });
  const res = await fetch(`/api/artifacts/?${qs}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.artifacts ?? [];
}

async function fetchArtifactContent(
  threadId: string,
  slug: string,
): Promise<string | null> {
  const qs = new URLSearchParams({ session_id: threadId });
  const res = await fetch(`/api/artifacts/${encodeURIComponent(slug)}?${qs}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.content ?? null;
}

function fileSlug(path: string): string {
  const last = path.split(/[/\\]/).pop() ?? "";
  return last.replace(/\.md$/i, "");
}

interface PlanTabProps {
  threadId: string;
}

export function PlanTab({ threadId }: PlanTabProps) {
  const t = useT();
  const [items, setItems] = useState<ArtifactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [openContent, setOpenContent] = useState<string>("");
  const [openLoading, setOpenLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void fetchArtifacts(threadId).then((list) => {
      if (!cancelled) {
        setItems(list);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const handleOpen = useCallback(
    async (item: ArtifactItem) => {
      const slug = fileSlug(item.path);
      setOpenSlug(slug);
      setOpenLoading(true);
      const content = await fetchArtifactContent(threadId, slug);
      setOpenContent(content ?? "");
      setOpenLoading(false);
    },
    [threadId],
  );

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 p-4 text-center">
        <FileText className="w-6 h-6 text-muted-foreground/40" />
        <p className="text-xs text-muted-foreground">
          {t("workbench.plan.empty")}
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto py-1">
        {items.map((item) => {
          const slug = fileSlug(item.path);
          const active = slug === openSlug;
          return (
            <button
              key={item.path}
              onClick={() => handleOpen(item)}
              className={`w-full flex items-start gap-2 px-2 py-2 text-left text-xs hover:bg-muted/40 border-b border-border/40 ${
                active ? "bg-muted/40" : ""
              }`}
            >
              <FileText className="w-3.5 h-3.5 shrink-0 text-primary mt-0.5" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-foreground">
                  {item.title}
                </p>
                {item.content_preview && (
                  <p className="truncate text-[11px] text-muted-foreground">
                    {item.content_preview}
                  </p>
                )}
                <p className="text-[10px] text-muted-foreground/60">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {openSlug && (
        <div className="border-t border-border/60 max-h-[55%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground">
              {openSlug}
            </span>
            <button
              onClick={() => setOpenSlug(null)}
              className="text-muted-foreground hover:text-foreground px-1"
              title={t("workbench.close")}
            >
              ×
            </button>
          </div>
          <div className="flex-1 overflow-auto p-3">
            {openLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : (
              <pre className="text-xs whitespace-pre-wrap break-words font-mono">
                {openContent}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
