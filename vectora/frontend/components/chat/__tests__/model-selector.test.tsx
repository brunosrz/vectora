// @vitest-environment jsdom
/**
 * Tests do ModelSelector: mostra o modelo ativo, abre o dropdown e dispara
 * onChange com o id do modelo escolhido.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { ModelSelector } from "../model-selector";
import {
  getAllowedModels,
  getModelDisplayName,
} from "@/lib/config/deployment-config";

afterEach(cleanup);

describe("ModelSelector", () => {
  it("exibe o nome do modelo ativo e começa fechado", () => {
    const value = getAllowedModels()[0];
    render(<ModelSelector value={value} onChange={() => {}} />);
    const toggle = screen.getByRole("button", { expanded: false });
    expect(toggle).toHaveTextContent(getModelDisplayName(value));
  });

  it("abre o dropdown ao clicar", () => {
    const value = getAllowedModels()[0];
    render(<ModelSelector value={value} onChange={() => {}} />);
    const toggle = screen.getByRole("button", { expanded: false });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("seleciona um modelo e dispara onChange com o id", () => {
    const onChange = vi.fn();
    const models = getAllowedModels();
    const value = models[0];
    const other = models[1];
    render(<ModelSelector value={value} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { expanded: false }));

    const otherLabel = getModelDisplayName(other);
    const optionButton = screen
      .getAllByText(otherLabel)
      .map((el) => el.closest("button"))
      .find((b): b is HTMLButtonElement => b !== null);

    expect(optionButton).toBeTruthy();
    fireEvent.click(optionButton!);
    expect(onChange).toHaveBeenCalledWith(other);
  });
});
