// @vitest-environment jsdom
/**
 * IdeModeSwitch — segmented control Assistente|IDE no header.
 * Visível apenas quando show=true (passado pelo Header).
 * O Header passa show={!chatMode} dentro de uma sessão ativa.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

const mockSetUiMode = vi.fn();
const mockSettings = {
  uiMode: "assistant",
  setUiMode: mockSetUiMode,
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
  mockSettings.uiMode = "assistant";
});

beforeEach(() => {
  mockSettings.uiMode = "assistant";
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
  it("modo Assistente tem aria-pressed=true quando uiMode='assistant'", () => {
    mockSettings.uiMode = "assistant";
    render(<IdeModeSwitch show />);
    const [assistente, ide] = screen.getAllByRole("button");
    expect(assistente).toHaveAttribute("aria-pressed", "true");
    expect(ide).toHaveAttribute("aria-pressed", "false");
  });

  it("modo IDE tem aria-pressed=true quando uiMode='ide'", () => {
    mockSettings.uiMode = "ide";
    render(<IdeModeSwitch show />);
    const [assistente, ide] = screen.getAllByRole("button");
    expect(assistente).toHaveAttribute("aria-pressed", "false");
    expect(ide).toHaveAttribute("aria-pressed", "true");
  });
});

describe("IdeModeSwitch — interações", () => {
  it("clicar IDE chama setUiMode('ide') quando uiMode='assistant'", () => {
    mockSettings.uiMode = "assistant";
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(mockSetUiMode).toHaveBeenCalledOnce();
    expect(mockSetUiMode).toHaveBeenCalledWith("ide");
  });

  it("clicar Assistente chama setUiMode('assistant') quando uiMode='ide'", () => {
    mockSettings.uiMode = "ide";
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(mockSetUiMode).toHaveBeenCalledOnce();
    expect(mockSetUiMode).toHaveBeenCalledWith("assistant");
  });

  it("clicar no modo já ativo (IDE quando uiMode='ide') não chama setUiMode", () => {
    mockSettings.uiMode = "ide";
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(mockSetUiMode).not.toHaveBeenCalled();
  });

  it("clicar no modo já ativo (Assistente quando uiMode='assistant') não chama setUiMode", () => {
    mockSettings.uiMode = "assistant";
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(mockSetUiMode).not.toHaveBeenCalled();
  });

  it("uiMode='kanban': nenhum dos dois botões fica marcado como ativo", () => {
    // O board Kanban é um terceiro modo — o seletor binário atual não o
    // representa, então nem Assistente nem IDE devem aparecer pressionados
    // (o seletor de 3 posições entra junto com o board).
    mockSettings.uiMode = "kanban";
    render(<IdeModeSwitch show />);
    const [assistente, ide] = screen.getAllByRole("button");
    expect(assistente).toHaveAttribute("aria-pressed", "false");
    expect(ide).toHaveAttribute("aria-pressed", "false");
  });

  it("uiMode='kanban': clicar em IDE troca pra 'ide', nunca pra booleano", () => {
    // Erro proposital coberto: um `setUiMode(true)` legado passaria no teste
    // antigo de booleano — aqui o argumento errado falha explicitamente.
    mockSettings.uiMode = "kanban";
    render(<IdeModeSwitch show />);
    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(mockSetUiMode).toHaveBeenCalledWith("ide");
    expect(mockSetUiMode).not.toHaveBeenCalledWith(true);
  });
});
