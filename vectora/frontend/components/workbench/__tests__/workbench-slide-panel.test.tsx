// @vitest-environment jsdom
/**
 * WorkbenchSlidePanel — base compartilhada dos painéis deslizantes da workbench.
 * Renderiza título + conteúdo quando aberto; fecha via botão ou backdrop.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

import { WorkbenchSlidePanel } from "../workbench-slide-panel";

afterEach(cleanup);

describe("WorkbenchSlidePanel", () => {
  it("não renderiza quando fechado", () => {
    render(
      <WorkbenchSlidePanel open={false} onClose={() => {}} title="Settings">
        <p>conteúdo</p>
      </WorkbenchSlidePanel>,
    );
    expect(screen.queryByText("conteúdo")).not.toBeInTheDocument();
  });

  it("renderiza título + filhos quando aberto", () => {
    render(
      <WorkbenchSlidePanel
        open
        onClose={() => {}}
        title="Configurações do RAG"
        testId="painel-x"
      >
        <p>corpo do painel</p>
      </WorkbenchSlidePanel>,
    );
    expect(screen.getByTestId("painel-x")).toBeInTheDocument();
    expect(screen.getByText("Configurações do RAG")).toBeInTheDocument();
    expect(screen.getByText("corpo do painel")).toBeInTheDocument();
  });

  it("o botão de fechar chama onClose", () => {
    const onClose = vi.fn();
    render(
      <WorkbenchSlidePanel open onClose={onClose} title="X">
        <p>c</p>
      </WorkbenchSlidePanel>,
    );
    fireEvent.click(screen.getByTestId("slide-panel-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("clicar no backdrop chama onClose", () => {
    const onClose = vi.fn();
    render(
      <WorkbenchSlidePanel open onClose={onClose} title="X">
        <p>c</p>
      </WorkbenchSlidePanel>,
    );
    // O backdrop é o elemento aria-hidden clicável.
    const backdrop = document.querySelector('[aria-hidden="true"]');
    expect(backdrop).toBeTruthy();
    fireEvent.click(backdrop!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
