// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { ThemePicker } from "../theme-picker";
import { THEME_PRESETS, type BaseThemeColors } from "@/lib/theme/presets";

afterEach(() => {
  cleanup();
});

/** jsdom normaliza `style.background` de hex pra `rgb(r, g, b)` ao ler de
 * volta — compara pela forma computada, não pela string hex original. */
function hexToRgb(hex: string): string {
  const n = Number.parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

const customColors: BaseThemeColors = {
  background: "#111111",
  foreground: "#eeeeee",
  card: "#161616",
  border: "#222222",
  primary: "#00ff88",
  accent: "#ff8800",
  muted: "#333333",
  sidebar: "#0d0d0d",
  userBubble: "#004488",
};

describe("ThemePicker", () => {
  it("renderiza system + todos os presets + custom, um botão por opção", () => {
    render(
      <ThemePicker
        value="system"
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        systemLabel="Sistema"
        customLabel="Personalizado"
        customColors={customColors}
      />,
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(THEME_PRESETS.length + 2);
    expect(screen.getByText("Sistema")).toBeInTheDocument();
    expect(screen.getByText("Personalizado")).toBeInTheDocument();
    for (const preset of THEME_PRESETS) {
      expect(screen.getByText(preset.label)).toBeInTheDocument();
    }
  });

  it("clicar num preset chama onChange com o id do preset", () => {
    const onChange = vi.fn();
    render(
      <ThemePicker
        value="system"
        onChange={onChange}
        presets={THEME_PRESETS}
        systemLabel="Sistema"
        customLabel="Personalizado"
        customColors={customColors}
      />,
    );

    fireEvent.click(screen.getByText(THEME_PRESETS[0].label));

    expect(onChange).toHaveBeenCalledWith(THEME_PRESETS[0].id);
  });

  it("opção ativa fica marcada com aria-pressed e as demais não", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        systemLabel="Sistema"
        customLabel="Personalizado"
        customColors={customColors}
      />,
    );

    const activeButton = screen
      .getByText(THEME_PRESETS[0].label)
      .closest("button");
    expect(activeButton).toHaveAttribute("aria-pressed", "true");

    const systemButton = screen.getByText("Sistema").closest("button");
    expect(systemButton).toHaveAttribute("aria-pressed", "false");
  });

  it("swatch do preset usa as cores reais do preset, não valor fixo — erro/borda", () => {
    render(
      <ThemePicker
        value="system"
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        systemLabel="Sistema"
        customLabel="Personalizado"
        customColors={customColors}
      />,
    );

    const firstPreset = THEME_PRESETS[0];
    const button = screen.getByText(firstPreset.label).closest("button");
    const swatchSpans = button!.querySelectorAll<HTMLElement>("span[style]");
    expect(swatchSpans).toHaveLength(3);
    expect(swatchSpans[0].style.background).toBe(
      hexToRgb(firstPreset.colors.background),
    );
    expect(swatchSpans[1].style.background).toBe(
      hexToRgb(firstPreset.colors.primary),
    );
    expect(swatchSpans[2].style.background).toBe(
      hexToRgb(firstPreset.colors.accent),
    );
  });

  it("swatch do custom reflete customColors passado, não os presets — erro/borda", () => {
    render(
      <ThemePicker
        value="custom"
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        systemLabel="Sistema"
        customLabel="Personalizado"
        customColors={customColors}
      />,
    );

    const button = screen.getByText("Personalizado").closest("button");
    const swatchSpans = button!.querySelectorAll<HTMLElement>("span[style]");
    expect(swatchSpans[0].style.background).toBe(
      hexToRgb(customColors.background),
    );
    expect(swatchSpans[1].style.background).toBe(
      hexToRgb(customColors.primary),
    );
    expect(swatchSpans[2].style.background).toBe(hexToRgb(customColors.accent));
  });
});
