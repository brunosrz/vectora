"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Square,
  Terminal,
  X,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useChatInputStore } from "@/lib/stores/chat-input-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { m as msg } from "@/lib/paraglide/messages";

interface LaunchConfig {
  name: string;
  runtimeExecutable: string;
  runtimeArgs: string[];
  port: number;
  env?: Record<string, string>;
}

interface ServerStatus {
  name: string;
  port: number;
  running: boolean;
  pid?: number | null;
}

interface BrowserTabProps {
  threadId: string;
}

/** Esqueleto do .vectora/launch.json enviado ao agente (formato Claude Code). */
const LAUNCH_JSON_TEMPLATE = `\`\`\`json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "<server-name>",
      "runtimeExecutable": "<command>",
      "runtimeArgs": ["<args>"],
      "port": <port>
    }
  ]
}
\`\`\``;

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

export function BrowserTab({ threadId: _threadId }: BrowserTabProps) {
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  // Presente só no desktop Electron — quando ausente, cai no `<iframe>` de
  // fallback abaixo (sujeito a X-Frame-Options, único caminho possível fora
  // do Electron). Ver electron/src/browser-view-manager.ts.
  const desktopBrowser =
    typeof window !== "undefined" ? window.vectora?.browserView : undefined;

  const [configs, setConfigs] = useState<LaunchConfig[]>([]);
  const [statuses, setStatuses] = useState<ServerStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showManualForm, setShowManualForm] = useState(false);
  const [serversCollapsed, setServersCollapsed] = useState(false);
  const [manual, setManual] = useState({
    name: "",
    runtimeExecutable: "",
    runtimeArgs: "",
    port: "",
  });
  const [consoleFor, setConsoleFor] = useState<string | null>(null);
  const [consoleLines, setConsoleLines] = useState<string[]>([]);
  const [consoleLoading, setConsoleLoading] = useState(false);

  // Navegação livre — histórico próprio (iframe cross-origin não expõe API
  // de histórico do navegador nativo pra fora), voltar/avançar operam sobre
  // ele. `history[historyIndex]` é a URL efetiva carregada no iframe.
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [urlInput, setUrlInput] = useState("");
  const [editingUrl, setEditingUrl] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  // Estado de navegação desktop — fonte de verdade é o Chromium (eventos do
  // WebContentsView via bridge), não um histórico replicado à mão como no
  // caminho web acima.
  const [viewId, setViewId] = useState<number | null>(null);
  const [desktopNav, setDesktopNav] = useState({
    url: "",
    canGoBack: false,
    canGoForward: false,
  });
  const [desktopLoading, setDesktopLoading] = useState(false);
  const [desktopLoadError, setDesktopLoadError] = useState<string | null>(null);
  const pendingNavigateRef = useRef<string | null>(null);
  const browserViewContainerRef = useRef<HTMLDivElement>(null);

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consolePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consoleLogRef = useRef<HTMLDivElement>(null);
  // Rastreia running por nome entre polls — só dispara auto-navegação na
  // transição false→true, nunca no primeiro poll (senão rouba o foco da
  // URL atual toda vez que a aba monta com um servidor já rodando).
  const prevRunningRef = useRef<Record<string, boolean> | null>(null);

  const currentUrl = desktopBrowser
    ? desktopNav.url
    : historyIndex >= 0
      ? history[historyIndex]
      : "";
  const canGoBack = desktopBrowser ? desktopNav.canGoBack : historyIndex > 0;
  const canGoForward = desktopBrowser
    ? desktopNav.canGoForward
    : historyIndex < history.length - 1;

  const navigate = useCallback(
    (raw: string) => {
      const url = normalizeUrl(raw);
      if (!url) return;
      if (desktopBrowser) {
        setDesktopNav((prev) => ({ ...prev, url }));
        if (viewId === null) {
          // View ainda não terminou de nascer (createView é async) — fica
          // pendente e é disparada assim que o id chegar, ver efeito abaixo.
          pendingNavigateRef.current = url;
          return;
        }
        void desktopBrowser.navigate(viewId, url).then((result) => {
          if (!result.ok) setDesktopLoadError(result.error ?? null);
        });
        return;
      }
      setHistory((prev) => {
        const base = prev.slice(0, historyIndexRef.current + 1);
        const next = [...base, url];
        historyIndexRef.current = next.length - 1;
        return next;
      });
      setHistoryIndex((i) => i + 1);
      setIframeKey((k) => k + 1);
    },
    [desktopBrowser, viewId],
  );

  // historyIndex muda via setState assíncrono — navigate() precisa do valor
  // atual síncrono pra cortar o histórico "à frente" corretamente quando o
  // usuário navega depois de ter voltado (senão duplicaria ramos velhos).
  const historyIndexRef = useRef(historyIndex);
  useEffect(() => {
    historyIndexRef.current = historyIndex;
  }, [historyIndex]);

  const goBack = useCallback(() => {
    if (!canGoBack) return;
    if (desktopBrowser && viewId !== null) {
      desktopBrowser.goBack(viewId);
      return;
    }
    setHistoryIndex((i) => i - 1);
    setIframeKey((k) => k + 1);
  }, [canGoBack, desktopBrowser, viewId]);

  const goForward = useCallback(() => {
    if (!canGoForward) return;
    if (desktopBrowser && viewId !== null) {
      desktopBrowser.goForward(viewId);
      return;
    }
    setHistoryIndex((i) => i + 1);
    setIframeKey((k) => k + 1);
  }, [canGoForward, desktopBrowser, viewId]);

  const refresh = useCallback(() => {
    if (desktopBrowser && viewId !== null) {
      desktopBrowser.reload(viewId);
      return;
    }
    setIframeKey((k) => k + 1);
  }, [desktopBrowser, viewId]);

  // Nasce a WebContentsView uma vez por montagem da aba e a destrói ao
  // desmontar (a aba já desmonta/remonta ao trocar de tab do workbench,
  // ver workbench-panel.tsx — não precisa de esconder/mostrar, só nascer e
  // morrer junto do componente).
  useEffect(() => {
    if (!desktopBrowser) return;
    let cancelled = false;
    let createdId: number | null = null;
    void desktopBrowser.createView().then((id) => {
      if (cancelled) {
        desktopBrowser.destroyView(id);
        return;
      }
      createdId = id;
      setViewId(id);
      if (pendingNavigateRef.current) {
        void desktopBrowser.navigate(id, pendingNavigateRef.current);
        pendingNavigateRef.current = null;
      }
    });
    return () => {
      cancelled = true;
      if (createdId !== null) desktopBrowser.destroyView(createdId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Espelha os eventos de navegação nativos do Chromium (fonte de verdade)
  // pro estado React — nunca escreve em desktopNav fora daqui, exceto a
  // atualização otimista de `url` em navigate() acima (feedback imediato na
  // barra antes do evento `navigated` real chegar).
  useEffect(() => {
    if (!desktopBrowser || viewId === null) return;
    return desktopBrowser.onEvent((eventViewId, event) => {
      if (eventViewId !== viewId) return;
      if (event.type === "navigated") {
        setDesktopNav({
          url: event.url,
          canGoBack: event.canGoBack,
          canGoForward: event.canGoForward,
        });
        setDesktopLoadError(null);
      } else if (event.type === "loadingChanged") {
        setDesktopLoading(event.isLoading);
      } else if (event.type === "loadFailed") {
        setDesktopLoadError(event.errorDescription);
      }
    });
  }, [desktopBrowser, viewId]);

  // Reporta os bounds reais do container (ResizeObserver) pro main process
  // posicionar a WebContentsView por cima — só existe depois da primeira
  // navegação (currentUrl truthy é quando o container abaixo é renderizado).
  // Depende de `hasUrl` (booleano), não da URL em si — o container é o
  // mesmo nó DOM entre navegações subsequentes, reanexar o observer a cada
  // troca de URL só piscaria a view escondendo/reexibindo à toa.
  const hasUrl = Boolean(currentUrl);
  useEffect(() => {
    if (!desktopBrowser || viewId === null || !hasUrl) return;
    const el = browserViewContainerRef.current;
    if (!el) return;
    desktopBrowser.setVisible(viewId, true);
    const report = () => {
      const rect = el.getBoundingClientRect();
      desktopBrowser.setBounds(viewId, {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    };
    report();
    const observer = new ResizeObserver(report);
    observer.observe(el);
    window.addEventListener("resize", report);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", report);
      desktopBrowser.setVisible(viewId, false);
    };
  }, [desktopBrowser, viewId, hasUrl]);

  const fetchLaunch = useCallback(async () => {
    if (!wsId) return;
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/browser/launch`,
      );
      if (res.ok) {
        const data = (await res.json()) as { configurations: LaunchConfig[] };
        setConfigs(data.configurations ?? []);
      }
    } catch {
      // silently ignore
    } finally {
      setIsLoading(false);
    }
  }, [wsId]);

  const fetchStatus = useCallback(async (): Promise<ServerStatus[] | null> => {
    if (!wsId) return null;
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/browser/status`,
      );
      if (res.ok) {
        const data = (await res.json()) as { servers: ServerStatus[] };
        const servers = data.servers ?? [];
        setStatuses(servers);

        // Auto-navegação: qualquer servidor que passe de parado pra rodando
        // entre um poll e outro abre sozinho na URL bar — funciona tanto pro
        // clique manual (handleStart) quanto pra tool `browser_start` do
        // agente, que sobe o servidor sem passar por nenhum handler do UI.
        const prevRunning = prevRunningRef.current;
        const nextRunning: Record<string, boolean> = {};
        for (const server of servers) {
          nextRunning[server.name] = server.running;
          if (prevRunning && server.running && !prevRunning[server.name]) {
            navigate(`http://localhost:${server.port}`);
          }
        }
        prevRunningRef.current = nextRunning;

        return servers;
      }
    } catch {
      // silently ignore
    }
    return null;
  }, [wsId, navigate]);

  const fetchConsoleLogs = useCallback(
    async (name: string) => {
      if (!wsId) return;
      setConsoleLoading(true);
      try {
        const res = await fetch(
          `/workspaces/${encodeURIComponent(wsId)}/browser/logs?name=${encodeURIComponent(name)}`,
        );
        if (res.ok) {
          const data = (await res.json()) as { lines: string[] };
          setConsoleLines(data.lines ?? []);
        }
      } catch {
        // silently ignore — o painel continua com as últimas linhas conhecidas
      } finally {
        setConsoleLoading(false);
      }
    },
    [wsId],
  );

  useEffect(() => {
    if (!consoleFor) {
      if (consolePollRef.current) clearInterval(consolePollRef.current);
      return;
    }
    fetchConsoleLogs(consoleFor);
    consolePollRef.current = setInterval(
      () => fetchConsoleLogs(consoleFor),
      3000,
    );
    return () => {
      if (consolePollRef.current) clearInterval(consolePollRef.current);
    };
  }, [consoleFor, fetchConsoleLogs]);

  useEffect(() => {
    const el = consoleLogRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [consoleLines]);

  useEffect(() => {
    fetchLaunch();
  }, [fetchLaunch]);

  useEffect(() => {
    if (!wsId || configs.length === 0) return;
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [wsId, configs.length, fetchStatus]);

  const saveConfigs = useCallback(
    async (next: LaunchConfig[]) => {
      const saveRes = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/browser/launch`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version: "0.0.1", configurations: next }),
        },
      );
      if (saveRes.ok) {
        setConfigs(next);
        fetchStatus();
      }
      return saveRes.ok;
    },
    [wsId, fetchStatus],
  );

  const handleAskAgent = useCallback(() => {
    const prompt = [
      msg.workbench_browser_ask_agent_prompt(),
      LAUNCH_JSON_TEMPLATE,
      msg.workbench_browser_ask_agent_note(),
    ].join("\n\n");
    useChatInputStore.getState().pushDraft(prompt);
  }, []);

  const handleManualSave = async () => {
    if (!wsId || !manual.name.trim() || !manual.runtimeExecutable.trim())
      return;
    const port = Number.parseInt(manual.port, 10);
    const cfg: LaunchConfig = {
      name: manual.name.trim(),
      runtimeExecutable: manual.runtimeExecutable.trim(),
      runtimeArgs: manual.runtimeArgs.trim()
        ? manual.runtimeArgs.trim().split(/\s+/)
        : [],
      port: Number.isFinite(port) ? port : 3000,
    };
    const ok = await saveConfigs([
      ...configs.filter((c) => c.name !== cfg.name),
      cfg,
    ]);
    if (ok) {
      setManual({ name: "", runtimeExecutable: "", runtimeArgs: "", port: "" });
      setShowManualForm(false);
    }
  };

  const handleStart = async (cfg: LaunchConfig) => {
    if (!wsId) return;
    setActionLoading(cfg.name);
    try {
      // POST bloqueia no backend até a porta abrir (ou ~15s de timeout) —
      // não precisa de espera fixa aqui; o status refletido já é real.
      // A navegação automática acontece dentro de fetchStatus() (transição
      // false→true), o mesmo caminho usado quando o servidor sobe via tool
      // do agente — não duplica lógica aqui.
      await fetch(`/workspaces/${encodeURIComponent(wsId)}/browser/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cfg.name }),
      });
      await fetchStatus();
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (name: string) => {
    if (!wsId) return;
    setActionLoading(name);
    try {
      await fetch(`/workspaces/${encodeURIComponent(wsId)}/browser/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      await fetchStatus();
    } finally {
      setActionLoading(null);
    }
  };

  const getStatus = (name: string): ServerStatus | undefined =>
    statuses.find((s) => s.name === name);

  // `allow-same-origin` junto de `allow-scripts` é a combinação clássica de
  // sandbox-escape (o conteúdo do iframe passa a poder acessar/manipular o
  // document do pai) — só é seguro pra um servidor de dev do próprio
  // workspace (processo local do usuário, mesma confiança que terminal/PTY
  // já assumem), nunca pra navegação livre a um site externo qualquer.
  // Sem esse flag, o iframe recebe origem opaca mesmo pra localhost, o que
  // faz o Next.js (allowedDevOrigins) bloquear os assets — daí o CSS sumir.
  const isTrustedWorkspaceServer = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      if (parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1")
        return false;
      const port = parsed.port
        ? Number.parseInt(parsed.port, 10)
        : parsed.protocol === "https:"
          ? 443
          : 80;
      return configs.some((c) => c.port === port);
    } catch {
      return false;
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const manualForm = (
    <div className="w-full max-w-[260px] space-y-1.5 rounded-md border border-border/60 bg-card/40 p-2 text-left">
      <Input
        value={manual.name}
        onChange={(e) => setManual((m) => ({ ...m, name: e.target.value }))}
        placeholder={msg.workbench_browser_field_name()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.runtimeExecutable}
        onChange={(e) =>
          setManual((m) => ({ ...m, runtimeExecutable: e.target.value }))
        }
        placeholder={msg.workbench_browser_field_executable()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.runtimeArgs}
        onChange={(e) =>
          setManual((m) => ({ ...m, runtimeArgs: e.target.value }))
        }
        placeholder={msg.workbench_browser_field_args()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.port}
        onChange={(e) => setManual((m) => ({ ...m, port: e.target.value }))}
        placeholder={msg.workbench_browser_field_port()}
        inputMode="numeric"
        className="h-7 text-xs"
      />
      <div className="flex gap-1 pt-0.5">
        <Button
          size="sm"
          onClick={handleManualSave}
          disabled={!manual.name.trim() || !manual.runtimeExecutable.trim()}
          className="h-7 flex-1 text-xs"
        >
          {msg.workbench_browser_manual_save()}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setShowManualForm(false)}
          className="h-7 text-xs"
        >
          {msg.workbench_browser_manual_cancel()}
        </Button>
      </div>
    </div>
  );

  const serverFavorites = configs.length > 0 && (
    <div className="shrink-0 border-b border-border/60 bg-card/40 px-3 py-2 space-y-1.5">
      <div className="flex w-full items-center justify-between">
        <button
          className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => setServersCollapsed((v) => !v)}
          title={
            serversCollapsed
              ? msg.workbench_browser_servers_expand()
              : msg.workbench_browser_servers_collapse()
          }
        >
          {serversCollapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
          {msg.workbench_browser_servers()}
        </button>
        <button
          onClick={() => setShowManualForm((v) => !v)}
          className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          title={msg.workbench_browser_manual_add()}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
      {!serversCollapsed && showManualForm && (
        <div className="pb-1">{manualForm}</div>
      )}
      {!serversCollapsed &&
        configs.map((cfg) => {
          const status = getStatus(cfg.name);
          const isRunning = status?.running ?? false;
          // `running` reflete só a porta estar aberta (qualquer processo,
          // de qualquer config) — `pid` só existe quando ESTE config foi
          // quem de fato subiu o processo rastreado pelo Vectora. Sem essa
          // distinção, dois configs que colidem na mesma porta (ex.: "API
          // (Local)" e o serviço web de "Full Stack (Turbo)" configurados
          // pro mesmo 3333) mostravam os dois como "rodando", com um botão
          // de parar que não fazia nada (nenhum processo rastreado sob
          // aquele nome pra matar).
          const isManaged = status?.pid != null;
          const isAction = actionLoading === cfg.name;
          const isActive = currentUrl === `http://localhost:${cfg.port}`;

          return (
            <div
              key={cfg.name}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent/40 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`h-1.5 w-1.5 rounded-full shrink-0 ${isRunning ? "bg-green-500" : "bg-muted-foreground/40"}`}
                  />
                  <span className="text-xs font-medium truncate">
                    {cfg.name}
                  </span>
                  {isRunning && (
                    <span className="text-[10px] text-muted-foreground">
                      :{cfg.port}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-muted-foreground/60 truncate pl-3">
                  {cfg.runtimeExecutable} {cfg.runtimeArgs.join(" ")}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-6 w-6"
                  title={msg.workbench_browser_console()}
                  onClick={() => setConsoleFor(cfg.name)}
                >
                  <Terminal className="h-3 w-3" />
                </Button>
                {isRunning && (
                  <Button
                    size="icon"
                    variant={isActive ? "secondary" : "ghost"}
                    className="h-6 w-6"
                    title={msg.workbench_browser_open_server()}
                    onClick={() => navigate(`http://localhost:${cfg.port}`)}
                  >
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                )}
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-6 w-6"
                  disabled={isAction || (isRunning && !isManaged)}
                  onClick={() =>
                    isRunning ? handleStop(cfg.name) : handleStart(cfg)
                  }
                  title={
                    isRunning
                      ? isManaged
                        ? msg.workbench_browser_stop()
                        : msg.workbench_browser_running_external()
                      : msg.workbench_browser_start()
                  }
                >
                  {isAction ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : isRunning ? (
                    <Square className="h-3 w-3 fill-current" />
                  ) : (
                    <Play className="h-3 w-3 fill-current" />
                  )}
                </Button>
              </div>
            </div>
          );
        })}
    </div>
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {serverFavorites}

      {/* Barra de navegação — sempre ativa, não depende de nenhum servidor */}
      <div className="flex items-center gap-1 border-b border-border/60 bg-card/20 px-2 py-1">
        <button
          className="rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors disabled:opacity-30 disabled:pointer-events-none"
          onClick={goBack}
          disabled={!canGoBack}
          title={msg.workbench_browser_back()}
        >
          <ArrowLeft className="h-3 w-3" />
        </button>
        <button
          className="rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors disabled:opacity-30 disabled:pointer-events-none"
          onClick={goForward}
          disabled={!canGoForward}
          title={msg.workbench_browser_forward()}
        >
          <ArrowRight className="h-3 w-3" />
        </button>
        <button
          className="rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors disabled:opacity-30 disabled:pointer-events-none"
          onClick={refresh}
          disabled={!currentUrl}
          title={msg.workbench_files_refresh()}
        >
          {desktopLoading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <RefreshCw className="h-3 w-3" />
          )}
        </button>
        <input
          type="text"
          data-testid="browser-url-bar"
          className="flex-1 min-w-0 bg-background/80 border border-border/40 rounded px-2 py-0.5 text-[11px] font-mono text-foreground focus:outline-none focus:border-primary/60"
          value={editingUrl ? urlInput : currentUrl}
          placeholder={msg.workbench_browser_url_placeholder()}
          onFocus={() => {
            setEditingUrl(true);
            setUrlInput(currentUrl);
          }}
          onBlur={() => setEditingUrl(false)}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              navigate(urlInput);
              (e.target as HTMLInputElement).blur();
            }
          }}
        />
        <a
          href={currentUrl || undefined}
          target="_blank"
          rel="noreferrer"
          aria-disabled={!currentUrl}
          className={`rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors ${!currentUrl ? "opacity-30 pointer-events-none" : ""}`}
          title={msg.workbench_browser_open_external()}
        >
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      <div className="flex-1 min-h-0 flex flex-col">
        {desktopLoadError && (
          <div className="shrink-0 border-b border-destructive/40 bg-destructive/10 px-3 py-1.5 text-[11px] text-destructive">
            {desktopLoadError}
          </div>
        )}
        {currentUrl ? (
          desktopBrowser ? (
            // WebContentsView real (Electron) desenhada pelo main process por
            // cima deste espaço reservado — este div fica sempre vazio, é só
            // a referência de bounds (ver o efeito de ResizeObserver acima).
            <div
              ref={browserViewContainerRef}
              data-testid="browser-webcontentsview-container"
              className="flex-1 w-full bg-white"
            />
          ) : (
            <iframe
              ref={iframeRef}
              key={iframeKey}
              src={currentUrl}
              className="flex-1 w-full border-0 bg-white"
              title="Browser"
              sandbox={
                isTrustedWorkspaceServer(currentUrl)
                  ? "allow-scripts allow-forms allow-modals allow-popups allow-same-origin"
                  : "allow-scripts allow-forms allow-modals allow-popups"
              }
            />
          )
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center pb-[18%] gap-3 p-4 text-center">
            <Zap className="h-8 w-8 text-muted-foreground/40 shrink-0" />
            <div className="min-w-0 max-w-[260px]">
              <p className="text-sm font-medium text-foreground leading-snug">
                {msg.workbench_browser_empty_title()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                {msg.workbench_browser_empty_description()}
              </p>
            </div>
            {configs.length === 0 &&
              (showManualForm ? (
                manualForm
              ) : (
                <div className="flex w-full max-w-[220px] flex-col gap-1.5">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={handleAskAgent}
                    className="gap-1.5 w-full h-auto py-1.5 px-3"
                  >
                    <Sparkles className="h-3.5 w-3.5 shrink-0" />
                    <span className="text-xs">
                      {msg.workbench_browser_ask_agent()}
                    </span>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowManualForm(true)}
                    className="gap-1.5 w-full h-auto py-1.5 px-3"
                  >
                    <Plus className="h-3.5 w-3.5 shrink-0" />
                    <span className="text-xs">
                      {msg.workbench_browser_manual_add()}
                    </span>
                  </Button>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Painel de console inline — dentro do fluxo da própria aba, não um
          portal/dialog (senão sobrepõe a janela inteira em vez de dividir
          o espaço com o iframe acima). */}
      {consoleFor !== null && (
        <div className="flex h-56 shrink-0 flex-col border-t border-border/60 bg-background">
          <div className="flex shrink-0 items-center justify-between border-b border-border/60 px-4 py-2">
            <span className="text-xs font-medium text-foreground">
              {msg.workbench_browser_console_title({ name: consoleFor })}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => consoleFor && fetchConsoleLogs(consoleFor)}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                title={msg.workbench_browser_console_refresh()}
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${consoleLoading ? "animate-spin" : ""}`}
                />
              </button>
              <button
                onClick={() => setConsoleFor(null)}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                title={msg.workbench_browser_console_close()}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div
            ref={consoleLogRef}
            className="flex-1 overflow-y-auto bg-background px-4 py-2 font-mono text-[11px] leading-relaxed text-foreground/90"
          >
            {consoleLines.length === 0 ? (
              <p className="text-muted-foreground">
                {msg.workbench_browser_console_empty()}
              </p>
            ) : (
              consoleLines.map((line, i) => (
                <div key={i} className="whitespace-pre-wrap break-all">
                  {line}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
