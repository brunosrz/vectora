/**
 * MessageList — Vectora Chat
 *
 * M1: Virtualização com @tanstack/react-virtual quando messages.length > 50.
 *     Abaixo do threshold, renderização direta (melhor para threads curtas).
 * M3: Auto-scroll inteligente — cancela ao detectar scroll manual para cima,
 *     mostra botão "Voltar ao fim" quando o usuário afastou o foco do bottom.
 * M4: Exibe MessageSkeletons durante isLoadingThread.
 * M5: Passa onRetry para cada MessageItem (botão de retry em erros).
 */

import { memo, useMemo, useEffect, useRef, useState, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useSearchParams } from "next/navigation";
import type { Message } from "@/lib/types";
import { MessageItem } from "./message-item";
import { MessageSkeletons } from "./message-skeleton";
import { ArrowDown } from "lucide-react";

// Ativa virtualização quando a thread tem mais que este número de mensagens.
// Abaixo do threshold, renderização direta é mais simples e igualmente rápida.
const VIRTUALIZE_THRESHOLD = 50;

// Estimativa de altura por mensagem (será refinada via measureElement).
const ESTIMATE_SIZE_PX = 200;

interface MessageListProps {
  messages: Message[];
  showToolCalls?: boolean;
  isRegenerating: boolean;
  /** M4 — exibe skeletons enquanto o histórico está carregando */
  isLoadingThread?: boolean;
  copiedId: string | null;
  onCopy: (content: string, messageId: string) => void;
  onRegenerate: () => void;
  onEditAndRerun?: (messageId: string, newContent: string) => void;
  feedbackComment: { [messageId: string]: string };
  showCommentInput: string | null;
  onFeedback: (
    messageId: string,
    feedbackType: "positive" | "negative",
    comment?: string,
  ) => void;
  onSubmitComment: (messageId: string) => void;
  onCancelComment: (messageId: string) => void;
  onToggleComment: (messageId: string) => void;
  setFeedbackComment: React.Dispatch<
    React.SetStateAction<{ [messageId: string]: string }>
  >;
  /** E2 — HITL */
  onHitlDecision?: (
    messageId: string,
    interruptId: string,
    decision: "approve" | "reject" | `edit:${string}`,
  ) => void;
  /** M5 — retry ao clicar no botão de erro */
  onRetry?: () => void;
  threadId?: string;
  /** A.2d — rewind: id do workspace ativo */
  workspaceId?: string;
  /** IDE sidebar: passa para MessageItem ocultar avatar e compactar. */
  compact?: boolean;
}

