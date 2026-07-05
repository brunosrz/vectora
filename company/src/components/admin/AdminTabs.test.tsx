// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import AdminTabs from "./AdminTabs";

const { mockUseRouterState } = vi.hoisted(() => ({
  mockUseRouterState: vi.fn(),
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
  useRouterState: mockUseRouterState,
}));

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

describe("AdminTabs", () => {
  it("renderiza as 3 abas (Usuários, Cupons, Presentes)", () => {
    mockUseRouterState.mockReturnValue({ location: { pathname: "/admin" } });
    render(<AdminTabs />);

    expect(screen.getByText("admin_tab_users")).toBeInTheDocument();
    expect(screen.getByText("admin_tab_coupons")).toBeInTheDocument();
    expect(screen.getByText("admin_tab_gifts")).toBeInTheDocument();
  });

  it("marca a aba de cupons como ativa quando a rota atual é /admin/coupons", () => {
    mockUseRouterState.mockReturnValue({
      location: { pathname: "/admin/coupons" },
    });
    render(<AdminTabs />);

    expect(screen.getByText("admin_tab_coupons")).toHaveClass("border-primary");
    expect(screen.getByText("admin_tab_users")).not.toHaveClass(
      "border-primary",
    );
  });
});
