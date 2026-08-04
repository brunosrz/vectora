// @vitest-environment jsdom
/**
 * IdeModeLayout — acima do breakpoint `md` os quatro painéis do modo IDE
 * (nav-bar, workbench, editor, chat) renderizam lado a lado sem mudança de
 * comportamento. Abaixo dele, só o painel selecionado fica montado, e a
 * faixa de abas no topo troca qual está visível.
 */

import { describe, expect, it } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";

import { IdeModeLayout } from "@/components/layout/ide-mode-layout";

function renderLayout(isNarrow: boolean) {
  return render(
    <IdeModeLayout
      isNarrow={isNarrow}
      navBar={<div data-testid="panel-navbar">NavBar</div>}
      workbenchContent={<div data-testid="panel-workbench">Workbench</div>}
      editor={<div data-testid="panel-editor">Editor</div>}
      chat={<div data-testid="panel-chat">Chat</div>}
    />,
  );
}

describe("IdeModeLayout", () => {
  it("viewport larga: os quatro painéis renderizam lado a lado (regressão do layout atual)", () => {
    renderLayout(false);

    expect(screen.getByTestId("panel-navbar")).toBeInTheDocument();
    expect(screen.getByTestId("panel-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("panel-editor")).toBeInTheDocument();
    expect(screen.getByTestId("panel-chat")).toBeInTheDocument();
    // Sem faixa de abas — não existe no layout largo.
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("viewport estreita: só o painel ativo aparece no DOM; trocar de aba muda qual está visível", () => {
    renderLayout(true);

    // Default: editor.
    expect(screen.getByTestId("panel-editor")).toBeInTheDocument();
    expect(screen.queryByTestId("panel-chat")).not.toBeInTheDocument();
    expect(screen.queryByTestId("panel-workbench")).not.toBeInTheDocument();
    expect(screen.queryByTestId("panel-navbar")).not.toBeInTheDocument();

    const tablist = screen.getByRole("tablist");
    fireEvent.click(within(tablist).getByTestId("ide-mobile-tab-chat"));

    expect(screen.getByTestId("panel-chat")).toBeInTheDocument();
    expect(screen.queryByTestId("panel-editor")).not.toBeInTheDocument();
    expect(screen.queryByTestId("panel-workbench")).not.toBeInTheDocument();

    fireEvent.click(within(tablist).getByTestId("ide-mobile-tab-workbench"));

    expect(screen.getByTestId("panel-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("panel-navbar")).toBeInTheDocument();
    expect(screen.queryByTestId("panel-chat")).not.toBeInTheDocument();
    expect(screen.queryByTestId("panel-editor")).not.toBeInTheDocument();
  });

  it("borda: viewport estreita sem workbenchContent (painel fechado) não quebra ao selecionar a aba workbench", () => {
    render(
      <IdeModeLayout
        isNarrow
        navBar={<div data-testid="panel-navbar">NavBar</div>}
        workbenchContent={null}
        editor={<div data-testid="panel-editor">Editor</div>}
        chat={<div data-testid="panel-chat">Chat</div>}
      />,
    );

    fireEvent.click(screen.getByTestId("ide-mobile-tab-workbench"));

    expect(screen.getByTestId("panel-navbar")).toBeInTheDocument();
    expect(screen.queryByTestId("panel-workbench")).not.toBeInTheDocument();
    expect(() => screen.getByTestId("panel-workbench")).toThrow();
  });
});
