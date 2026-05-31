"use client";

import Image from "next/image";
import { useT } from "@/lib/i18n";

/**
 * Cabeçalho exibido acima da lista de mensagens quando a thread ainda
 * está vazia. Substitui a tela de boas-vindas dedicada; o input do
 * chat é o mesmo nos dois estados.
 */
export function EmptyStateHeader() {
  const t = useT();
  return (
    <div className="flex-1 flex items-center justify-center px-3 sm:px-4 pointer-events-none">
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
          className="text-2xl sm:text-4xl font-semibold text-white mb-2"
          style={{ fontFamily: "var(--font-aeonik-mono)" }}
        >
          {t("welcome.title")}
        </h2>
      </div>
    </div>
  );
}
