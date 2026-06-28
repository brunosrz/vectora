import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "./types";

// Singleton para evitar múltiplas instâncias no cliente
let client: ReturnType<typeof createBrowserClient<Database>> | null = null;

export function getSupabaseBrowserClient() {
  if (client) return client;

  const url = import.meta.env.VITE_SUPABASE_URL;
  const key = import.meta.env.VITE_SUPABASE_KEY;

  // Sem credenciais (dev local sem .env preenchido), o site público deve
  // funcionar sem auth em vez de derrubar a hidratação inteira.
  if (!url || !key) return null;

  client = createBrowserClient<Database>(url, key);

  return client;
}
