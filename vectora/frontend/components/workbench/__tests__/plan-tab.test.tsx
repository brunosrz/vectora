// @vitest-environment jsdom
/**
 * PlanTab — TasksSection (item 7 do plano de Plan Mode real): a seção
 * "Tasks" passou a renderizar a checklist real de write_todos
 * (pending/in_progress/completed), não mais os mesmos artifacts da lista
 * principal. Cobre os 3 estados visuais e confirma que a lista de
 * artifacts continua intacta (fonte de dados diferente, seção separada).
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import { PlanTab } from "../tabs/plan-tab";

vi.mock("@/lib/api/vectora-client", () => ({
  getThreadActivity: vi.fn().mockResolvedValue({ files_touched: [] }),
}));

const fetchMock = vi.fn();

function renderPlanTab(threadId: string) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PlanTab threadId={threadId} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({
    ok: true,
    json: async () => ({ artifacts: [] }),
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("PlanTab — TasksSection (write_todos)", () => {
  it("renderiza os 3 estados de status (pending/in_progress/completed)", async () => {
    const threadId = "t-tasks-1";
    useWorkbenchStore.getState().setPlanItems(threadId, [
      {
        title: "doc.md",
        path: "/doc.md",
        session_id: threadId,
        created_at: "2025",
      },
    ]);
    useWorkbenchStore.getState().setTodos(threadId, [
      { content: "passo pendente", status: "pending" },
      { content: "passo em andamento", status: "in_progress" },
      { content: "passo concluído", status: "completed" },
    ]);

    renderPlanTab(threadId);

    expect(await screen.findByText("passo pendente")).toBeInTheDocument();
    expect(screen.getByText("passo em andamento")).toBeInTheDocument();
    const completed = screen.getByText("passo concluído");
    expect(completed).toBeInTheDocument();
    expect(completed.className).toContain("line-through");
  });

  it("não renderiza a seção Tasks quando não há todos", async () => {
    const threadId = "t-tasks-2";
    useWorkbenchStore.getState().setPlanItems(threadId, [
      {
        title: "doc.md",
        path: "/doc.md",
        session_id: threadId,
        created_at: "2025",
      },
    ]);
    useWorkbenchStore.getState().setTodos(threadId, []);

    renderPlanTab(threadId);

    await screen.findByText("doc.md");
    expect(screen.queryByText(/Tasks/)).not.toBeInTheDocument();
  });

  it("a lista de artifacts continua intacta — fonte de dados separada dos todos", async () => {
    const threadId = "t-tasks-3";
    useWorkbenchStore.getState().setPlanItems(threadId, [
      {
        title: "spec.md",
        path: "/spec.md",
        session_id: threadId,
        created_at: "2025",
      },
    ]);
    useWorkbenchStore
      .getState()
      .setTodos(threadId, [{ content: "passo 1", status: "in_progress" }]);

    renderPlanTab(threadId);

    expect(await screen.findByText("spec.md")).toBeInTheDocument();
    expect(screen.getByText("passo 1")).toBeInTheDocument();
  });
});
