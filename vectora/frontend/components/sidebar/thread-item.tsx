"use client";

import { memo } from "react";
import { Trash2 } from "lucide-react";
import type { Thread } from "@/lib/hooks/threads";
import { queryClient } from "../../src/router";
import { getHistory, listThreads } from "@/lib/api/vectora-client";
import { threadsQueryKey } from "@/lib/queries/threads";
import { m } from "@/lib/paraglide/messages";
import { getRelativeTime } from "./sidebar-utils";

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
  const threadDate = new Date(thread.updated_at || thread.created_at);
  const title = thread.metadata?.title || m.sidebar_new_conversation();

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
      className={`group flex items-center gap-3 px-3 py-2.5 text-sm w-full rounded-lg transition-all duration-200 cursor-pointer shadow-depth-xs ${
        isActive
          ? "bg-[#7FC8FF]/15 text-sidebar-foreground shadow-depth-sm border border-[#7FC8FF]/40"
          : "text-sidebar-foreground"
      }`}
      onClick={() => onSelect(thread.thread_id)}
      onMouseEnter={handleMouseEnter}
    >
      <div className="flex-1 min-w-0">
        <div className="truncate font-medium">{title}</div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {getRelativeTime(threadDate)}
        </div>
      </div>
      <button
        onClick={(e) => onDelete(thread.thread_id, e)}
        className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-1 rounded-md hover:bg-destructive/10"
      >
        <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
      </button>
    </div>
  );
});
