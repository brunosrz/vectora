import { useState, useEffect, useMemo } from "react";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff } from "lucide-react";
import { z } from "zod";

import { useAuthStore } from "@/lib/stores/auth-store";
import { useT } from "@/lib/i18n";
import type { AuthUser } from "@/lib/types/auth";

/** Tamanho mínimo de senha — espelha a validação do backend. */
const PASSWORD_MIN = 8;
const NAME_MAX = 100;

const searchSchema = z.object({
  invite: z.string().optional(),
});

export const Route = createFileRoute("/auth/signup")({
  validateSearch: searchSchema,
  component: SignUpPage,
});

function SignUpPage() {
  const navigate = useNavigate();
  const t = useT();
  const { invite: inviteFromUrl } = Route.useSearch();
  const setUser = useAuthStore((s) => s.setUser);

  const schema = useMemo(
    () =>
      z
        .object({
          name: z
            .string()
            .trim()
            .min(1, t("auth.signup.name_required"))
            .max(NAME_MAX, t("auth.signup.name_too_long", { n: NAME_MAX })),
          email: z.string().email(t("auth.email_invalid")),
          password: z
            .string()
            .min(
              PASSWORD_MIN,
              t("auth.signup.password_min", { n: PASSWORD_MIN }),
            ),
          confirm: z.string(),
        })
        .refine((d) => d.password === d.confirm, {
          message: t("auth.signup.passwords_mismatch"),
          path: ["confirm"],
        }),
    [t],
  );

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [inviteToken, setInviteToken] = useState("");
  const [inviteRole, setInviteRole] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function resolve() {
      let hasUsers = true;
      try {
        const r = await fetch("/auth/has-users", { credentials: "include" });
        hasUsers = Boolean((await r.json()).exists);
      } catch {
        hasUsers = true;
      }
      if (cancelled) return;

      if (!hasUsers) {
        setReady(true);
        return;
      }

      const token = inviteFromUrl ?? "";
      if (token) {
        try {
          const r = await fetch(`/auth/invite/${token}`, {
            credentials: "include",
          });
          const data = await r.json();
          if (!cancelled && data.valid) {
            setInviteToken(token);
            setInviteRole(data.role ?? "member");
            if (data.email) setEmail(data.email);
            setReady(true);
            return;
          }
        } catch {
          // cai no redirect abaixo
        }
      }

      if (!cancelled) {
        void navigate({ to: "/auth/signin" });
      }
    }

    void resolve();
    return () => {
      cancelled = true;
    };
  }, [navigate, inviteFromUrl]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);
    setErrors({});

    const result = schema.safeParse({ name, email, password, confirm });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      for (const err of result.error.issues) {
        const field = err.path[0]?.toString() ?? "form";
        fieldErrors[field] = err.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/auth/signup", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email,
          password,
          invite_token: inviteToken,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setServerError(data.detail ?? t("auth.signup.create_error"));
        return;
      }

      setUser(data.user as AuthUser);
      void navigate({ to: "/" });
    } catch {
      setServerError(t("auth.conn_error"));
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">{t("auth.loading")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
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
          <div className="text-center">
            {inviteRole ? (
              <>
                <p className="text-sm text-muted-foreground">
                  {t("auth.signup.invite_title")}
                </p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {t("auth.signup.invite_role")}{" "}
                  <span className="text-primary font-medium">{inviteRole}</span>
                </p>
              </>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">
                  {t("auth.signup.first_access")}
                </p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  {t("auth.signup.root_hint")
                    .split("{root}")
                    .flatMap((part, i) =>
                      i === 0
                        ? [part]
                        : [
                            <span
                              key="root"
                              className="text-yellow-400 font-medium"
                            >
                              root
                            </span>,
                            part,
                          ],
                    )}
                </p>
              </>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="name"
            >
              {t("auth.signup.name")}
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={NAME_MAX}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              placeholder={t("auth.signup.name_ph")}
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>

          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="email"
            >
              {t("auth.email")}
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              placeholder={t("auth.email_ph")}
            />
            {errors.email && (
              <p className="text-xs text-destructive">{errors.email}</p>
            )}
          </div>

          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="password"
            >
              {t("auth.password")}
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                placeholder={t("auth.signup.password_ph", { n: PASSWORD_MIN })}
              />
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onTouchEnd={(e) => {
                  e.preventDefault();
                  setShowPassword((v) => !v);
                }}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center justify-center w-11 min-h-[44px] text-muted-foreground hover:text-foreground transition-colors touch-manipulation"
                aria-label={
                  showPassword
                    ? t("auth.hide_password")
                    : t("auth.show_password")
                }
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password}</p>
            )}
          </div>

          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="confirm"
            >
              {t("auth.signup.confirm")}
            </label>
            <div className="relative">
              <input
                id="confirm"
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                placeholder={t("auth.signup.confirm_ph")}
              />
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onTouchEnd={(e) => {
                  e.preventDefault();
                  setShowConfirm((v) => !v);
                }}
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center justify-center w-11 min-h-[44px] text-muted-foreground hover:text-foreground transition-colors touch-manipulation"
                aria-label={
                  showConfirm
                    ? t("auth.signup.hide_confirm")
                    : t("auth.signup.show_confirm")
                }
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.confirm && (
              <p className="text-xs text-destructive">{errors.confirm}</p>
            )}
          </div>

          {serverError && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
          >
            {loading ? t("auth.signup.submitting") : t("auth.signup.submit")}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          {t("auth.signup.have_account")}{" "}
          <Link to={"/auth/signin"} className="text-primary hover:underline">
            {t("auth.signup.signin_link")}
          </Link>
        </p>
      </div>
    </div>
  );
}
