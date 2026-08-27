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

  it("clicar no trigger expande e revela a descrição completa", () => {
    render(<FeaturesAccordion items={ITEMS} />);

    fireEvent.click(screen.getByText("Feature A"));

    expect(
      screen.getByText("Descrição completa da feature A."),
    ).toBeInTheDocument();
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
});
