import { Link } from '@tanstack/react-router'
import { m } from '#/paraglide/messages'
import Logo from './Logo'

export default function Footer() {
  const year = new Date().getFullYear()

  const linkClass = 'transition-colors hover:text-foreground'

  return (
    <footer className="bg-muted">
      {/* Top: 3 colunas iguais, links empilhados, gap uniforme. Mobile-first:
          2 colunas no estreito, 3 a partir de sm. */}
      <div className="mx-auto grid max-w-[1024px] grid-cols-2 gap-x-8 gap-y-10 px-4 pb-8 pt-10 sm:grid-cols-3 sm:px-6">
        {/* Produto */}
        <div className="flex flex-col gap-2.5">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_product()}
          </p>
          <div className="flex flex-col gap-2.5 text-[14px] text-muted-foreground">
            <Link to="/pricing" className={linkClass}>
              {m.nav_pricing()}
            </Link>
            <a
              href="https://docs.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
            >
              {m.footer_docs()}
            </a>
            <Link to="/faq" className={linkClass}>
              {m.footer_faq()}
            </Link>
            <Link to="/roadmap" className={linkClass}>
              {m.footer_roadmap()}
            </Link>
            <a
              href="https://status.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
            >
              {m.footer_status()}
            </a>
          </div>
        </div>

        {/* Suporte */}
        <div className="flex flex-col gap-2.5">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_support()}
          </p>
          <div className="flex flex-col gap-2.5 text-[14px] text-muted-foreground">
            <Link to="/support" className={linkClass}>
              {m.nav_support()}
            </Link>
            <Link to="/issues" className={linkClass}>
              Issues
            </Link>
            <a
              href="https://github.com/vectora-company"
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
            >
              GitHub
            </a>
          </div>
        </div>

        {/* Legal */}
        <div className="flex flex-col gap-2.5">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_legal()}
          </p>
          <div className="flex flex-col gap-2.5 text-[14px] text-muted-foreground">
            <Link to="/privacy" className={linkClass}>
              {m.footer_privacy()}
            </Link>
            <Link to="/terms" className={linkClass}>
              {m.footer_terms()}
            </Link>
            <Link to="/cookies" className={linkClass}>
              {m.footer_cookies()}
            </Link>
            <Link to="/sla" className={linkClass}>
              {m.footer_sla()}
            </Link>
            <Link to="/dpa" className={linkClass}>
              {m.footer_dpa()}
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex flex-col items-center justify-center gap-2 border-t border-border px-4 py-6 text-center sm:flex-row sm:gap-3">
        <Logo size="sm" />
        <span className="text-[12px] text-muted-foreground">
          © {year} Vectora. All rights reserved.
        </span>
        <span className="text-[12px] text-muted-foreground">
          CNPJ a confirmar
        </span>
      </div>
    </footer>
  )
}
