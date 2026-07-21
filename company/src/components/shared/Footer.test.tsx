// @vitest-environment jsdom
/**
 * Footer — decisão do produto: lançamento sem CNPJ (custo de abertura +
 * contador inviável agora). O rodapé não deve mencionar CNPJ nem ser
 * substituído por CPF (que nunca fica público) — a menção simplesmente
 * deixa de existir. Regressão que travaria se alguém reintroduzisse sem
 * querer.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import Footer from "./Footer";

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

describe("Footer", () => {
  it("não menciona CNPJ nem CPF no rodapé público", () => {
    render(<Footer />);

    expect(screen.queryByText(/CNPJ/i)).toBeNull();
    expect(screen.queryByText(/CPF/i)).toBeNull();
  });

  it("mantém o copyright normal", () => {
    render(<Footer />);

    expect(screen.getByText(/Vectora\. All rights reserved\./)).toBeTruthy();
  });
});
