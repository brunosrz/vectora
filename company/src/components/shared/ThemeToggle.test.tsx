// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";

import ThemeToggle from "./ThemeToggle";

vi.mock("#/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

const {
  mockApplyTheme,
  mockGetStoredTheme,
  mockResolveTheme,
  mockSetTheme,
  mockWatchSystemTheme,
} = vi.hoisted(() => ({
  mockApplyTheme: vi.fn(),
  mockGetStoredTheme: vi.fn(),
  mockResolveTheme: vi.fn(),
  mockSetTheme: vi.fn(),
  mockWatchSystemTheme: vi.fn(() => vi.fn()),
}));

vi.mock("#/lib/theme", () => ({
  applyTheme: mockApplyTheme,
  getStoredTheme: mockGetStoredTheme,
  resolveTheme: mockResolveTheme,
  setTheme: mockSetTheme,
  watchSystemTheme: mockWatchSystemTheme,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockWatchSystemTheme.mockReturnValue(vi.fn());
});

describe("ThemeToggle", () => {
  it("aplica o tema salvo e mostra o ícone de lua quando o modo efetivo é claro", async () => {
    mockGetStoredTheme.mockReturnValue("light");
    mockResolveTheme.mockReturnValue("light");

    await act(async () => {
      render(<ThemeToggle />);
    });

    expect(mockApplyTheme).toHaveBeenCalledWith("light");
    expect(screen.getByRole("button")).toHaveAttribute(
      "aria-label",
      "theme_dark",
    );
  });

  it("mostra o ícone de sol quando o modo efetivo é escuro", async () => {
    mockGetStoredTheme.mockReturnValue("dark");
    mockResolveTheme.mockReturnValue("dark");

    await act(async () => {
      render(<ThemeToggle />);
    });

    expect(screen.getByRole("button")).toHaveAttribute(
      "aria-label",
      "theme_light",
    );
  });

  it("alterna de claro para escuro ao clicar", async () => {
    mockGetStoredTheme.mockReturnValue("light");
    mockResolveTheme.mockReturnValue("light");

    await act(async () => {
      render(<ThemeToggle />);
    });

    fireEvent.click(screen.getByRole("button"));

    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("remove o listener do SO ao desmontar (edge — evita leak)", async () => {
    const unsubscribe = vi.fn();
    mockWatchSystemTheme.mockReturnValue(unsubscribe);
    mockGetStoredTheme.mockReturnValue("system");
    mockResolveTheme.mockReturnValue("dark");

    let unmount!: () => void;
    await act(async () => {
      ({ unmount } = render(<ThemeToggle />));
    });
    unmount();

    expect(unsubscribe).toHaveBeenCalled();
  });
});
