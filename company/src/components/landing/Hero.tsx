import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";

export default function Hero() {
  return (
    <section className="relative overflow-hidden px-4 pb-20 pt-24 sm:px-6 lg:px-8">
      {/* Background gradient mesh */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -20%, rgba(59,130,246,0.18) 0%, transparent 70%)",
        }}
      />

      <div className="mx-auto max-w-5xl text-center">
        {/* Eyebrow */}
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-brand-700 bg-brand-800/60 px-4 py-1.5 text-xs font-medium text-brand-300 backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
          {m.hero_eyebrow()}
        </div>

        {/* H1 */}
        <h1 className="mb-6 text-5xl font-semibold leading-tight tracking-tight text-white sm:text-6xl lg:text-7xl">
          {m
            .hero_tagline()
            .split(". ")
            .map((part, i, arr) => (
              <span key={i}>
                {i === 0 ? (
                  <span className="bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
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
        <p className="mx-auto mb-10 max-w-2xl text-lg text-slate-400 leading-relaxed">
          {m.hero_subtitle()}
        </p>

        {/* CTAs */}
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            to="/signup"
            className="rounded-xl bg-brand-500 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-500/25 transition-all hover:bg-brand-400 hover:shadow-brand-400/30 active:scale-95"
          >
            {m.hero_cta_trial()}
          </Link>
          <Link
            to="/pricing"
            className="rounded-xl border border-brand-700 bg-brand-800/50 px-8 py-3.5 text-sm font-semibold text-slate-300 transition-all hover:border-brand-500 hover:text-white active:scale-95"
          >
            {m.hero_cta_pricing()}
          </Link>
        </div>

        {/* GIF hero */}
        <div className="mx-auto mt-16 max-w-[860px]">
          <div
            className="overflow-hidden rounded-2xl border border-brand-700 glow-brand-lg"
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
              <div className="flex h-full w-full items-center justify-center bg-brand-800 text-sm text-slate-500">
                [GIF showcase-chat — placeholder during dev]
              </div>
            </noscript>
          </div>
        </div>
      </div>
    </section>
  );
}
