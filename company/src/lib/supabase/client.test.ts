import { describe, it, expect, vi, afterEach } from "vitest";

// getSupabaseBrowserClient lê VITE_SUPABASE_URL + VITE_SUPABASE_KEY (não mais
// ANON_KEY) e é singleton. Sem credenciais retorna null (site público funciona
// sem auth em vez de derrubar a hidratação). resetModules zera o singleton entre
// os casos.

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("getSupabaseBrowserClient", () => {
  it("retorna null sem credenciais", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_KEY", "");
    const { getSupabaseBrowserClient } = await import("./client");
    expect(getSupabaseBrowserClient()).toBeNull();
  });

  it("retorna null se falta só a key (par de erro)", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "https://proj.supabase.co");
    vi.stubEnv("VITE_SUPABASE_KEY", "");
    const { getSupabaseBrowserClient } = await import("./client");
    expect(getSupabaseBrowserClient()).toBeNull();
  });

  it("cria e reusa o mesmo client (singleton) com credenciais", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "https://proj.supabase.co");
    vi.stubEnv("VITE_SUPABASE_KEY", "sb_publishable_test");
    const { getSupabaseBrowserClient } = await import("./client");
    const a = getSupabaseBrowserClient();
    const b = getSupabaseBrowserClient();
    expect(a).not.toBeNull();
    expect(a).toBe(b);
  });
});
