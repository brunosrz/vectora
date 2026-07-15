// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import AdminTabs from "./AdminTabs";

const { mockUseRouterState, mockListIssuesAdmin } = vi.hoisted(() => ({
  mockUseRouterState: vi.fn(),
  mockListIssuesAdmin: vi.fn(),
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

vi.mock("#/server/fns/admin", () => ({
  listIssuesAdmin: mockListIssuesAdmin,
}));

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("AdminTabs", () => {
  it("renderiza as 4 abas (Usuários, Cupons, Presentes, Issues)", () => {
    mockUseRouterState.mockReturnValue({ location: { pathname: "/admin" } });
    mockListIssuesAdmin.mockResolvedValue({ issues: [] });
    renderWithClient(<AdminTabs />);

    expect(screen.getByText("admin_tab_users")).toBeInTheDocument();
    expect(screen.getByText("admin_tab_coupons")).toBeInTheDocument();
    expect(screen.getByText("admin_tab_gifts")).toBeInTheDocument();
    expect(screen.getByText("admin_tab_issues")).toBeInTheDocument();
  });

  it("marca a aba de cupons como ativa quando a rota atual é /admin/coupons", () => {
    mockUseRouterState.mockReturnValue({
      location: { pathname: "/admin/coupons" },
    });
    mockListIssuesAdmin.mockResolvedValue({ issues: [] });
    renderWithClient(<AdminTabs />);

    expect(screen.getByText("admin_tab_coupons")).toHaveClass("border-primary");
    expect(screen.getByText("admin_tab_users")).not.toHaveClass(
      "border-primary",
    );
  });

  it("mostra o badge de contagem só quando há issues abertas (notificação in-app)", async () => {
    mockUseRouterState.mockReturnValue({ location: { pathname: "/admin" } });
    mockListIssuesAdmin.mockResolvedValue({
      issues: [
        { id: "1", status: "open" },
        { id: "2", status: "open" },
        { id: "3", status: "resolved" },
      ],
    });
    renderWithClient(<AdminTabs />);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
  });

  it("não mostra badge quando não há issues abertas (edge)", async () => {
    mockUseRouterState.mockReturnValue({ location: { pathname: "/admin" } });
    mockListIssuesAdmin.mockResolvedValue({
      issues: [{ id: "1", status: "resolved" }],
    });
    renderWithClient(<AdminTabs />);

    await waitFor(() => {
      expect(mockListIssuesAdmin).toHaveBeenCalled();
    });
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
