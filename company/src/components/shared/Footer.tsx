import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Logo from "./Logo";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Logo size="sm" className="mb-4" />
            <p className="text-xs text-muted-foreground">
              {m.footer_made_in()}
            </p>
          </div>

          {/* Product */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {m.footer_product()}
            </p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link
                  to="/pricing"
                  className="hover:text-foreground transition-colors"
                >
                  {m.nav_pricing()}
                </Link>
              </li>
              <li>
                <a
                  href="https://docs.vectora.company"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_docs()}
                </a>
              </li>
              <li>
                <Link
                  to="/faq"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_faq()}
                </Link>
              </li>
              <li>
                <Link
                  to="/roadmap"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_roadmap()}
                </Link>
              </li>
              <li>
                <a
                  href="https://status.vectora.company"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_status()}
                </a>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {m.footer_support()}
            </p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link
                  to="/support"
                  className="hover:text-foreground transition-colors"
                >
                  {m.nav_support()}
                </Link>
              </li>
              <li>
                <Link
                  to="/issues"
                  className="hover:text-foreground transition-colors"
                >
                  Issues
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/vectora-company"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {m.footer_legal()}
            </p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link
                  to="/privacy"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_privacy()}
                </Link>
              </li>
              <li>
                <Link
                  to="/terms"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_terms()}
                </Link>
              </li>
              <li>
                <Link
                  to="/cookies"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_cookies()}
                </Link>
              </li>
              <li>
                <Link
                  to="/sla"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_sla()}
                </Link>
              </li>
              <li>
                <Link
                  to="/dpa"
                  className="hover:text-foreground transition-colors"
                >
                  {m.footer_dpa()}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground/80 sm:flex-row">
          <p>© {year} Vectora. All rights reserved.</p>
          <p>CNPJ a confirmar</p>
        </div>
      </div>
    </footer>
  );
}
