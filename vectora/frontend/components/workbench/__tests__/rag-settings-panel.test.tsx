// @vitest-environment jsdom
/**
 * RagSettingsPanel: o gear abre o painel, carrega /rag/settings + /rag/collections,
 * faz PATCH ao alternar o reranker, e lista coleções com botão de apagar.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";

import { RagSettingsPanel } from "../rag-settings-panel";

const FETCH = vi.fn();

function jsonRes(body: unknown, ok = true) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: ok ? 200 : 500,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

beforeEach(() => {
  FETCH.mockReset();
  vi.stubGlobal("fetch", FETCH);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("RagSettingsPanel", () => {
  it("o gear abre o painel e carrega settings + coleções", async () => {
    FETCH.mockImplementation((url: string) => {
      if (url.includes("/rag/settings"))
        return jsonRes({
          reranker_enabled: true,
          reranker_top_k: 7,
          rerank_provider: "auto",
          embed_provider: "auto",
          ingest_file_types: [],
        });
      if (url.includes("/rag/collections"))
        return jsonRes({ collections: [{ name: "articles", count: 3 }] });
      return jsonRes({});
    });

    render(<RagSettingsPanel />);
    expect(screen.queryByTestId("rag-settings-panel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("rag-settings-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("rag-settings-panel")).toBeInTheDocument(),
    );
    // top_k carregado do backend
    await waitFor(() =>
      expect((screen.getByDisplayValue("7") as HTMLInputElement).value).toBe(
        "7",
      ),
    );
    // coleção listada
    expect(screen.getByText("articles")).toBeInTheDocument();
  });

  it("alternar o reranker dispara PATCH /rag/settings", async () => {
    FETCH.mockImplementation((url: string) => {
      if (url.includes("/rag/settings"))
        return jsonRes({
          reranker_enabled: true,
          reranker_top_k: 5,
          rerank_provider: "auto",
          embed_provider: "auto",
          ingest_file_types: [],
        });
      if (url.includes("/rag/collections")) return jsonRes({ collections: [] });
      return jsonRes({});
    });

    render(<RagSettingsPanel />);
    fireEvent.click(screen.getByTestId("rag-settings-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("rag-settings-panel")).toBeInTheDocument(),
    );

    const checkbox = screen.getAllByRole("checkbox")[0] as HTMLInputElement;
    fireEvent.click(checkbox);

    await waitFor(() => {
      const patchCall = FETCH.mock.calls.find(
        (c) => c[0].includes("/rag/settings") && c[1]?.method === "PATCH",
      );
      expect(patchCall).toBeTruthy();
      expect(JSON.parse(patchCall![1].body as string)).toHaveProperty(
        "reranker_enabled",
        false,
      );
    });
  });
});
