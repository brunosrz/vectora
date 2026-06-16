import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "./Logo";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-[#18191C]">
      {/* Top: 3 colunas — flex-row sem wrap conforme Figma (1024px container, gap-8=32px) */}
      <div className="mx-auto flex max-w-[1024px] flex-col items-start gap-8 px-4 pb-3 pt-6 sm:px-0 md:flex-row md:items-start md:justify-center">
        {/* Produto — 5 links em grid 3×2 */}
        <div className="flex flex-col gap-3">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_product()}
          </p>
          <div className="grid grid-cols-3 gap-x-6 gap-y-[10px] text-[14px] text-muted-foreground">
            <Link
              to="/pricing"
              className="transition-colors hover:text-foreground"
            >
              {m.nav_pricing()}
            </Link>
            <a
              href="https://docs.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_docs()}
            </a>
            <Link to="/faq" className="transition-colors hover:text-foreground">
              {m.footer_faq()}
            </Link>
            <Link
              to="/roadmap"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_roadmap()}
            </Link>
            <a
              href="https://status.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_status()}
            </a>
          </div>
        </div>

        {/* Suporte — 3 links em linha única */}
        <div className="flex flex-col gap-3">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_support()}
          </p>
          <div className="flex gap-[10px] text-[14px] text-muted-foreground">
            <Link
              to="/support"
              className="transition-colors hover:text-foreground"
            >
              {m.nav_support()}
            </Link>
            <Link
              to="/issues"
              className="transition-colors hover:text-foreground"
            >
              Issues
            </Link>
            <a
              href="https://github.com/vectora-company"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-foreground"
            >
              GitHub
            </a>
          </div>
        </div>

        {/* Legal — 5 links em grid 3×2 */}
        <div className="flex flex-col gap-3">
          <p className="text-[12px] font-semibold uppercase tracking-[0.6px] text-muted-foreground">
            {m.footer_legal()}
          </p>
          <div className="grid grid-cols-3 gap-x-4 gap-y-[10px] text-[14px] text-muted-foreground">
            <Link
              to="/privacy"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_privacy()}
            </Link>
            <Link
              to="/terms"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_terms()}
            </Link>
            <Link
              to="/cookies"
              className="transition-colors hover:text-foreground"
            >
              {m.footer_cookies()}
            </Link>
            <Link to="/sla" className="transition-colors hover:text-foreground">
              {m.footer_sla()}
            </Link>
            <Link to="/dpa" className="transition-colors hover:text-foreground">
              {m.footer_dpa()}
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-center gap-3 border-t border-white/10 px-4 py-6">
        <Logo size="sm" />
        <span className="text-[12px] text-[rgba(158,158,158,0.8)]">
          © {year} Vectora. All rights reserved.
        </span>
        <span className="text-[12px] text-[rgba(158,158,158,0.8)]">
          CNPJ a confirmar
        </span>
      </div>
    </footer>
  );
}
