/**
 * buildThemeTokens e applyThemeTokens — contrato dos tokens de tema.
 *
 * buildThemeTokens é pura (sem DOM), então roda em ambiente node.
 * applyThemeTokens precisa de document — roda em jsdom.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildThemeTokens, type BaseThemeColors } from "../presets";

// Paleta mínima válida para os testes
const DARK_BASE: BaseThemeColors = {
  background: "#1f1f1f",
  foreground: "#d4d4d4",
  card: "#1a1a1a",
  border: "#2a2a2a",
  primary: "#d4d4d4",
  accent: "#2a2a2a",
  muted: "#262626",
};

const LIGHT_BASE: BaseThemeColors = {
  background: "#ffffff",
  foreground: "#2b2b2b",
  card: "#f6f6f6",
  border: "#d8d8d8",
  primary: "#2b2b2b",
  accent: "#eeeeee",
  muted: "#f0f0f0",
};

// ── buildThemeTokens ─────────────────────────────────────────────────────────

describe("buildThemeTokens — tokens obrigatórios", () => {
  it("produz --background", () => {
    const t = buildThemeTokens(DARK_BASE);
    expect(t["--background"]).toBe(DARK_BASE.background);
  });

  it("produz --sidebar derivado de background", () => {
    const t = buildThemeTokens(DARK_BASE);
    expect(t["--sidebar"]).toBeDefined();
  });

  it("--sidebar usa color-mix para derivar do background", () => {
    const t = buildThemeTokens(DARK_BASE);
    expect(t["--sidebar"]).toContain("color-mix");
    expect(t["--sidebar"]).toContain(DARK_BASE.background);
  });

  it("--sidebar é diferente de --background (não é cópia direta)", () => {
    const t = buildThemeTokens(DARK_BASE);
    expect(t["--sidebar"]).not.toBe(DARK_BASE.background);
  });

  it("--sidebar em tema claro usa o background claro como base", () => {
    const t = buildThemeTokens(LIGHT_BASE);
    expect(t["--sidebar"]).toContain(LIGHT_BASE.background);
  });

  it("--sidebar muda se o background mudar", () => {
    const t1 = buildThemeTokens(DARK_BASE);
    const t2 = buildThemeTokens({ ...DARK_BASE, background: "#0d0d0d" });
    expect(t1["--sidebar"]).not.toBe(t2["--sidebar"]);
  });

  it("produz todos os tokens de cor padrão", () => {
    const t = buildThemeTokens(DARK_BASE);
    const required = [
      "--background",
      "--foreground",
      "--card",
      "--muted",
      "--border",
      "--primary",
      "--ring",
      "--sidebar",
    ];
    for (const k of required) {
      expect(t[k], `faltando ${k}`).toBeDefined();
    }
  });
});

// ── applyThemeTokens — gerencia --sidebar no DOM ─────────────────────────────

describe("applyThemeTokens — --sidebar no DOM", () => {
  let applyThemeTokens: (tokens: Record<string, string> | null) => void;

  // O módulo usa `document` portanto precisa de jsdom — importamos
  // dinamicamente para não poluir o ambiente node dos testes acima.
  beforeEach(async () => {
    vi.resetModules();
    ({ applyThemeTokens } = await import("../presets"));
  });

  it("aplica --sidebar em document.documentElement", () => {
    if (typeof document === "undefined") return; // pula em node puro
    const tokens = buildThemeTokens(DARK_BASE);
    applyThemeTokens(tokens);
    const val = document.documentElement.style.getPropertyValue("--sidebar");
    expect(val.trim()).toBeTruthy();
  });

  it("null remove --sidebar de document.documentElement", () => {
    if (typeof document === "undefined") return;
    const tokens = buildThemeTokens(DARK_BASE);
    applyThemeTokens(tokens);
    applyThemeTokens(null);
    const val = document.documentElement.style.getPropertyValue("--sidebar");
    expect(val).toBe("");
  });
});
