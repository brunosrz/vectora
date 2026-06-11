import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "#/components/shared/Logo";

export default function Hero() {
  return (
    <section className="relative overflow-hidden px-4 pb-10 pt-12 sm:px-6 sm:pb-12 sm:pt-16 lg:px-8">
      {/* Background gradient mesh */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -20%, color-mix(in srgb, var(--primary) 16%, transparent) 0%, transparent 70%)",
        }}
      />

      <div className="mx-auto max-w-5xl text-center">
        {/* Logo + Vectora — a logo nunca aparece sem o texto ao lado */}
        <div className="mb-6 flex justify-center">
          <Logo size="lg" asLink={false} />
        </div>

        {/* Eyebrow */}
        <div className="mb-6 inline-flex max-w-full flex-wrap items-center justify-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-[11px] font-medium text-primary backdrop-blur sm:text-xs">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          {m.hero_eyebrow()}
        </div>

        {/* H1 */}
        <h1 className="mb-5 text-3xl font-semibold leading-tight tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          {m
            .hero_tagline()
            .split(". ")
            .map((part, i, arr) => (
              <span key={i}>
                {i === 0 ? (
                  <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                    {part}
                  </span>
                ) : (
                  part
                )}
                {i < arr.length - 1 ? ". " : ""}
              </span>
            ))}
        </h1>

        {/* Subtitle */}
        <p className="mx-auto mb-8 max-w-2xl text-base text-muted-foreground leading-relaxed">
          {m.hero_subtitle()}
        </p>

        {/* CTAs */}
        <div className="flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
          <Link
            to="/signup"
            className="w-full rounded-xl bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 hover:shadow-primary/30 active:scale-95 sm:w-auto"
          >
            {m.hero_cta_trial()}
          </Link>
          <Link
            to="/pricing"
            className="w-full rounded-xl border border-border bg-card/50 px-8 py-3 text-sm font-semibold text-foreground/90 transition-all hover:border-primary hover:text-foreground active:scale-95 sm:w-auto"
          >
            {m.hero_cta_pricing()}
          </Link>
        </div>

        {/* GIF hero */}
        <div className="mx-auto mt-10 max-w-[860px] sm:mt-12">
          <div
            className="overflow-hidden rounded-2xl border border-border glow-brand-lg"
            style={{ aspectRatio: "16/10" }}
          >
            <img
              src="/gifs/showcase-chat.gif"
              alt="Vectora AI agent in action"
              loading="lazy"
              decoding="async"
              className="h-full w-full object-cover gif-skeleton"
              onLoad={(e) => (e.currentTarget.style.background = "none")}
            />
            {/* Dev placeholder */}
            <noscript>
              <div className="flex h-full w-full items-center justify-center bg-card text-sm text-muted-foreground">
                [GIF showcase-chat — placeholder during dev]
              </div>
            </noscript>
          </div>
        </div>
      </div>
    </section>
  );
}
