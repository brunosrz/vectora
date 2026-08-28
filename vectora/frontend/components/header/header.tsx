"use client";

import Image from "next/image";
import { Menu } from "lucide-react";

import { ContextualHelp } from "./contextual-help";
import { SettingsMenu } from "./settings-menu";
import { m } from "@/lib/paraglide/messages";
import { useIsDesktop } from "@/lib/hooks/use-is-desktop";
interface HeaderProps {
  showToolCalls?: boolean;
  onToggleToolCalls?: () => void;
  onShowShortcuts?: () => void;
  onOpenSidebar?: () => void;
}

export function Header({ onShowShortcuts, onOpenSidebar }: HeaderProps) {
  // No desktop, ícone+título já aparecem na TitleBar (canto superior
  // esquerdo, ao lado de voltar/recarregar) — repeti-los aqui só ocupa
  // altura à toa. Na web (sem TitleBar), continuam aqui como identidade
  // da página.
  const desktop = useIsDesktop();

  return (
    <header className="border-b border-border/60 bg-background h-11 flex items-center">
      {/* max-w-4xl mx-auto: mesma largura/centralização de message-list.tsx —
          sem isso, o ícone de dicas (à direita) não alinha com a borda das
          bolhas de mensagem em telas largas. */}
      <div className="flex items-center justify-between w-full min-w-0 max-w-4xl mx-auto px-4 sm:px-6">
        <div className="flex items-center gap-2 shrink-0">
          {/* Hamburger só em mobile — reabre o sidebar como overlay. */}
          {onOpenSidebar && (
            <button
              type="button"
              onClick={onOpenSidebar}
              aria-label={m.sidebar_open()}
              className="md:hidden -ml-1 mr-1 inline-flex items-center justify-center w-10 h-10 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          {!desktop && (
            <>
              <Image
                src="/vectora.svg"
                alt="Vectora"
                width={28}
                height={28}
                priority
                className="h-7 w-7"
              />
              <span
                className="text-xl font-semibold tracking-tight text-foreground"
                style={{ fontFamily: "var(--font-aeonik-mono)" }}
              >
                Vectora
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <ContextualHelp onShowShortcuts={onShowShortcuts} />
          <SettingsMenu />
        </div>
      </div>
    </header>
  );
}
