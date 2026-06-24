// @vitest-environment jsdom
/**
 * Tests dos RPCs do vectora-client (mock de `fetch`): serialização do body,
 * credentials, parse da resposta, refresh automático em 401 e erro tipado.
 * Cobre os RPCs novos (generateTitle) e o caminho de auth compartilhado.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getHistory,
  generateTitle,
  listThreads,
  createThread,
  getThreadPins,
  setThreadPins,
} from "@/lib/api/vectora-client";

function jsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("RPCs simples", () => {
  it("generateTitle: POST GenerateTitle com thread_id e retorna {title}", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ title: "Plano de deploy" }));
    const r = await generateTitle("t1");
    expect(r.title).toBe("Plano de deploy");

    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain(
      "/vectora.chat.v1.ThreadService/GenerateTitle",
    );
    expect(opts.method).toBe("POST");
    expect(opts.credentials).toBe("include");
    expect(JSON.parse(opts.body as string)).toEqual({ thread_id: "t1" });
  });

  it("getHistory: retorna a lista de mensagens do backend", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ messages: [{ role: "human", content: "oi" }] }),
    );
    const r = await getHistory("t1");
    expect(r.messages).toHaveLength(1);
    expect(r.messages[0]).toEqual({ role: "human", content: "oi" });
  });

  it("createThread: envia workspace_id (vazio quando ausente)", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "abc", created_at: "", updated_at: "", title: "" }),
    );
    await createThread();
    const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(opts.body as string)).toEqual({ workspace_id: "" });
  });
});

describe("auth no postRpc", () => {
  it("401 dispara /auth/refresh e retenta uma única vez", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({}, 401)) // RPC → 401
      .mockResolvedValueOnce(jsonResponse({}, 200)) // /auth/refresh → ok
      .mockResolvedValueOnce(jsonResponse({ messages: [] })); // retry → ok

    const r = await getHistory("t1");
    expect(r.messages).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1][0])).toContain("/auth/refresh");
  });

  it("erro não-401 lança com o status", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "boom" }, 500));
    await expect(listThreads()).rejects.toThrow(/500/);
  });
});

describe("ThreadService pins (WB-1)", () => {
  it("getThreadPins: POST GetThreadPins com thread_id", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t1", pins: ["a.py", "b.py"] }),
    );
    const r = await getThreadPins("t1");
    expect(r.pins).toEqual(["a.py", "b.py"]);
    expect(r.thread_id).toBe("t1");

    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain(
      "/vectora.chat.v1.ThreadService/GetThreadPins",
    );
    expect(opts.method).toBe("POST");
    expect(opts.credentials).toBe("include");
    expect(JSON.parse(opts.body as string)).toEqual({ thread_id: "t1" });
  });

  it("getThreadPins: lista vazia quando a sessão não tem pins", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t1", pins: [] }),
    );
    const r = await getThreadPins("t1");
    expect(r.pins).toEqual([]);
  });

  it("setThreadPins: POST SetThreadPins com thread_id e pins", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t2", pins: ["x.py"] }),
    );
    const r = await setThreadPins("t2", ["x.py"]);
    expect(r.pins).toEqual(["x.py"]);

    const [url, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain(
      "/vectora.chat.v1.ThreadService/SetThreadPins",
    );
    expect(JSON.parse(opts.body as string)).toEqual({
      thread_id: "t2",
      pins: ["x.py"],
    });
  });

  it("setThreadPins: envia lista vazia (limpar pins)", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t3", pins: [] }),
    );
    const r = await setThreadPins("t3", []);
    expect(r.pins).toEqual([]);
    const [, opts] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(opts.body as string)).toEqual({
      thread_id: "t3",
      pins: [],
    });
  });

  it("setThreadPins: devolve a lista normalizada do backend (dedup)", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t4", pins: ["a.py"] }),
    );
    const r = await setThreadPins("t4", ["a.py", "a.py"]);
    expect(r.pins).toEqual(["a.py"]);
  });

  it("setThreadPins: preserva ordem de múltiplos pins", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ thread_id: "t5", pins: ["a.py", "b.py", "c.py"] }),
    );
    const r = await setThreadPins("t5", ["a.py", "b.py", "c.py"]);
    expect(r.pins).toEqual(["a.py", "b.py", "c.py"]);
  });

  it("getThreadPins: 401 dispara refresh e retenta", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({}, 200))
      .mockResolvedValueOnce(jsonResponse({ thread_id: "t6", pins: ["z.py"] }));
    const r = await getThreadPins("t6");
    expect(r.pins).toEqual(["z.py"]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("setThreadPins: erro não-401 lança com o status", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "boom" }, 500));
    await expect(setThreadPins("t7", ["a.py"])).rejects.toThrow(/500/);
  });

  it("getThreadPins: erro não-401 lança com o status", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "x" }, 503));
    await expect(getThreadPins("t8")).rejects.toThrow(/503/);
  });
});
