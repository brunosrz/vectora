import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  THEME_STORAGE_KEY,
  getStoredTheme,
  resolveTheme,
  applyTheme,
  setTheme,
  watchSystemTheme,
} from "./theme";

function mockMatchMedia(matches: boolean) {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mql = {
    matches,
    media: "(prefers-color-scheme: dark)",
    addEventListener: vi.fn(
      (_event: string, cb: (e: MediaQueryListEvent) => void) =>
        listeners.add(cb),
    ),
    removeEventListener: vi.fn(
      (_event: string, cb: (e: MediaQueryListEvent) => void) =>
        listeners.delete(cb),
    ),
  } as unknown as MediaQueryList;
  window.matchMedia = vi.fn().mockReturnValue(mql);
  return {
    fire: () => {
      for (const cb of listeners) cb({} as MediaQueryListEvent);
    },
  };
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark", "light");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getStoredTheme", () => {
  it("retorna 'light' quando salvo", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    expect(getStoredTheme()).toBe("light");
  });

  it("retorna 'dark' quando salvo", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    expect(getStoredTheme()).toBe("dark");
  });

  it("retorna 'system' quando nada foi salvo (edge)", () => {
    expect(getStoredTheme()).toBe("system");
  });

  it("retorna 'system' para valor corrompido/inesperado no storage (edge)", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "purple");
    expect(getStoredTheme()).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("retorna o próprio tema quando não é 'system'", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
  });

  it("resolve 'system' para 'dark' quando o SO prefere dark", () => {
    mockMatchMedia(true);
    expect(resolveTheme("system")).toBe("dark");
  });

  it("resolve 'system' para 'light' quando o SO prefere light (edge)", () => {
    mockMatchMedia(false);
    expect(resolveTheme("system")).toBe("light");
  });
});

describe("applyTheme", () => {
  it("aplica a classe 'dark' e remove 'light' para tema escuro", () => {
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);
  });

  it("aplica a classe 'light' e remove 'dark' para tema claro", () => {
    applyTheme("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});

describe("setTheme", () => {
  it("persiste no localStorage e aplica a classe", () => {
    setTheme("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});

describe("watchSystemTheme", () => {
  it("reaplica o tema quando o SO muda E a preferência salva é 'system'", () => {
    const mq = mockMatchMedia(true);
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    watchSystemTheme();

    mq.fire();

    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("ignora a mudança do SO quando a preferência salva não é 'system' (edge)", () => {
    const mq = mockMatchMedia(true);
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    watchSystemTheme();

    mq.fire();

    // Preferência explícita 'light' não deve ser sobrescrita pelo evento do SO.
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("retorna uma função de unsubscribe que remove o listener", () => {
    const mq = mockMatchMedia(true);
    const unsubscribe = watchSystemTheme();
    unsubscribe();

    mq.fire();

    // Sem listener ativo, nenhuma classe deveria ter sido tocada pelo evento.
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
