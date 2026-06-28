import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { m } from "#/paraglide/messages";
import Logo from "#/components/shared/Logo";
import { getSession } from "#/server/fns/auth";
import { authorizeDevice } from "#/server/fns/oauth";

const SearchSchema = z.object({ state: z.string().min(1) });

export const Route = createFileRoute("/auth/device")({
  validateSearch: SearchSchema,
  head: () => ({ meta: [{ title: m.auth_device_title() }] }),
  component: DevicePage,
});

function DevicePage() {
  const { state } = Route.useSearch();
  const navigate = useNavigate();
  const [user, setUser] = useState<{ email?: string } | null | undefined>(
    undefined,
  );

  useEffect(() => {
    getSession()
      .then((u) => setUser(u))
      .catch(() => setUser(null));
  }, []);

  const mutation = useMutation({
    mutationFn: () => authorizeDevice({ data: { state } }),
  });

  if (user === undefined) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    void navigate({
      to: "/login",
      search: { redirect: `/auth/device?state=${encodeURIComponent(state)}` },
    });
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Logo size="md" />

      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-lg">
        {mutation.isSuccess ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500" />
            <h1 className="text-xl font-semibold">
              {m.auth_device_success_title()}
            </h1>
            <p className="text-sm text-muted-foreground">
              {m.auth_device_success_desc()}
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6 text-center">
            <ShieldCheck className="h-10 w-10 text-primary" />
            <div>
              <h1 className="text-xl font-semibold">{m.auth_device_title()}</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {m.auth_device_desc()}
              </p>
            </div>

            <p className="rounded-xl border border-border bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
              {user.email}
            </p>

            {mutation.isError && (
              <p className="text-sm text-destructive">
                {(mutation.error as Error).message === "no_token"
                  ? m.auth_device_no_token()
                  : m.auth_device_error()}
              </p>
            )}

            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : null}
              {m.auth_device_btn()}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
