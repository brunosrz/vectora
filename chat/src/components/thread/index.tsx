"use client";

import { v4 as uuidv4 } from "uuid";
import { ReactNode, useEffect, useRef, useState, FormEvent } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useStreamContext } from "@/providers/Stream";
import { Button } from "../ui/button";
import { Checkpoint, Message } from "@langchain/langgraph-sdk";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
import {
  DO_NOT_RENDER_ID_PREFIX,
  ensureToolCallsHaveResponses,
} from "@/lib/ensure-tool-responses";
import { TooltipIconButton } from "./tooltip-icon-button";
import {
  ArrowDown,
  LoaderCircle,
  PanelRightOpen,
  PanelRightClose,
  SquarePen,
  Network,
  MessageSquare,
  BarChart2,
  Sun,
  Moon,
  Info,
} from "lucide-react";
import { useQueryState, parseAsBoolean } from "nuqs";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import ThreadHistory from "./history";
import { toast } from "sonner";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useTheme } from "next-themes";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { GraphView } from "./GraphView";
import { MetricsPanel, MetricsBadges } from "./MetricsPanel";

// ── Vectora logo ──────────────────────────────────────────────────────────────

function VectoraLogo({ size = 32 }: { size?: number }) {
  return (
    <img
      src="/vectora.svg"
      alt="Vectora Logo"
      width={size}
      height={size}
      className="rounded-lg shadow-sm"
    />
  );
}

// ── Theme Toggle ──────────────────────────────────────────────────────────────

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="p-2 w-9 h-9" />;

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="p-2 rounded-md transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:text-gray-400"
    >
      {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}

// ── Tab type ──────────────────────────────────────────────────────────────────

type ActiveTab = "chat" | "graph";

// ── Layout helpers ────────────────────────────────────────────────────────────

