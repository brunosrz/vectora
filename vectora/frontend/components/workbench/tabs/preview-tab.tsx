"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ExternalLink,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Square,
  Terminal,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent } from "@/components/ui/sheet";
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

interface PreviewTabProps {
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

export function PreviewTab({ threadId: _threadId }: PreviewTabProps) {
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  const [configs, setConfigs] = useState<LaunchConfig[]>([]);
  const [statuses, setStatuses] = useState<ServerStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeServer, setActiveServer] = useState<ServerStatus | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [urlOverride, setUrlOverride] = useState<string>("");
  const [showUrlBar, setShowUrlBar] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manual, setManual] = useState({
    name: "",
    runtimeExecutable: "",
    runtimeArgs: "",
    port: "",
  });
  const [consoleFor, setConsoleFor] = useState<string | null>(null);
  const [consoleLines, setConsoleLines] = useState<string[]>([]);
  const [consoleLoading, setConsoleLoading] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consolePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consoleLogRef = useRef<HTMLDivElement>(null);

  const fetchLaunch = useCallback(async () => {
    if (!wsId) return;
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/preview/launch`,
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
        `/workspaces/${encodeURIComponent(wsId)}/preview/status`,
      );
      if (res.ok) {
        const data = (await res.json()) as { servers: ServerStatus[] };
        const servers = data.servers ?? [];
        setStatuses(servers);
        if (activeServer) {
          const updated = servers.find((s) => s.name === activeServer.name);
          if (updated) setActiveServer(updated);
        }
        return servers;
      }
    } catch {
      // silently ignore
    }
    return null;
  }, [wsId, activeServer]);

  const fetchConsoleLogs = useCallback(
    async (name: string) => {
      if (!wsId) return;
      setConsoleLoading(true);
      try {
        const res = await fetch(
          `/workspaces/${encodeURIComponent(wsId)}/preview/logs?name=${encodeURIComponent(name)}`,
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
        `/workspaces/${encodeURIComponent(wsId)}/preview/launch`,
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
      msg.workbench_preview_ask_agent_prompt(),
      LAUNCH_JSON_TEMPLATE,
      msg.workbench_preview_ask_agent_note(),
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
      await fetch(`/workspaces/${encodeURIComponent(wsId)}/preview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cfg.name }),
      });
      const servers = await fetchStatus();
      const status = servers?.find((s) => s.name === cfg.name);
      if (status) setActiveServer(status);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (name: string) => {
    if (!wsId) return;
    setActionLoading(name);
    try {
      await fetch(`/workspaces/${encodeURIComponent(wsId)}/preview/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      await fetchStatus();
      if (activeServer?.name === name) setActiveServer(null);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatus = (name: string): ServerStatus | undefined =>
    statuses.find((s) => s.name === name);

  // Só navega o iframe quando o backend confirmou a porta aberta — evita o
  // ERR_CONNECTION_REFUSED de apontar pra um dev server ainda compilando.
  const activeUrl =
    activeServer && activeServer.running
      ? `http://localhost:${activeServer.port}`
      : null;
  const activeServerStarting = Boolean(activeServer && !activeServer.running);

  const effectiveUrl = urlOverride || activeUrl || "";

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
        placeholder={msg.workbench_preview_field_name()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.runtimeExecutable}
        onChange={(e) =>
          setManual((m) => ({ ...m, runtimeExecutable: e.target.value }))
        }
        placeholder={msg.workbench_preview_field_executable()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.runtimeArgs}
        onChange={(e) =>
          setManual((m) => ({ ...m, runtimeArgs: e.target.value }))
        }
        placeholder={msg.workbench_preview_field_args()}
        className="h-7 text-xs"
      />
      <Input
        value={manual.port}
        onChange={(e) => setManual((m) => ({ ...m, port: e.target.value }))}
        placeholder={msg.workbench_preview_field_port()}
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
          {msg.workbench_preview_manual_save()}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setShowManualForm(false)}
          className="h-7 text-xs"
        >
          {msg.workbench_preview_manual_cancel()}
        </Button>
      </div>
    </div>
  );

  if (configs.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center pb-[18%] gap-3 p-4 text-center">
        <Zap className="h-8 w-8 text-muted-foreground/40 shrink-0" />
        <div className="min-w-0 max-w-[220px]">
          <p className="text-sm font-medium text-foreground leading-snug">
            {msg.workbench_preview_empty_title()}
          </p>
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
            {msg.workbench_preview_empty_description()}
          </p>
        </div>
        {showManualForm ? (
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
                {msg.workbench_preview_ask_agent()}
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
                {msg.workbench_preview_manual_add()}
              </span>
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Painel de controle dos servidores */}
      <div className="shrink-0 border-b border-border/60 bg-card/40 px-3 py-2 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {msg.workbench_preview_servers()}
          </span>
          <button
            onClick={() => setShowManualForm((v) => !v)}
            className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            title={msg.workbench_preview_manual_add()}
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>
        {showManualForm && <div className="pb-1">{manualForm}</div>}
        {configs.map((cfg) => {
          const status = getStatus(cfg.name);
          const isRunning = status?.running ?? false;
          const isAction = actionLoading === cfg.name;
          const isActive = activeServer?.name === cfg.name;

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
                  title={msg.workbench_preview_console()}
                  onClick={() => setConsoleFor(cfg.name)}
                >
                  <Terminal className="h-3 w-3" />
                </Button>
                {isRunning && (
                  <Button
                    size="icon"
                    variant={isActive ? "secondary" : "ghost"}
                    className="h-6 w-6"
                    title={msg.workbench_preview_open_preview()}
                    onClick={() => {
                      setActiveServer(status ?? null);
                      setUrlOverride("");
                      setIframeKey((k) => k + 1);
                    }}
                  >
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                )}
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-6 w-6"
                  disabled={isAction}
                  onClick={() =>
                    isRunning ? handleStop(cfg.name) : handleStart(cfg)
                  }
                  title={
                    isRunning
                      ? msg.workbench_preview_stop()
                      : msg.workbench_preview_start()
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

      {/* URL bar + iframe */}
      {effectiveUrl ? (
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex items-center gap-1 border-b border-border/60 bg-card/20 px-2 py-1">
            <button
              className="rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setIframeKey((k) => k + 1)}
              title={msg.workbench_files_refresh()}
            >
              <RefreshCw className="h-3 w-3" />
            </button>
            <input
              type="text"
              className="flex-1 min-w-0 bg-background/80 border border-border/40 rounded px-2 py-0.5 text-[11px] font-mono text-foreground focus:outline-none focus:border-primary/60"
              value={showUrlBar ? urlOverride : effectiveUrl}
              onFocus={() => {
                setShowUrlBar(true);
                setUrlOverride(effectiveUrl);
              }}
              onBlur={() => setShowUrlBar(false)}
              onChange={(e) => setUrlOverride(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setIframeKey((k) => k + 1);
                  (e.target as HTMLInputElement).blur();
                }
              }}
            />
            <a
              href={effectiveUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded p-1 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              title={msg.workbench_preview_open_external()}
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <iframe
            ref={iframeRef}
            key={iframeKey}
            src={effectiveUrl}
            className="flex-1 w-full border-0 bg-white"
            title="Live Preview"
            sandbox="allow-scripts allow-forms allow-modals allow-popups"
          />
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          {activeServerStarting && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
          <p className="text-xs text-muted-foreground">
            {activeServerStarting
              ? msg.workbench_preview_starting()
              : msg.workbench_preview_select_server()}
          </p>
        </div>
      )}

      <Sheet
        open={consoleFor !== null}
        onOpenChange={(open) => {
          if (!open) setConsoleFor(null);
        }}
      >
        <SheetContent side="bottom" className="h-[50vh] p-0 gap-0">
          <div className="flex shrink-0 items-center justify-between border-b border-border/60 px-4 py-2">
            <span className="text-xs font-medium text-foreground">
              {consoleFor
                ? msg.workbench_preview_console_title({ name: consoleFor })
                : msg.workbench_preview_console()}
            </span>
            <button
              onClick={() => consoleFor && fetchConsoleLogs(consoleFor)}
              className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              title={msg.workbench_preview_console_refresh()}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${consoleLoading ? "animate-spin" : ""}`}
              />
            </button>
          </div>
          <div
            ref={consoleLogRef}
            className="flex-1 overflow-y-auto bg-background px-4 py-2 font-mono text-[11px] leading-relaxed text-foreground/90"
          >
            {consoleLines.length === 0 ? (
              <p className="text-muted-foreground">
                {msg.workbench_preview_console_empty()}
              </p>
            ) : (
              consoleLines.map((line, i) => (
                <div key={i} className="whitespace-pre-wrap break-all">
                  {line}
                </div>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
