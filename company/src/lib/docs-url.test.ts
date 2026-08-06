import { describe, it, expect, vi } from "vitest";

const { mockGetLocale } = vi.hoisted(() => ({ mockGetLocale: vi.fn() }));

vi.mock("#/paraglide/runtime", () => ({
  getLocale: mockGetLocale,
}));

const { getDocsUrl } = await import("./docs-url");

describe("getDocsUrl", () => {
  it("usa o locale atual quando a docs publica esse idioma", () => {
    mockGetLocale.mockReturnValue("pt");
    expect(getDocsUrl()).toBe("https://docs.vectora.company/pt");
  });

  it("cai pra en quando o locale do site não tem página na docs (fr/it/de/ru)", () => {
    mockGetLocale.mockReturnValue("fr");
    expect(getDocsUrl()).toBe("https://docs.vectora.company/en");
  });

  it("anexa o path informado, sem barra duplicada", () => {
    mockGetLocale.mockReturnValue("es");
    expect(getDocsUrl("getting-started/installation")).toBe(
      "https://docs.vectora.company/es/getting-started/installation",
    );
    expect(getDocsUrl("/getting-started/installation")).toBe(
      "https://docs.vectora.company/es/getting-started/installation",
    );
  });
});
