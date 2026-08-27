"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Settings, SlidersHorizontal, Shield } from "lucide-react";

import { useAuthStore } from "@/lib/stores/auth-store";
import { usePreferenciasDialogStore } from "@/lib/stores/preferencias-dialog-store";
import { useEnvironmentDialogStore } from "@/lib/stores/environment-dialog-store";
import { useAdministracaoDialogStore } from "@/lib/stores/administracao-dialog-store";
import { ROLE_COLORS, ROLE_LABELS } from "@/lib/types/auth";
import { SettingsOverlay } from "@/components/settings/settings-overlay";
import { m } from "@/lib/paraglide/messages";

export function SettingsMenu() {
  const router = useRouter();
  const { user, isAuthenticated, clearUser } = useAuthStore();
  const openPreferencias = usePreferenciasDialogStore((s) => s.openAt);
  const openEnvironment = useEnvironmentDialogStore((s) => s.openAt);
  const openAdmin = useAdministracaoDialogStore((s) => s.openAt);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Fecha o menu ao clicar fora
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout() {
    setOpen(false);
    try {
      await fetch("/auth/signout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
    } catch {
      // Ignora erro de rede — limpa localmente de qualquer jeito
    }
    clearUser();
    router.replace("/auth/signin");
  }

  // O backend sempre injeta um usuário em /auth/me (real no Pro, virtual
  // "local" no Free — ver _get_virtual_local_user em
  // backend/api/middleware/auth.py) — o botão nunca depende de isAuthenticated.
  // Só o botão "Sair" distingue conta real de usuário local virtual (abaixo).
  const displayName = user?.name?.trim() || user?.username || "Vectora";
  const initial = Array.from(displayName)[0]?.toUpperCase() ?? "V";
  const roleLabel = user ? (ROLE_LABELS[user.role] ?? user.role) : "Local";
  const roleColor = user
    ? (ROLE_COLORS[user.role] ?? "text-muted-foreground")
    : "text-muted-foreground";
  const isRealAccount = isAuthenticated && user?.id !== "local";

  return (
    <>
      <div className="relative" ref={menuRef}>
        {/* Botão de configurações (engrenagem) */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-muted/70 text-muted-foreground hover:text-foreground transition-colors select-none"
          title={displayName}
          aria-label="Configurações"
          aria-expanded={open}
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* Dropdown */}
        {open && (
          <div className="absolute right-0 top-10 z-[80] w-64 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-top-2">
            <div className="px-4 py-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-9 h-9 rounded-full bg-primary/20 text-primary font-semibold text-base select-none">
                  {initial}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {displayName}
                  </p>
                  {user?.name?.trim() && user.username && (
                    <p className="text-xs text-muted-foreground truncate">
                      @{user.username}
                    </p>
                  )}
                  <p className={`text-xs font-medium ${roleColor}`}>
                    {roleLabel}
                  </p>
                </div>
              </div>
            </div>

            {/* Ações */}
            <div className="py-1">
              <button
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
                onClick={() => {
                  setOpen(false);
                  openPreferencias("preferencias");
                }}
              >
                <Settings className="w-4 h-4 shrink-0 text-muted-foreground" />
                {m.settings_group_preferencias()}
              </button>

              <button
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
                onClick={() => {
                  setOpen(false);
                  openEnvironment("integracoes");
                }}
              >
                <SlidersHorizontal className="w-4 h-4 shrink-0 text-muted-foreground" />
                {m.settings_group_environment()}
              </button>

              {(user?.role === "root" || user?.role === "admin") && (
                <button
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
                  onClick={() => {
                    setOpen(false);
                    openAdmin();
                  }}
                >
                  <Shield className="w-4 h-4 shrink-0 text-muted-foreground" />
                  {m.settings_group_admin()}
                </button>
              )}

              {isRealAccount && (
                <button
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors text-left"
                  onClick={handleLogout}
                >
                  <LogOut className="w-4 h-4 shrink-0" />
                  {m.user_logout()}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <SettingsOverlay />
    </>
  );
}
