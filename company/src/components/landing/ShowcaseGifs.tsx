import { m } from '#/paraglide/messages'
import { track } from '#/lib/analytics/plausible'

interface ShowcaseCardProps {
  gif: string
  alt: string
  title: string
  desc: string
}

function ShowcaseCard({ gif, alt, title, desc }: ShowcaseCardProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card/40">
      <div
        style={{ aspectRatio: '496 / 232' }}
        onMouseEnter={() => track('gif_viewed', { gif })}
      >
        <img
          src={gif}
          alt={alt}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover gif-skeleton"
          onLoad={(e) => (e.currentTarget.style.background = 'none')}
        />
      </div>
      <div className="p-4">
        <p className="text-base font-semibold leading-6 text-foreground">
          {title}
        </p>
        <p className="text-[14px] leading-[23px] text-muted-foreground">
          {desc}
        </p>
      </div>
    </div>
  )
}

export default function ShowcaseGifs() {
  const cards: ShowcaseCardProps[] = [
    {
      gif: '/gifs/showcase-chat.gif',
      alt: m.showcase_chat_alt(),
      title: m.showcase_chat_title(),
      desc: m.showcase_chat_desc(),
    },
    {
      gif: '/gifs/showcase-rag.gif',
      alt: m.showcase_rag_alt(),
      title: m.showcase_rag_title(),
      desc: m.showcase_rag_desc(),
    },
    {
      gif: '/gifs/showcase-code.gif',
      alt: m.showcase_code_alt(),
      title: m.showcase_code_title(),
      desc: m.showcase_code_desc(),
    },
    {
      gif: '/gifs/showcase-plan.gif',
      alt: m.showcase_plan_alt(),
      title: m.showcase_plan_title(),
      desc: m.showcase_plan_desc(),
    },
  ]

  return (
    <section className="bg-background/50 py-[23px]">
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-8 px-4 sm:px-6 lg:px-0">
        <h2 className="text-[28px] font-semibold leading-[36px] text-foreground">
          {m.showcase_title()}
        </h2>
        <div className="grid w-full grid-cols-1 gap-8 sm:grid-cols-2">
          {cards.map((card) => (
            <ShowcaseCard key={card.gif} {...card} />
          ))}
        </div>
      </div>
    </section>
  )
}
