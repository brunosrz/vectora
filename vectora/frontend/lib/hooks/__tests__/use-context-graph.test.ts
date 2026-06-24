// @vitest-environment jsdom
/**
 * useContextGraph — busca de status/report, build, polling e getHtmlUrl.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// ── fetch global mockado ─────────────────────────────────────────────────────

const FETCH_MOCK = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  FETCH_MOCK.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockOk(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFail(status = 404): Response {
  return new Response(JSON.stringify({ detail: "not found" }), { status });
}

import { useContextGraph } from "@/lib/hooks/use-context-graph";

// ── testes ───────────────────────────────────────────────────────────────────

describe("useContextGraph", () => {
  it("busca status ao montar com workspaceId válido", async () => {
    FETCH_MOCK.mockResolvedValueOnce(mockOk({ status: "not_built" }));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    expect(FETCH_MOCK).toHaveBeenCalledWith(
      expect.stringContaining("/workspaces/ws1/context-graph/status"),
    );
    expect(result.current.status.status).toBe("not_built");
  });

  it("não busca e mantém unknown quando workspaceId é null", () => {
    const { result } = renderHook(() => useContextGraph(null));
    expect(FETCH_MOCK).not.toHaveBeenCalled();
    expect(result.current.status.status).toBe("unknown");
  });

  it("não busca quando workspaceId é string vazia", () => {
    const { result } = renderHook(() => useContextGraph(""));
    expect(FETCH_MOCK).not.toHaveBeenCalled();
    expect(result.current.status.status).toBe("unknown");
  });

  it("busca report automaticamente quando status é done", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      mockOk({ status: "done", node_count: 5, edge_count: 3 }),
    ).mockResolvedValueOnce(mockOk({ report: "**God nodes**\n- Auth\n" }));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    expect(FETCH_MOCK).toHaveBeenCalledTimes(2);
    expect(result.current.report).toContain("God nodes");
    expect(result.current.status.node_count).toBe(5);
  });

  it("mantém report null quando status não é done", async () => {
    FETCH_MOCK.mockResolvedValueOnce(mockOk({ status: "running" }));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    expect(result.current.report).toBeNull();
  });

  it("build POST e seta status running após resposta ok", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      mockOk({ status: "not_built" }),
    ).mockResolvedValueOnce(
      mockOk({ status: "queued", message: "enfileirado" }),
    );

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    await act(async () => {
      await result.current.build();
    });

    expect(FETCH_MOCK).toHaveBeenCalledWith(
      expect.stringContaining("/build"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.current.status.status).toBe("running");
  });

  it("build envia opções model/mode/update no body", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      mockOk({ status: "not_built" }),
    ).mockResolvedValueOnce(mockOk({ status: "queued" }));

    const { result } = renderHook(() => useContextGraph("ws2"));
    await act(async () => {});

    await act(async () => {
      await result.current.build({
        model: "gpt-4o",
        mode: "ast",
        update: true,
      });
    });

    const call = FETCH_MOCK.mock.calls.find((args) =>
      String(args[0]).includes("/build"),
    );
    const body = JSON.parse(call![1].body as string);
    expect(body.model).toBe("gpt-4o");
    expect(body.mode).toBe("ast");
    expect(body.update).toBe(true);
  });

  it("build falha silenciosamente se fetch rejeita (sem lançar)", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      mockOk({ status: "not_built" }),
    ).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    await act(async () => {
      await result.current.build();
    });

    expect(result.current.loading).toBe(false);
  });

  it("getHtmlUrl retorna URL com workspaceId codificado", async () => {
    FETCH_MOCK.mockResolvedValue(mockOk({ status: "unknown" }));
    const { result } = renderHook(() => useContextGraph("ws-abc"));
    await act(async () => {});
    expect(result.current.getHtmlUrl()).toContain(
      "/workspaces/ws-abc/context-graph/html",
    );
  });

  it("getHtmlUrl retorna null sem workspaceId", () => {
    const { result } = renderHook(() => useContextGraph(null));
    expect(result.current.getHtmlUrl()).toBeNull();
  });

  it("fetch com erro de rede não quebra o hook", async () => {
    FETCH_MOCK.mockRejectedValueOnce(new Error("offline"));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    expect(result.current.status.status).toBe("unknown");
  });

  it("resposta não-ok do status não altera o estado além do fallback", async () => {
    FETCH_MOCK.mockResolvedValueOnce(mockFail(500));

    const { result } = renderHook(() => useContextGraph("ws1"));
    await act(async () => {});

    expect(result.current.status.status).toBe("unknown");
  });
});
