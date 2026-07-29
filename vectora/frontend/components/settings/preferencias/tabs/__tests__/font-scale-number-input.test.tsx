// @vitest-environment jsdom
/**
 * FontScaleNumberInput — campo numérico ao lado dos sliders de escala de
 * fonte (Preferências → Aparência). Sincronização bidirecional: digitar
 * atualiza o estado (onChange) em tempo real; valor fora do range só é
 * clampado no blur/Enter (não trava o usuário no meio da digitação); campo
 * vazio/inválido não quebra o estado — mantém o último valor válido.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { FontScaleNumberInput } from "../preferencias-tab";

afterEach(() => {
  cleanup();
});

describe("FontScaleNumberInput", () => {
  it("digitar um valor válido dentro do range chama onChange em tempo real", () => {
    const onChange = vi.fn();
    render(
      <FontScaleNumberInput
        id="x"
        value={16}
        min={13}
        max={24}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "18" } });

    expect(onChange).toHaveBeenCalledWith(18);
    expect(input.value).toBe("18");
  });

  it("valor fora do range não é clampado durante a digitação, só no blur", () => {
    const onChange = vi.fn();
    render(
      <FontScaleNumberInput
        id="x"
        value={16}
        min={13}
        max={24}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "999" } });
    expect(onChange).toHaveBeenCalledWith(999);

    onChange.mockClear();
    fireEvent.blur(input);
    expect(onChange).toHaveBeenCalledWith(24);
    expect(input.value).toBe("24");
  });

  it("par de erro: campo vazio/inválido no blur não quebra o estado, reverte pro último valor válido", () => {
    const onChange = vi.fn();
    render(
      <FontScaleNumberInput
        id="x"
        value={16}
        min={13}
        max={24}
        onChange={onChange}
      />,
    );

    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.blur(input);

    expect(onChange).not.toHaveBeenCalled();
    expect(input.value).toBe("16");
  });

  it("mudar o valor externo (slider) reflete no campo numérico", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <FontScaleNumberInput
        id="x"
        value={16}
        min={13}
        max={24}
        onChange={onChange}
      />,
    );
    rerender(
      <FontScaleNumberInput
        id="x"
        value={20}
        min={13}
        max={24}
        onChange={onChange}
      />,
    );

    expect((screen.getByRole("spinbutton") as HTMLInputElement).value).toBe(
      "20",
    );
  });
});
