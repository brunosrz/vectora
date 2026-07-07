import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  submitIssue,
  submitIssueWithFiles,
  listOpenIssues,
  joinWaitlist,
} from "./issues";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
  SERVICES_URL: "https://services.test",
}));

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("submitIssue", () => {
  const base = {
    title: "Bug ao revelar token",
    category: "bug" as const,
    turnstileToken: "tt-1",
  };

  it("envia o issue com descrição e email opcionais preenchidos", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await submitIssue({
      data: { ...base, description: "Não funciona", email: "a@b.com" },
    });

    expect(result).toEqual({ ok: true });
  });

  it("aceita email como string vazia (edge — schema permite email opcional ou '')", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    await expect(
      submitIssue({ data: { ...base, email: "" } }),
    ).resolves.toEqual({ ok: true });
  });

  it("rejeita título com menos de 3 caracteres (edge — validação Zod)", async () => {
    await expect(
      submitIssue({ data: { ...base, title: "ab" } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita categoria fora do enum (edge)", async () => {
    await expect(
      submitIssue({ data: { ...base, category: "spam" as never } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita descrição acima de 5000 caracteres (edge)", async () => {
    await expect(
      submitIssue({ data: { ...base, description: "x".repeat(5001) } }),
    ).rejects.toBeTruthy();
  });
});

describe("submitIssueWithFiles", () => {
  function validForm() {
    const form = new FormData();
    form.set("title", "Bug com anexo");
    form.set("category", "bug");
    form.set("description", "Descrição");
    form.set("turnstileToken", "tt-1");
    form.append(
      "files",
      new File([new Uint8Array(8)], "print.png", { type: "image/png" }),
    );
    return form;
  }

  it("repassa o FormData intacto pro worker via fetch multipart", async () => {
    const fetchMock = vi.fn(
      async (_url: string, _init?: RequestInit) =>
        new Response(JSON.stringify({ ok: true })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(submitIssueWithFiles({ data: validForm() })).resolves.toEqual({
      ok: true,
    });
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      "https://services.test/issues",
      expect.objectContaining({ method: "POST" }),
    );
    const sent = fetchMock.mock.calls[0]?.[1] as { body: FormData };
    expect(sent.body).toBeInstanceOf(FormData);
    expect(sent.body.getAll("files")).toHaveLength(1);
  });

  it("rejeita título curto antes de bater na rede e propaga erro do worker (pares de erro)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const badForm = validForm();
    badForm.set("title", "ab");
    await expect(submitIssueWithFiles({ data: badForm })).rejects.toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ error: "file_too_large" }), {
        status: 413,
      }),
    );
    await expect(submitIssueWithFiles({ data: validForm() })).rejects.toThrow(
      "file_too_large",
    );
  });
});

describe("listOpenIssues", () => {
  it("retorna a lista com keys de anexo resolvidas pra URLs do worker", async () => {
    mockServicesFetch.mockResolvedValue([
      {
        id: "1",
        title: "Bug X",
        category: "bug",
        description: null,
        files: ["issues/1/abc-print.png"],
        created_at: "now",
      },
    ]);

    const result = await listOpenIssues();
    expect(result).toHaveLength(1);
    expect(result[0]?.files).toEqual([
      "https://services.test/issues/files/issues/1/abc-print.png",
    ]);
  });

  it("issue sem anexos e worker antigo sem campo files não quebram (edge)", async () => {
    mockServicesFetch.mockResolvedValue([
      {
        id: "1",
        title: "Bug X",
        category: "bug",
        description: null,
        created_at: "now",
      },
    ]);
    const result = await listOpenIssues();
    expect(result[0]?.files).toEqual([]);
  });

  it("retorna array vazio quando não há issues (edge)", async () => {
    mockServicesFetch.mockResolvedValue([]);
    await expect(listOpenIssues()).resolves.toEqual([]);
  });
});

describe("joinWaitlist", () => {
  it("entra na waitlist com source informado", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await joinWaitlist({
      data: { email: "a@b.com", turnstileToken: "tt-1", source: "landing" },
    });

    expect(result).toEqual({ ok: true });
  });

  it("funciona sem 'source' (edge — campo opcional)", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    await expect(
      joinWaitlist({ data: { email: "a@b.com", turnstileToken: "tt-1" } }),
    ).resolves.toEqual({ ok: true });
  });

  it("rejeita email inválido (edge — validação Zod)", async () => {
    await expect(
      joinWaitlist({
        data: { email: "invalido", turnstileToken: "tt-1" },
      }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});
