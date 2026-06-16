"use client";

/**
 * StorageTab — "Memória da sessão": o que o Vectora recuperou nesta thread.
 *
 * Agrega o contexto trazido para as respostas — trechos da base de
 * conhecimento (RAG) e resultados de web search / fetch — em pílulas que
 * expandem para leitura do conteúdo completo. É a visão de "o que o agente
 * sabe agora", derivada das mensagens da thread (sem novo endpoint).
 */

import { useMemo, useState } from "react";
import { Brain, ChevronRight, Database, Globe } from "lucide-react";
import { useThreadMessages } from "@/lib/hooks/chat/use-thread-messages";
import { MarkdownView } from "@/components/workbench/markdown-view";
import { m } from "@/lib/paraglide/messages";

interface StorageTabProps {
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

export function StorageTab({ threadId }: StorageTabProps) {
  const [messages] = useThreadMessages(threadId);

  const { rag, web } = useMemo(() => {
    const ragItems: MemoryItem[] = [];
    const webItems: MemoryItem[] = [];
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
        webItems.push({
          id: `web-${call.id}`,
          kind: "web",
          title,
          subtitle: call.name === "fetch_url" ? "fetch" : "search",
          content: toText(call.output) || m.workbench_memory_no_result(),
        });
      }
    }
    return { rag: ragItems, web: webItems };
  }, [messages]);

  const isEmpty = rag.length === 0 && web.length === 0;

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
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
    );
  }

  return (
    <div className="h-full space-y-4 overflow-auto p-3">
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
  );
}
