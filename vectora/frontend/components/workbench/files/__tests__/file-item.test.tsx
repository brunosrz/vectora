// @vitest-environment jsdom
/**
 * FileItem — comportamento de abertura de arquivo em modo IDE vs Assistente.
 *
 * Em uiMode='ide': clique chama openDocked.
 * Em uiMode='assistant': clique chama openWindow (open).
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

const mockOpenWindow = vi.fn();
const mockOpenDocked = vi.fn();
const mockTogglePinned = vi.fn();
const mockSettings = { uiMode: "assistant" };

vi.mock("@/lib/stores/windows-store", () => ({
  useWindowsStore: (
    sel: (s: {
      open: typeof mockOpenWindow;
      openDocked: typeof mockOpenDocked;
    }) => unknown,
  ) => sel({ open: mockOpenWindow, openDocked: mockOpenDocked }),
}));

vi.mock("@/lib/stores/settings-store", () => ({
  useSettingsStore: (sel: (s: typeof mockSettings) => unknown) =>
    sel(mockSettings),
}));

vi.mock("@/lib/stores/workbench-store", () => ({
  useWorkbenchStore: (
    sel: (s: {
      isPinned: () => boolean;
      togglePinned: typeof mockTogglePinned;
      getFiles: () => { openPath: null };
    }) => unknown,
  ) =>
    sel({
      isPinned: () => false,
      togglePinned: mockTogglePinned,
      getFiles: () => ({ openPath: null }),
    }),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy({}, { get: (_t, prop) => () => String(prop) }),
}));

vi.mock("@/components/icons/file-icon", () => ({
  FileIcon: () => null,
}));

vi.mock("../git-badge", () => ({
  GitBadge: () => null,
}));

vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.resolve(new Response("{}", { status: 200 }))),
);

import { FileItem } from "../file-item";

const ENTRY = {
  name: "main.ts",
  path: "src/main.ts",
  kind: "file" as const,
  size: 100,
};

function renderItem(uiMode: "assistant" | "ide" | "kanban" = "assistant") {
  mockSettings.uiMode = uiMode;
  render(
    <FileItem
      threadId="t1"
      workspaceId="ws1"
      entry={ENTRY}
      depth={0}
      onOpenFile={vi.fn()}
      onDelete={vi.fn()}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockSettings.uiMode = "assistant";
});

beforeEach(() => {
  mockSettings.uiMode = "assistant";
});

describe("FileItem — abertura em modo IDE vs Assistente", () => {
  it("uiMode='assistant': clicar no arquivo chama openWindow", () => {
    renderItem("assistant");
    fireEvent.click(screen.getByText("main.ts"));
    expect(mockOpenWindow).toHaveBeenCalledWith("ws1", "src/main.ts");
    expect(mockOpenDocked).not.toHaveBeenCalled();
  });

  it("uiMode='ide': clicar no arquivo chama openDocked", () => {
    renderItem("ide");
    fireEvent.click(screen.getByText("main.ts"));
    expect(mockOpenDocked).toHaveBeenCalledWith("ws1", "src/main.ts");
    expect(mockOpenWindow).not.toHaveBeenCalled();
  });

  it("uiMode='assistant': openWindow recebe o workspaceId e path corretos", () => {
    renderItem("assistant");
    fireEvent.click(screen.getByText("main.ts"));
    expect(mockOpenWindow).toHaveBeenCalledOnce();
    const [wsId, path] = mockOpenWindow.mock.calls[0];
    expect(wsId).toBe("ws1");
    expect(path).toBe("src/main.ts");
  });

  it("uiMode='ide': openDocked recebe o workspaceId e path corretos", () => {
    renderItem("ide");
    fireEvent.click(screen.getByText("main.ts"));
    expect(mockOpenDocked).toHaveBeenCalledOnce();
    const [wsId, path] = mockOpenDocked.mock.calls[0];
    expect(wsId).toBe("ws1");
    expect(path).toBe("src/main.ts");
  });

  it("renderiza o nome do arquivo no botão", () => {
    renderItem("assistant");
    expect(screen.getByText("main.ts")).toBeInTheDocument();
  });

  it("renderiza com role=treeitem", () => {
    renderItem("assistant");
    expect(document.querySelector("[role='treeitem']")).not.toBeNull();
  });
});