export const MessageList = memo(function MessageList({
  messages,
  showToolCalls,
  isRegenerating,
  isLoadingThread = false,
  copiedId,
  onCopy,
  onRegenerate,
  onEditAndRerun,
  feedbackComment,
  showCommentInput,
  onFeedback,
  onSubmitComment,
  onCancelComment,
  onToggleComment,
  setFeedbackComment,
  onHitlDecision,
  onRetry,
  threadId,
  workspaceId,
  compact = false,
}: MessageListProps) {
  // D4 — dev mode detectado uma vez por render de lista
  const searchParams = useSearchParams();
  const isDevMode = searchParams?.get("dev") === "1";

  // Scroll container
  const scrollRef = useRef<HTMLDivElement>(null);

  // Estado do botão "Voltar ao fim" (M3)
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Refs de controle do auto-scroll (M3)
  const shouldAutoScrollRef = useRef(true);
  const isProgrammaticScrollRef = useRef(false);
  const isAutoScrollingRef = useRef(false);
  const lastScrollTopRef = useRef(0);
  const firstMessageIdRef = useRef<string | null>(null);

  // Refs para debounce de scroll na thread inicial
  const scrollTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const mutationObserverRef = useRef<MutationObserver | null>(null);
  const scrollAttemptsRef = useRef(0);

  // M1 — Ativa virtualização somente acima do threshold
  const shouldVirtualize = messages.length > VIRTUALIZE_THRESHOLD;

  // M1 — Virtualizer (@tanstack/react-virtual)
  const virtualizer = useVirtualizer({
    count: shouldVirtualize ? messages.length : 0,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ESTIMATE_SIZE_PX,
    overscan: 4,
    // measureElement usa ResizeObserver — mede alturas reais (incluindo streaming)
    measureElement:
      typeof window !== "undefined"
        ? (el) => el?.getBoundingClientRect().height ?? ESTIMATE_SIZE_PX
        : undefined,
  });

  // Último ID de mensagem assistant (para controles de ação)
  const lastAssistantId = useMemo(() => {
    const assistantMessages = messages.filter((m) => m.role === "assistant");
    return assistantMessages.length > 0
      ? assistantMessages[assistantMessages.length - 1]?.id
      : undefined;
  }, [messages]);

  // ──────────────────────────────────────────────────────────────────────────
  // Helpers de scroll
  // ──────────────────────────────────────────────────────────────────────────

  const cancelAutoScroll = useCallback(() => {
    isAutoScrollingRef.current = false;
    isProgrammaticScrollRef.current = false;
    mutationObserverRef.current?.disconnect();
    mutationObserverRef.current = null;
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
  }, []);

  const scrollToAbsoluteBottom = useCallback(() => {
    if (!scrollRef.current) return;
    const maxScroll = scrollRef.current.scrollHeight;
    scrollRef.current.scrollTop = maxScroll;
    lastScrollTopRef.current = maxScroll;
  }, []);

  const isAtAbsoluteBottom = useCallback(() => {
    if (!scrollRef.current) return true;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    return scrollTop >= scrollHeight - clientHeight - 5;
  }, []);

  const isAtBottom = useCallback(() => {
    if (!scrollRef.current) return true;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    return scrollHeight - scrollTop - clientHeight < 1;
  }, []);

  // ──────────────────────────────────────────────────────────────────────────
  // M3 — Auto-scroll ao trocar de thread ou load inicial
  // ──────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!scrollRef.current || messages.length === 0) return;

    const currentFirstMessageId = messages[0]?.id;
    const isInitialLoad = firstMessageIdRef.current === null;
    const threadChanged =
      firstMessageIdRef.current !== null &&
      firstMessageIdRef.current !== currentFirstMessageId;

    if (isInitialLoad || threadChanged) {
      isProgrammaticScrollRef.current = true;
      isAutoScrollingRef.current = true;
      shouldAutoScrollRef.current = true;
      scrollAttemptsRef.current = 0;

      mutationObserverRef.current?.disconnect();
      mutationObserverRef.current = null;
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);

      const scrollContainer = scrollRef.current;
      let lastScrollHeight = 0;
      let stabilityCheckCount = 0;
      const MAX_SCROLL_ATTEMPTS = 100;
      const STABILITY_THRESHOLD = 5;
      const CHECK_INTERVAL = 100;

      const scrollAndCheck = () => {
        if (!isAutoScrollingRef.current) return;
        if (
          !scrollContainer ||
          scrollAttemptsRef.current >= MAX_SCROLL_ATTEMPTS
        ) {
          scrollToAbsoluteBottom();
          setTimeout(() => {
            scrollToAbsoluteBottom();
            isProgrammaticScrollRef.current = false;
            isAutoScrollingRef.current = false;
            mutationObserverRef.current?.disconnect();
          }, 200);
          return;
        }

        scrollAttemptsRef.current++;
        const currentScrollHeight = scrollContainer.scrollHeight;
        scrollToAbsoluteBottom();

        if (currentScrollHeight === lastScrollHeight) {
          stabilityCheckCount++;
          if (stabilityCheckCount >= STABILITY_THRESHOLD) {
            const maxScrollTop =
              scrollContainer.scrollHeight - scrollContainer.clientHeight;
            const distanceFromBottom = maxScrollTop - scrollContainer.scrollTop;
            if (distanceFromBottom <= 10) {
              setTimeout(() => {
                scrollToAbsoluteBottom();
                isProgrammaticScrollRef.current = false;
                isAutoScrollingRef.current = false;
                mutationObserverRef.current?.disconnect();
              }, 200);
              return;
            }
            stabilityCheckCount = 0;
          }
        } else {
          stabilityCheckCount = 0;
          lastScrollHeight = currentScrollHeight;
        }

        scrollTimeoutRef.current = setTimeout(scrollAndCheck, CHECK_INTERVAL);
      };

      mutationObserverRef.current = new MutationObserver((mutations) => {
        if (mutations.length > 0) {
          scrollToAbsoluteBottom();
          stabilityCheckCount = 0;
        }
      });

      mutationObserverRef.current.observe(scrollContainer, {
        childList: true,
        subtree: true,
        attributes: true,
        characterData: true,
      });

      scrollToAbsoluteBottom();
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          scrollTimeoutRef.current = setTimeout(scrollAndCheck, 150);
        });
      });
    }

    firstMessageIdRef.current = currentFirstMessageId;
  }, [messages, scrollToAbsoluteBottom, isAtAbsoluteBottom]);

  // Cleanup ao desmontar
  useEffect(() => {
    return () => {
      mutationObserverRef.current?.disconnect();
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
    };
  }, []);

  // Refs de tracking para o auto-scroll de streaming
  const lastMessageCountRef = useRef(0);
  const lastContentRef = useRef("");

  // M3 — Auto-scroll durante streaming (se usuário não scrollou para cima)
  useEffect(() => {
    if (!scrollRef.current) return;

    const lastMessage = messages[messages.length - 1];
    const currentContent = lastMessage?.content || "";
    const isNewMessage = messages.length > lastMessageCountRef.current;
    const isStreaming =
      currentContent !== lastContentRef.current && !isNewMessage;

    if (shouldAutoScrollRef.current && (isNewMessage || isStreaming)) {
      isProgrammaticScrollRef.current = true;

      if (shouldVirtualize) {
        // Com virtualização: rola para o último item via virtualizer
        virtualizer.scrollToIndex(messages.length - 1, { align: "end" });
      } else {
        scrollRef.current.scrollTo({
          top: scrollRef.current.scrollHeight,
          behavior: isStreaming ? "instant" : "auto",
        });
      }

      requestAnimationFrame(() => {
        isProgrammaticScrollRef.current = false;
      });
    }

    lastMessageCountRef.current = messages.length;
    lastContentRef.current = currentContent;
  }, [messages, shouldVirtualize, virtualizer]);

  // M3 — Detecta scroll manual do usuário
  const handleScroll = useCallback(() => {
    if (!scrollRef.current || isProgrammaticScrollRef.current) return;

    const currentScrollTop = scrollRef.current.scrollTop;
    const atBottom = isAtBottom();

    // Cancela auto-scroll se usuário scrollou para cima durante streaming
    if (isAutoScrollingRef.current) {
      if (currentScrollTop < lastScrollTopRef.current) {
        cancelAutoScroll();
        shouldAutoScrollRef.current = false;
      }
    }

    lastScrollTopRef.current = currentScrollTop;
    // M3 — mostra botão "Voltar ao fim"
    setShowScrollButton(!atBottom);
    shouldAutoScrollRef.current = atBottom;
  }, [isAtBottom, cancelAutoScroll]);

  // M3 — Botão "Voltar ao fim"
  const scrollToBottom = useCallback(() => {
    if (!scrollRef.current) return;
    isProgrammaticScrollRef.current = true;
    shouldAutoScrollRef.current = true;
    setShowScrollButton(false);

    if (shouldVirtualize) {
      virtualizer.scrollToIndex(messages.length - 1, { align: "end" });
    } else {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight - scrollRef.current.clientHeight,
        behavior: "smooth",
      });
    }

    setTimeout(() => {
      if (scrollRef.current)
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      isProgrammaticScrollRef.current = false;
    }, 400);
  }, [shouldVirtualize, virtualizer, messages.length]);

  // ──────────────────────────────────────────────────────────────────────────
  // A.2d — humanMessageRevIdx: índice reverso de cada mensagem do usuário
  // (0 = última, 1 = penúltima, …). Mapeia message.id → índice para o rewind.
  // ──────────────────────────────────────────────────────────────────────────

  const humanMessageRevIdx = useMemo(() => {
    const map = new Map<string, number>();
    const userMsgs = messages.filter((m) => m.role === "user");
    userMsgs.forEach((m, i) => {
      map.set(m.id, userMsgs.length - 1 - i);
    });
    return map;
  }, [messages]);

  // ──────────────────────────────────────────────────────────────────────────
  // Props comuns para cada MessageItem
  // ──────────────────────────────────────────────────────────────────────────

  const commonItemProps = {
    showToolCalls,
    isRegenerating,
    copiedId,
    onCopy,
    onRegenerate,
    onEditAndRerun,
    feedbackComment,
    showCommentInput,
    onFeedback,
    onSubmitComment,
    onCancelComment,
    onToggleComment,
    setFeedbackComment,
    isDevMode,
    onHitlDecision,
    threadId,
    onRetry,
    workspaceId,
    compact,
  };

  // ──────────────────────────────────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────────────────────────────────

  return (
    <>
      <style>{`
        @keyframes slideInUp {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes slideInButton {
          from {
            opacity: 0;
            transform: translateY(10px) scale(0.9);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .scroll-button {
          animation: slideInButton 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}</style>

      <div
        className="flex-1 overflow-y-auto custom-scrollbar relative"
        ref={scrollRef}
        onScroll={handleScroll}
        aria-live="polite"
        aria-busy={isLoadingThread}
        aria-label="Messages"
        style={{
          willChange: "scroll-position",
          contain: "layout style paint",
          WebkitOverflowScrolling: "touch",
        }}
      >
        {/* M4 — Skeletons de carregamento */}
        {isLoadingThread ? (
          <MessageSkeletons />
        ) : shouldVirtualize ? (
          // M1 — Renderização virtualizada (> 50 mensagens)
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((vItem) => {
              const message = messages[vItem.index]!;
              const isLastMessage = vItem.index === messages.length - 1;
              return (
                <div
                  key={vItem.key}
                  data-index={vItem.index}
                  ref={virtualizer.measureElement}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${vItem.start}px)`,
                  }}
                >
                  <div
                    className="w-full max-w-4xl mx-auto px-4 sm:px-6 py-3"
                    style={{
                      animation:
                        isLastMessage && message.role === "user"
                          ? "slideInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)"
                          : "none",
                    }}
                  >
                    <MessageItem
                      message={message}
                      isLastAssistant={message.id === lastAssistantId}
                      humanMessageIndex={humanMessageRevIdx.get(message.id)}
                      {...commonItemProps}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          // Renderização direta (≤ 50 mensagens)
          <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-5 space-y-2">
            {messages.map((message, idx) => {
              const isLastMessage = idx === messages.length - 1;
              return (
                <div
                  key={message.id}
                  style={{
                    animation:
                      isLastMessage && message.role === "user"
                        ? "slideInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)"
                        : "none",
                  }}
                >
                  <MessageItem
                    message={message}
                    isLastAssistant={message.id === lastAssistantId}
                    humanMessageIndex={humanMessageRevIdx.get(message.id)}
                    {...commonItemProps}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* M3 — Botão "Voltar ao fim" */}
      {showScrollButton && !isLoadingThread && (
        <button
          onClick={scrollToBottom}
          // absolute (não fixed): posiciona relativo ao container de
          // mensagens (que já é `relative`, ver acima), não ao viewport —
          // evita sobrepor a nav rail do workbench quando ele está aberto.
          className="scroll-button absolute bottom-32 right-4 sm:right-8 p-3 rounded-full shadow-lg hover:scale-110 active:scale-95 transition-transform z-50 bg-primary text-primary-foreground"
          aria-label="Voltar ao fim"
        >
          <ArrowDown className="w-5 h-5" />
        </button>
      )}
    </>
  );
});
