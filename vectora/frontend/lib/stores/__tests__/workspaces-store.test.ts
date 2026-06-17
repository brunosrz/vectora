/**
 * Tests para a lógica pura do `workspaces-store`: getActive (com fallback),
 * getById, setWorkspaces e invalidate. As ações de rede não são exercidas.
 */

import { describe, expect, it, beforeEach } from "vitest";
import { useWorkspacesStore, type WorkspaceInfo } from "../workspaces-store";

function ws(id: string, name = id): WorkspaceInfo {
  return { id, name, cwd: `/home/${id}` } as unknown as WorkspaceInfo;
}

beforeEach(() => {
  useWorkspacesStore.setState({
    workspaces: [],
    active_id: null,
    fetchedAt: null,
  });
});

describe("workspaces-store — leitura pura", () => {
  it("getActive devolve null quando não há workspaces", () => {
    expect(useWorkspacesStore.getState().getActive()).toBeNull();
  });

  it("getActive cai no primeiro workspace quando active_id é nulo", () => {
    useWorkspacesStore.getState().setWorkspaces([ws("a"), ws("b")], null);
    expect(useWorkspacesStore.getState().getActive()?.id).toBe("a");
  });

  it("getActive devolve o workspace ativo quando active_id casa", () => {
    useWorkspacesStore.getState().setWorkspaces([ws("a"), ws("b")], "b");
    expect(useWorkspacesStore.getState().getActive()?.id).toBe("b");
  });

  it("getActive cai no primeiro quando active_id não existe na lista", () => {
    useWorkspacesStore.getState().setWorkspaces([ws("a"), ws("b")], "fantasma");
    expect(useWorkspacesStore.getState().getActive()?.id).toBe("a");
  });

  it("getById encontra por id ou devolve null", () => {
    useWorkspacesStore.getState().setWorkspaces([ws("a"), ws("b")], "a");
    expect(useWorkspacesStore.getState().getById("b")?.id).toBe("b");
    expect(useWorkspacesStore.getState().getById("z")).toBeNull();
  });

  it("setWorkspaces marca fetchedAt e invalidate o zera", () => {
    useWorkspacesStore.getState().setWorkspaces([ws("a")], "a");
    expect(useWorkspacesStore.getState().fetchedAt).toBeGreaterThan(0);
    useWorkspacesStore.getState().invalidate();
    expect(useWorkspacesStore.getState().fetchedAt).toBeNull();
  });
});
