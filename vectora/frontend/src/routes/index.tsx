import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Sidebar } from "@/components/sidebar/sidebar";
import { LicenseBanner } from "@/components/layout/license-banner";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useSettingsStore } from "@/lib/stores/settings-store";
import {
  useThreadsQuery,
  useDeleteThread,
  threadsQueryKey,
} from "@/lib/queries/threads";
import { queryClient } from "../router";
import { listThreads } from "@/lib/api/vectora-client";

export const Route = createFileRoute("/")({
  loader: async () => {
    await queryClient.ensureQueryData({
      queryKey: threadsQueryKey,
      queryFn: () => listThreads(1),
      staleTime: 30_000,
    });
  },
  component: HomeScreen,
});

function HomeScreen() {
  const navigate = useNavigate();
  const userId = useAuthStore((s) => s.user?.id);
  const { data: threads = [], isLoading } = useThreadsQuery(userId);
  const deleteThread = useDeleteThread();
  const setChatMode = useSettingsStore((s) => s.setChatMode);
  const sidebarWidth = useSettingsStore((s) => s.sidebarWidth);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleSelectThread = (id: string) => {
    const t = threads.find((th) => th.thread_id === id);
    if (t) setChatMode((t.mode ?? "dev") === "chat");
    void navigate({ to: "/session/$threadId", params: { threadId: id } });
  };

  const handleNewChat = () => {
    void navigate({ to: "/session/$threadId", params: { threadId: "new" } });
  };

  const handleDeleteThread = async (id: string) => {
    await deleteThread.mutateAsync(id);
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <LicenseBanner fullWidth />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div
          className="hidden md:flex shrink-0"
          style={isCollapsed ? undefined : { width: sidebarWidth }}
        >
          <Sidebar
            isCollapsed={isCollapsed}
            onToggle={() => setIsCollapsed((v) => !v)}
            threads={threads}
            currentThreadId=""
            onSelectThread={handleSelectThread}
            onDeleteThread={handleDeleteThread}
            onNewChat={handleNewChat}
            isLoading={isLoading}
            isNewSession={false}
          />
        </div>
        <main className="flex-1 min-w-0" />
      </div>
    </div>
  );
}
