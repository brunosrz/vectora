// @vitest-environment jsdom
/**
 * TasksTab — delegação de subagente (trigger_type/kind "subagent") aparece
 * com o badge próprio e sem os controles de rodar-agora/toggle, que não se
 * aplicam a uma tarefa-âncora auto-gerenciada pelo backend.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { TasksTab } from "../tasks-tab";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (...args: unknown[]) =>
          args.length
            ? `${String(prop)}(${JSON.stringify(args[0])})`
            : String(prop),
    },
  ),
}));

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (sel: (s: { getActive: () => undefined }) => unknown) =>
    sel({ getActive: () => undefined }),
}));

vi.mock("@/lib/hooks/use-webhook-events", () => ({
  useWebhookEvents: () => {},
}));

const mockTasks = vi.fn();
vi.mock("@/lib/hooks/use-background-tasks", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/hooks/use-background-tasks")
  >("@/lib/hooks/use-background-tasks");
  return {
    ...actual,
    useBackgroundTasks: () => mockTasks(),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function baseHook(overrides: Partial<ReturnType<typeof mockTasks>> = {}) {
  return {
    tasks: [],
    runs: [],
    loading: false,
    refetch: vi.fn(),
    createTask: vi.fn(),
    toggleTask: vi.fn(),
    deleteTask: vi.fn(),
    runTask: vi.fn(),
    ...overrides,
  };
}

describe("TasksTab", () => {
  it("mostra o badge de subagente e esconde rodar-agora/toggle pra tarefa-âncora", () => {
    mockTasks.mockReturnValue(
      baseHook({
        tasks: [
          {
            id: "t1",
            session_id: "s1",
            workspace_id: null,
            kind: "subagent",
            name: "Subagente: coder",
            instruction: "",
            trigger_type: "subagent",
            trigger_config: { subagent_type: "coder" },
            enabled: true,
            last_run_at: null,
            next_run_at: null,
          },
        ],
      }),
    );

    render(<TasksTab threadId="t1" />);

    expect(
      screen.getAllByText("background_trigger_subagent").length,
    ).toBeGreaterThan(0);
    expect(screen.queryByTestId("background-run-now")).not.toBeInTheDocument();
  });

  it("mantém rodar-agora e toggle pra tarefas normais (regressão)", () => {
    mockTasks.mockReturnValue(
      baseHook({
        tasks: [
          {
            id: "t2",
            session_id: "s1",
            workspace_id: null,
            kind: "routine",
            name: "Resumo diário",
            instruction: "Resuma o dia",
            trigger_type: "interval",
            trigger_config: { cron_expr: "0 9 * * *" },
            enabled: true,
            last_run_at: null,
            next_run_at: null,
          },
        ],
      }),
    );

    render(<TasksTab threadId="t1" />);

    expect(screen.getByTestId("background-run-now")).toBeInTheDocument();
  });
});
