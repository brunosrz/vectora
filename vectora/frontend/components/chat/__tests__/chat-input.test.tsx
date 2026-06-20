// @vitest-environment jsdom
/**
 * Tests para ChatInput: textarea controlado, botão de enviar (habilita só com
 * texto + usuário online) e callback onSend. Cobre o layout pós-swap
 * (enviar dentro da linha do input).
 */

import { describe, expect, it, afterEach, beforeEach, vi } from "vitest";
import {
  render as rtlRender,
  screen,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatInput } from "../chat-input";
import { m } from "@/lib/paraglide/messages";

// Estado mockável para o settings store — cobre ChatInput e ChatParamsMenu.
const mockSettings = {
  chatMode: false,
  setChatMode: vi.fn(),
  verbosity: "normal" as const,
  reasoningEffort: "medium" as const,
  fastMode: false,
  historyLimit: 50,
  showToolCalls: false,
  setVerbosity: vi.fn(),
  setReasoningEffort: vi.fn(),
  setFastMode: vi.fn(),
  setHistoryLimit: vi.fn(),
  setShowToolCalls: vi.fn(),
};

vi.mock("@/lib/stores/settings-store", () => ({
  useSettingsStore: (selector?: (s: typeof mockSettings) => unknown) =>
    selector ? selector(mockSettings) : mockSettings,
}));

const mockWsState = {
  workspaces: [],
  active_id: null,
  status: "idle" as const,
  error: null,
  getActive: () => null,
  setActive: vi.fn(),
  addWorkspace: vi.fn(),
  removeWorkspace: vi.fn(),
  updateWorkspace: vi.fn(),
  hydrate: vi.fn(),
  trust: vi.fn(),
};

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (selector: (s: typeof mockWsState) => unknown) =>
    selector(mockWsState),
}));

afterEach(() => {
  cleanup();
  mockSettings.chatMode = false;
  mockSettings.setChatMode.mockReset();
});

// ChatInput usa Tooltip — precisa do provider no entorno.
function render(ui: React.ReactElement) {
  return rtlRender(<TooltipProvider>{ui}</TooltipProvider>);
}

type Props = Parameters<typeof ChatInput>[0];

function baseProps(over: Partial<Props> = {}): Props {
  return {
    input: "",
    onInputChange: vi.fn(),
    onSend: vi.fn(),
    onKeyDown: vi.fn(),
    isLoading: false,
    isStopping: false,
    onStop: vi.fn(),
    userId: "u1",
    attachedFiles: [],
    uploadError: null,
    inputError: null,
    isDragging: false,
    onDragOver: vi.fn(),
    onDragLeave: vi.fn(),
    onDrop: vi.fn(),
    onPaste: vi.fn(),
    onRemoveFile: vi.fn(),
    onFileButtonClick: vi.fn(),
    fileInputRef: { current: null },
    onFileSelect: vi.fn(),
    ...over,
  } as Props;
}

function sendButton(): HTMLButtonElement {
  return screen.getByRole("button", {
    name: m.tooltip_chat_send(),
  }) as HTMLButtonElement;
}

describe("ChatInput", () => {
  it("renderiza o textarea de mensagem", () => {
    render(<ChatInput {...baseProps()} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("desabilita o enviar quando o input está vazio", () => {
    render(<ChatInput {...baseProps({ input: "" })} />);
    expect(sendButton()).toBeDisabled();
  });

  it("habilita o enviar quando há texto", () => {
    render(<ChatInput {...baseProps({ input: "olá" })} />);
    expect(sendButton()).not.toBeDisabled();
  });

  it("clicar em enviar chama onSend", () => {
    const onSend = vi.fn();
    render(<ChatInput {...baseProps({ input: "oi", onSend })} />);
    fireEvent.click(sendButton());
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("digitar no textarea chama onInputChange", () => {
    const onInputChange = vi.fn();
    render(<ChatInput {...baseProps({ onInputChange })} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "novo" },
    });
    expect(onInputChange).toHaveBeenCalledWith("novo");
  });

  // Sprint 4 — Modo Chat
  it("botão de toggle de modo chat está sempre visível", () => {
    render(<ChatInput {...baseProps()} />);
    const toggle = document.querySelector("[data-chatmode]");
    expect(toggle).toBeTruthy();
  });

  it("em chatMode=false o botão tem aria-label de ativar modo chat", () => {
    mockSettings.chatMode = false;
    render(<ChatInput {...baseProps()} />);
    const toggle = document.querySelector("[data-chatmode='off']");
    expect(toggle).toBeTruthy();
    expect(toggle?.getAttribute("aria-label")).toBe(m.chat_mode_enable());
  });

  it("em chatMode=true o botão tem aria-label de desativar modo chat", () => {
    mockSettings.chatMode = true;
    render(<ChatInput {...baseProps()} />);
    const toggle = document.querySelector("[data-chatmode='on']");
    expect(toggle).toBeTruthy();
    expect(toggle?.getAttribute("aria-label")).toBe(m.chat_mode_disable());
  });

  it("clicar no toggle chama setChatMode com valor invertido", () => {
    mockSettings.chatMode = false;
    render(<ChatInput {...baseProps()} />);
    const toggle = document.querySelector(
      "[data-chatmode]",
    ) as HTMLButtonElement;
    fireEvent.click(toggle);
    expect(mockSettings.setChatMode).toHaveBeenCalledWith(true);
  });

  it("em chatMode=true WorkspaceSelector não está no DOM", () => {
    mockSettings.chatMode = true;
    render(<ChatInput {...baseProps()} />);
    // WorkspaceSelector renderiza um button com role combobox ou com
    // aria-label relacionado a workspace — em chatMode deve estar ausente.
    // Verificamos indiretamente: sem nenhum elemento data-testid="workspace-selector"
    // e que o toggle data-chatmode='on' existe
    expect(document.querySelector("[data-chatmode='on']")).toBeTruthy();
    // O único seletor de workspace visível seria o WorkspaceSelector —
    // em chatMode deve estar ausente do DOM
    expect(
      document.querySelector("[data-testid='workspace-selector']"),
    ).toBeNull();
  });
});
