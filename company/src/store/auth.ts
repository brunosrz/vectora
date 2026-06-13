import { create } from "zustand";
import type { User } from "@supabase/supabase-js";
import { getSupabaseBrowserClient } from "#/lib/supabase/client";

interface AuthState {
  session: User | null;
  isLoading: boolean;
  setSession: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  isLoading: true,
  setSession: (user) => set({ session: user, isLoading: false }),
}));

export function initAuthListener() {
  const supabase = getSupabaseBrowserClient();

  if (!supabase) {
    useAuthStore.getState().setSession(null);
    return () => {};
  }

  supabase.auth.getUser().then(({ data }) => {
    useAuthStore.getState().setSession(data.user ?? null);
  });

  const { data: listener } = supabase.auth.onAuthStateChange(
    (_event, session) => {
      useAuthStore.getState().setSession(session?.user ?? null);
    },
  );

  return () => listener.subscription.unsubscribe();
}
