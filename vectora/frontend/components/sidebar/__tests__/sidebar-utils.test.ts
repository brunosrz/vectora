import { describe, it, expect } from "vitest";
import { groupThreadsByWorkspace } from "../sidebar-utils";
import type { Thread } from "@/lib/hooks/threads";
import type { WorkspaceInfo } from "@/lib/stores/workspaces-store";

function thread(overrides: Partial<Thread> & { thread_id: string }): Thread {
  return {
    created_at: "2026-07-09T10:00:00Z",
    updated_at: "2026-07-09T10:00:00Z",
    metadata: { user_id: "u1", title: overrides.thread_id },
    ...overrides,
  };
}

function ws(id: string): WorkspaceInfo {
  return {
    id,
    name: id,
    cwd: `/proj/${id}`,
    trusted: true,
    is_git_repo: true,
    git_remote: null,
    git_current_branch: null,
    git_default_branch: null,
  };
}

describe("groupThreadsByWorkspace — isolação e cache", () => {
  it("sessão de código com workspace_id NUNCA vai pra orphans, mesmo com lista vazia", () => {
    // Cenário do bug de cache: no boot a lista de workspaces ainda não hidratou
    // (`workspaces === []`). A sessão de código não pode cair em OUTRAS CONVERSAS
    // (que é exclusiva de chat) só porque o workspace ainda não carregou.
    const t = thread({ thread_id: "a", workspace_id: "w1", mode: "code" });
    const { groups, orphans } = groupThreadsByWorkspace([t], []);

    expect(orphans).toHaveLength(0);
    expect(groups).toHaveLength(1);
    expect(groups[0].workspace.id).toBe("w1");
    expect(groups[0].threads).toContain(t);
  });

  it("usa o workspace real quando ele já está na lista hidratada", () => {
    const t = thread({ thread_id: "a", workspace_id: "w1", mode: "code" });
    const { groups, orphans } = groupThreadsByWorkspace([t], [ws("w1")]);

    expect(orphans).toHaveLength(0);
    expect(groups).toHaveLength(1);
    expect(groups[0].workspace.cwd).toBe("/proj/w1");
  });

  it("sessão de chat (sem workspace_id) vai pra orphans/OUTRAS CONVERSAS", () => {
    const t = thread({ thread_id: "c", mode: "chat" });
    const { groups, orphans } = groupThreadsByWorkspace([t], [ws("w1")]);

    expect(groups).toHaveLength(0);
    expect(orphans).toEqual([t]);
  });

  it("separa código (grupo por workspace) de chat (orphan) numa lista mista", () => {
    const code = thread({ thread_id: "a", workspace_id: "w1", mode: "code" });
    const chat = thread({ thread_id: "b", mode: "chat" });
    const { groups, orphans } = groupThreadsByWorkspace([code, chat], []);

    expect(orphans).toEqual([chat]);
    expect(groups).toHaveLength(1);
    expect(groups[0].threads).toEqual([code]);
  });
});
