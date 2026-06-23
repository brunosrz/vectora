import { createClient } from "@supabase/supabase-js";
import type { Database } from "./types";

// Apenas para server functions privilegiadas — bypassa RLS.
// NUNCA expor SUPABASE_SERVICE_ROLE_KEY no cliente.
export function createSupabaseAdminClient() {
  return createClient<Database>(
    process.env.VITE_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    },
  );
}
