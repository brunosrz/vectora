// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { ThemePicker, ThemeModeToggle } from "../theme-picker";
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
  it("renderiza todos os presets + custom, um card por opção (sem 'system' no grid)", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(THEME_PRESETS.length + 1);
    expect(screen.getByText("Personalizado")).toBeInTheDocument();
    for (const preset of THEME_PRESETS) {
      expect(screen.getByText(preset.label)).toBeInTheDocument();
    }
  });

  it("clicar num preset chama onChange com o id do preset", () => {
    const onChange = vi.fn();
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={onChange}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    fireEvent.click(screen.getByText(THEME_PRESETS[1].label));

    expect(onChange).toHaveBeenCalledWith(THEME_PRESETS[1].id);
  });

  it("opção ativa fica marcada com aria-pressed e as demais não", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    const activeButton = screen
      .getByText(THEME_PRESETS[0].label)
      .closest("button");
    expect(activeButton).toHaveAttribute("aria-pressed", "true");

    const otherButton = screen
      .getByText(THEME_PRESETS[1].label)
      .closest("button");
    expect(otherButton).toHaveAttribute("aria-pressed", "false");
  });

  it("card pintado usa a cor real de background do preset (não um valor fixo) — erro/borda", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    const firstPreset = THEME_PRESETS[0];
    const button = screen.getByText(firstPreset.label).closest("button")!;
    expect(button.style.background).toBe(
      hexToRgb(firstPreset.colors.background),
    );
  });

  it("card do custom reflete customColors passado, não os presets — erro/borda", () => {
    render(
      <ThemePicker
        value="custom"
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    const button = screen.getByText("Personalizado").closest("button")!;
    expect(button.style.background).toBe(hexToRgb(customColors.background));
  });

  it("busca filtra as opções por label", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    const target = THEME_PRESETS.find((p) => p.label === "GitHub Dark")!;
    fireEvent.change(screen.getByPlaceholderText("Buscar..."), {
      target: { value: "GitHub Dark" },
    });

    expect(screen.getByText(target.label)).toBeInTheDocument();
    for (const preset of THEME_PRESETS.filter((p) => p.id !== target.id)) {
      expect(screen.queryByText(preset.label)).toBeNull();
    }
    expect(screen.queryByText("Personalizado")).toBeNull();
  });

  it("erro de borda — busca sem nenhum resultado não quebra, só não renderiza cards", () => {
    render(
      <ThemePicker
        value={THEME_PRESETS[0].id}
        onChange={vi.fn()}
        presets={THEME_PRESETS}
        customLabel="Personalizado"
        customColors={customColors}
        searchPlaceholder="Buscar..."
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Buscar..."), {
      target: { value: "paleta-que-nao-existe-em-lugar-nenhum" },
    });

    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});

describe("ThemeModeToggle", () => {
  const labels = { system: "Sistema", light: "Claro", dark: "Escuro" };

  it("renderiza os 3 modos, com o valor atual marcado ativo", () => {
    render(<ThemeModeToggle value="dark" onChange={vi.fn()} labels={labels} />);

    expect(screen.getByText("Sistema")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByText("Claro")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Escuro")).toHaveAttribute("aria-pressed", "true");
  });

  it("clicar num modo chama onChange com esse modo", () => {
    const onChange = vi.fn();
    render(
      <ThemeModeToggle value="system" onChange={onChange} labels={labels} />,
    );

    fireEvent.click(screen.getByText("Claro"));

    expect(onChange).toHaveBeenCalledWith("light");
  });
});
