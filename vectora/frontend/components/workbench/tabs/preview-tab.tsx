"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ExternalLink,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Square,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

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

export function PreviewTab({ threadId: _threadId }: PreviewTabProps) {
  const t = useT();
  const workspace = useWorkspacesStore((s) => s.getActive());
  const wsId = workspace?.id ?? "";

  const [configs, setConfigs] = useState<LaunchConfig[]>([]);
  const [statuses, setStatuses] = useState<ServerStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetecting, setIsDetecting] = useState(false);
  const [activeServer, setActiveServer] = useState<ServerStatus | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [urlOverride, setUrlOverride] = useState<string>("");
  const [showUrlBar, setShowUrlBar] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  const fetchStatus = useCallback(async () => {
    if (!wsId) return;
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
      }
    } catch {
      // silently ignore
    }
  }, [wsId, activeServer]);

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

  const handleDetect = async () => {
    if (!wsId) return;
    setIsDetecting(true);
    try {
      const res = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/preview/detect`,
      );
      if (!res.ok) return;
      const data = (await res.json()) as { configurations: LaunchConfig[] };
      if (data.configurations.length === 0) return;

      const saveRes = await fetch(
        `/workspaces/${encodeURIComponent(wsId)}/preview/launch`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            version: "0.0.1",
            configurations: data.configurations,
          }),
        },
      );
      if (saveRes.ok) {
        setConfigs(data.configurations);
        fetchStatus();
      }
    } finally {
      setIsDetecting(false);
    }
  };

  const handleStart = async (cfg: LaunchConfig) => {
    if (!wsId) return;
    setActionLoading(cfg.name);
    try {
      await fetch(`/workspaces/${encodeURIComponent(wsId)}/preview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cfg.name }),
      });
      await new Promise((r) => setTimeout(r, 1500));
      await fetchStatus();
      const status = statuses.find((s) => s.name === cfg.name);
      if (status) setActiveServer({ ...status, running: true });
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

  const activeUrl = activeServer
    ? `http://localhost:${activeServer.port}`
    : null;

  const effectiveUrl = urlOverride || activeUrl || "";

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (configs.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center pb-[28%] gap-3 p-4 text-center">
        <Zap className="h-8 w-8 text-muted-foreground/40 shrink-0" />
        <div className="min-w-0 max-w-[200px]">
          <p className="text-sm font-medium text-foreground leading-snug">
            {t("workbench.preview.empty_title")}
          </p>
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
            {t("workbench.preview.empty_description")}
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={handleDetect}
          disabled={isDetecting}
          className="gap-1.5 max-w-full whitespace-normal h-auto py-1.5 px-3"
        >
          {isDetecting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
          ) : (
            <Search className="h-3.5 w-3.5 shrink-0" />
          )}
          <span className="text-xs">{t("workbench.preview.detect")}</span>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Painel de controle dos servidores */}
      <div className="shrink-0 border-b border-border/60 bg-card/40 px-3 py-2 space-y-1.5">
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
                {isRunning && (
                  <Button
                    size="icon"
                    variant={isActive ? "secondary" : "ghost"}
                    className="h-6 w-6"
                    title={t("workbench.preview.open_preview")}
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
                      ? t("workbench.preview.stop")
                      : t("workbench.preview.start")
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
              title={t("workbench.files.refresh")}
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
              title={t("workbench.preview.open_external")}
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
        <div className="flex flex-1 items-center justify-center">
          <p className="text-xs text-muted-foreground">
            {t("workbench.preview.select_server")}
          </p>
        </div>
      )}
    </div>
  );
}
