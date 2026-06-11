"use client";

/**
 * SetupWizard — Wizard de primeiro acesso (7 passos).
 *
 * Aparece uma única vez por usuário, determinado pela flag
 * `vectora:onboarding-done-<userId>` no localStorage.
 *
 * Passos:
 *   1. Boas-vindas
 *   2. Idioma & Tema
 *   3. Token de licença (VECTORA_TOKEN)
 *   4. Modo de armazenamento (Lite vs Completo)
 *   5. Workspaces (conceito)
 *   6. O que é RAG
 *   7. Pronto
 */

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useSettingsStore, type Lang } from "@/lib/stores/settings-store";
import { useT } from "@/lib/i18n";

const TOTAL_STEPS = 7;

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

// ---------------------------------------------------------------------------
// Step: Token de licença (VECTORA_TOKEN)
// ---------------------------------------------------------------------------

interface ConfigSummary {
  vectora_token_configured: boolean;
  vectora_token_masked: string;
}

function StepToken() {
  const t = useT();
  const [config, setConfig] = useState<ConfigSummary | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/admin/config", { credentials: "include" })
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => void 0);
  }, []);

  const handleSave = async () => {
    const value = tokenInput.trim();
    if (!value) return;
    setSaving(true);
    try {
      await fetch("/admin/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ vectora_token: value }),
      });
      const fresh = await fetch("/admin/config", {
        credentials: "include",
      }).then((r) => r.json());
      setConfig(fresh);
      setTokenInput("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 py-2">
      <p className="text-sm text-muted-foreground">
        {t("onboarding.token_body")}
      </p>
      {config?.vectora_token_configured && (
        <p className="text-xs text-muted-foreground font-mono">
          {t("onboarding.token_configured")}: {config.vectora_token_masked}
        </p>
      )}
      <div className="flex gap-1.5">
        <Input
          type={showToken ? "text" : "password"}
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          placeholder="vct_…"
          className="h-8 text-xs font-mono flex-1"
          autoComplete="off"
        />
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 px-2"
          onClick={() => setShowToken((v) => !v)}
        >
          {showToken ? t("onboarding.token_hide") : t("onboarding.token_show")}
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={handleSave}
          disabled={saving || !tokenInput.trim()}
        >
          {saving ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
          ) : null}
          {saved ? t("onboarding.token_saved") : t("onboarding.token_save")}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("onboarding.token_hint")}{" "}
        <a
          href="https://vectora.company/dashboard"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline"
        >
          vectora.company/dashboard
        </a>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step: Modo de armazenamento (Lite vs Completo)
// ---------------------------------------------------------------------------

interface StorageTestResult {
  ok: boolean;
  error?: string;
  latency_ms?: number;
  started?: boolean;
}

interface ServiceFieldConfig {
  service: "postgres" | "redis" | "qdrant";
  title: string;
  fieldKey: string;
  testKey: string;
  placeholder: string;
  type?: string;
}

const SERVICE_FIELDS: ServiceFieldConfig[] = [
  {
    service: "postgres",
    title: "PostgreSQL",
    fieldKey: "postgres_dsn",
    testKey: "dsn",
    placeholder: "postgresql+asyncpg://user:pass@host:5432/vectora",
  },
  {
    service: "redis",
    title: "Redis",
    fieldKey: "redis_url",
    testKey: "url",
    placeholder: "redis://localhost:6379/0",
  },
  {
    service: "qdrant",
    title: "Qdrant",
    fieldKey: "qdrant_url",
    testKey: "url",
    placeholder: "http://localhost:6333",
  },
];

