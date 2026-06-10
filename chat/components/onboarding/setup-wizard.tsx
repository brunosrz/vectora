"use client";

/**
 * SetupWizard — Wizard de primeiro acesso (4 passos).
 *
 * Aparece uma única vez por usuário, determinado pela flag
 * `vectora:onboarding-done-<userId>` no localStorage.
 *
 * Passos:
 *   1. Boas-vindas
 *   2. Idioma & Tema
 *   3. Workspaces (conceito)
 *   4. Pronto
 */

import { useState, useCallback } from "react";
import Image from "next/image";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useSettingsStore, type Lang } from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";

const TOTAL_STEPS = 4;

const ONBOARDING_KEY = (userId: string) => `vectora:onboarding-done-${userId}`;

export function isOnboardingDone(userId: string): boolean {
  if (typeof localStorage === "undefined") return true;
  return localStorage.getItem(ONBOARDING_KEY(userId)) === "1";
}

function markOnboardingDone(userId: string): void {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(ONBOARDING_KEY(userId), "1");
  }
}

interface SetupWizardProps {
  userId: string;
  onComplete: () => void;
}

// ===========================================================================
// Step components
// ===========================================================================

function StepWelcome() {
  const t = useT();
  return (
    <div className="flex flex-col items-center gap-4 py-4">
      <Image
        src="/vectora.svg"
        alt="Vectora"
        width={72}
        height={72}
        className="h-16 w-16"
      />
      <p className="text-sm text-muted-foreground text-center max-w-xs">
        {t("onboarding.welcome_body")}
      </p>
    </div>
  );
}

const LANGUAGES: { code: Lang; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português (BR)" },
];

function StepLanguage() {
  const t = useT();
  const lang = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);
  const theme = useSettingsStore((s) => s.theme);
  const setTheme = useSettingsStore((s) => s.setTheme);

  return (
    <div className="space-y-4 py-2">
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2">
          {t("onboarding.language_label")}
        </p>
        <div className="flex gap-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`px-3 py-1.5 rounded-md text-xs border transition-colors ${
                lang === l.code
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2">
          {t("onboarding.theme_label")}
        </p>
        <div className="flex gap-2">
          {(["dark", "light", "system"] as const).map((th) => (
            <button
              key={th}
              onClick={() => setTheme(th)}
              className={`px-3 py-1.5 rounded-md text-xs border capitalize transition-colors ${
                theme === th
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {th}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function StepWorkspace() {
  const t = useT();
  return (
    <div className="space-y-3 py-2 text-sm text-muted-foreground">
      <p>{t("onboarding.workspace_body")}</p>
      <ul className="list-disc list-inside space-y-1 text-xs">
        <li>{t("onboarding.workspace_bullet_1")}</li>
        <li>{t("onboarding.workspace_bullet_2")}</li>
        <li>{t("onboarding.workspace_bullet_3")}</li>
      </ul>
    </div>
  );
}

function StepDone() {
  const t = useT();
  return (
    <div className="flex flex-col items-center gap-3 py-4 text-center">
      <span className="text-4xl">🎉</span>
      <p className="text-sm text-muted-foreground max-w-xs">
        {t("onboarding.done_body")}
      </p>
    </div>
  );
}

const STEP_COMPONENTS = [StepWelcome, StepLanguage, StepWorkspace, StepDone];

const STEP_TITLE_KEYS = [
  "onboarding.step1_title",
  "onboarding.step2_title",
  "onboarding.step3_title",
  "onboarding.step4_title",
] as const;

// ===========================================================================
// Step indicator — bolinhas de progresso conectadas por "ganchos"
// ===========================================================================

function StepIndicator({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-1.5 py-1">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              i === step
                ? "w-5 bg-primary"
                : i < step
                  ? "w-2 bg-primary/50"
                  : "w-2 bg-border"
            }`}
          />
          {i < total - 1 && (
            <div
              className={`h-px w-5 transition-colors duration-300 ${
                i < step ? "bg-primary/50" : "bg-border"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ===========================================================================
// Wizard
// ===========================================================================

export function SetupWizard({ userId, onComplete }: SetupWizardProps) {
  const t = useT();
  const [step, setStep] = useState(0);

  const handleNext = useCallback(() => {
    if (step < TOTAL_STEPS - 1) {
      setStep((s) => s + 1);
    } else {
      markOnboardingDone(userId);
      onComplete();
    }
  }, [step, userId, onComplete]);

  const handleBack = useCallback(() => {
    setStep((s) => Math.max(0, s - 1));
  }, []);

  const handleSkip = useCallback(() => {
    markOnboardingDone(userId);
    onComplete();
  }, [userId, onComplete]);

  const StepContent = STEP_COMPONENTS[step]!;
  const isFirstStep = step === 0;
  const isLastStep = step === TOTAL_STEPS - 1;

  return (
    <Dialog open onOpenChange={() => void 0}>
      <DialogContent
        className="max-w-sm"
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>{t(STEP_TITLE_KEYS[step]!)}</DialogTitle>
          <DialogDescription className="sr-only">
            {step + 1} / {TOTAL_STEPS}
          </DialogDescription>
        </DialogHeader>

        <StepContent />

        <StepIndicator step={step} total={TOTAL_STEPS} />

        <DialogFooter className="flex-row items-center justify-between gap-2 sm:justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            disabled={isFirstStep}
            className={`text-xs ${isFirstStep ? "invisible" : ""}`}
          >
            {t("onboarding.back")}
          </Button>

          <div className="flex items-center gap-2">
            {!isLastStep && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSkip}
                className="text-xs"
              >
                {t("onboarding.skip")}
              </Button>
            )}
            <Button size="sm" onClick={handleNext} autoFocus>
              {isLastStep ? t("onboarding.finish") : t("onboarding.next")}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
