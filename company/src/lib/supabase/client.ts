import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "./types";

// Singleton para evitar múltiplas instâncias no cliente
let client: ReturnType<typeof createBrowserClient<Database>> | null = null;

export function getSupabaseBrowserClient() {
  if (client) return client;

  client = createBrowserClient<Database>(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_ANON_KEY,
  );

  return client;
}
