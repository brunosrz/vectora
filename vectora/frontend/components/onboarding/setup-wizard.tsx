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
import { Loader2, CheckCircle2, XCircle, ExternalLink } from "lucide-react";
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
import { m } from "@/lib/paraglide/messages";
import { mDyn } from "@/lib/i18n-dyn";
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

/** Props comuns a todos os passos — apenas StepMode usa `onValidityChange`. */
interface StepProps {
  onValidityChange?: (valid: boolean) => void;
}

// ===========================================================================
// Step components
// ===========================================================================

function StepWelcome(_props: StepProps) {
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
        {m.onboarding_welcome_body()}
      </p>
    </div>
  );
}

const LANGUAGES: { code: Lang; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português (BR)" },
];

function StepLanguage(_props: StepProps) {
  const lang = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);
  const theme = useSettingsStore((s) => s.theme);
  const setTheme = useSettingsStore((s) => s.setTheme);

  return (
    <div className="space-y-4 py-2">
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2">
          {m.onboarding_language_label()}
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
          {m.onboarding_theme_label()}
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

/** Resultado de POST /license/validate ou /license/connect. */
interface LicenseResult {
  valid: boolean;
  tier?: string;
  status?: string;
  days_remaining?: number;
  error?: string;
}

/** Classe do botão segmentado Token | Login do StepToken. */
const segmentClass = (active: boolean) =>
  `flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
    active
      ? "bg-primary/10 text-primary border border-primary"
      : "border border-border text-muted-foreground hover:text-foreground"
  }`;

/** Badge compacto com o resultado da validação da licença. */
function LicenseResultBadge({ result }: { result: LicenseResult }) {
  if (result.valid) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
        {m.onboarding_token_valid()}
        {result.tier ? ` — ${result.tier}` : ""}
        {result.status === "trial" && result.days_remaining
          ? ` (trial, ${result.days_remaining}d)`
          : ""}
      </p>
    );
  }
  return (
    <p className="flex items-center gap-1.5 text-xs text-destructive">
      <XCircle className="w-3.5 h-3.5 shrink-0" />
      {result.error || m.onboarding_token_invalid()}
    </p>
  );
}

