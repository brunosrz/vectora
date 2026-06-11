import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { m } from "#/paraglide/messages";
import Logo from "#/components/shared/Logo";
import { getSession, signIn, sendMagicLink } from "#/server/fns/auth";
import { toast } from "sonner";

const SearchSchema = z.object({ redirect: z.string().optional() });

export const Route = createFileRoute("/login")({
  validateSearch: SearchSchema,
  beforeLoad: async () => {
    const user = await getSession();
    if (user) throw { redirect: { to: "/dashboard" } };
  },
  head: () => ({ meta: [{ title: m.page_login_title() }] }),
  component: LoginPage,
});

const AUTH_ERROR_MAP: Partial<Record<string, () => string>> = {
  "Invalid login credentials": m.error_invalid_credentials,
  "Email not confirmed": m.error_email_not_confirmed,
};

function LoginPage() {
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const loginMutation = useMutation({
    mutationFn: () => signIn({ data: { email, password } }),
    onSuccess: () =>
      navigate({ to: (redirect ?? "/dashboard") as "/dashboard" }),
    onError: (err: Error) => {
      const msgFn = AUTH_ERROR_MAP[err.message];
      toast.error(msgFn ? msgFn() : m.error_generic());
    },
  });

  const magicLinkMutation = useMutation({
    mutationFn: () => sendMagicLink({ data: { email } }),
    onSuccess: () => toast.success(m.login_magic_sent()),
    onError: () => toast.error(m.error_generic()),
  });

  const canSubmit =
    email.includes("@") && password.length >= 1 && !loginMutation.isPending;

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Logo size="md" className="justify-center" />
          <h1 className="mt-4 text-2xl font-semibold text-foreground">
            {m.login_heading()}
          </h1>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) loginMutation.mutate();
          }}
          className="space-y-4"
        >
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
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-sm font-medium text-foreground/90">
                {m.form_password()}
              </label>
              <button
                type="button"
                disabled={!email.includes("@") || magicLinkMutation.isPending}
                onClick={() => magicLinkMutation.mutate()}
                className="text-xs text-primary hover:text-primary transition-colors disabled:opacity-40"
              >
                {m.login_forgot()}
              </button>
            </div>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 transition-all hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loginMutation.isPending ? m.form_submitting() : m.login_cta()}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link
            to="/signup"
            className="text-primary hover:text-primary transition-colors"
          >
            {m.login_no_account()}
          </Link>
        </p>
      </div>
    </div>
  );
}
