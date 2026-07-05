// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type * as SubscriptionModule from "#/server/fns/subscription";

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
  mockToastSuccess,
} = vi.hoisted(() => ({
  mockGetSubscription: vi.fn(),
  mockCreateCheckout: vi.fn(),
  mockCreatePortal: vi.fn(),
  mockToastError: vi.fn(),
  mockToastSuccess: vi.fn(),
}));

vi.mock("#/server/fns/subscription", async () => {
  const actual = await vi.importActual<typeof SubscriptionModule>(
    "#/server/fns/subscription",
  );
  return {
    ...actual,
    getSubscription: mockGetSubscription,
    createCheckout: mockCreateCheckout,
    createPortal: mockCreatePortal,
  };
});

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: mockToastSuccess },
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

  it("clicar em fazer upgrade envia o plano default (1m) e redireciona para a URL de checkout", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "BRL" });
    mockCreateCheckout.mockResolvedValue({ url: "https://checkout.test/x" });
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_upgrade_pro"));

    fireEvent.click(screen.getByText("billing_upgrade_pro"));

    await waitFor(() =>
      expect(window.location.href).toBe("https://checkout.test/x"),
    );
    expect(mockCreateCheckout).toHaveBeenCalledWith({
      data: { planId: "1m", couponCode: undefined },
    });
  });

  it("selecionar um plano diferente e digitar um cupom envia ambos no checkout", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "USD" });
    mockCreateCheckout.mockResolvedValue({ url: "https://checkout.test/y" });
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_upgrade_pro"));

    fireEvent.change(screen.getByDisplayValue(/billing_plan_1m/), {
      target: { value: "3m" },
    });
    fireEvent.change(
      screen.getByPlaceholderText("billing_coupon_placeholder"),
      {
        target: { value: "galego" },
      },
    );
    fireEvent.click(screen.getByText("billing_upgrade_pro"));

    await waitFor(() =>
      expect(mockCreateCheckout).toHaveBeenCalledWith({
        data: { planId: "3m", couponCode: "galego" },
      }),
    );
  });

  it("um cupom free_lifetime (redeemed: true) mostra toast de sucesso em vez de redirecionar (edge)", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "free", currency: "USD" });
    mockCreateCheckout.mockResolvedValue({ redeemed: true });
    renderWithClient(<BillingSection />);
    await waitFor(() => screen.getByText("billing_upgrade_pro"));

    fireEvent.click(screen.getByText("billing_upgrade_pro"));

    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("billing_coupon_redeemed"),
    );
    expect(window.location.href).toBe("");
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
