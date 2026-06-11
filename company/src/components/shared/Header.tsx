import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";
import { m } from "#/paraglide/messages";
import { useAuthStore } from "#/store/auth";
import LocaleSwitcher from "./LocaleSwitcher";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const session = useAuthStore((s) => s.session);
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinkClass =
    "text-muted-foreground transition-colors hover:text-foreground";

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      {/* grid 1fr/auto/1fr: nav central fica de fato centralizado na viewport */}
      <div className="mx-auto grid h-14 max-w-7xl grid-cols-[1fr_auto_1fr] items-center px-4 sm:h-16 sm:px-6 lg:px-8">
        <div className="justify-self-start">
          <Logo size="md" />
        </div>

        {/* Nav desktop */}
        <nav className="hidden items-center justify-center gap-6 text-sm md:flex">
          <Link
            to="/pricing"
            className={navLinkClass}
            activeProps={{ className: "text-foreground" }}
          >
            {m.nav_pricing()}
          </Link>
          <a
            href="https://docs.vectora.company"
            target="_blank"
            rel="noopener noreferrer"
            className={navLinkClass}
          >
            {m.nav_docs()}
          </a>
          <Link
            to="/faq"
            className={navLinkClass}
            activeProps={{ className: "text-foreground" }}
          >
            {m.nav_faq()}
          </Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2 justify-self-end sm:gap-3">
          <div className="hidden md:block">
            <LocaleSwitcher />
          </div>
          <ThemeToggle />

          {session ? (
            <Link
              to="/dashboard"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:block"
              >
                {m.nav_login()}
              </Link>
              <Link
                to="/signup"
                className="hidden rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 sm:block"
              >
                {m.nav_signup()}
              </Link>
            </>
          )}

          {/* Hambúrguer mobile */}
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={m.nav_menu()}
            aria-expanded={mobileOpen}
            className="rounded-lg border border-border bg-card p-2 text-muted-foreground transition-colors hover:text-foreground md:hidden"
          >
            {mobileOpen ? (
              <X className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Menu mobile */}
      {mobileOpen && (
        <nav className="border-t border-border bg-background px-4 py-3 md:hidden">
          <div className="flex flex-col gap-1 text-sm">
            <Link
              to="/pricing"
              onClick={() => setMobileOpen(false)}
              className="rounded-md px-2 py-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {m.nav_pricing()}
            </Link>
            <a
              href="https://docs.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMobileOpen(false)}
              className="rounded-md px-2 py-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {m.nav_docs()}
            </a>
            <Link
              to="/faq"
              onClick={() => setMobileOpen(false)}
              className="rounded-md px-2 py-2 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {m.nav_faq()}
            </Link>
            {!session && (
              <Link
                to="/login"
                onClick={() => setMobileOpen(false)}
                className="rounded-md px-2 py-2 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {m.nav_login()}
              </Link>
            )}
            <div className="mt-2 border-t border-border pt-3">
              <LocaleSwitcher />
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}
