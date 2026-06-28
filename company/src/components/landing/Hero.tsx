import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "#/components/shared/Logo";

/** Três bullets do eyebrow — textos vindos das mensagens i18n */
function Eyebrow() {
  return (
    <div className="inline-flex max-w-full flex-wrap items-center justify-center gap-x-4 gap-y-1.5 rounded-3xl border border-border bg-card/60 px-4 py-2 backdrop-blur sm:flex-nowrap sm:gap-7 sm:rounded-full sm:px-[17px] sm:py-1.5">
      {m
        .hero_eyebrow()
        .split(" · ")
        .map((text) => (
          <span key={text} className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
            <span className="whitespace-nowrap text-[12px] font-medium text-primary">
              {text}
            </span>
          </span>
        ))}
    </div>
  );
}

export default function Hero() {
  return (
    <section className="flex flex-col items-center px-4 py-[23px] sm:px-8">
      {/* Container interno — max 1024 px conforme Figma */}
      <div className="flex w-full max-w-[1024px] flex-col items-center gap-6">
        {/* Logo maior no hero (40 px) */}
        <Logo size="lg" asLink={false} />

        {/* Eyebrow */}
        <Eyebrow />

        {/* H1 — gradiente azul */}
        <h1
          className="text-center text-4xl font-semibold leading-[1.25] tracking-[-1.2px] sm:text-5xl lg:text-[48px]"
          style={{
            background:
              "linear-gradient(90deg, #79B8FF 0%, rgba(121,184,255,0.7) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          {m.hero_tagline()}
        </h1>

        {/* Subtítulo */}
        <p className="max-w-[672px] text-center text-base leading-[26px] text-muted-foreground">
          {m.hero_subtitle()}
        </p>

        {/* CTAs */}
        <div className="flex flex-col items-center gap-4 sm:flex-row">
          <Link
            to="/signup"
            className="flex h-[42px] items-center justify-center rounded-2xl bg-primary px-8 text-sm font-semibold text-primary-foreground shadow-[0px_10px_15px_-3px_rgba(121,184,255,0.25),0px_4px_6px_-4px_rgba(121,184,255,0.25)] transition-colors hover:bg-primary/90 sm:w-auto"
          >
            {m.hero_cta_trial()}
          </Link>
          <Link
            to="/"
            hash="pricing"
            className="flex h-[44px] items-center justify-center rounded-2xl border border-border bg-card/50 px-8 text-sm font-semibold text-foreground/90 transition-colors hover:border-primary hover:text-foreground sm:w-auto"
          >
            {m.hero_cta_pricing()}
          </Link>
        </div>

        {/* Imagem hero — borda azul + shadow azul + rounded-3xl */}
        <div className="w-full pt-5">
          <div
            className="overflow-hidden rounded-3xl border border-primary"
            style={{
              aspectRatio: "1023 / 358.67",
              boxShadow:
                "0px 10px 15px -3px rgba(121,184,255,0.25), 0px 4px 6px -4px rgba(121,184,255,0.25)",
            }}
          >
            <img
              src="/gifs/showcase-chat.gif"
              alt={m.hero_gif_alt()}
              loading="lazy"
              decoding="async"
              className="h-full w-full object-cover gif-skeleton"
              onLoad={(e) => (e.currentTarget.style.background = "none")}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
