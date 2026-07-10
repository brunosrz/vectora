// @vitest-environment jsdom

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

// SetupWizard é pesado — mocka só pra observar se monta ou não.
vi.mock("../setup-wizard", () => ({
  SetupWizard: ({ userId }: { userId: string }) => (
    <div data-testid="setup-wizard">wizard {userId}</div>
  ),
  isOnboardingDone: vi.fn(),
}));

let mockUserId: string | null = "u1";
vi.mock("@/lib/stores/auth-store", () => ({
  useAuthStore: (sel: (s: { user: { id: string } | null }) => unknown) =>
    sel({ user: mockUserId ? { id: mockUserId } : null }),
}));

import { OnboardingGate } from "../onboarding-gate";
import { isOnboardingDone } from "../setup-wizard";

describe("OnboardingGate", () => {
  beforeEach(() => {
    mockUserId = "u1";
    vi.mocked(isOnboardingDone).mockReset();
  });

  afterEach(cleanup);

  it("monta o wizard quando há userId e o onboarding não foi concluído", () => {
    vi.mocked(isOnboardingDone).mockReturnValue(false);
    render(<OnboardingGate />);
    expect(screen.getByTestId("setup-wizard")).toBeInTheDocument();
  });

  it("não monta quando o onboarding já foi concluído", () => {
    vi.mocked(isOnboardingDone).mockReturnValue(true);
    render(<OnboardingGate />);
    expect(screen.queryByTestId("setup-wizard")).toBeNull();
  });

  it("não monta sem userId (não autenticado / rota pública)", () => {
    mockUserId = null;
    vi.mocked(isOnboardingDone).mockReturnValue(false);
    render(<OnboardingGate />);
    expect(screen.queryByTestId("setup-wizard")).toBeNull();
  });
});
