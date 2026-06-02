"use client";

import { useState, useMemo, memo, useCallback } from "react";
import {
  Trash2,
  PanelLeftClose,
  PanelLeft,
  BookOpen,
  Search,
  X,
  MessageSquare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Thread } from "@/lib/hooks/threads";
import { useT } from "@/lib/i18n";
import { SidebarFolders } from "./sidebar-folders";

type TFunc = (key: string, params?: Record<string, string | number>) => string;

// Add custom scrollbar styles - overlay scrollbar that doesn't affect layout
const scrollbarStyles = `
  .custom-scrollbar {
    scrollbar-width: thin;
    scrollbar-color: transparent transparent;
  }
  .custom-scrollbar:hover {
    scrollbar-color: var(--sidebar-primary, #7FC8FF) transparent;
  }
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: transparent;
    border-radius: 3px;
  }
  .custom-scrollbar:hover::-webkit-scrollbar-thumb {
    background: var(--sidebar-primary, #7FC8FF);
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: var(--sidebar-primary, #99D3FF);
  }
`;

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

function getRelativeTime(date: Date, t: TFunc): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return t("time.just_now");
  if (diffMins < 60) return t("time.minutes_ago", { n: diffMins });
  if (diffHours < 24)
    return diffHours === 1
      ? t("time.hour_ago")
      : t("time.hours_ago", { n: diffHours });
  if (diffDays === 1) return t("time.yesterday");
  if (diffDays < 7) return t("time.days_ago", { n: diffDays });
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return weeks === 1 ? t("time.week_ago") : t("time.weeks_ago", { n: weeks });
  }
  const months = Math.floor(diffDays / 30);
  return months === 1
    ? t("time.month_ago")
    : t("time.months_ago", { n: months });
}

function groupThreads(threads: Thread[]) {
  const now = new Date();
  const today: Thread[] = [];
  const yesterday: Thread[] = [];
  const last7Days: Thread[] = [];
  const older: Thread[] = [];

  threads.forEach((thread) => {
    // Use updated_at from LangGraph thread
    const threadDate = new Date(thread.updated_at || thread.created_at);
    const diffMs = now.getTime() - threadDate.getTime();
    const diffHours = diffMs / 3600000;
    const diffDays = diffMs / 86400000;

    if (diffHours < 24) {
      today.push(thread);
    } else if (diffDays < 2) {
      yesterday.push(thread);
    } else if (diffDays < 7) {
      last7Days.push(thread);
    } else {
      older.push(thread);
    }
  });

  return { today, yesterday, last7Days, older };
}

