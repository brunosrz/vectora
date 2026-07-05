// @vitest-environment jsdom
/**
 * Tests da paginação do HistoryView (offset 50 em 50) — regressão do pedido
 * de adicionar "carregar mais" ao histórico de commits, que antes só trazia
 * os primeiros 50 sem forma de avançar.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { HistoryView } from "../history-view";
import * as api from "../api";

function commit(sha: string) {
  return {
    sha,
    sha_short: sha.slice(0, 7),
    author: "Test <test@example.com>",
    date: "2026-01-01T00:00:00+00:00",
    message: `commit ${sha}`,
    refs: [],
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("HistoryView — paginação", () => {
  it("carrega a primeira página com offset 0 e mostra o botão quando has_more", async () => {
    const spy = vi.spyOn(api, "fetchGitLog").mockResolvedValue({
      branch: "main",
      commits: [commit("a1"), commit("a2")],
      has_more: true,
    });

    render(<HistoryView workspaceId="ws1" onChanged={() => {}} />);

    await waitFor(() => expect(spy).toHaveBeenCalledWith("ws1", 0));
    expect(await screen.findByText("commit a1")).toBeInTheDocument();
    expect(screen.getByText("Load 50 more")).toBeInTheDocument();
  });

  it("clicar em 'carregar mais' busca com offset = nº de commits já carregados e concatena", async () => {
    const spy = vi
      .spyOn(api, "fetchGitLog")
      .mockResolvedValueOnce({
        branch: "main",
        commits: [commit("a1"), commit("a2")],
        has_more: true,
      })
      .mockResolvedValueOnce({
        branch: "main",
        commits: [commit("a3")],
        has_more: false,
      });

    render(<HistoryView workspaceId="ws1" onChanged={() => {}} />);
    await screen.findByText("commit a1");

    fireEvent.click(screen.getByText("Load 50 more"));

    await waitFor(() => expect(spy).toHaveBeenCalledWith("ws1", 2));
    expect(await screen.findByText("commit a3")).toBeInTheDocument();
    // Todos os commits anteriores continuam na lista (concatenado, não substituído).
    expect(screen.getByText("commit a1")).toBeInTheDocument();
    expect(screen.getByText("commit a2")).toBeInTheDocument();
    // has_more=false na 2ª página — botão some.
    expect(screen.queryByText("Load 50 more")).not.toBeInTheDocument();
  });

  it("sem has_more, não mostra o botão de carregar mais", async () => {
    vi.spyOn(api, "fetchGitLog").mockResolvedValue({
      branch: "main",
      commits: [commit("a1")],
      has_more: false,
    });

    render(<HistoryView workspaceId="ws1" onChanged={() => {}} />);

    await screen.findByText("commit a1");
    expect(screen.queryByText("Load 50 more")).not.toBeInTheDocument();
  });
});
