"use client";

import { memo } from "react";
import { Trash2 } from "lucide-react";
import type { Thread } from "@/lib/hooks/threads";
import { queryClient } from "../../src/router";
import { getHistory, listThreads } from "@/lib/api/vectora-client";
import { threadsQueryKey } from "@/lib/queries/threads";
import { m } from "@/lib/paraglide/messages";
import { useStreamingStore } from "@/lib/stores/streaming-store";

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string, e: React.MouseEvent) => void;
}

export const ThreadItem = memo(function ThreadItem({
  thread,
  isActive,
  onSelect,
  onDelete,
}: ThreadItemProps) {
  const title = thread.metadata?.title || m.sidebar_new_conversation();
  const isStreaming = useStreamingStore((s) =>
    Boolean(s.streaming[thread.thread_id]),
  );

  const handleMouseEnter = () => {
    void queryClient.prefetchQuery({
      queryKey: ["thread-history", thread.thread_id],
      queryFn: () => getHistory(thread.thread_id),
      staleTime: 30_000,
    });
    void queryClient.prefetchQuery({
      queryKey: threadsQueryKey,
      queryFn: () => listThreads(50),
      staleTime: 30_000,
    });
  };

  return (
    <div
      className={`group flex items-center gap-2 px-2 py-1 text-sm w-full rounded-md transition-colors duration-150 cursor-pointer ${
        isActive
          ? "bg-muted/60 text-foreground"
          : "text-muted-foreground hover:bg-muted/30 hover:text-foreground"
      }`}
      onClick={() => onSelect(thread.thread_id)}
      onMouseEnter={handleMouseEnter}
    >
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {isStreaming ? (
          <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-foreground/50 animate-pulse" />
        ) : (
          <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-transparent" />
        )}
        <span className="truncate text-[12px] leading-5">{title}</span>
      </div>
      <button
        onClick={(e) => onDelete(thread.thread_id, e)}
        className="opacity-0 group-hover:opacity-100 transition-opacity duration-150 p-1 rounded hover:bg-destructive/10 shrink-0"
      >
        <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
      </button>
    </div>
  );
});