const UserProfileSection = memo(function UserProfileSection() {
  return null;
});

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
  const t = useT();

  // Filter threads based on search query
  const filteredThreads = useMemo(() => {
    if (!searchQuery.trim()) return threads;

    const query = searchQuery.toLowerCase();
    return threads.filter((thread) => {
      const title = thread.metadata?.title?.toLowerCase() || "";
      const lastMessage = thread.metadata?.lastMessage?.toLowerCase() || "";
      return title.includes(query) || lastMessage.includes(query);
    });
  }, [threads, searchQuery]);

  // Memoize grouped threads to avoid recalculating on every render
  const groupedThreads = useMemo(
    () => groupThreads(filteredThreads),
    [filteredThreads],
  );
  const { today, yesterday, last7Days, older } = groupedThreads;

  // Memoize event handlers to prevent unnecessary re-renders
  const handleSelectThread = useCallback(
    (threadId: string) => {
      onSelectThread(threadId);
    },
    [onSelectThread],
  );

  const handleDeleteThread = useCallback(
    (threadId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onDeleteThread(threadId);
    },
    [onDeleteThread],
  );

  const handleClearSearch = useCallback(() => {
    setSearchQuery("");
  }, []);

  // Memoize renderThreadGroup to prevent recreation on every render
  // IMPORTANT: Must be defined before any conditional returns (Rules of Hooks)
  const renderThreadGroup = useCallback(
    (groupThreads: Thread[], label: string) => {
      if (groupThreads.length === 0) return null;

      return (
        <div className="mt-4 px-3 first:mt-0">
          <h3 className="px-3 text-xs font-semibold text-sidebar-accent-foreground uppercase tracking-wider mb-2 shadow-inset-light">
            {label}
          </h3>
          <div className="space-y-2">
            {groupThreads.map((thread) => {
              const threadDate = new Date(
                thread.updated_at || thread.created_at,
              );
              const title =
                thread.metadata?.title || t("sidebar.new_conversation");

              return (
                <div
                  key={thread.thread_id}
                  className={`group flex items-center gap-3 px-3 py-2.5 text-sm w-full rounded-lg transition-all duration-200 cursor-pointer shadow-depth-xs ${thread.thread_id === currentThreadId ? "bg-[#7FC8FF]/15 text-sidebar-foreground shadow-depth-sm border border-[#7FC8FF]/40" : "text-sidebar-foreground"}`}
                  onClick={() => handleSelectThread(thread.thread_id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {getRelativeTime(threadDate, t)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteThread(thread.thread_id, e)}
                    className="opacity-0 group-hover:opacity-100 transition-all duration-200 p-1 rounded-md hover:bg-destructive/10"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      );
    },
    [currentThreadId, handleSelectThread, handleDeleteThread, t],
  );

  // Early return for collapsed state (after all hooks)
  if (isCollapsed) {
    // Mobile: sem barra slim — só a hamburger no Header reabre.
    // Desktop: barra de 64px com botão de expandir.
    return (
      <aside className="hidden md:flex w-16 bg-gradient-to-b from-sidebar via-sidebar-light to-sidebar border-r border-border/60 flex-col shadow-depth-sm">
        <div className="px-3 py-4 border-b border-border/60 h-16 flex items-center justify-center">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="hover:bg-sidebar-primary/10 hover:text-sidebar-primary transition-all duration-200 shadow-depth-xs hover:shadow-depth-hover rounded-lg"
          >
            <PanelLeft className="w-5 h-5" />
          </Button>
        </div>
      </aside>
    );
  }

  return (
    <>
      <style>{scrollbarStyles}</style>
      {/* J.2.5 — Backdrop atrás do overlay no mobile. Click fecha. */}
      <div
        className="md:hidden fixed inset-0 z-30 bg-background/60 backdrop-blur-sm"
        onClick={onToggle}
        aria-hidden
      />
      <aside className="fixed md:relative inset-y-0 left-0 z-40 flex w-72 md:w-56 bg-gradient-to-b from-sidebar via-sidebar-light to-sidebar-lighter border-r border-border/60 flex-col shadow-depth-md">
        <div className="px-3 pt-[13px] pb-[14px] border-b border-border/60 bg-gradient-to-r from-sidebar-accent/20 via-sidebar-accent/10 to-transparent">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="hover:bg-sidebar-primary/10 hover:text-sidebar-primary transition-all duration-200 shadow-depth-xs hover:shadow-depth-hover rounded-lg"
            >
              <PanelLeftClose className="w-5 h-5" />
            </Button>
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("sidebar.title")}
            </span>
          </div>
        </div>

        {onNewChat && (
          <div className="px-3 pt-2">
            <button
              onClick={onNewChat}
              className="group w-full inline-flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-primary/15 to-primary/5 hover:from-primary/25 hover:to-primary/10 border border-primary/30 hover:border-primary/50 rounded-md text-sm font-medium text-foreground/90 hover:text-foreground transition-all duration-200 whitespace-nowrap"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-primary"
              >
                <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
              </svg>
              {t("header.new_chat")}
            </button>
          </div>
        )}

        {/* F.3.5 — Acesso rápido: workspaces + safe-roots */}
        <SidebarFolders />

        {/* Search Bar */}
        <div className="px-3 py-2 bg-gradient-to-r from-sidebar-accent/5 via-transparent to-transparent">
          <div className="relative group">
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 z-10">
              <Search className="w-4 h-4 text-muted-foreground/70 group-focus-within:text-primary transition-all duration-200" />
            </div>
            <Input
              type="text"
              placeholder={t("sidebar.search_placeholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-8 h-10 text-sm bg-background/80 backdrop-blur-sm border-border/40 focus:border-primary/60 focus:bg-background/90 focus:shadow-sm transition-all duration-200 shadow-sm hover:shadow-md hover:bg-background/90 rounded-lg"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 z-10 text-muted-foreground/60 hover:text-foreground transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/30 rounded-full p-0.5 hover:bg-muted/50"
                aria-label={t("sidebar.clear_search")}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-2 bg-gradient-to-b from-sidebar-accent/5 via-transparent to-sidebar-accent/10 custom-scrollbar">
          {isLoading ? (
            /* M4 — Skeleton rows no lugar do spinner */
            <div className="mt-4 px-3 space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="px-3 py-2.5 rounded-lg"
                  style={{ opacity: 1 - i * 0.12 }}
                >
                  <div className="h-3 w-3/4 rounded-full bg-muted/60 animate-pulse mb-1.5" />
                  <div className="h-2 w-1/3 rounded-full bg-muted/40 animate-pulse" />
                </div>
              ))}
            </div>
          ) : searchQuery && filteredThreads.length === 0 ? (
            <div className="px-6 py-8 text-center text-sm text-muted-foreground bg-gradient-to-br from-card/10 via-card/5 to-transparent rounded-lg mx-3 shadow-depth-xs">
              <div className="font-medium mb-1">{t("sidebar.no_results")}</div>
              <div className="text-xs">{t("sidebar.no_results_hint")}</div>
            </div>
          ) : filteredThreads.length === 0 ? (
            <div className="px-6 py-8 text-center text-sm text-muted-foreground bg-gradient-to-br from-card/10 via-card/5 to-transparent rounded-lg mx-3 shadow-depth-xs">
              <div className="font-medium mb-1">
                {t("sidebar.no_conversations")}
              </div>
              <div className="text-xs">
                {t("sidebar.no_conversations_hint")}
              </div>
            </div>
          ) : (
            <>
              {renderThreadGroup(today, t("sidebar.group.today"))}
              {renderThreadGroup(yesterday, t("sidebar.group.yesterday"))}
              {renderThreadGroup(last7Days, t("sidebar.group.last_7_days"))}
              {renderThreadGroup(older, t("sidebar.group.older"))}
            </>
          )}
        </nav>

        <div className="bg-gradient-to-t from-sidebar-accent/10 via-sidebar-accent/5 to-transparent pt-2 pb-0 space-y-0">
          <a
            href="https://github.com/brunosrz/vectora"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 text-sm text-sidebar-foreground transition-all duration-300 ease-out hover:bg-sidebar-accent/10 group"
          >
            <div className="h-6 w-6 rounded-full bg-sidebar-primary/20 flex items-center justify-center shadow-sm shrink-0">
              <BookOpen className="w-3 h-3 text-sidebar-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium leading-tight transition-colors duration-300 group-hover:text-sidebar-primary/90">
                {t("sidebar.documentation")}
              </div>
              <div className="text-[10px] text-muted-foreground leading-tight transition-colors duration-300 group-hover:text-muted-foreground/80">
                {t("sidebar.documentation_caption")}
              </div>
            </div>
          </a>

          <a
            href="https://github.com/brunosrz/src/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 text-sm text-sidebar-foreground transition-all duration-300 ease-out hover:bg-sidebar-accent/10 group"
          >
            <div className="h-6 w-6 rounded-full bg-sidebar-primary/20 flex items-center justify-center shadow-sm shrink-0">
              <MessageSquare className="w-3 h-3 text-sidebar-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium leading-tight transition-colors duration-300 group-hover:text-sidebar-primary/90">
                {t("sidebar.feedback")}
              </div>
              <div className="text-[10px] text-muted-foreground leading-tight transition-colors duration-300 group-hover:text-muted-foreground/80">
                {t("sidebar.report_issue")}
              </div>
            </div>
          </a>

          <UserProfileSection />
        </div>
      </aside>
    </>
  );
});
