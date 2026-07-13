"use client";

/**
 * PreAuthWizard — primeiro acesso, antes de qualquer conta existir.
 *
 * Substitui o antigo redirect direto pra /auth/signup. Pergunta nome
 * (+ empresa opcional) e o modo de operação:
 *
 * - Local: chama POST /auth/setup-local (persiste VECTORA_AUTH_REQUIRED=false
 *   + nome/empresa) e recarrega a raiz — a partir daí o guard de rota vê
 *   auth_required=false e libera direto pro app, sem nenhuma conta real.
 * - VPS: recurso Pro — pede um VECTORA_TOKEN, valida via
 *   POST /license/validate-token (só funciona no primeiro acesso, mesma
 *   guarda do setup-local) e, se válido e tier=pro, segue pro /auth/signup
 *   de verdade (conta real, multi-usuário) com o nome pré-preenchido.
 */

import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Loader2,
  Check,
  Monitor,
  Server,
  Moon,
  Sun,
  Laptop,
} from "lucide-react";
import { m } from "@/lib/paraglide/messages";
import { signalVpsGatePassed } from "@/lib/stores/onboarding-signal";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useSettingsStore,
  SUPPORTED_LANGS,
  type Lang,
  type Theme,
} from "@/lib/stores/settings-store";

type Step = "identity" | "mode" | "vps-token";

const VPS_FEATURE_LABELS = [
  m.onboarding_pre_vps_feature_1,
  m.onboarding_pre_vps_feature_2,
  m.onboarding_pre_vps_feature_3,
  m.onboarding_pre_vps_feature_4,
  m.onboarding_pre_vps_feature_5,
];

