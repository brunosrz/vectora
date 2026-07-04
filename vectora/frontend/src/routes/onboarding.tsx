import { createFileRoute } from "@tanstack/react-router";
import { PreAuthWizard } from "@/components/onboarding/pre-auth-wizard";

export const Route = createFileRoute("/onboarding")({
  component: PreAuthWizard,
});
