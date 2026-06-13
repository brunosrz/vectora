"use client";

/**
 * PlanTab — lista de artifacts da sessão.
 *
 * Estado vive no workbench-store (slice `plan`):
 *   - lista de artifacts da sessão → cacheada por threadId
 *   - artifact aberto + conteúdo carregado → idem
 * SWR via `useWorkbenchSWR`.
 */

import {
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useCallback } from "react";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { useWorkbenchSWR } from "@/lib/hooks/workbench/use-swr";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { getThreadActivity } from "@/lib/api/vectora-client";
import {
  WORKBENCH_STALE_MS,
  useWorkbenchStore,
  type PlanItem,
} from "@/lib/stores/workbench-store";

async function fetchArtifacts(threadId: string): Promise<PlanItem[]> {
  const qs = new URLSearchParams({ session_id: threadId });
  const res = await fetch(`/artifacts/?${qs}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.artifacts ?? [];
}

async function fetchArtifactContent(
  threadId: string,
  slug: string,
): Promise<string | null> {
  const qs = new URLSearchParams({ session_id: threadId });
  const res = await fetch(`/artifacts/${encodeURIComponent(slug)}?${qs}`);
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

function FilesTouchedSection({ threadId }: { threadId: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["thread-activity", threadId],
    queryFn: () => getThreadActivity(threadId),
    staleTime: 60_000,
  });
  const files = data?.files_touched ?? [];
  if (files.length === 0) return null;
  return (
    <div className="border-t border-border/40">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0" />
        )}
        <span className="font-medium flex-1 text-left">
          {t("workbench.plan.files_touched")} ({files.length})
        </span>
      </button>
      {open && (
        <div className="px-2 pb-2 space-y-0.5">
          {files.map((f) => (
            <p
              key={f}
              className="text-[10px] font-mono text-muted-foreground truncate pl-4"
            >
              {f}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function PlanTab({ threadId }: PlanTabProps) {
  const t = useT();
  const items = useWorkbenchStore((s) => s.getPlan(threadId).items);
  const fetchedAt = useWorkbenchStore((s) => s.getPlan(threadId).fetchedAt);
  const openSlug = useWorkbenchStore((s) => s.getPlan(threadId).openSlug);
  const openContent = useWorkbenchStore((s) =>
    openSlug ? s.getPlan(threadId).contentsBySlug[openSlug] : undefined,
  );

  const setPlanItems = useWorkbenchStore((s) => s.setPlanItems);
  const setPlanOpenSlug = useWorkbenchStore((s) => s.setPlanOpenSlug);
  const setPlanContent = useWorkbenchStore((s) => s.setPlanContent);

  useWorkbenchSWR({
    key: `plan:${threadId}`,
    hasCache: fetchedAt > 0,
    isStale: Date.now() - fetchedAt > WORKBENCH_STALE_MS,
    revalidate: async () => {
      const list = await fetchArtifacts(threadId);
      setPlanItems(threadId, list);
    },
  });

  useWorkbenchSWR({
    key: `plan-content:${threadId}:${openSlug ?? ""}`,
    hasCache: openContent !== undefined,
    isStale: false,
    revalidate: async () => {
      if (!openSlug) return;
      const content = await fetchArtifactContent(threadId, openSlug);
      if (content !== null) setPlanContent(threadId, openSlug, content);
    },
    skip: !openSlug,
  });

  const handleOpen = useCallback(
    (item: PlanItem) => {
      setPlanOpenSlug(threadId, fileSlug(item.path));
    },
    [threadId, setPlanOpenSlug],
  );

  // Estado de loading inicial: ainda não fetchamos uma única vez.
  const initialLoading = fetchedAt === 0;

  if (initialLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 p-4 text-center">
        <FileText className="w-6 h-6 text-muted-foreground/40" />
        <p className="text-xs text-muted-foreground">
          {t("workbench.plan.empty")}
        </p>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1.5"
          onClick={() =>
            useChatInputStore
              .getState()
              .pushDraft(t("workbench.plan.ask_prompt"))
          }
        >
          <Sparkles className="w-3 h-3" />
          {t("workbench.plan.ask_cta")}
        </Button>
      </div>
    );
  }

  const openLoading = openSlug !== null && openContent === undefined;

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

      <FilesTouchedSection threadId={threadId} />

      {openSlug && (
        <div className="border-t border-border/60 max-h-[55%] flex flex-col">
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30 text-xs">
            <span className="truncate font-mono text-muted-foreground">
              {openSlug}
            </span>
            <button
              onClick={() => setPlanOpenSlug(threadId, null)}
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
