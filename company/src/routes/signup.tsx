import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { m } from "#/paraglide/messages";
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
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Link to="/" className="text-xl font-bold text-white">
            Vectora
          </Link>
          <h1 className="mt-4 text-2xl font-semibold text-white">
            {m.signup_heading()}
          </h1>
          {plan && (
            <p className="mt-1 text-sm text-brand-400">
              Plano {plan === "pro" ? "Pro" : "Plus"} selecionado
            </p>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) mutation.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_name()}
            </label>
            <input
              type="text"
              required
              minLength={2}
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_email()}
            </label>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              {m.form_password()}
            </label>
            <input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
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
                      ? "border-brand-500 bg-brand-500/10 text-brand-300"
                      : "border-brand-700 text-slate-500 hover:text-slate-300"
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
            className="w-full rounded-xl bg-brand-500 py-3 text-sm font-semibold text-white shadow shadow-brand-500/25 transition-all hover:bg-brand-400 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? m.form_submitting() : m.signup_cta()}
          </button>
        </form>

        <div className="mt-6 flex justify-between text-sm text-slate-500">
          <Link to="/login" className="hover:text-slate-300 transition-colors">
            {m.signup_have_account()}
          </Link>
          <Link
            to="/pricing"
            className="hover:text-slate-300 transition-colors"
          >
            {m.signup_see_pricing()}
          </Link>
        </div>
      </div>
    </div>
  );
}
