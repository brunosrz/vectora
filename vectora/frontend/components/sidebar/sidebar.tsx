"use client";

import { useState, useMemo, memo, useCallback } from "react";
import type { Thread } from "@/lib/hooks/threads";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { groupThreads, groupThreadsByWorkspace } from "./sidebar-utils";
import { CollapsedSidebar } from "./collapsed-sidebar";
import { SidebarHeader } from "./sidebar-header";
import { NewChatButton } from "./new-chat-button";
import { SessionSearch } from "./session-search";
import { ThreadList } from "./thread-list";
import { SidebarFooter } from "./sidebar-footer";

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  threads: Thread[];
  currentThreadId: string;
  onSelectThread: (threadId: string) => void;
  onDeleteThread: (threadId: string) => void;
  onNewChat?: () => void;
  isLoading?: boolean;
}

export const Sidebar = memo(function Sidebar({
  isCollapsed,
  onToggle,
  threads,
  currentThreadId,
  onSelectThread,
  onDeleteThread,
  onNewChat,
  isLoading = false,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState<Set<string>>(
    () => new Set(),
  );

  const workspaces = useWorkspacesStore((s) => s.workspaces);

  const filteredThreads = useMemo(() => {
    if (!searchQuery.trim()) return threads;
    const query = searchQuery.toLowerCase();
    return threads.filter((thread) => {
      const title = thread.metadata?.title?.toLowerCase() ?? "";
      const lastMessage = thread.metadata?.lastMessage?.toLowerCase() ?? "";
      return title.includes(query) || lastMessage.includes(query);
    });
  }, [threads, searchQuery]);

  const { groups: workspaceGroups, orphans } = useMemo(
    () => groupThreadsByWorkspace(filteredThreads, workspaces),
    [filteredThreads, workspaces],
  );

  const grouped = useMemo(() => groupThreads(orphans), [orphans]);

  const isSearching = searchQuery.trim().length > 0;

  const handleDeleteThread = useCallback(
    (threadId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onDeleteThread(threadId);
    },
    [onDeleteThread],
  );

  const handleClearSearch = useCallback(() => setSearchQuery(""), []);

  const toggleWorkspaceGroup = useCallback((workspaceId: string) => {
    setCollapsedWorkspaces((prev) => {
      const next = new Set(prev);
      if (next.has(workspaceId)) next.delete(workspaceId);
      else next.add(workspaceId);
      return next;
    });
  }, []);

  if (isCollapsed) {
    return (
      <CollapsedSidebar
        threads={threads}
        currentThreadId={currentThreadId}
        onToggle={onToggle}
        onSelectThread={onSelectThread}
        onNewChat={onNewChat}
      />
    );
  }

  return (
    <>
      <div
        className="md:hidden fixed inset-0 z-30 bg-background/60 backdrop-blur-sm"
        onClick={onToggle}
        aria-hidden
      />
      <aside className="fixed md:relative inset-y-0 left-0 z-40 flex w-72 md:w-full bg-sidebar border-r border-border/40 flex-col">
        <SidebarHeader onToggle={onToggle} />

        {onNewChat && <NewChatButton onClick={onNewChat} />}

        <SessionSearch
          value={searchQuery}
          onChange={setSearchQuery}
          onClear={handleClearSearch}
        />

        <ThreadList
          isLoading={isLoading}
          searchQuery={searchQuery}
          filteredThreads={filteredThreads}
          workspaceGroups={workspaceGroups}
          orphans={orphans}
          grouped={grouped}
          currentThreadId={currentThreadId}
          collapsedWorkspaces={collapsedWorkspaces}
          isSearching={isSearching}
          onSelectThread={onSelectThread}
          onDeleteThread={handleDeleteThread}
          onToggleWorkspace={toggleWorkspaceGroup}
        />

        <SidebarFooter />
      </aside>
    </>
  );
});