function StepToken(_props: StepProps) {
  const [mode, setMode] = useState<"token" | "login">("token");
  const [config, setConfig] = useState<ConfigSummary | null>(null);
  const [result, setResult] = useState<LicenseResult | null>(null);

  // Modo token
  const [tokenInput, setTokenInput] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [saving, setSaving] = useState(false);

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
    setResult(null);
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
      // Valida imediatamente — antes o token era salvo sem nenhum feedback.
      const validation = (await fetch("/license/validate", {
        method: "POST",
        credentials: "include",
      }).then((r) => r.json())) as LicenseResult;
      setResult(validation);
    } catch {
      setResult({ valid: false, error: m.onboarding_token_invalid() });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 py-2">
      <p className="text-sm text-muted-foreground">
        {m.onboarding_token_body()}
      </p>

      {/* Seletor: colar token OU entrar com a conta vectora.company */}
      <div className="flex gap-1.5">
        <button
          type="button"
          className={segmentClass(mode === "token")}
          onClick={() => setMode("token")}
        >
          {m.onboarding_token_mode_token()}
        </button>
        <button
          type="button"
          className={segmentClass(mode === "login")}
          onClick={() => setMode("login")}
        >
          {m.onboarding_token_mode_login()}
        </button>
      </div>

      {config?.vectora_token_configured && (
        <p className="text-xs text-muted-foreground font-mono">
          {m.onboarding_token_configured()}: {config.vectora_token_masked}
        </p>
      )}

      {mode === "token" ? (
        <>
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
              {showToken
                ? m.onboarding_token_hide()
                : m.onboarding_token_show()}
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
              {m.onboarding_token_save()}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            {m.onboarding_token_hint()}{" "}
            <a
              href="https://vectora.company/dashboard"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              vectora.company/dashboard
            </a>
          </p>
        </>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            {m.onboarding_token_login_hint()}
          </p>
          <a
            href="https://vectora.company/dashboard"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
          >
            vectora.company/dashboard
            <ExternalLink className="w-3 h-3" />
          </a>
          <p className="text-xs text-muted-foreground">
            {m.onboarding_token_login_copy_hint()}
          </p>
        </>
      )}

      {result && <LicenseResultBadge result={result} />}
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

function ServiceConnectionCard({
  config,
  onConnectedChange,
}: {
  config: ServiceFieldConfig;
  onConnectedChange?: (service: string, ok: boolean) => void;
}) {
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
    onConnectedChange?.(config.service, false);
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
      const result = (await res.json()) as StorageTestResult;
      setTestResult(result);
      onConnectedChange?.(config.service, result.ok);
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
        autoComplete={config.type === "password" ? "new-password" : "off"}
        placeholder={config.placeholder}
        className="h-7 text-xs font-mono"
      />
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <Switch checked={selfHosted} onCheckedChange={setSelfHosted} />
        {m.onboarding_mode_self_hosted()}
      </label>
      {selfHosted && (
        <Input
          value={startCommand}
          onChange={(e) => setStartCommand(e.target.value)}
          autoComplete="off"
          placeholder={m.onboarding_mode_start_command_placeholder()}
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
            m.onboarding_mode_test()
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
            m.onboarding_token_saved()
          ) : (
            m.onboarding_mode_save()
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

function StepMode({ onValidityChange }: StepProps) {
  const [mode, setMode] = useState<"lite" | "complete">("lite");
  const [saving, setSaving] = useState(false);
  const [connected, setConnected] = useState<Record<string, boolean>>({});
  // Serviços já configurados via env (ex: docker-compose com Postgres/Redis/
  // Qdrant embutidos) — o wizard não pede para configurá-los novamente.
  const [preconfigured, setPreconfigured] = useState<Record<string, boolean>>(
    {},
  );
  // Resultado do teste automático dos serviços pré-configurados (via env).
  const [preconfiguredTests, setPreconfiguredTests] = useState<
    Record<string, StorageTestResult | null>
  >({});

  const handleConnectedChange = useCallback((service: string, ok: boolean) => {
    setConnected((prev) => ({ ...prev, [service]: ok }));
  }, []);

  useEffect(() => {
    if (mode === "lite") {
      onValidityChange?.(true);
      return;
    }
    onValidityChange?.(
      SERVICE_FIELDS.every(
        (f) => preconfigured[f.service] || connected[f.service],
      ),
    );
  }, [mode, connected, preconfigured, onValidityChange]);

  useEffect(() => {
    fetch("/admin/storage", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        const cfg = data?.config ?? {};
        setMode(cfg.storage_mode === "complete" ? "complete" : "lite");
        const pre: Record<string, boolean> = {
          postgres: !!cfg.postgres_configured,
          redis: !!cfg.redis_configured,
          qdrant: !!cfg.qdrant_configured,
        };
        setPreconfigured(pre);

        // Testa em background cada serviço já configurado via env.
        Object.entries(pre)
          .filter(([, ok]) => ok)
          .forEach(([service]) => {
            fetch("/admin/storage/test", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({ backend: service }),
            })
              .then((r) => r.json())
              .then((result: StorageTestResult) => {
                setPreconfiguredTests((prev) => ({
                  ...prev,
                  [service]: result,
                }));
                if (!result.ok) {
                  // Teste falhou: remove da lista de pré-configurados para
                  // exibir o card de configuração manual.
                  setPreconfigured((prev) => ({ ...prev, [service]: false }));
                } else {
                  setConnected((prev) => ({ ...prev, [service]: true }));
                }
              })
              .catch(() => {
                setPreconfiguredTests((prev) => ({
                  ...prev,
                  [service]: { ok: false, error: "Erro ao testar conexão" },
                }));
                setPreconfigured((prev) => ({ ...prev, [service]: false }));
              });
          });
      })
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
        {m.onboarding_mode_body()}
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
            {m.onboarding_mode_lite_title()}
          </p>
          <p className="text-[11px] mt-1">{m.onboarding_mode_lite_desc()}</p>
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
            {m.onboarding_mode_complete_title()}
          </p>
          <p className="text-[11px] mt-1">
            {m.onboarding_mode_complete_desc()}
          </p>
        </button>
      </div>
      {saving && (
        <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
      )}
      {mode === "complete" && (
        <div className="space-y-2 pt-2 border-t max-h-64 overflow-y-auto pr-1">
          {SERVICE_FIELDS.map((cfg) =>
            preconfigured[cfg.service] ? (
              <div
                key={cfg.service}
                className="flex items-center justify-between gap-2 rounded border px-2.5 py-2"
              >
                <p className="text-xs font-medium">{cfg.title}</p>
                {preconfiguredTests[cfg.service] === undefined ? (
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    {m.onboarding_mode_testing()}
                  </span>
                ) : preconfiguredTests[cfg.service]?.ok ? (
                  <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {m.onboarding_mode_already_configured()}
                    {preconfiguredTests[cfg.service]?.latency_ms !==
                      undefined && (
                      <span className="text-muted-foreground">
                        ({preconfiguredTests[cfg.service]?.latency_ms}ms)
                      </span>
                    )}
                  </span>
                ) : null}
              </div>
            ) : (
              <ServiceConnectionCard
                key={cfg.service}
                config={cfg}
                onConnectedChange={handleConnectedChange}
              />
            ),
          )}
        </div>
      )}
      {mode === "complete" &&
        !SERVICE_FIELDS.every(
          (f) => preconfigured[f.service] || connected[f.service],
        ) && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            {m.onboarding_mode_validation_warning()}
          </p>
        )}
    </div>
  );
}

function StepWorkspace(_props: StepProps) {
  return (
    <div className="space-y-3 py-2 text-sm text-muted-foreground">
      <p>{m.onboarding_workspace_body()}</p>
      <ul className="list-disc list-inside space-y-1 text-xs">
        <li>{m.onboarding_workspace_bullet_1()}</li>
        <li>{m.onboarding_workspace_bullet_2()}</li>
        <li>{m.onboarding_workspace_bullet_3()}</li>
      </ul>
    </div>
  );
}

function StepRag(_props: StepProps) {
  return (
    <div className="space-y-3 py-2 text-sm text-muted-foreground">
      <p>{m.onboarding_rag_body()}</p>
    </div>
  );
}

function StepDone(_props: StepProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-4 text-center">
      <span className="text-4xl">🎉</span>
      <p className="text-sm text-muted-foreground max-w-xs">
        {m.onboarding_done_body()}
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
  const [step, setStep] = useState(0);
  const [valid, setValid] = useState(true);

  useEffect(() => {
    setValid(true);
  }, [step]);

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
          <DialogTitle>{mDyn(STEP_TITLE_KEYS[step]!)}</DialogTitle>
          <DialogDescription className="sr-only">
            {step + 1} / {TOTAL_STEPS}
          </DialogDescription>
        </DialogHeader>

        <StepContent onValidityChange={setValid} />

        <StepIndicator step={step} total={TOTAL_STEPS} />

        <DialogFooter className="flex-row items-center justify-between gap-2 sm:justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            disabled={isFirstStep}
            className={`text-xs ${isFirstStep ? "invisible" : ""}`}
          >
            {m.onboarding_back()}
          </Button>

          <div className="flex items-center gap-2">
            {!isLastStep && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSkip}
                className="text-xs"
              >
                {m.onboarding_skip()}
              </Button>
            )}
            <Button size="sm" onClick={handleNext} disabled={!valid} autoFocus>
              {isLastStep ? m.onboarding_finish() : m.onboarding_next()}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
