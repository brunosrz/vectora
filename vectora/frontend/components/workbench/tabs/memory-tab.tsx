"use client";

/**
 * MemoryTab — "Memória da sessão": o que o Vectora está recuperando e já sabe.
 *
 * Estilo deep research: uma timeline de **atividade** (indexações RAG em
 * progresso e buscas/fetch web em andamento) seguida do **contexto recuperado**
 * (trechos da base de conhecimento + resultados web) em pílulas expansíveis.
 */

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Brain,
  ChevronRight,
  Database,
  Globe,
  Loader2,
} from "lucide-react";
import { useThreadMessages } from "@/lib/hooks/chat/use-thread-messages";
import { useRagJobsStore } from "@/lib/stores/rag-jobs-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { MarkdownView } from "@/components/workbench/markdown-view";
import { RagSettingsPanel } from "@/components/workbench/rag-settings-panel";
import { m } from "@/lib/paraglide/messages";

interface MemoryTabProps {
  threadId: string;
}

interface MemoryItem {
  id: string;
  kind: "rag" | "web";
  title: string;
  subtitle?: string;
  content: string;
}

const WEB_TOOLS = new Set(["web_search", "fetch_url", "web_fetch"]);

function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** Último segmento de um caminho (Windows ou POSIX). */
function baseName(path: string): string {
  const parts = path.split(/[/\\]/).filter(Boolean);
  return parts[parts.length - 1] || path;
}

function MemoryPill({ item }: { item: MemoryItem }) {
  const [open, setOpen] = useState(false);
  const Icon = item.kind === "rag" ? Database : Globe;
  return (
    <div className="rounded-lg border border-border/60 bg-card/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-2.5 py-2 text-left"
        aria-expanded={open}
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-90" : ""}`}
        />
        <Icon className="h-3.5 w-3.5 shrink-0 text-primary" />
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-foreground">
          {item.title}
        </span>
        {item.subtitle && (
          <span className="shrink-0 truncate text-[10px] text-muted-foreground">
            {item.subtitle}
          </span>
        )}
      </button>
      {open && (
        <div className="max-h-80 overflow-auto border-t border-border/60 px-3 py-2">
          <MarkdownView content={item.content} />
        </div>
      )}
    </div>
  );
}

export function MemoryTab({ threadId }: MemoryTabProps) {
  const [messages] = useThreadMessages(threadId);
  const activeWorkspaceId = useWorkspacesStore((s) => s.getActive()?.id);
  const jobs = useRagJobsStore((s) => s.jobs);

  // Jobs de indexação RAG do workspace ativo (atividade ao vivo).
  const ragJobs = useMemo(
    () =>
      Object.values(jobs).filter(
        (j) => !activeWorkspaceId || j.workspaceId === activeWorkspaceId,
      ),
    [jobs, activeWorkspaceId],
  );

  const { rag, web, activeWeb } = useMemo(() => {
    const ragItems: MemoryItem[] = [];
    const webItems: MemoryItem[] = [];
    const activeWebItems: string[] = [];
    const seenRag = new Set<string>();

    for (const msg of messages) {
      for (const c of msg.ragCitations ?? []) {
        const key = `${c.source}::${c.chunk.slice(0, 64)}`;
        if (seenRag.has(key)) continue;
        seenRag.add(key);
        ragItems.push({
          id: `rag-${ragItems.length}`,
          kind: "rag",
          title: c.source,
          subtitle: `[${c.index}]`,
          content: c.chunk,
        });
      }
      for (const call of msg.toolCalls ?? []) {
        if (!WEB_TOOLS.has(call.name)) continue;
        const args = call.args ?? {};
        const title =
          (typeof args.query === "string" && args.query) ||
          (typeof args.url === "string" && args.url) ||
          call.name;
        // Sem output ainda → busca em andamento (deep research ao vivo).
        if (call.output == null || call.output === "") {
          activeWebItems.push(title);
          continue;
        }
        webItems.push({
          id: `web-${call.id}`,
          kind: "web",
          title,
          subtitle: call.name === "fetch_url" ? "fetch" : "search",
          content: toText(call.output) || m.workbench_memory_no_result(),
        });
      }
    }
    return { rag: ragItems, web: webItems, activeWeb: activeWebItems };
  }, [messages]);

  const hasActivity = ragJobs.length > 0 || activeWeb.length > 0;
  const isEmpty = !hasActivity && rag.length === 0 && web.length === 0;

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col">
        <RagSettingsPanel />
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <Brain className="h-8 w-8 shrink-0 text-muted-foreground/40" />
          <div className="max-w-[240px]">
            <p className="text-sm font-medium text-foreground">
              {m.workbench_memory_empty_title()}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {m.workbench_memory_empty_desc()}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <RagSettingsPanel />
      <div className="flex-1 space-y-4 overflow-auto px-3 pb-3">
        {hasActivity && (
          <section className="space-y-1.5">
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {m.workbench_memory_activity()}
            </h3>
            {ragJobs.map((job) => {
              const pct =
                job.total > 0
                  ? Math.min(100, Math.round((job.processed / job.total) * 100))
                  : job.status === "done"
                    ? 100
                    : 5;
              const stalled =
                job.status === "paused" || job.status === "failed";
              return (
                <div
                  key={job.jobId}
                  className="rounded-lg border border-border/60 bg-card/30 px-2.5 py-2"
                >
                  <div className="flex items-center gap-2">
                    {job.status === "done" ? (
                      <Database className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                    ) : stalled ? (
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" />
                    ) : (
                      <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />
                    )}
                    <span className="min-w-0 flex-1 truncate text-xs text-foreground">
                      {m.workbench_memory_indexing()} {baseName(job.path)}
                    </span>
                    <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                      {job.processed}/{job.total}
                    </span>
                  </div>
                  {stalled && job.errorReason ? (
                    <p className="mt-1.5 text-[11px] leading-snug text-amber-600 dark:text-amber-400">
                      {job.errorReason}
                    </p>
                  ) : (
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted/60">
                      <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
            {activeWeb.map((query, i) => (
              <div
                key={`active-web-${i}`}
                className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/30 px-2.5 py-2"
              >
                <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />
                <span className="min-w-0 flex-1 truncate text-xs text-foreground">
                  {m.workbench_memory_searching()} {query}
                </span>
              </div>
            ))}
          </section>
        )}

        {rag.length > 0 && (
          <section className="space-y-1.5">
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <Database className="h-3 w-3" />
              {m.workbench_memory_group_rag()} ({rag.length})
            </h3>
            {rag.map((item) => (
              <MemoryPill key={item.id} item={item} />
            ))}
          </section>
        )}
        {web.length > 0 && (
          <section className="space-y-1.5">
            <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <Globe className="h-3 w-3" />
              {m.workbench_memory_group_web()} ({web.length})
            </h3>
            {web.map((item) => (
              <MemoryPill key={item.id} item={item} />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
