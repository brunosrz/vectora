"use client";

import { memo } from "react";
import type { Thread } from "@/lib/hooks/threads";
import { ThreadItem } from "./thread-item";

interface ThreadGroupProps {
  threads: Thread[];
  label: string;
  currentThreadId: string;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string, e: React.MouseEvent) => void;
}

export const ThreadGroup = memo(function ThreadGroup({
  threads,
  label,
  currentThreadId,
  onSelect,
  onDelete,
}: ThreadGroupProps) {
  if (threads.length === 0) return null;

  return (
    <div className="mt-4 px-3 first:mt-0">
      <h3 className="px-3 text-xs font-semibold text-sidebar-accent-foreground uppercase tracking-wider mb-2 shadow-inset-light">
        {label}
      </h3>
      <div className="space-y-2">
        {threads.map((thread) => (
          <ThreadItem
            key={thread.thread_id}
            thread={thread}
            isActive={thread.thread_id === currentThreadId}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
});
