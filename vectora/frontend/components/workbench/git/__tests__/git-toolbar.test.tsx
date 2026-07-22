// @vitest-environment jsdom
/**
 * Testes do GitToolbar — branch atual, botão de sync adaptativo (fetch/pull/
 * push) e disparo do PR. O menu dropdown de branches (Radix) não é aberto
 * aqui — cobrimos apenas o trigger e as ações fora do menu.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GitToolbar } from "../git-toolbar";
import * as api from "../api";
import type { GitBranches, GitStatus } from "../api";

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get: (_target, prop) => (args?: Record<string, unknown>) =>
        args ? `${String(prop)}(${JSON.stringify(args)})` : String(prop),
    },
  ),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderToolbar(props: {
  status: GitStatus | null;
  branches: GitBranches | null;
  onCompare?: () => void;
  onOpenStash?: () => void;
  onOpenWorktrees?: () => void;
  onOpenPR?: (head: string) => void;
  onChanged?: () => void;
}) {
  return render(
    <TooltipProvider>
      <GitToolbar
        workspaceId="ws1"
        status={props.status}
        branches={props.branches}
        onCompare={props.onCompare ?? (() => {})}
        onOpenStash={props.onOpenStash ?? (() => {})}
        onOpenWorktrees={props.onOpenWorktrees ?? (() => {})}
        onOpenPR={props.onOpenPR ?? (() => {})}
        onChanged={props.onChanged ?? (() => {})}
      />
    </TooltipProvider>,
  );
}

describe("GitToolbar", () => {
  it("mostra o branch atual do status, com fallback para '—' quando não há status nem branches", () => {
    renderToolbar({ status: null, branches: null });
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("usa branches.current quando status é null", () => {
    renderToolbar({
      status: null,
      branches: { current: "develop", branches: ["develop"], remotes: [] },
    });
    expect(screen.getByText("develop")).toBeInTheDocument();
  });

  it("quando behind > 0, o botão de sync mostra pull e a ação é pull", async () => {
    const spy = vi.spyOn(api, "apiSync").mockResolvedValue({
      status: "ok",
      message: "",
    });
    const onChanged = vi.fn();
    renderToolbar({
      status: {
        is_git_repo: true,
        branch: "main",
        clean: true,
        ahead: 0,
        behind: 3,
      },
      branches: null,
      onChanged,
    });

    fireEvent.click(screen.getByLabelText(/workbench_git_sync_pull/));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("ws1", "pull"));
    expect(onChanged).toHaveBeenCalled();
  });

  it("quando ahead > 0 (e behind = 0), o botão de sync mostra push e a ação é push", async () => {
    const spy = vi.spyOn(api, "apiSync").mockResolvedValue({
      status: "ok",
      message: "",
    });
    renderToolbar({
      status: {
        is_git_repo: true,
        branch: "main",
        clean: true,
        ahead: 2,
        behind: 0,
      },
      branches: null,
    });

    fireEvent.click(screen.getByLabelText(/workbench_git_sync_push/));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("ws1", "push"));
  });

  it("sem ahead/behind, a ação de sync é fetch", async () => {
    const spy = vi.spyOn(api, "apiSync").mockResolvedValue({
      status: "ok",
      message: "",
    });
    renderToolbar({
      status: {
        is_git_repo: true,
        branch: "main",
        clean: true,
        ahead: 0,
        behind: 0,
      },
      branches: null,
    });

    fireEvent.click(screen.getByLabelText("workbench_git_sync_fetch"));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("ws1", "fetch"));
  });

  it("clicar no botão de PR chama onOpenPR com o branch atual", () => {
    const onOpenPR = vi.fn();
    renderToolbar({
      status: {
        is_git_repo: true,
        branch: "main",
        clean: true,
        ahead: 0,
        behind: 0,
      },
      branches: null,
      onOpenPR,
    });

    fireEvent.click(screen.getByLabelText("tooltip_git_pr"));
    expect(onOpenPR).toHaveBeenCalledWith("main");
  });
});
