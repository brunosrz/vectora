"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Settings, Shield } from "lucide-react";

import { useAuthStore } from "@/lib/stores/auth-store";
import { useSettingsDialogStore } from "@/lib/stores/settings-dialog-store";
import { ROLE_COLORS, ROLE_LABELS } from "@/lib/types/auth";
import { SettingsDialog } from "./settings-dialog";

export function UserMenu() {
  const router = useRouter();
  const { user, isAuthenticated, clearUser } = useAuthStore();
  const openSettings = useSettingsDialogStore((s) => s.openAt);
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
      await fetch("/api/auth/signout", {
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

  if (!isAuthenticated || !user) {
    return null;
  }

  const initial = user.email[0]?.toUpperCase() ?? "?";
  const roleLabel = ROLE_LABELS[user.role] ?? user.role;
  const roleColor = ROLE_COLORS[user.role] ?? "text-muted-foreground";

  return (
    <>
      <div className="relative" ref={menuRef}>
        {/* Avatar circular com inicial do e-mail */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/20 hover:bg-primary/30 text-primary font-semibold text-sm transition-colors select-none"
          title={user.email}
          aria-label="Menu do usuário"
          aria-expanded={open}
        >
          {initial}
        </button>

        {/* Dropdown */}
        {open && (
          <div className="absolute right-0 top-10 z-50 w-64 rounded-lg border border-border bg-background shadow-xl py-1 animate-in fade-in slide-in-from-top-2">
            {/* Info do usuário */}
            <div className="px-4 py-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-9 h-9 rounded-full bg-primary/20 text-primary font-semibold text-base select-none">
                  {initial}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {user.email}
                  </p>
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
                  openSettings("conta");
                }}
              >
                <Settings className="w-4 h-4 shrink-0 text-muted-foreground" />
                Configurações
              </button>

              {(user.role === "root" || user.role === "admin") && (
                <button
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-accent transition-colors text-left"
                  onClick={() => {
                    setOpen(false);
                    openSettings("admin");
                  }}
                >
                  <Shield className="w-4 h-4 shrink-0 text-muted-foreground" />
                  Administração
                </button>
              )}

              <button
                className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors text-left"
                onClick={handleLogout}
              >
                <LogOut className="w-4 h-4 shrink-0" />
                Sair
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Settings Dialog — Bloco L2 (estado no settings-dialog-store) */}
      <SettingsDialog />
    </>
  );
}
