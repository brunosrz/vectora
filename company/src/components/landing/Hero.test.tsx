// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import Hero from "./Hero";

vi.mock("#/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    ...rest
  }: {
    children: React.ReactNode;
    to: string;
  } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}));

describe("Hero", () => {
  it("mostra o gif de demo quando carrega com sucesso", () => {
    render(<Hero />);
    const img = screen.getByRole("img", { name: "hero_gif_alt" });
    fireEvent.load(img);
    expect(img).toBeInTheDocument();
    expect(screen.queryByText("showcase_preview_soon")).not.toBeInTheDocument();
  });

  it("mostra o placeholder 'prévia em breve' quando o gif falha ao carregar", () => {
    render(<Hero />);
    const img = screen.getByRole("img", { name: "hero_gif_alt" });
    fireEvent.error(img);
    expect(
      screen.queryByRole("img", { name: "hero_gif_alt" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("showcase_preview_soon")).toBeInTheDocument();
  });

  it("mostra o placeholder quando o gif já falhou antes da hidratação (evento error perdido)", () => {
    // O SSR entrega o <img> puro; se o GIF já 404 nesse meio-tempo, o
    // navegador dispara "error" antes do React anexar o onError — o
    // handler nunca roda. complete=true + naturalWidth=0 é o estado que o
    // navegador expõe nesse caso; sem o fallback via useEffect, a imagem
    // quebrada ficaria visível pra sempre (bug relatado em produção).
    const completeSpy = vi
      .spyOn(window.HTMLImageElement.prototype, "complete", "get")
      .mockReturnValue(true);
    const widthSpy = vi
      .spyOn(window.HTMLImageElement.prototype, "naturalWidth", "get")
      .mockReturnValue(0);

    render(<Hero />);

    expect(
      screen.queryByRole("img", { name: "hero_gif_alt" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("showcase_preview_soon")).toBeInTheDocument();

    completeSpy.mockRestore();
    widthSpy.mockRestore();
  });
});
