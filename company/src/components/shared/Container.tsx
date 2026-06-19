/**
 * Container — frame horizontal canônico da company, alinhado à home (Figma).
 *
 * - `default`: largura de conteúdo da landing (max-w-[1024px]).
 * - `prose`: largura de leitura confortável para texto longo (legal, FAQ).
 *
 * Padding lateral padrão `px-4 sm:px-6` (mesmo ritmo da home). Use em toda
 * página para manter espaçamento e largura consistentes.
 */

interface ContainerProps {
  children: React.ReactNode
  size?: 'default' | 'prose'
  className?: string
}

export default function Container({
  children,
  size = 'default',
  className = '',
}: ContainerProps) {
  const maxWidth = size === 'prose' ? 'max-w-[720px]' : 'max-w-[1024px]'
  return (
    <div className={`mx-auto w-full ${maxWidth} px-4 sm:px-6 ${className}`}>
      {children}
    </div>
  )
}
