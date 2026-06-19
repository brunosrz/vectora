/**
 * DashboardHeading — título (e subtítulo) padrão das páginas do dashboard.
 *
 * Título `text-2xl font-semibold`, mantendo a área compacta do painel.
 * Fonte única para todas as páginas internas ficarem consistentes.
 */

interface DashboardHeadingProps {
  title: string
  subtitle?: string
}

export default function DashboardHeading({
  title,
  subtitle,
}: DashboardHeadingProps) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold text-foreground">{title}</h1>
      {subtitle && (
        <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
      )}
    </div>
  )
}
