// @vitest-environment jsdom
/**
 * IdeModeSwitch — segmented control Assistente|IDE no header.
 * Visível apenas quando show=true (passado pelo Header).
 * O Header passa show={!chatMode} dentro de uma sessão ativa.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

const mockSetIdeMode = vi.fn();
const mockSettings = {
  ideMode: false,
  setIdeMode: mockSetIdeMode,
};

vi.mock("@/lib/stores/settings-store", () => ({
  useSettingsStore: (sel: (s: typeof mockSettings) => unknown) =>
    sel(mockSettings),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy({}, { get: (_t, prop) => () => String(prop) }),
}));

import { IdeModeSwitch } from "../ide-mode-switcher";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockSettings.ideMode = false;
});

beforeEach(() => {
  mockSettings.ideMode = false;
});

describe("IdeModeSwitch — visibilidade", () => {
  it("não renderiza nada quando show=false (default)", () => {
    const { container } = render(<IdeModeSwitch />);
    expect(container).toBeEmptyDOMElement();
  });

  it("não renderiza nada quando show=false explícito", () => {
    const { container } = render(<IdeModeSwitch show={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renderiza dois botões quando show=true", () => {
    render(<IdeModeSwitch show />);
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("tem role=group com aria-label quando visível", () => {
    render(<IdeModeSwitch show />);
    expect(
      screen.getByRole("group", { name: "ide_mode_switcher_label" }),
    ).toBeInTheDocument();
  });
});

describe("IdeModeSwitch — estado ativo", () => {
  it("modo Assistente tem aria-pressed=true quando ideMode=false", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch show />);
    const [assistente, ide] = screen.getAllByRole("button");
    expect(assistente).toHaveAttribute("aria-pressed", "true");
    expect(ide).toHaveAttribute("aria-pressed", "false");
  });

  it("modo IDE tem aria-pressed=true quando ideMode=true", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch show />);
    const [assistente, ide] = screen.getAllByRole("button");
    expect(assistente).toHaveAttribute("aria-pressed", "false");
    expect(ide).toHaveAttribute("aria-pressed", "true");
  });
});

describe("IdeModeSwitch — interações", () => {
  it("clicar IDE chama setIdeMode(true) quando ideMode=false", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(mockSetIdeMode).toHaveBeenCalledOnce();
    expect(mockSetIdeMode).toHaveBeenCalledWith(true);
  });

  it("clicar Assistente chama setIdeMode(false) quando ideMode=true", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(mockSetIdeMode).toHaveBeenCalledOnce();
    expect(mockSetIdeMode).toHaveBeenCalledWith(false);
  });

  it("clicar no modo já ativo (IDE quando ideMode=true) não chama setIdeMode", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(mockSetIdeMode).not.toHaveBeenCalled();
  });

  it("clicar no modo já ativo (Assistente quando ideMode=false) não chama setIdeMode", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(mockSetIdeMode).not.toHaveBeenCalled();
  });
});