function StickyToBottomContent(props: {
  content: ReactNode;
  footer?: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  const context = useStickToBottomContext();
  return (
    <div
      ref={context.scrollRef}
      style={{ width: "100%", height: "100%" }}
      className={props.className}
    >
      <div ref={context.contentRef} className={props.contentClassName}>
        {props.content}
      </div>
      {props.footer}
    </div>
  );
}

function ScrollToBottom(props: { className?: string }) {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();
  if (isAtBottom) return null;
  return (
    <Button
      variant="outline"
      className={props.className}
      onClick={() => scrollToBottom()}
    >
      <ArrowDown className="w-4 h-4" />
      <span>Scroll to bottom</span>
    </Button>
  );
}

// ── Thread ─────────────────────────────────────────────────────────────────────

export function Thread() {
  const [threadId, setThreadId] = useQueryState("threadId");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );
  const [hideToolCalls, setHideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );
  const [input, setInput] = useState("");
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [metricsOpen, setMetricsOpen] = useState(false);
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");

  const stream = useStreamContext();
  const messages = stream.messages;
  const isLoading = stream.isLoading;

  // Obter config do contexto (via setup ou defaults)
  const apiUrl = stream.apiUrl;
  const assistantId = stream.assistantId;

  const lastError = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    try {
      const message = (stream.error as { message?: string }).message;
      if (!message || lastError.current === message) return;
      lastError.current = message;
      toast.error("Ocorreu um erro. Tente novamente.", {
        description: (
          <p>
            <strong>Erro:</strong> <code>{message}</code>
          </p>
        ),
        richColors: true,
        closeButton: true,
      });
    } catch {
      // no-op
    }
  }, [stream.error]);

  const prevMessageLength = useRef(0);
  useEffect(() => {
    if (
      messages.length !== prevMessageLength.current &&
      messages?.length &&
      messages[messages.length - 1].type === "ai"
    ) {
      setFirstTokenReceived(true);
    }
    prevMessageLength.current = messages.length;
  }, [messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // ── Slash commands support ──────────────────────────────────────────────
    if (input.startsWith("/")) {
      const parts = input.trim().split(" ");
      const cmd = parts[0].toLowerCase();
      
      if (cmd === "/help" || cmd === "/list") {
        toast.info("Comandos do Vectora", {
          description: (
            <div className="text-xs space-y-1 mt-2">
              <p><strong>/help</strong>, <strong>/list</strong> — mostra esta lista</p>
              <p><strong>/new</strong> — inicia uma nova conversa</p>
              <p><strong>/clear</strong> — limpa o ID da sessão atual</p>
              <p><strong>/model</strong> — abre configurações de modelo</p>
              <p><strong>/rag</strong> — informações sobre a base de conhecimento</p>
            </div>
          ),
          duration: 5000,
        });
        setInput("");
        return;
      }
      
      if (cmd === "/new" || cmd === "/clear") {
        setThreadId(null);
        setInput("");
        toast.success("Sessão reiniciada");
        return;
      }

      if (cmd === "/model") {
        // Force setup screen to show
        const url = new URL(window.location.href);
        url.searchParams.set("setup", "true");
        window.history.pushState({}, "", url.toString());
        // For immediate effect we'll reload or use a simpler trick
        window.location.search = "?setup=true";
        return;
      }
    }

    setFirstTokenReceived(false);

    const newHumanMessage: Message = {
      id: uuidv4(),
      type: "human",
      content: input,
    };

    const toolMessages = ensureToolCallsHaveResponses(stream.messages);
    stream.submit(
      { messages: [...toolMessages, newHumanMessage] },
      {
        streamMode: ["values"],
        optimisticValues: (prev) => ({
          ...prev,
          messages: [
            ...(prev.messages ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );

    setInput("");
  };

  const handleRegenerate = (
    parentCheckpoint: Checkpoint | null | undefined,
  ) => {
    prevMessageLength.current = prevMessageLength.current - 1;
    setFirstTokenReceived(false);
    stream.submit(undefined, {
      checkpoint: parentCheckpoint,
      streamMode: ["values"],
    });
  };

  const chatStarted = !!threadId || !!messages.length;
  const hasNoAIOrToolMessages = !messages.find(
    (m) => m.type === "ai" || m.type === "tool",
  );

  return (
    <div className="flex w-full h-screen overflow-hidden">
      {/* ── Thread History Sidebar ─────────────────────────────────────── */}
      <div className="relative lg:flex hidden">
        <motion.div
          className="absolute h-full border-r bg-white overflow-hidden z-20"
          style={{ width: 300 }}
          animate={{ x: chatHistoryOpen ? 0 : -300 }}
          initial={{ x: -300 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <div className="relative h-full" style={{ width: 300 }}>
            <ThreadHistory />
          </div>
        </motion.div>
      </div>

      {/* ── Main Chat Area ─────────────────────────────────────────────── */}
      <motion.div
        className={cn(
          "flex-1 flex flex-col min-w-0 overflow-hidden relative",
          !chatStarted && "grid-rows-[1fr]",
        )}
        layout={isLargeScreen}
        animate={{
          marginLeft: chatHistoryOpen ? (isLargeScreen ? 300 : 0) : 0,
          width: chatHistoryOpen
            ? isLargeScreen
              ? "calc(100% - 300px)"
              : "100%"
            : "100%",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        {!chatStarted && (
          <div className="absolute top-0 left-0 w-full flex items-center justify-between gap-3 p-2 pl-4 z-10">
            <div>
              {(!chatHistoryOpen || !isLargeScreen) && (
                <Button
                  className="hover:bg-gray-100"
                  variant="ghost"
                  onClick={() => setChatHistoryOpen((p) => !p)}
                >
                  {chatHistoryOpen ? (
                    <PanelRightOpen className="size-5" />
                  ) : (
                    <PanelRightClose className="size-5" />
                  )}
                </Button>
              )}
            </div>
          </div>
        )}

        {chatStarted && (
          <div className="flex items-center justify-between gap-3 p-2 z-10 relative border-b border-gray-100 dark:border-gray-800">
            {/* Left: history toggle + branding */}
            <div className="flex items-center justify-start gap-2 relative">
              <div className="absolute left-0 z-10">
                {(!chatHistoryOpen || !isLargeScreen) && (
                  <Button
                    className="hover:bg-gray-100 dark:hover:bg-gray-800"
                    variant="ghost"
                    onClick={() => setChatHistoryOpen((p) => !p)}
                  >
                    {chatHistoryOpen ? (
                      <PanelRightOpen className="size-5" />
                    ) : (
                      <PanelRightClose className="size-5" />
                    )}
                  </Button>
                )}
              </div>
              <motion.button
                className="flex gap-2 items-center cursor-pointer"
                onClick={() => setThreadId(null)}
                animate={{ marginLeft: !chatHistoryOpen ? 48 : 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              >
                <VectoraLogo size={28} />
                <span className="text-lg font-semibold tracking-tight text-indigo-700 dark:text-indigo-400">
                  Vectora
                </span>
              </motion.button>
            </div>

            {/* Center: tabs Chat | Graph */}
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-900 rounded-lg p-1">
              <button
                onClick={() => setActiveTab("chat")}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  activeTab === "chat"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
                )}
              >
                <MessageSquare className="size-4" />
                <span className="hidden sm:inline">Chat</span>
              </button>
              <button
                onClick={() => setActiveTab("graph")}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  activeTab === "graph"
                    ? "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm"
                    : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300",
                )}
              >
                <Network className="size-4" />
                <span className="hidden sm:inline">Grafo</span>
              </button>
            </div>

            {/* Right: metrics + new thread */}
            <div className="flex items-center gap-2">
              <ThemeToggle />
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => setMetricsOpen((p) => !p)}
                      className={cn(
                        "p-2 rounded-md transition-colors",
                        metricsOpen
                          ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
                          : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800",
                      )}
                    >
                      <BarChart2 className="size-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    <p>Métricas</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipIconButton
                size="lg"
                className="p-4"
                tooltip="Nova conversa"
                variant="ghost"
                onClick={() => setThreadId(null)}
              >
                <SquarePen className="size-5" />
              </TooltipIconButton>
            </div>

            <div className="absolute inset-x-0 top-full h-5 bg-gradient-to-b from-background to-background/0" />
          </div>
        )}

        {/* ── Mobile metrics badges ──────────────────────────────────── */}
        <div className="md:hidden">
          <MetricsBadges />
        </div>

        {/* ── Content area (Chat or Graph) ────────────────────────────── */}
        <div className="flex flex-1 overflow-hidden">
          {/* Metrics sidebar (desktop) */}
          {metricsOpen && isLargeScreen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 220, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="border-r border-gray-100 dark:border-gray-800 overflow-y-auto shrink-0 bg-white dark:bg-gray-950"
            >
              <MetricsPanel />
            </motion.div>
          )}

          {/* Graph tab */}
          {activeTab === "graph" && (
            <div className="flex-1 h-full hidden md:block bg-white dark:bg-gray-950">
              <GraphView assistantId={assistantId} apiUrl={apiUrl} />
            </div>
          )}

          {/* Graph not available on mobile */}
          {activeTab === "graph" && !isLargeScreen && (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-400 p-8 text-center bg-white dark:bg-gray-950">
              Visualização do grafo disponível apenas em telas maiores.
            </div>
          )}

          {/* Chat tab */}
          {activeTab === "chat" && (
            <StickToBottom className="relative flex-1 overflow-hidden bg-white dark:bg-gray-950">
              <StickyToBottomContent
                className={cn(
                  "absolute px-4 inset-0 overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 dark:[&::-webkit-scrollbar-thumb]:bg-gray-700 [&::-webkit-scrollbar-track]:bg-transparent",
                  !chatStarted && "flex flex-col items-stretch mt-[25vh]",
                  chatStarted && "grid grid-rows-[1fr_auto]",
                )}
                contentClassName="pt-8 pb-16 max-w-3xl mx-auto flex flex-col gap-4 w-full"
                content={
                  <>
                    {messages
                      .filter((m) => !m.id?.startsWith(DO_NOT_RENDER_ID_PREFIX))
                      .map((message, index) =>
                        message.type === "human" ? (
                          <HumanMessage
                            key={message.id || `${message.type}-${index}`}
                            message={message}
                            isLoading={isLoading}
                          />
                        ) : (
                          <AssistantMessage
                            key={message.id || `${message.type}-${index}`}
                            message={message}
                            isLoading={isLoading}
                            handleRegenerate={handleRegenerate}
                          />
                        ),
                      )}
                    {hasNoAIOrToolMessages && !!stream.interrupt && (
                      <AssistantMessage
                        key="interrupt-msg"
                        message={undefined}
                        isLoading={isLoading}
                        handleRegenerate={handleRegenerate}
                      />
                    )}
                    {isLoading && !firstTokenReceived && (
                      <AssistantMessageLoading />
                    )}
                  </>
                }
                footer={
                  <div className="sticky flex flex-col items-center gap-8 bottom-0 bg-white dark:bg-gray-950">
                    {!chatStarted && (
                      <div className="flex gap-3 items-center">
                        <VectoraLogo size={40} />
                        <h1 className="text-2xl font-semibold tracking-tight text-indigo-700 dark:text-indigo-400">
                          Vectora Chat
                        </h1>
                      </div>
                    )}

                    <ScrollToBottom className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 animate-in fade-in-0 zoom-in-95" />

                    <div className="bg-muted dark:bg-gray-900 rounded-2xl border dark:border-gray-800 shadow-xs mx-auto mb-8 w-full max-w-3xl relative z-10">
                      <form
                        onSubmit={handleSubmit}
                        className="grid grid-rows-[1fr_auto] gap-2 max-w-3xl mx-auto"
                      >
                        <textarea
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (
                              e.key === "Enter" &&
                              !e.shiftKey &&
                              !e.metaKey &&
                              !e.nativeEvent.isComposing
                            ) {
                              e.preventDefault();
                              const el = e.target as HTMLElement | undefined;
                              const form = el?.closest("form");
                              form?.requestSubmit();
                            }
                          }}
                          placeholder="Digite sua mensagem… (Enter para enviar, Shift+Enter para nova linha)"
                          className="p-3.5 pb-0 border-none bg-transparent field-sizing-content shadow-none ring-0 outline-none focus:outline-none focus:ring-0 resize-none text-gray-900 dark:text-gray-100 placeholder:text-gray-400"
                        />

                        <div className="flex items-center justify-between p-2 pt-4">
                          <div className="flex items-center space-x-2">
                            <Switch
                              id="render-tool-calls"
                              checked={hideToolCalls ?? false}
                              onCheckedChange={setHideToolCalls}
                            />
                            <Label
                              htmlFor="render-tool-calls"
                              className="text-sm text-gray-600 dark:text-gray-400"
                            >
                              Ocultar tool calls
                            </Label>
                          </div>
                          {stream.isLoading ? (
                            <Button key="stop" onClick={() => stream.stop()} variant="outline">
                              <LoaderCircle className="w-4 h-4 animate-spin mr-2" />
                              Cancelar
                            </Button>
                          ) : (
                            <Button
                              type="submit"
                              className="bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 transition-all shadow-md text-white"
                              disabled={isLoading || !input.trim()}
                            >
                              Enviar
                            </Button>
                          )}
                        </div>
                      </form>
                    </div>
                  </div>
                }
              />
            </StickToBottom>
          )}
        </div>
      </motion.div>
    </div>
  );
}