function openExternal(url: string): void {
  if (typeof window !== "undefined" && window.vectora?.openExternal) {
    void window.vectora.openExternal(url);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

const THEME_OPTIONS: {
  value: Theme;
  label: () => string;
  icon: typeof Laptop;
}[] = [
  { value: "system", label: m.onboarding_pre_theme_system, icon: Laptop },
  { value: "dark", label: m.onboarding_pre_theme_dark, icon: Moon },
  { value: "light", label: m.onboarding_pre_theme_light, icon: Sun },
];

export function PreAuthWizard() {
  const navigate = useNavigate();
  const language = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);
  const theme = useSettingsStore((s) => s.theme);
  const setTheme = useSettingsStore((s) => s.setTheme);
  const [step, setStep] = useState<Step>("identity");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [settingUpLocal, setSettingUpLocal] = useState(false);

  function handleIdentityNext() {
    if (!name.trim()) {
      setNameError(m.onboarding_pre_name_required());
      return;
    }
    setNameError(null);
    setStep("mode");
  }

  async function handleSelectLocal() {
    setSettingUpLocal(true);
    setNameError(null);
    try {
      const res = await fetch("/auth/setup-local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), company: company.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setNameError(
          (data as { detail?: string }).detail ??
            m.onboarding_pre_setup_error(),
        );
        setSettingUpLocal(false);
        return;
      }
      // Full reload: o guard de __root.tsx precisa reavaliar auth_required
      // do zero (o valor já foi lido em memória antes do setup rodar).
      window.location.href = "/";
    } catch {
      setNameError(m.onboarding_pre_setup_error());
      setSettingUpLocal(false);
    }
  }

  async function handleValidateVpsToken() {
    const value = token.trim();
    if (!value) return;
    setValidating(true);
    setTokenError(null);
    try {
      const res = await fetch("/license/validate-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: value }),
      });
      const data = (await res.json()) as { valid: boolean; error?: string };
      if (!data.valid) {
        setTokenError(
          data.error === "not_pro_tier"
            ? m.onboarding_pre_vps_token_invalid()
            : (data.error ?? m.onboarding_pre_vps_token_invalid()),
        );
        return;
      }
      signalVpsGatePassed();
      void navigate({
        to: "/auth/signup",
        search: { name: name.trim() },
      });
    } catch {
      setTokenError(m.onboarding_pre_vps_token_invalid());
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2.5">
            <img src="/vectora.svg" alt="Vectora" width={36} height={36} />
            <h1
              className="text-2xl font-semibold tracking-tight text-foreground"
              style={{ fontFamily: "var(--font-aeonik-mono)" }}
            >
              Vectora
            </h1>
          </div>
        </div>

        {step === "identity" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              {m.onboarding_pre_identity_title()}
            </p>
            <div className="space-y-1">
              <label
                className="text-sm font-medium text-foreground"
                htmlFor="pre-name"
              >
                {m.onboarding_pre_name_label()}
              </label>
              <input
                id="pre-name"
                type="text"
                autoComplete="name"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={m.onboarding_pre_name_ph()}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              />
              {nameError && (
                <p className="text-xs text-destructive">{nameError}</p>
              )}
            </div>
            <div className="space-y-1">
              <label
                className="text-sm font-medium text-foreground"
                htmlFor="pre-company"
              >
                {m.onboarding_pre_company_label()}
              </label>
              <input
                id="pre-company"
                type="text"
                autoComplete="organization"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder={m.onboarding_pre_company_ph()}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-foreground">
                  {m.onboarding_pre_language_label()}
                </label>
                <Select
                  value={language}
                  onValueChange={(v) => setLanguage(v as Lang)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue>
                      {SUPPORTED_LANGS.find((l) => l.value === language)
                        ?.label ?? language}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {SUPPORTED_LANGS.map(({ value, label }) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-foreground">
                  {m.onboarding_pre_theme_label()}
                </label>
                <div className="flex rounded-md border border-border overflow-hidden">
                  {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setTheme(value)}
                      title={label()}
                      aria-label={label()}
                      aria-pressed={theme === value}
                      className={`flex-1 flex items-center justify-center py-2 transition-colors ${
                        theme === value
                          ? "bg-primary/15 text-primary"
                          : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={handleIdentityNext}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {m.onboarding_next()}
            </button>
          </div>
        )}

        {step === "mode" && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              {m.onboarding_pre_mode_body()}
            </p>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => void handleSelectLocal()}
                disabled={settingUpLocal}
                className="flex items-start gap-3 text-left p-3 rounded-md border border-border hover:bg-muted/50 transition-colors disabled:opacity-60"
              >
                {settingUpLocal ? (
                  <Loader2 className="w-4 h-4 mt-0.5 shrink-0 animate-spin text-muted-foreground" />
                ) : (
                  <Monitor className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
                )}
                <span>
                  <span className="block text-sm font-medium text-foreground">
                    {m.onboarding_pre_mode_local_title()}
                  </span>
                  <span className="block text-xs text-muted-foreground mt-0.5">
                    {m.onboarding_pre_mode_local_desc()}
                  </span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => setStep("vps-token")}
                className="flex items-start gap-3 text-left p-3 rounded-md border border-border hover:bg-muted/50 transition-colors"
              >
                <Server className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
                <span>
                  <span className="block text-sm font-medium text-foreground">
                    {m.onboarding_pre_mode_vps_title()}
                  </span>
                  <span className="block text-xs text-muted-foreground mt-0.5">
                    {m.onboarding_pre_mode_vps_desc()}
                  </span>
                </span>
              </button>
            </div>
            {nameError && (
              <p className="text-xs text-destructive text-center">
                {nameError}
              </p>
            )}
            <button
              type="button"
              onClick={() => setStep("identity")}
              className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {m.onboarding_back()}
            </button>
          </div>
        )}

        {step === "vps-token" && (
          <div className="space-y-4">
            <p className="text-sm font-medium text-foreground text-center">
              {m.onboarding_pre_vps_title()}
            </p>
            <p className="text-sm text-muted-foreground">
              {m.onboarding_pre_vps_body()}
            </p>
            <div className="rounded-md border border-border/60 p-3 space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                {m.onboarding_pre_vps_features_title()}
              </p>
              <ul className="space-y-1">
                {VPS_FEATURE_LABELS.map((label, idx) => (
                  <li
                    key={idx}
                    className="flex items-center gap-1.5 text-xs text-foreground"
                  >
                    <Check className="w-3.5 h-3.5 shrink-0 text-primary" />
                    {label()}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-1">
              <label
                className="text-sm font-medium text-foreground"
                htmlFor="pre-vps-token"
              >
                {m.onboarding_pre_vps_token_label()}
              </label>
              <input
                id="pre-vps-token"
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={m.onboarding_pre_vps_token_ph()}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              />
              {tokenError && (
                <p className="text-xs text-destructive">{tokenError}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => void handleValidateVpsToken()}
              disabled={validating || !token.trim()}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors flex items-center justify-center gap-1.5"
            >
              {validating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {validating
                ? m.onboarding_pre_vps_validating()
                : m.onboarding_pre_vps_continue()}
            </button>
            <p className="text-center text-xs text-muted-foreground">
              {m.onboarding_pre_vps_subscribe_hint()}{" "}
              <button
                type="button"
                onClick={() => openExternal("https://vectora.company/")}
                className="text-primary hover:underline"
              >
                {m.onboarding_pre_vps_subscribe_cta()}
              </button>
            </p>
            <button
              type="button"
              onClick={() => setStep("mode")}
              className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {m.onboarding_back()}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
