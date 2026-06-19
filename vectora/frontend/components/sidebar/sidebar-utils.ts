import type { Thread } from "@/lib/hooks/threads";
import type { WorkspaceInfo } from "@/lib/stores/workspaces-store";
import { m } from "@/lib/paraglide/messages";

export interface WorkspaceThreadGroup {
  workspace: WorkspaceInfo;
  threads: Thread[];
}

export function activityOf(thread: Thread): number {
  return new Date(thread.updated_at || thread.created_at).getTime();
}

export function shortWorkspaceName(ws: WorkspaceInfo): string {
  if (ws.name) return ws.name;
  const match = ws.cwd.match(/[/\\]([^/\\]+)[/\\]?$/);
  return match?.[1] ?? ws.cwd;
}

export function getRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return m.time_just_now();
  if (diffMins < 60) return m.time_minutes_ago({ n: diffMins });
  if (diffHours < 24)
    return diffHours === 1
      ? m.time_hour_ago()
      : m.time_hours_ago({ n: diffHours });
  if (diffDays === 1) return m.time_yesterday();
  if (diffDays < 7) return m.time_days_ago({ n: diffDays });
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return weeks === 1 ? m.time_week_ago() : m.time_weeks_ago({ n: weeks });
  }
  const months = Math.floor(diffDays / 30);
  return months === 1 ? m.time_month_ago() : m.time_months_ago({ n: months });
}

export interface GroupedThreads {
  today: Thread[];
  yesterday: Thread[];
  last7Days: Thread[];
  older: Thread[];
}

export function groupThreads(threads: Thread[]): GroupedThreads {
  const now = new Date();
  const today: Thread[] = [];
  const yesterday: Thread[] = [];
  const last7Days: Thread[] = [];
  const older: Thread[] = [];

  threads.forEach((thread) => {
    const threadDate = new Date(thread.updated_at || thread.created_at);
    const diffMs = now.getTime() - threadDate.getTime();
    const diffHours = diffMs / 3600000;
    const diffDays = diffMs / 86400000;

    if (diffHours < 24) today.push(thread);
    else if (diffDays < 2) yesterday.push(thread);
    else if (diffDays < 7) last7Days.push(thread);
    else older.push(thread);
  });

  return { today, yesterday, last7Days, older };
}

export function groupThreadsByWorkspace(
  threads: Thread[],
  workspaces: WorkspaceInfo[],
): { groups: WorkspaceThreadGroup[]; orphans: Thread[] } {
  const byWorkspace = new Map<string, Thread[]>();
  const orphans: Thread[] = [];

  threads.forEach((thread) => {
    const ws = thread.workspace_id
      ? workspaces.find((w) => w.id === thread.workspace_id)
      : undefined;
    if (ws) {
      const list = byWorkspace.get(ws.id);
      if (list) list.push(thread);
      else byWorkspace.set(ws.id, [thread]);
    } else {
      orphans.push(thread);
    }
  });

  const groups: WorkspaceThreadGroup[] = workspaces
    .filter((ws) => byWorkspace.has(ws.id))
    .map((ws) => {
      const list = (byWorkspace.get(ws.id) ?? []).toSorted(
        (a, b) => activityOf(b) - activityOf(a),
      );
      return { workspace: ws, threads: list };
    })
    .toSorted((a, b) => activityOf(b.threads[0]) - activityOf(a.threads[0]));

  return { groups, orphans };
}
