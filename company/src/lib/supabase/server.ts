import { createServerClient } from '@supabase/ssr'
import type { CookieOptions } from '@supabase/ssr'
import { getCookie, setCookie } from '@tanstack/react-start/server'
import type { Database } from './types'

// Usar dentro de createServerFn() do TanStack Start.
// Lê/escreve cookies de sessão via H3 event do Nitro.
export function createSupabaseServerClient() {
  return createServerClient<Database>(
    process.env.VITE_SUPABASE_URL!,
    process.env.VITE_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return getCookie(name) ?? undefined
        },
        set(name: string, value: string, options: CookieOptions) {
          setCookie(name, value, options)
        },
        remove(name: string, options: CookieOptions) {
          setCookie(name, '', { ...options, maxAge: 0 })
        },
      },
    },
  )
}
