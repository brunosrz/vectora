import { m } from "#/paraglide/messages";
import { track } from "#/lib/analytics/plausible";

interface ShowcaseCardProps {
  gif: string;
  alt: string;
  title: string;
  desc: string;
  index: number;
}

function ShowcaseCard({ gif, alt, title, desc, index }: ShowcaseCardProps) {
  return (
    <div
      className="group overflow-hidden rounded-xl border border-brand-700 bg-brand-800/40 transition-all hover:border-brand-500 hover:shadow-lg hover:shadow-brand-500/10"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div
        className="overflow-hidden"
        style={{ aspectRatio: "16/10" }}
        onMouseEnter={() => track("gif_viewed", { gif })}
      >
        <img
          src={gif}
          alt={alt}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover gif-skeleton transition-transform duration-300 group-hover:scale-[1.02]"
          onLoad={(e) => (e.currentTarget.style.background = "none")}
        />
      </div>
      <div className="p-4">
        <p className="mb-1 font-semibold text-white">{title}</p>
        <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

export default function ShowcaseGifs() {
  const cards: ShowcaseCardProps[] = [
    {
      gif: "/gifs/showcase-chat.gif",
      alt: "Vectora contextual conversation",
      title: m.showcase_chat_title(),
      desc: m.showcase_chat_desc(),
      index: 0,
    },
    {
      gif: "/gifs/showcase-rag.gif",
      alt: "Vectora RAG semantic search",
      title: m.showcase_rag_title(),
      desc: m.showcase_rag_desc(),
      index: 1,
    },
    {
      gif: "/gifs/showcase-code.gif",
      alt: "Vectora coding agent",
      title: m.showcase_code_title(),
      desc: m.showcase_code_desc(),
      index: 2,
    },
    {
      gif: "/gifs/showcase-plan.gif",
      alt: "Vectora structured reasoning",
      title: m.showcase_plan_title(),
      desc: m.showcase_plan_desc(),
      index: 3,
    },
  ];

  return (
    <section className="px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className="mb-12 text-center text-3xl font-semibold text-white sm:text-4xl">
          {m.showcase_title()}
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {cards.map((card) => (
            <ShowcaseCard key={card.gif} {...card} />
          ))}
        </div>
      </div>
    </section>
  );
}
