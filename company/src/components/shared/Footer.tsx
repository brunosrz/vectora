import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "./Logo";

export default function Footer() {
  const year = new Date().getFullYear();

  const linkClass = "whitespace-nowrap transition-colors hover:text-foreground";

  // Títulos em foreground (mais contraste) sinalizam que NÃO são links.
  const titleClass =
    "text-[12px] font-semibold uppercase tracking-[0.6px] text-foreground";
  // Links de cada seção fluem num grid de 3 colunas (quebra em 2 linhas),
  // colunas dimensionadas ao conteúdo — não numa coluna única empilhada.
  const linksGridClass =
    "grid grid-cols-[repeat(3,auto)] justify-start gap-x-6 gap-y-3 text-[14px] text-muted-foreground";

  return (
    <footer className="bg-footer">
      {/* Seções distribuídas na largura (quebram no estreito); links em grid 3-col. */}
      <div className="mx-auto flex max-w-[1024px] flex-wrap justify-between gap-x-12 gap-y-10 px-4 pb-8 pt-10 sm:px-6">
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
  );
}