function ServiceConnectionCard({ config }: { config: ServiceFieldConfig }) {
  const t = useT();
  const [value, setValue] = useState("");
  const [selfHosted, setSelfHosted] = useState(false);
  const [startCommand, setStartCommand] = useState("");
  const [testResult, setTestResult] = useState<StorageTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleTest = async () => {
    const v = value.trim();
    if (!v) return;
    setTesting(true);
    setTestResult(null);
    try {
      const body: Record<string, unknown> = {
        backend: config.service,
        [config.testKey]: v,
      };
      if (selfHosted && startCommand.trim()) {
        body.self_hosted = true;
        body.start_command = startCommand.trim();
      }
      const res = await fetch("/admin/storage/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      setTestResult(await res.json());
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    const v = value.trim();
    if (!v) return;
    setSaving(true);
    try {
      const body: Record<string, unknown> = { [config.fieldKey]: v };
      if (selfHosted || startCommand.trim()) {
        body.services = {
          [config.service]: {
            self_hosted: selfHosted,
            start_command: startCommand.trim() || null,
          },
        };
      }
      await fetch("/admin/storage", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-1.5 rounded border px-2.5 py-2">
      <p className="text-xs font-medium">{config.title}</p>
      <Input
        type={config.type ?? "text"}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={config.placeholder}
        className="h-7 text-xs font-mono"
      />
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <Switch checked={selfHosted} onCheckedChange={setSelfHosted} />
        {t("onboarding.mode_self_hosted")}
      </label>
      {selfHosted && (
        <Input
          value={startCommand}
          onChange={(e) => setStartCommand(e.target.value)}
          placeholder={t("onboarding.mode_start_command_placeholder")}
          className="h-7 text-xs font-mono"
        />
      )}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          onClick={handleTest}
          disabled={testing || !value.trim()}
        >
          {testing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            t("onboarding.mode_test")
          )}
        </Button>
        <Button
          size="sm"
          className="h-7 text-xs"
          onClick={handleSave}
          disabled={saving || !value.trim()}
        >
          {saving ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : saved ? (
            t("onboarding.token_saved")
          ) : (
            t("onboarding.mode_save")
          )}
        </Button>
      </div>
      {testResult && (
        <div
          className={`text-xs flex items-center gap-1 ${testResult.ok ? "text-green-600" : "text-destructive"}`}
        >
          {testResult.ok ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              OK
              {testResult.latency_ms !== undefined && (
                <span className="text-muted-foreground">
                  ({testResult.latency_ms}ms)
                </span>
              )}
            </>
          ) : (
            <>
              <XCircle className="w-3.5 h-3.5" />
              {testResult.error ?? "Falha na conexão"}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function StepMode() {
  const t = useT();
  const [mode, setMode] = useState<"lite" | "complete">("lite");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/admin/storage", { credentials: "include" })
      .then((r) => r.json())
      .then((data) =>
        setMode(
          data?.config?.storage_mode === "complete" ? "complete" : "lite",
        ),
      )
      .catch(() => void 0);
  }, []);

  const handleSelect = async (next: "lite" | "complete") => {
    setMode(next);
    setSaving(true);
    try {
      await fetch("/admin/storage", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ storage_mode: next }),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 py-2">
      <p className="text-sm text-muted-foreground">
        {t("onboarding.mode_body")}
      </p>
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => handleSelect("lite")}
          className={`text-left p-3 rounded-md border transition-colors ${
            mode === "lite"
              ? "border-primary bg-primary/10"
              : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          <p className="text-xs font-medium">
            {t("onboarding.mode_lite_title")}
          </p>
          <p className="text-[11px] mt-1">{t("onboarding.mode_lite_desc")}</p>
        </button>
        <button
          onClick={() => handleSelect("complete")}
          className={`text-left p-3 rounded-md border transition-colors ${
            mode === "complete"
              ? "border-primary bg-primary/10"
              : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          <p className="text-xs font-medium">
            {t("onboarding.mode_complete_title")}
          </p>
          <p className="text-[11px] mt-1">
            {t("onboarding.mode_complete_desc")}
          </p>
        </button>
      </div>
      {saving && (
        <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
      )}
      {mode === "complete" && (
        <div className="space-y-2 pt-2 border-t max-h-64 overflow-y-auto pr-1">
          {SERVICE_FIELDS.map((cfg) => (
            <ServiceConnectionCard key={cfg.service} config={cfg} />
          ))}
        </div>
      )}
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

function StepRag() {
  const t = useT();
  return (
    <div className="space-y-3 py-2 text-sm text-muted-foreground">
      <p>{t("onboarding.rag_body")}</p>
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

const STEP_COMPONENTS = [
  StepWelcome,
  StepLanguage,
  StepToken,
  StepMode,
  StepWorkspace,
  StepRag,
  StepDone,
];

const STEP_TITLE_KEYS = [
  "onboarding.step1_title",
  "onboarding.step2_title",
  "onboarding.step3_title",
  "onboarding.step4_title",
  "onboarding.step5_title",
  "onboarding.step6_title",
  "onboarding.step7_title",
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
