// @vitest-environment jsdom
/**
 * Tests para useBackgroundTasks — CRUD session-scoped das tarefas em segundo
 * plano. Mocka `fetch` e verifica método + URL de cada operação, com o par
 * de erro/borda no mesmo teste (CLAUDE.md §18).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useBackgroundTasks } from "../use-background-tasks";

interface Call {
  url: string;
  method: string;
}

function jsonRes(body: unknown, ok = true): Response {
  return { ok, json: async () => body } as unknown as Response;
}

function installFetch(handler: (url: string, init?: RequestInit) => Response) {
  const calls: Call[] = [];
  const mock = vi.fn((url: string, init?: RequestInit) => {
    calls.push({ url, method: init?.method ?? "GET" });
    return Promise.resolve(handler(url, init));
  });
  vi.stubGlobal("fetch", mock);
  return calls;
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.unstubAllGlobals());

const TASK = {
  id: "t1",
  session_id: "thread-1",
  workspace_id: null,
  kind: "routine",
  name: "Resumo",
  instruction: "i",
  trigger_type: "interval",
  trigger_config: { cron_expr: "0 9 * * *" },
  enabled: true,
  last_run_at: null,
  next_run_at: null,
};
const RUN = {
  id: "r1",
  task_id: "t1",
  run_thread_id: "bg-t1-1",
  trigger_source: "manual",
  status: "done",
  summary: "ok",
  started_at: "2026-06-23T00:00:00Z",
  finished_at: "2026-06-23T00:00:01Z",
};

describe("useBackgroundTasks", () => {
  it("carrega tasks e runs scoped pela session", async () => {
    installFetch((url) => {
      if (url.endsWith("/tasks")) return jsonRes([TASK]);
      if (url.endsWith("/runs")) return jsonRes([RUN]);
      return jsonRes([]);
    });

    const { result } = renderHook(() => useBackgroundTasks("thread-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.runs).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith("/sessions/thread-1/background/tasks");
    expect(fetch).toHaveBeenCalledWith("/sessions/thread-1/background/runs");

    // Erro/borda: backend devolve !ok → listas vazias, sem quebrar.
    vi.unstubAllGlobals();
    installFetch(() => jsonRes(null, false));
    const { result: r2 } = renderHook(() => useBackgroundTasks("thread-1"));
    await waitFor(() => expect(r2.current.loading).toBe(false));
    expect(r2.current.tasks).toEqual([]);
    expect(r2.current.runs).toEqual([]);
  });

  it("createTask faz POST scoped e refetcha; !ok devolve false", async () => {
    let postOk = true;
    const calls = installFetch((url, init) => {
      if (init?.method === "POST" && url.endsWith("/tasks")) {
        return jsonRes({}, postOk);
      }
      if (url.endsWith("/tasks") || url.endsWith("/runs")) return jsonRes([]);
      return jsonRes([]);
    });

    const { result } = renderHook(() => useBackgroundTasks("s"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let ok = false;
    await act(async () => {
      ok = await result.current.createTask({
        kind: "routine",
        name: "n",
        instruction: "i",
        trigger_type: "manual",
      });
    });
    expect(ok).toBe(true);
    expect(
      calls.some(
        (c) => c.method === "POST" && c.url === "/sessions/s/background/tasks",
      ),
    ).toBe(true);

    // Erro/borda: POST !ok → createTask devolve false.
    postOk = false;
    await act(async () => {
      ok = await result.current.createTask({
        kind: "routine",
        name: "n",
        instruction: "i",
        trigger_type: "manual",
      });
    });
    expect(ok).toBe(false);
  });

  it("toggle/delete/run usam PATCH/DELETE/POST nas URLs certas", async () => {
    const calls = installFetch((url) => {
      if (url.endsWith("/tasks") || url.endsWith("/runs")) return jsonRes([]);
      return jsonRes({});
    });

    const { result } = renderHook(() => useBackgroundTasks("s"));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.toggleTask("t1", false);
    });
    await act(async () => {
      await result.current.deleteTask("t1");
    });
    await act(async () => {
      await result.current.runTask("t1");
    });

    expect(
      calls.some(
        (c) =>
          c.method === "PATCH" && c.url === "/sessions/s/background/tasks/t1",
      ),
    ).toBe(true);
    expect(
      calls.some(
        (c) =>
          c.method === "DELETE" && c.url === "/sessions/s/background/tasks/t1",
      ),
    ).toBe(true);
    expect(
      calls.some(
        (c) =>
          c.method === "POST" &&
          c.url === "/sessions/s/background/tasks/t1/run",
      ),
    ).toBe(true);
  });
});
