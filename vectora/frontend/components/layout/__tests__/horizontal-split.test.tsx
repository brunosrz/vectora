// @vitest-environment jsdom
/**
 * HorizontalSplit — regressão: o painel esquerdo (`left`, onde o Header vive)
 * usava `min-w-0` puro, sem piso — arrastar o workbench bem largo numa janela
 * estreita podia encolher o Header até sumir ícones inteiros (ajuda,
 * configurações, mode-switch) em vez de só truncar texto.
 */
import { describe, expect, it, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

import { HorizontalSplit } from "../horizontal-split";

afterEach(cleanup);

describe("HorizontalSplit — piso de largura do painel esquerdo", () => {
  it("aplica min-width de 360px por padrão no painel esquerdo", () => {
    render(
      <HorizontalSplit
        left={<div data-testid="left-content">Header + chat</div>}
        right={null}
        showRight={false}
        rightSize={280}
        onResize={() => {}}
      />,
    );
    const wrapper = screen.getByTestId("left-content").parentElement;
    expect(wrapper?.style.minWidth).toBe("360px");
  });

  it("aceita um minLeft customizado (edge — 0 desativa o piso)", () => {
    render(
      <HorizontalSplit
        left={<div data-testid="left-content">Header + chat</div>}
        right={null}
        showRight={false}
        rightSize={280}
        onResize={() => {}}
        minLeft={0}
      />,
    );
    const wrapper = screen.getByTestId("left-content").parentElement;
    expect(wrapper?.style.minWidth).toBe("0px");
  });
});
