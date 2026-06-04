import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff } from "lucide-react";
import { z } from "zod";

import { useAuthStore } from "@/lib/stores/auth-store";
import type { AuthUser } from "@/lib/types/auth";

const schema = z.object({
  email: z.string().email("E-mail inválido."),
  password: z.string().min(1, "Informe a senha."),
});

const searchSchema = z.object({
  from: z.string().optional(),
});

// `as never` em createFileRoute e nos `to:`: o tipo definitivo de cada rota
// só fica disponível depois que o plugin do TanStack Router gera o
// `routeTree.gen.ts`. Durante a primeira execução do tsc os tipos são
// "vazios" e o type-check estrito recusa as strings literais.
export const Route = createFileRoute("/auth/signin" as never)({
  validateSearch: searchSchema,
  component: SignInPage,
});

function SignInPage() {
  const navigate = useNavigate();
  const search = Route.useSearch();
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Primeiro acesso (sem usuários) → setup do root
  useEffect(() => {
    let cancelled = false;
    fetch("/auth/has-users", { credentials: "include" })
      .then((r) => r.json())
      .then((d: { exists?: boolean }) => {
        if (!cancelled && d.exists === false) {
          void navigate({ to: "/auth/signup" as never });
        }
      })
      .catch(() => {
        // Falha de rede → permanece no login
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const result = schema.safeParse({ email, password });
    if (!result.success) {
      setError(result.error.issues[0]?.message ?? "Dados inválidos.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/auth/signin", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Credenciais inválidas.");
        return;
      }

      setUser(data.user as AuthUser);
      const from = (search as { from?: string }).from;
      void navigate({ to: (from ?? "/") as never });
    } catch {
      setError("Erro de conexão. Verifique se o servidor está rodando.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="flex flex-col items-center gap-3">
          <img src="/vectora.svg" alt="Vectora" width={48} height={48} />
          <h1
            className="text-2xl font-semibold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-aeonik-mono)" }}
          >
            Vectora
          </h1>
          <p className="text-sm text-muted-foreground">
            Entre na sua conta para continuar
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="email"
            >
              E-mail
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              placeholder="voce@empresa.com"
            />
          </div>

          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="password"
            >
              Senha
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                placeholder="••••••••••••"
              />
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onTouchEnd={(e) => {
                  e.preventDefault();
                  setShowPassword((v) => !v);
                }}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center justify-center w-11 min-h-[44px] text-muted-foreground hover:text-foreground transition-colors touch-manipulation"
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
