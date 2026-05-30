"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import { z } from "zod";

import { useAuthStore } from "@/lib/stores/auth-store";
import type { AuthUser } from "@/lib/types/auth";

const schema = z
  .object({
    // Nome aceita qualquer caractere UTF-8 (acentos, espaços, etc.). O
    // backend trim+normaliza espaços internos e limita a 100 chars; aqui
    // só exigimos um mínimo razoável.
    name: z
      .string()
      .trim()
      .min(1, "Informe seu nome.")
      .max(100, "Nome muito longo (máx. 100 caracteres)."),
    email: z.string().email("E-mail inválido."),
    password: z.string().min(12, "Senha deve ter no mínimo 12 caracteres."),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "As senhas não conferem.",
    path: ["confirm"],
  });

export default function SignUpPage() {
  const router = useRouter();
  const setUser = useAuthStore((s) => s.setUser);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [inviteToken, setInviteToken] = useState("");
  const [inviteRole, setInviteRole] = useState<string | null>(null);

  // Resolve o fluxo de entrada: primeiro acesso, convite válido, ou bloqueado.
  useEffect(() => {
    const token =
      new URLSearchParams(window.location.search).get("invite") ?? "";

    async function resolve() {
      let hasUsers = true;
      try {
        const r = await fetch("/api/auth/has-users");
        hasUsers = Boolean((await r.json()).exists);
      } catch {
        hasUsers = true;
      }

      // Sem usuários → setup do root, sem necessidade de convite
      if (!hasUsers) {
        setReady(true);
        return;
      }

      // Com usuários → exige convite válido
      if (token) {
        try {
          const r = await fetch(`/api/auth/invite/${token}`);
          const data = await r.json();
          if (data.valid) {
            setInviteToken(token);
            setInviteRole(data.role ?? "member");
            if (data.email) setEmail(data.email);
            setReady(true);
            return;
          }
        } catch {
          // cai no redirect abaixo
        }
      }

      // Sem convite válido e com usuários → signup público bloqueado
      router.replace("/auth/signin");
    }

    void resolve();
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);
    setErrors({});

    const result = schema.safeParse({ name, email, password, confirm });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      for (const err of result.error.issues) {
        const field = err.path[0]?.toString() ?? "form";
        fieldErrors[field] = err.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email,
          password,
          invite_token: inviteToken,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setServerError(data.detail ?? "Erro ao criar conta.");
        return;
      }

      setUser(data.user as AuthUser);
      router.replace("/");
    } catch {
      setServerError("Erro de conexão. Verifique se o servidor está rodando.");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Carregando…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <Image
            src="/vectora.svg"
            alt="Vectora"
            width={48}
            height={48}
            priority
          />
          <h1
            className="text-2xl font-semibold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-aeonik-mono)" }}
          >
            Vectora
          </h1>
          <div className="text-center">
            {inviteRole ? (
              <>
                <p className="text-sm text-muted-foreground">Criar conta</p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  Convite para função:{" "}
                  <span className="text-primary font-medium">{inviteRole}</span>
                </p>
              </>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">Primeiro acesso</p>
                <p className="text-xs text-muted-foreground/70 mt-0.5">
                  O primeiro usuário criado vira{" "}
                  <span className="text-yellow-400 font-medium">root</span>{" "}
                  automaticamente.
                </p>
              </>
            )}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="name"
            >
              Nome
            </label>
            <input
              id="name"
              type="text"
              // UTF-8 livre — acentos, espaços, ç, traços ('Bruno Soares', 'João D'Ávila' etc.)
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={100}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
              placeholder="Como o Vectora deve te chamar?"
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>

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
            {errors.email && (
              <p className="text-xs text-destructive">{errors.email}</p>
            )}
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
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                placeholder="Mínimo 12 caracteres"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-destructive">{errors.password}</p>
            )}
          </div>

          <div className="space-y-1">
            <label
              className="text-sm font-medium text-foreground"
              htmlFor="confirm"
            >
              Confirmar senha
            </label>
            <div className="relative">
              <input
                id="confirm"
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                placeholder="••••••••••••"
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={
                  showConfirm ? "Ocultar confirmação" : "Mostrar confirmação"
                }
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.confirm && (
              <p className="text-xs text-destructive">{errors.confirm}</p>
            )}
          </div>

          {serverError && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
          >
            {loading ? "Criando conta…" : "Criar conta"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          Já tem conta?{" "}
          <Link href="/auth/signin" className="text-primary hover:underline">
            Entrar
          </Link>
        </p>
      </div>
    </div>
  );
}
