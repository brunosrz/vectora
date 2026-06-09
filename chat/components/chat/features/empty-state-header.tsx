"use client";

import Image from "next/image";
import { useT } from "@/lib/i18n";

interface EmptyStateHeaderProps {
  /** Chamado quando o usuário clica em uma sugestão — popula o input do chat. */
  onSelect?: (prompt: string) => void;
}

/**
 * Cabeçalho exibido acima da lista de mensagens quando a thread ainda
 * está vazia. Mostra logo, título e 3 sugestões clicáveis (CTAs) que
 * populam o input ao ser selecionadas.
 */
export function EmptyStateHeader({ onSelect }: EmptyStateHeaderProps) {
  const t = useT();

  const suggestions = [
    t("welcome.suggestion_1"),
    t("welcome.suggestion_2"),
    t("welcome.suggestion_3"),
  ];

  return (
    <div className="flex-1 flex items-center justify-center px-3 sm:px-4">
      <div className="w-full max-w-3xl -mt-10 sm:-mt-20 text-center">
        <div className="mb-6 flex items-center justify-center gap-3 sm:gap-4">
          <Image
            src="/vectora.svg"
            alt="Vectora"
            width={64}
            height={64}
            priority
            className="h-12 w-12 sm:h-16 sm:w-16"
          />
          <span
            className="text-5xl sm:text-6xl font-bold tracking-tight text-primary"
            style={{ fontFamily: "var(--font-aeonik-mono)" }}
          >
            Vectora
          </span>
        </div>
        <h2
          className="text-2xl sm:text-4xl font-semibold text-white mb-8"
          style={{ fontFamily: "var(--font-aeonik-mono)" }}
        >
          {t("welcome.title")}
        </h2>

        {onSelect && (
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => onSelect(s)}
                className="px-4 py-3 rounded-xl border border-border/60 bg-muted/30 hover:bg-muted/60 text-sm text-foreground/80 hover:text-foreground transition-colors text-left sm:flex-1 sm:max-w-[240px]"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
