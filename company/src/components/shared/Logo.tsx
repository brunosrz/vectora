import { Link } from '@tanstack/react-router'

/**
 * Logo — pássaro Vectora + texto "Vectora" ao lado.
 *
 * Regra de marca: a logo NUNCA é exibida sozinha — o texto "Vectora"
 * sempre acompanha o símbolo. Use este componente em vez de <img> direto.
 */
interface LogoProps {
  size?: 'sm' | 'md' | 'lg'
  /** Quando false, renderiza sem <Link> (ex: dentro de outro link). */
  asLink?: boolean
  className?: string
}

const SIZES = {
  sm: { img: 'h-6 w-6', text: 'text-base' },
  md: { img: 'h-7 w-7', text: 'text-lg' },
  lg: { img: 'h-10 w-10', text: 'text-2xl' },
} as const

export default function Logo({
  size = 'md',
  asLink = true,
  className = '',
}: LogoProps) {
  const s = SIZES[size]
  const content = (
    <>
      <img src="/vectora.svg" alt="" className={`${s.img} w-auto`} />
      <span
        className={`${s.text} font-semibold tracking-tight text-foreground`}
      >
        Vectora
      </span>
    </>
  )

  if (!asLink) {
    return (
      <span className={`flex items-center gap-2 ${className}`}>{content}</span>
    )
  }
  return (
    <Link
      to="/"
      aria-label="Vectora"
      className={`flex items-center gap-2 ${className}`}
    >
      {content}
    </Link>
  )
}
