// @vitest-environment jsdom
/**
 * SkillsSection — seção Skills da Library. Cobre a sub-área "Catálogo":
 * vem expandida por padrão (não escondida atrás de um toggle fechado —
 * regressão de descoberta), lista GET /skills/catalog, instalar chama
 * POST /skills {source}, toggle ainda permite recolher/reabrir; erro/borda:
 * catálogo vazio mostra estado específico, não quebra a lista de instaladas
 * ao lado (SkillsTab, mockado).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";

vi.mock("@/components/settings/environment/tabs/skills-tab", () => ({
  SkillsTab: () => <div>stub-skills-tab</div>,
}));

import { SkillsSection } from "../library-skills-section";

afterEach(cleanup);

const CATALOG = [
  {
    id: "pdf-extract",
    name: "PDF Extract",
    description: "Extrai texto de PDFs",
    source: "https://github.com/example/pdf-extract-skill",
  },
];

function mockFetch(entries: typeof CATALOG = CATALOG, installOk = true) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/skills/catalog") {
        return Promise.resolve({
          ok: true,
          json: async () => ({ entries, total: entries.length }),
        } as Response);
      }
      if (url === "/skills" && init?.method === "POST") {
        return Promise.resolve({
          ok: installOk,
          json: async () => ({}),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });
}

describe("SkillsSection — Catálogo", () => {
  it("vem expandido por padrão e lista as skills curadas do registry remoto sem precisar de clique", async () => {
    mockFetch();
    render(<SkillsSection query="" onCountChange={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("PDF Extract")).toBeTruthy();
    });
  });

  it("toggle ainda permite recolher e reabrir o catálogo", async () => {
    mockFetch();
    render(<SkillsSection query="" onCountChange={() => {}} />);
    await waitFor(() => screen.getByText("PDF Extract"));

    fireEvent.click(screen.getByText("Browse catalog"));
    expect(screen.queryByText("PDF Extract")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Browse catalog"));
    await waitFor(() => {
      expect(screen.getByText("PDF Extract")).toBeTruthy();
    });
  });

  it("instalar chama POST /skills com o source da skill", async () => {
    mockFetch();
    render(<SkillsSection query="" onCountChange={() => {}} />);
    await waitFor(() => screen.getByText("PDF Extract"));

    fireEvent.click(screen.getByText("Install"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/skills",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ source: CATALOG[0].source }),
        }),
      );
    });
  });

  it("catálogo vazio mostra estado específico, não erro e não quebra SkillsTab", async () => {
    mockFetch([]);
    render(<SkillsSection query="" onCountChange={() => {}} />);
    expect(screen.getByText("stub-skills-tab")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("No curated skills available yet.")).toBeTruthy();
    });
  });
});
