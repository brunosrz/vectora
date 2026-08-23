// @vitest-environment jsdom
/**
 * Guarda de segurança dos overlays de Header/ChatInterface em
 * `$threadId.tsx`: o mecanismo normal (chatSlotRef.../headerSlotRef...) só
 * limpa o slot antigo quando o AnimatePresence completa a animação de
 * saída da branch anterior — um contrato de terceiro (framer/motion) sem
 * garantia de sempre disparar (ex.: janela do Electron criada oculta pausa
 * requestAnimationFrame e trava a saída). Sem uma guarda independente, o
 * chat pode continuar "vazando" por cima do Kanban mesmo depois da troca
 * de modo já ter acontecido no resto da UI.
 *
 * Este teste reproduz o padrão exato usado em `$threadId.tsx` (mesmo
 * cálculo de `effectiveMode`, mesma forma de guardar `chatSlot`/
 * `headerSlot`) num componente mínimo e isolado — testar o arquivo real é
 * inviável (SessionPage depende de dezenas de stores/queries/SSE) — e
 * simula deliberadamente o cenário "a animação de saída nunca completa":
 * o placeholder da branch antiga nunca chama seu ref-callback com `null`.
 */

import { describe, it, expect, afterEach } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import { useCallback, useEffect, useState } from "react";

afterEach(cleanup);

type Mode = "kanban" | "ide" | "assistente";

function effectiveMode(uiMode: Mode, chatMode: boolean): Mode {
  if (uiMode === "kanban" && !chatMode) return "kanban";
  if (uiMode === "ide" && !chatMode) return "ide";
  return "assistente";
}

/** Reprodução mínima do padrão chatSlot/headerSlot + guarda de $threadId.tsx. */
function Sonda({ uiMode, chatMode }: { uiMode: Mode; chatMode: boolean }) {
  const [chatSlot, setChatSlot] = useState<{
    el: HTMLDivElement;
    kind: "ide" | "assistente";
  } | null>(null);
  const [headerSlot, setHeaderSlot] = useState<{
    el: HTMLDivElement;
    kind: Mode;
  } | null>(null);

  // Placeholder "preso": simula a animação de saída nunca completando —
  // ao trocar de modo, este componente é desmontado pelo React (troca de
  // `key` no teste), mas SEM que o ref callback chegue a rodar com
  // `null` primeiro, reproduzindo exatamente o cenário problemático.
  const chatSlotRefAssistente = useCallback((el: HTMLDivElement | null) => {
    if (el) setChatSlot({ el, kind: "assistente" });
    // deliberadamente NÃO limpa no unmount — é o bug que a guarda cobre.
  }, []);
  const headerSlotRefAssistente = useCallback((el: HTMLDivElement | null) => {
    if (el) setHeaderSlot({ el, kind: "assistente" });
    // idem — nunca limpa no unmount.
  }, []);

  const mode = effectiveMode(uiMode, chatMode);

  // A mesma guarda implementada em $threadId.tsx — sincroniza com um
  // sistema externo (refs de DOM anexados por outras branches via
  // ref-callback), não deriva de props/state locais, por isso o
  // setState dentro do efeito é o padrão correto aqui.
  /* oxlint-disable react/set-state-in-effect -- ver comentário acima */
  useEffect(() => {
    if (mode === "kanban") {
      setChatSlot((prev) => (prev ? null : prev));
    }
    setHeaderSlot((prev) => (prev && prev.kind !== mode ? null : prev));
  }, [mode]);
  /* oxlint-enable react/set-state-in-effect */

  return (
    <div>
      <div data-testid="chat-slot-state">{chatSlot ? "visible" : "hidden"}</div>
      <div data-testid="header-slot-kind">{headerSlot?.kind ?? "none"}</div>
      {mode === "assistente" && (
        <>
          <div
            ref={chatSlotRefAssistente}
            data-testid="assistente-placeholder"
          />
          <div ref={headerSlotRefAssistente} data-testid="header-placeholder" />
        </>
      )}
    </div>
  );
}

describe("guarda de mode-slot ($threadId.tsx: chatSlot/headerSlot)", () => {
  it("esconde o chat ao entrar em Kanban mesmo se o placeholder anterior nunca desmontar 'limpo'", () => {
    const { rerender, getByTestId } = render(
      <Sonda uiMode="assistente" chatMode={false} />,
    );

    // Monta o placeholder do Assistente — chatSlot fica visível.
    act(() => {
      getByTestId("assistente-placeholder");
    });
    expect(getByTestId("chat-slot-state").textContent).toBe("visible");

    // Troca pra Kanban — o placeholder do Assistente é removido da árvore
    // SEM nunca ter chamado seu ref com `null` (cenário de animação
    // presa). Sem a guarda, chatSlot continuaria "visible" pra sempre.
    rerender(<Sonda uiMode="kanban" chatMode={false} />);

    expect(getByTestId("chat-slot-state").textContent).toBe("hidden");
  });

  it("caso de borda: headerSlot com kind desatualizado (de um modo anterior) é limpo ao trocar de modo", () => {
    const { rerender, getByTestId } = render(
      <Sonda uiMode="assistente" chatMode={false} />,
    );

    // headerSlot fica "assistente" — o placeholder do Assistente montou.
    expect(getByTestId("header-slot-kind").textContent).toBe("assistente");

    // Troca pra IDE sem o placeholder do Assistente nunca chamar seu ref
    // com `null` (mesmo cenário de animação presa). Sem a guarda,
    // headerSlot continuaria reportando "assistente" (largura errada)
    // até o placeholder do IDE eventualmente montar por outro caminho.
    rerender(<Sonda uiMode="ide" chatMode={false} />);

    expect(getByTestId("header-slot-kind").textContent).toBe("none");
  });
});
