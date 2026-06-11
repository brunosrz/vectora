"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import Turnstile from "#/components/shared/Turnstile";
import { joinWaitlist } from "#/server/fns/issues";
import { track } from "#/lib/analytics/plausible";

export default function WaitlistCta() {
  const [email, setEmail] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [duplicate, setDuplicate] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      joinWaitlist({
        data: { email, turnstileToken: turnstileToken!, source: "landing-cta" },
      }),
    onSuccess: () => {
      track("waitlist_join", { source: "landing-cta" });
      setDone(true);
    },
    onError: (err: Error) => {
      if (
        err.message.includes("duplicate") ||
        err.message.includes("already")
      ) {
        setDuplicate(true);
      }
    },
  });

  const canSubmit =
    email.length > 0 && turnstileToken !== null && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setDuplicate(false);
    mutation.mutate();
  };

  const isVisible = import.meta.env.VITE_LAUNCH_MODE === "waitlist";
  if (!isVisible) return null;

  return (
    <section className="px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        {/* Gradient background blob */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 opacity-20"
          style={{
            background:
              "radial-gradient(ellipse 60% 40% at 50% 50%, color-mix(in srgb, var(--primary) 35%, transparent) 0%, transparent 70%)",
          }}
        />

        <h2 className="mb-3 text-2xl font-semibold text-foreground sm:text-3xl">
          {m.waitlist_heading()}
        </h2>
        <p className="mb-8 text-muted-foreground">{m.waitlist_subtitle()}</p>

        {done ? (
          <div className="rounded-xl border border-accent-green/30 bg-accent-green/10 px-6 py-5 text-green-300">
            ✓ {m.waitlist_success()}
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col items-center gap-4"
          >
            <div className="w-full max-w-md">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={m.waitlist_email_placeholder()}
                className="w-full rounded-xl border border-border bg-card/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
              />
            </div>

            <Turnstile onSuccess={setTurnstileToken} />

            {duplicate && (
              <p className="text-sm text-accent-amber">
                {m.waitlist_duplicate()}
              </p>
            )}
            {mutation.isError && !duplicate && (
              <p className="text-sm text-accent-red">{m.error_generic()}</p>
            )}

            <button
              type="submit"
              disabled={!canSubmit}
              className="rounded-xl bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {mutation.isPending ? m.form_submitting() : m.waitlist_cta()}
            </button>

            <p className="text-xs text-muted-foreground">
              {m.waitlist_no_spam()}
            </p>
          </form>
        )}
      </div>
    </section>
  );
}
