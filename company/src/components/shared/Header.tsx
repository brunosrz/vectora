import { Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import { useAuthStore } from "#/store/auth";
import LocaleSwitcher from "./LocaleSwitcher";

export default function Header() {
  const session = useAuthStore((s) => s.session);

  return (
    <header className="sticky top-0 z-50 border-b border-brand-800 bg-brand-900/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <img src="/vectora.svg" alt="Vectora" className="h-7 w-auto" />
        </Link>

        {/* Nav */}
        <nav className="hidden items-center gap-6 text-sm md:flex">
          <Link
            to="/pricing"
            className="text-slate-400 transition-colors hover:text-white"
            activeProps={{ className: "text-white" }}
          >
            {m.nav_pricing()}
          </Link>
          <a
            href="https://docs.vectora.company"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 transition-colors hover:text-white"
          >
            {m.nav_docs()}
          </a>
          <Link
            to="/faq"
            className="text-slate-400 transition-colors hover:text-white"
            activeProps={{ className: "text-white" }}
          >
            {m.nav_faq()}
          </Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <div className="hidden md:block">
            <LocaleSwitcher />
          </div>

          {session ? (
            <Link
              to="/dashboard"
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-400"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="hidden text-sm text-slate-400 transition-colors hover:text-white sm:block"
              >
                {m.nav_login()}
              </Link>
              <Link
                to="/signup"
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-400"
              >
                {m.nav_signup()}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
