// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Bot } from "lucide-react";

import FeaturesAccordion from "./FeaturesAccordion";

const ITEMS = [
  {
    id: "a",
    Icon: Bot,
    title: "Feature A",
    summary: "Resumo A",
    description: "Descrição completa da feature A.",
  },
  {
    id: "b",
    Icon: Bot,
    title: "Feature B",
    summary: "Resumo B",
    description: "Descrição completa da feature B.",
  },
];

describe("FeaturesAccordion", () => {
  it("mostra título e resumo de cada item, sem a descrição completa (fechado por padrão)", () => {
    render(<FeaturesAccordion items={ITEMS} />);

    expect(screen.getByText("Feature A")).toBeInTheDocument();
    expect(screen.getByText("Resumo A")).toBeInTheDocument();
    expect(
      screen.queryByText("Descrição completa da feature A."),
    ).not.toBeInTheDocument();
  });

  it("clicar no trigger expande e revela a descrição completa; clicar de novo fecha", () => {
    render(<FeaturesAccordion items={ITEMS} />);

    fireEvent.click(screen.getByText("Feature A"));
    expect(
      screen.getByText("Descrição completa da feature A."),
    ).toBeInTheDocument();

    // Par de erro/borda: reclicar no mesmo trigger tem que fechar de volta —
    // sem `@keyframes slideDown/slideUp` reais, o Presence do Radix nunca via
    // `animationend` e o conteúdo ficava preso montado mesmo com o accordion
    // já fechado (bug real relatado pelo usuário, invisível em jsdom porque
    // jsdom não anima CSS de verdade — este teste cobre o estado final do
    // DOM, não a transição).
    fireEvent.click(screen.getByText("Feature A"));
    expect(
      screen.queryByText("Descrição completa da feature A."),
    ).not.toBeInTheDocument();
  });

  it("erro/borda: expandir um item não revela a descrição de outro (accordion single)", () => {
    render(<FeaturesAccordion items={ITEMS} />);

    fireEvent.click(screen.getByText("Feature A"));
    expect(
      screen.getByText("Descrição completa da feature A."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Descrição completa da feature B."),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Feature B"));
    expect(
      screen.getByText("Descrição completa da feature B."),
    ).toBeInTheDocument();
  });

  it('título/resumo não ficam dentro de um <button> nativo — browsers bloqueiam seleção de texto por clique-arraste dentro de <button> (bug real reportado, o trigger vira <div role="button">)', () => {
    render(<FeaturesAccordion items={ITEMS} />);

    const title = screen.getByText("Feature A");
    expect(title.closest("button")).toBeNull();
    expect(title.closest('[role="button"]')).not.toBeNull();
  });

  it("teclado: Enter no trigger expande a descrição; erro/borda: outras teclas não fazem nada", () => {
    render(<FeaturesAccordion items={ITEMS} />);

    const trigger = screen.getByText("Feature A").closest('[role="button"]')!;

    fireEvent.keyDown(trigger, { key: "a" });
    expect(
      screen.queryByText("Descrição completa da feature A."),
    ).not.toBeInTheDocument();

    fireEvent.keyDown(trigger, { key: "Enter" });
    expect(
      screen.getByText("Descrição completa da feature A."),
    ).toBeInTheDocument();
  });
});
