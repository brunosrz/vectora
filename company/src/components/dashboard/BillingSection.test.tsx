// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import BillingSection from "./BillingSection";

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

const {
  mockGetSubscription,
  mockCreateCheckout,
  mockCreatePortal,
  mockToastError,
} = vi.hoisted(() => ({
  mockGetSubscription: vi.fn(),
  mockCreateCheckout: vi.fn(),
  mockCreatePortal: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("#/server/fns/subscription", () => ({
  getSubscription: mockGetSubscription,
  createCheckout: mockCreateCheckout,
  createPortal: mockCreatePortal,
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const originalLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...originalLocation, href: "" },
  });
});

afterEach(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: originalLocation,
  });
});

describe("BillingSection", () => {
  it("não renderiza nada enquanto carrega (skeleton) e depois mostra o conteúdo", async () => {
    mockGetSubscription.mockResolvedValue({
      tier: "free",
      currency: "BRL",
    });
    const { container } = renderWithClient(<BillingSection />);

    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByText("billing_upgrade_pro")).toBeInTheDocument(),
    );
  });

  it("renderiza null quando não há assinatura (edge — free antes do primeiro checkout)", async () => {
    mockGetSubscription.mockResolvedValue(null);
    const { container } = renderWithClient(<BillingSection />);

    await waitFor(() =>
      expect(container.querySelector(".animate-pulse")).not.toBeInTheDocument(),
    );
    expect(container.querySelector(".max-w-xl")).not.toBeInTheDocument();
  });

  it("mostra copy BR (Asaas) quando currency=BRL", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "BRL" });
    renderWithClient(<BillingSection />);

    await waitFor(() => expect(screen.getByText(/Asaas/)).toBeInTheDocument());
  });

  it("mostra copy internacional (Stripe) quando currency=USD (edge)", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "USD" });
    renderWithClient(<BillingSection />);

    await waitFor(() => expect(screen.getByText(/Stripe/)).toBeInTheDocument());
  });

  it("clicar em fazer upgrade redireciona para a URL de checkout", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "BRL" });
    mockCreateCheckout.mockResolvedValue({ url: "https://checkout.test/x" });
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_upgrade_pro"));

    fireEvent.click(screen.getByText("billing_upgrade_pro"));

    await waitFor(() =>
      expect(window.location.href).toBe("https://checkout.test/x"),
    );
  });

  it("mostra o botão 'gerenciar' (portal) quando o tier é pro", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "pro", currency: "USD" });
    renderWithClient(<BillingSection />);

    await waitFor(() =>
      expect(screen.getByText("billing_manage")).toBeInTheDocument(),
    );
    expect(screen.queryByText("billing_upgrade_pro")).not.toBeInTheDocument();
  });

  it("clicar em gerenciar redireciona para o portal de billing", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "pro", currency: "USD" });
    mockCreatePortal.mockResolvedValue({ url: "https://portal.test/x" });
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_manage"));

    fireEvent.click(screen.getByText("billing_manage"));

    await waitFor(() =>
      expect(window.location.href).toBe("https://portal.test/x"),
    );
  });

  it("mostra toast de erro quando o checkout falha (edge)", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "BRL" });
    mockCreateCheckout.mockRejectedValue(new Error("services_error_500"));
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_upgrade_pro"));

    fireEvent.click(screen.getByText("billing_upgrade_pro"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
  });
});
