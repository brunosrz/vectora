"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { useT } from "@/lib/i18n";
import { getStackHint } from "@/lib/api/vectora-client";

interface EmptyStateHeaderProps {
  /** Chamado quando o usuário clica em uma sugestão — popula o input do chat. */
  onSelect?: (prompt: string) => void;
  /** Workspace ativo, se houver — usado para detectar a stack e adaptar as sugestões. */
  workspaceId?: string;
}

/** Stacks conhecidas com 3 sugestões cada. "unknown" é o fallback. */
const KNOWN_STACKS = ["nodejs", "python", "go", "rust", "java"] as const;
type KnownStack = (typeof KNOWN_STACKS)[number] | "unknown";

function isKnownStack(s: string): s is KnownStack {
  return (KNOWN_STACKS as readonly string[]).includes(s) || s === "unknown";
}

/**
 * Cabeçalho exibido acima da lista de mensagens quando a thread ainda
 * está vazia. Mostra logo, título e 3 sugestões clicáveis (CTAs) que
 * populam o input ao ser selecionadas.
 *
 * Quando um workspace está ativo, busca `GET /workspaces/{id}/stack-hint`
 * e usa sugestões específicas da stack detectada.
 */
export function EmptyStateHeader({
  onSelect,
  workspaceId,
}: EmptyStateHeaderProps) {
  const t = useT();

  // Busca o stack hint apenas quando há workspace ativo.
  const { data: hintData } = useQuery({
    queryKey: ["stack-hint", workspaceId],
    queryFn: () => getStackHint(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 5 * 60_000,
  });

  const stack: KnownStack =
    hintData && isKnownStack(hintData.stack) ? hintData.stack : "unknown";

  const suggestions = [
    t(`stack.${stack}.1`),
    t(`stack.${stack}.2`),
    t(`stack.${stack}.3`),
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
          className="text-2xl sm:text-4xl font-semibold text-foreground mb-8"
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
