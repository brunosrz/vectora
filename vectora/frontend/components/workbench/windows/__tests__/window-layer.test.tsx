// @vitest-environment jsdom
/**
 * WindowLayer — overlay de janelas flutuantes.
 * Retorna null em ideMode ou quando não há janelas visíveis.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

const mockSettings = { ideMode: false };
const mockWindowsState = {
  windows: [] as Array<{ id: string; minimized: boolean }>,
};

vi.mock("@/lib/stores/settings-store", () => ({
  useSettingsStore: (sel: (s: typeof mockSettings) => unknown) =>
    sel(mockSettings),
}));

vi.mock("@/lib/stores/windows-store", () => ({
  useWindowsStore: (
    sel: (s: { windows: typeof mockWindowsState.windows }) => unknown,
  ) => sel(mockWindowsState),
}));

vi.mock("../file-window", () => ({
  FileWindow: ({ win }: { win: { id: string } }) => (
    <div data-testid="file-window" data-id={win.id} />
  ),
}));

import { WindowLayer } from "../window-layer";

afterEach(() => {
  cleanup();
  mockSettings.ideMode = false;
  mockWindowsState.windows = [];
});

describe("WindowLayer", () => {
  it("retorna null quando ideMode=true", () => {
    mockSettings.ideMode = true;
    mockWindowsState.windows = [{ id: "ws1", minimized: false }];
    const { container } = render(<WindowLayer />);
    expect(container).toBeEmptyDOMElement();
  });

  it("retorna null quando não há janelas", () => {
    mockSettings.ideMode = false;
    mockWindowsState.windows = [];
    const { container } = render(<WindowLayer />);
    expect(container).toBeEmptyDOMElement();
  });

  it("retorna null quando todas as janelas estão minimizadas", () => {
    mockSettings.ideMode = false;
    mockWindowsState.windows = [{ id: "ws1", minimized: true }];
    const { container } = render(<WindowLayer />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renderiza FileWindow para cada janela visível (não minimizada)", () => {
    mockSettings.ideMode = false;
    mockWindowsState.windows = [
      { id: "ws1", minimized: false },
      { id: "ws2", minimized: false },
      { id: "ws3", minimized: true },
    ];
    const { getAllByTestId } = render(<WindowLayer />);
    expect(getAllByTestId("file-window")).toHaveLength(2);
  });

  it("renderiza FileWindow com o id correto", () => {
    mockSettings.ideMode = false;
    mockWindowsState.windows = [{ id: "ws42", minimized: false }];
    const { getByTestId } = render(<WindowLayer />);
    expect(getByTestId("file-window")).toHaveAttribute("data-id", "ws42");
  });

  it("ideMode=true retorna null mesmo com janelas visíveis (edge: ambas condições)", () => {
    mockSettings.ideMode = true;
    mockWindowsState.windows = [
      { id: "ws1", minimized: false },
      { id: "ws2", minimized: false },
    ];
    const { container } = render(<WindowLayer />);
    expect(container).toBeEmptyDOMElement();
  });
});
