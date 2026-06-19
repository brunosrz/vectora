import { Link, useRouterState } from '@tanstack/react-router'
import { m } from '#/paraglide/messages'
import { Key, Shield, CreditCard, Zap, User, HelpCircle } from 'lucide-react'
import Logo from '#/components/shared/Logo'
import ThemeToggle from '#/components/shared/ThemeToggle'

const NAV_ITEMS = [
  { to: '/dashboard' as const, exact: true, icon: Key, labelKey: 'nav_token' },
  {
    to: '/dashboard/license' as const,
    exact: false,
    icon: Shield,
    labelKey: 'nav_license',
  },
  {
    to: '/dashboard/billing' as const,
    exact: false,
    icon: CreditCard,
    labelKey: 'nav_billing',
  },
  {
    to: '/dashboard/api-keys' as const,
    exact: false,
    icon: Zap,
    labelKey: 'nav_api_keys',
  },
  {
    to: '/dashboard/account' as const,
    exact: false,
    icon: User,
    labelKey: 'nav_account',
  },
  {
    to: '/support' as const,
    exact: false,
    icon: HelpCircle,
    labelKey: 'nav_support',
  },
] as const

export default function Sidebar() {
  const { location } = useRouterState()
  const pathname = location.pathname

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col w-56 shrink-0 border-r border-border bg-background min-h-screen py-6">
        <div className="mb-8 flex items-center justify-between px-5">
          <Logo size="sm" />
          <ThemeToggle />
        </div>
        <nav className="flex flex-col gap-0.5 px-3">
          {NAV_ITEMS.map((item) => {
            const active = item.exact
              ? pathname === item.to
              : pathname.startsWith(item.to)
            const Icon = item.icon
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                  active
                    ? 'bg-primary/15 text-primary'
                    : 'text-muted-foreground hover:bg-card hover:text-foreground'
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 ${active ? 'text-primary' : ''}`}
                />
                {m[item.labelKey]()}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Mobile bottom tab bar (5 items + support excluded) */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 border-t border-border bg-background/95 backdrop-blur flex">
        {NAV_ITEMS.slice(0, 5).map((item) => {
          const active = item.exact
            ? pathname === item.to
            : pathname.startsWith(item.to)
          const Icon = item.icon
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex-1 flex flex-col items-center py-2 gap-0.5 text-[10px] font-medium transition-colors ${
                active
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground/90'
              }`}
            >
              <Icon className="h-5 w-5" />
              {m[item.labelKey]()}
            </Link>
          )
        })}
      </nav>
    </>
  )
}
