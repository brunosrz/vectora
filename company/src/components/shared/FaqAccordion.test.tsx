// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FaqAccordion from "./FaqAccordion";
import type { FaqItem } from "./FaqAccordion";

const ITEMS: FaqItem[] = [
  { question: "O que é o Vectora?", answer: "Um agente self-hosted." },
  { question: "Como funciona o RAG?", answer: "BM25 + vetorial + reranker." },
];

describe("FaqAccordion", () => {
  it("renderiza todas as perguntas", () => {
    render(<FaqAccordion items={ITEMS} />);
    expect(screen.getByText("O que é o Vectora?")).toBeInTheDocument();
    expect(screen.getByText("Como funciona o RAG?")).toBeInTheDocument();
  });

  it("não mostra a resposta antes de clicar na pergunta", () => {
    render(<FaqAccordion items={ITEMS} />);
    expect(
      screen.queryByText("Um agente self-hosted."),
    ).not.toBeInTheDocument();
  });

  it("revela a resposta ao clicar na pergunta", () => {
    render(<FaqAccordion items={ITEMS} />);

    fireEvent.click(screen.getByText("O que é o Vectora?"));

    expect(screen.getByText("Um agente self-hosted.")).toBeInTheDocument();
  });

  it("é 'single collapsible': abrir uma pergunta fecha a anterior", () => {
    render(<FaqAccordion items={ITEMS} />);

    fireEvent.click(screen.getByText("O que é o Vectora?"));
    expect(screen.getByText("Um agente self-hosted.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Como funciona o RAG?"));
    expect(
      screen.queryByText("Um agente self-hosted."),
    ).not.toBeInTheDocument();
    expect(screen.getByText("BM25 + vetorial + reranker.")).toBeInTheDocument();
  });

  it("renderiza sem itens sem lançar (edge — lista vazia)", () => {
    const { container } = render(<FaqAccordion items={[]} />);
    expect(container.querySelectorAll('[role="button"]')).toHaveLength(0);
  });
});
