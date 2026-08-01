// @vitest-environment jsdom
/**
 * Regressão do bug real reportado ao vivo no Electron: o seletor de modo
 * (`IdeModeSwitch`) media a própria largura via ResizeObserver, mas o
 * wrapper do `<header>` não tinha `min-w-0` — por padrão CSS um flex-item
 * sem isso nunca encolhe abaixo do min-content do próprio conteúdo, então
 * a medição nunca cruzava os limiares de truncamento/ícone-only. jsdom não
 * calcula layout real (getBoundingClientRect sempre 0), então não dá pra
 * reproduzir o encolhimento em si — mas dá pra travar a classe que causou
 * a regressão, que é o suficiente pra pegar a próxima vez que alguém
 * remover `min-w-0` sem saber por que ela existe.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img alt={props.alt as string} />;
  },
}));
vi.mock("../contextual-help", () => ({ ContextualHelp: () => null }));
vi.mock("../settings-menu", () => ({ SettingsMenu: () => null }));
vi.mock("../ide-mode-switcher", () => ({
  IdeModeSwitch: () => <div data-testid="mode-switch" />,
}));

const { Header } = await import("../header");

afterEach(() => cleanup());

describe("Header — wrapper do seletor de modo pode encolher", () => {
  it("a div que envolve o IdeModeSwitch tem min-w-0", () => {
    const { container } = render(<Header showModeSwitch />);
    const wrapper = container.querySelector(
      '[data-testid="mode-switch"]',
    )?.parentElement;

    expect(wrapper?.className).toContain("min-w-0");
  });
});
