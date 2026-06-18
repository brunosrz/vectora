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
