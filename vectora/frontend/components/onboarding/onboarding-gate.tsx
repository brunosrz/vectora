"use client";

/**
 * OnboardingGate — monta o SetupWizard de primeiro acesso em qualquer rota.
 *
 * Fica na raiz (não só na rota de sessão) para aparecer também na home logo
 * após o setup-local. Gated por `isOnboardingDone(userId)`; o próprio wizard
 * persiste a flag ao concluir/pular, então basta esconder localmente.
 */

import { useState } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";
import { SetupWizard, isOnboardingDone } from "./setup-wizard";

export function OnboardingGate() {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const [dismissed, setDismissed] = useState(false);

  if (!userId || dismissed || isOnboardingDone(userId)) return null;

  return <SetupWizard userId={userId} onComplete={() => setDismissed(true)} />;
}
