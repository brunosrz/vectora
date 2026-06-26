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

  // Sprint 4 — Modo Chat (toggle removido da AppBar; sidebar-mode-toggle é o ponto canônico)
  it("toggle data-chatmode não existe na AppBar (removido — use a sidebar)", () => {
    render(<ChatInput {...baseProps()} />);
    expect(document.querySelector("[data-chatmode]")).toBeNull();
  });

  it("em chatMode=true WorkspaceSelector não está no DOM", () => {
    mockSettings.chatMode = true;
    render(<ChatInput {...baseProps()} />);
    expect(
      document.querySelector("[data-testid='workspace-selector']"),
    ).toBeNull();
  });

  it("em code mode (chatMode=false) WorkspaceSelector não está na AppBar", () => {
    // O workspace é imutável após iniciar a conversa — escolhido só no modal.
    mockSettings.chatMode = false;
    render(<ChatInput {...baseProps()} />);
    expect(
      document.querySelector("[data-testid='workspace-selector']"),
    ).toBeNull();
  });

  // ── erros / fila / botão VS Code (render direto da ChatInput) ────────────────

  it("exibe uploadError quando presente", () => {
    render(
      <ChatInput {...baseProps({ uploadError: "Arquivo grande demais" })} />,
    );
    expect(screen.getByText("Arquivo grande demais")).toBeTruthy();
  });

  it("não exibe bloco de uploadError quando null", () => {
    render(<ChatInput {...baseProps({ uploadError: null })} />);
    expect(screen.queryByText(/demais/)).toBeNull();
  });

  it("exibe voiceError quando presente", () => {
    render(
      <ChatInput {...baseProps({ voiceError: "Microfone indisponível" })} />,
    );
    expect(screen.getByText("Microfone indisponível")).toBeTruthy();
  });

  it("renderiza mensagens enfileiradas", () => {
    render(
      <ChatInput
        {...baseProps({
          queuedMessages: [
            { id: "q1", content: "primeira na fila" },
            { id: "q2", content: "segunda na fila" },
          ],
        })}
      />,
    );
    expect(screen.getByText("primeira na fila")).toBeTruthy();
    expect(screen.getByText("segunda na fila")).toBeTruthy();
  });

  it("sem mensagens enfileiradas não renderiza a fila", () => {
    render(<ChatInput {...baseProps({ queuedMessages: [] })} />);
    expect(screen.queryByText(/na fila/)).toBeNull();
  });

  it("botão VS Code aparece em code mode com workspace ativo", () => {
    mockSettings.chatMode = false;
    mockWsState.getActive = () => ({ id: "ws1" }) as never;
    try {
      render(<ChatInput {...baseProps()} />);
      expect(screen.queryByLabelText(m.workbench_open_vscode())).toBeTruthy();
    } finally {
      mockWsState.getActive = () => null;
    }
  });

  it("botão VS Code NÃO aparece em chat mode mesmo com workspace", () => {
    mockSettings.chatMode = true;
    mockWsState.getActive = () => ({ id: "ws1" }) as never;
    try {
      render(<ChatInput {...baseProps()} />);
      expect(screen.queryByLabelText(m.workbench_open_vscode())).toBeNull();
    } finally {
      mockWsState.getActive = () => null;
      mockSettings.chatMode = false;
    }
  });

  it("botão VS Code NÃO aparece sem workspace ativo", () => {
    mockSettings.chatMode = false;
    render(<ChatInput {...baseProps()} />);
    expect(screen.queryByLabelText(m.workbench_open_vscode())).toBeNull();
  });

  it("enviar fica desabilitado sem userId", () => {
    render(<ChatInput {...baseProps({ input: "oi", userId: null })} />);
    expect(sendButton().disabled).toBe(true);
  });
});
