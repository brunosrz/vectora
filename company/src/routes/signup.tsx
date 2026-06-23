import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { m } from "#/paraglide/messages";
import AuthLayout from "#/components/shared/AuthLayout";
import Turnstile from "#/components/shared/Turnstile";
import { getSession, signUp } from "#/server/fns/auth";
import { track } from "#/lib/analytics/plausible";
import { toast } from "sonner";

const SearchSchema = z.object({ plan: z.enum(["plus", "pro"]).optional() });

export const Route = createFileRoute("/signup")({
  validateSearch: SearchSchema,
  beforeLoad: async () => {
    const user = await getSession();
    if (user) throw { redirect: { to: "/dashboard" } };
  },
  head: () => ({ meta: [{ title: m.page_signup_title() }] }),
  component: SignupPage,
});

const AUTH_ERROR_MAP: Partial<Record<string, () => string>> = {
  "User already registered": m.error_email_taken,
  "Password should be at least 6 characters": m.error_password_weak,
};

function SignupPage() {
  const navigate = useNavigate();
  const { plan } = Route.useSearch();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [country, setCountry] = useState<"BR" | "INTL">("BR");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      signUp({
        data: {
          name,
          email,
          password,
          country,
          turnstileToken: turnstileToken!,
        },
      }),
    onSuccess: (res) => {
      track("signup", { plan: plan ?? "plus" });
      navigate({ to: res.redirect as "/dashboard" });
    },
    onError: (err: Error) => {
      const msgFn = AUTH_ERROR_MAP[err.message];
      toast.error(msgFn ? msgFn() : m.error_generic());
    },
  });

  const canSubmit =
    name.length >= 2 &&
    email.includes("@") &&
    password.length >= 8 &&
    turnstileToken !== null &&
    !mutation.isPending;

  return (
    <AuthLayout
      heading={m.signup_heading()}
      subheading={
        plan && (
          <p className="mt-1 text-sm text-primary">
            Plano {plan === "pro" ? "Pro" : "Plus"} selecionado
          </p>
        )
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) mutation.mutate();
        }}
        className="space-y-4"
      >
        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground/90">
            {m.form_name()}
          </label>
          <input
            type="text"
            required
            minLength={2}
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground/90">
            {m.form_email()}
          </label>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground/90">
            {m.form_password()}
          </label>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground/90">
            {m.form_country()}
          </label>
          <div className="flex gap-2">
            {(["BR", "INTL"] as const).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCountry(c)}
                className={`flex-1 rounded-xl border py-2.5 text-sm font-medium transition-all ${
                  country === c
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground/90"
                }`}
              >
                {c === "BR" ? "🇧🇷 Brasil" : "🌍 Internacional"}
              </button>
            ))}
          </div>
        </div>

        <Turnstile onSuccess={setTurnstileToken} />

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 transition-all hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? m.form_submitting() : m.signup_cta()}
        </button>
      </form>

      <div className="mt-6 flex justify-between text-sm text-muted-foreground">
        <Link
          to="/login"
          className="hover:text-foreground/90 transition-colors"
        >
          {m.signup_have_account()}
        </Link>
        <Link
          to="/pricing"
          className="hover:text-foreground/90 transition-colors"
        >
          {m.signup_see_pricing()}
        </Link>
      </div>
    </AuthLayout>
  );
}
