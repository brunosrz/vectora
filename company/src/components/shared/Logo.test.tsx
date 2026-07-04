// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import Logo from "./Logo";

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

describe("Logo", () => {
  it("renderiza como link para '/' por padrão", () => {
    render(<Logo />);
    const link = screen.getByRole("link", { name: "Vectora" });
    expect(link).toHaveAttribute("href", "/");
  });

  it("renderiza sem <Link> quando asLink=false (edge — dentro de outro link)", () => {
    render(<Logo asLink={false} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("Vectora")).toBeInTheDocument();
  });

  it("sempre exibe o texto 'Vectora' ao lado do símbolo (regra de marca)", () => {
    const { container } = render(<Logo size="lg" />);
    expect(screen.getByText("Vectora")).toBeInTheDocument();
    // alt="" é proposital (decorativo) — por isso não tem role "img" acessível.
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "/vectora.svg",
    );
  });
});
