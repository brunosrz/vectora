import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "./Logo";

export default function Footer() {
  const year = new Date().getFullYear();

  const linkClass = "whitespace-nowrap transition-colors hover:text-foreground";

  // Títulos em foreground (mais contraste) sinalizam que NÃO são links.
  const titleClass =
    "text-[12px] font-semibold uppercase tracking-[0.6px] text-foreground";
  // Mobile/tablet: links empilhados numa coluna só (largura da seção é
  // fixa em 1/3 do grid abaixo, não sobra espaço para 3 colunas de texto).
  // Desktop (lg+): grid de 3 colunas dimensionadas ao conteúdo, como antes.
  const linksGridClass =
    "grid grid-cols-1 gap-y-2 text-[14px] text-muted-foreground lg:grid-cols-[repeat(3,auto)] lg:justify-start lg:gap-x-6 lg:gap-y-3";

  return (
    <footer className="bg-footer">
      {/* Mobile/tablet: 3 colunas iguais lado a lado (Produto/Suporte/Legal),
          largura total do container. Desktop (lg+): comportamento original,
          seções dimensionadas ao próprio conteúdo. */}
      <div className="mx-auto grid max-w-[1024px] grid-cols-3 gap-x-4 gap-y-10 px-4 pb-8 pt-10 sm:px-6 lg:flex lg:flex-wrap lg:justify-between lg:gap-x-12">
        {/* Produto */}
        <div className="flex flex-col gap-3">
          <p className={titleClass}>{m.footer_product()}</p>
          <div className={linksGridClass}>
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
          </div>
        </div>

        {/* Suporte */}
        <div className="flex flex-col gap-3">
          <p className={titleClass}>{m.footer_support()}</p>
          <div className={linksGridClass}>
            <Link to="/support" className={linkClass}>
              {m.nav_support()}
            </Link>
            <Link to="/issues" className={linkClass}>
              {m.nav_issues()}
            </Link>
          </div>
        </div>

        {/* Legal */}
        <div className="flex flex-col gap-3">
          <p className={titleClass}>{m.footer_legal()}</p>
          <div className={linksGridClass}>
            <Link to="/privacy" className={linkClass}>
              {m.footer_privacy()}
            </Link>
            <Link to="/terms" className={linkClass}>
              {m.footer_terms()}
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
      </div>
    </footer>
  );
}
