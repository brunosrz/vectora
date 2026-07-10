import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchPrefs, pushPrefs } from "../settings-prefs";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchPrefs", () => {
  it("devolve o JSON quando a resposta é ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          theme: "dark",
          selectedModel: "cohere:command-a",
        }),
      }),
    );
    const prefs = await fetchPrefs();
    expect(prefs).toEqual({ theme: "dark", selectedModel: "cohere:command-a" });
  });

  it("devolve objeto vazio quando a resposta não é ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    expect(await fetchPrefs()).toEqual({});
  });

  it("devolve objeto vazio em falha de rede (sem lançar)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(fetchPrefs()).resolves.toEqual({});
  });
});

describe("pushPrefs", () => {
  it("faz PATCH com o corpo serializado", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    await pushPrefs({ theme: "dark" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/settings/prefs",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ theme: "dark" }),
      }),
    );
  });

  it("nunca lança em falha de rede (fire-and-forget)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(pushPrefs({ theme: "dark" })).resolves.toBeUndefined();
  });
});
