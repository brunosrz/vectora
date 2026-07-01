// @vitest-environment jsdom
/**
 * IdeModeSwitch — segmented control Assistente|IDE no header.
 * Visível apenas em Dev mode (chatMode=false); ativo/inativo por ideMode.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

const mockSetIdeMode = vi.fn();
const mockSettings = {
  chatMode: false,
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
  mockSettings.chatMode = false;
  mockSettings.ideMode = false;
});

beforeEach(() => {
  mockSettings.chatMode = false;
  mockSettings.ideMode = false;
});

describe("IdeModeSwitch", () => {
  it("renderiza dois botões quando chatMode=false", () => {
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
  });

  it("não renderiza nada quando chatMode=true", () => {
    mockSettings.chatMode = true;
    const { container } = render(<IdeModeSwitch />);
    expect(container).toBeEmptyDOMElement();
  });

  it("modo Assistente tem aria-pressed=true quando ideMode=false", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
    expect(buttons[1]).toHaveAttribute("aria-pressed", "false");
  });

  it("modo IDE tem aria-pressed=true quando ideMode=true", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "false");
    expect(buttons[1]).toHaveAttribute("aria-pressed", "true");
  });

  it("clicar no botão IDE chama setIdeMode(true) quando ideMode=false", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]);
    expect(mockSetIdeMode).toHaveBeenCalledOnce();
    expect(mockSetIdeMode).toHaveBeenCalledWith(true);
  });

  it("clicar no botão Assistente chama setIdeMode(false) quando ideMode=true", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(mockSetIdeMode).toHaveBeenCalledOnce();
    expect(mockSetIdeMode).toHaveBeenCalledWith(false);
  });

  it("clicar no modo já ativo (IDE quando ideMode=true) não chama setIdeMode", () => {
    mockSettings.ideMode = true;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]);
    expect(mockSetIdeMode).not.toHaveBeenCalled();
  });

  it("clicar no modo já ativo (Assistente quando ideMode=false) não chama setIdeMode", () => {
    mockSettings.ideMode = false;
    render(<IdeModeSwitch />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(mockSetIdeMode).not.toHaveBeenCalled();
  });
});
