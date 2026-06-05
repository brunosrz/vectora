"use client";

/**
 * XtermView (Bloco T, T3)
 *
 * Wrapper client-only do xterm.js. Conecta direto ao WebSocket do backend
 * (uvicorn) — o proxy Hono/Next App Router não faz upgrade de WS. O token de
 * autenticação é obtido via /auth/ws-token (cookies httpOnly não trafegam
 * em WS cross-origin) e passa na query string.
 */

import { useEffect, useRef } from "react";

import { VECTORA_API_URL } from "@/lib/constants/api";

interface XtermViewProps {
  terminalId: string;
  threadId: string;
  workspaceId: string;
  onClosed?: () => void;
}

export function XtermView({
  terminalId,
  threadId,
  workspaceId,
  onClosed,
}: XtermViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<any | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitRef = useRef<any | null>(null);
  const resizeObsRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;
    const host = containerRef.current;

    (async () => {
      // CSS + libs carregados só no cliente
      await import("@xterm/xterm/css/xterm.css");
      const [{ Terminal }, { FitAddon }, { WebLinksAddon }] = await Promise.all(
        [
          import("@xterm/xterm"),
          import("@xterm/addon-fit"),
          import("@xterm/addon-web-links"),
        ],
      );
      if (cancelled) return;

      const term = new Terminal({
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        fontSize: 13,
        cursorBlink: true,
        theme: {
          background: "#0a0a0a",
          foreground: "#e4e4e7",
          cursor: "#7FC8FF",
          selectionBackground: "#7FC8FF44",
        },
        scrollback: 5000,
        convertEol: true,
      });
      const fit = new FitAddon();
      term.loadAddon(fit);
      term.loadAddon(new WebLinksAddon());
      term.open(host);
      try {
        fit.fit();
      } catch {
        // ignora se o container não tiver dimensões ainda
      }
      termRef.current = term;
      fitRef.current = fit;

      // Token para o WS
      let token = "";
      try {
        const r = await fetch("/auth/ws-token");
        if (r.ok) {
          const data = await r.json();
          token = String(data?.token ?? "");
        }
      } catch {
        // sem token: o backend recusa
      }

      const wsBase = VECTORA_API_URL.replace(/^http/i, "ws");
      const url = `${wsBase}/vectora.terminal.v1/ws?terminal_id=${encodeURIComponent(terminalId)}&thread_id=${encodeURIComponent(threadId)}&workspace_id=${encodeURIComponent(workspaceId)}&token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      const sendResize = () => {
        try {
          fit.fit();
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                type: "resize",
                cols: term.cols,
                rows: term.rows,
              }),
            );
          }
        } catch {
          // ignora
        }
      };

      ws.addEventListener("open", () => {
        sendResize();
      });

      ws.addEventListener("message", (ev: MessageEvent) => {
        if (typeof ev.data === "string") {
          try {
            const j = JSON.parse(ev.data);
            if (j.type === "error") {
              term.write(`\r\n\x1b[31m${j.message}\x1b[0m\r\n`);
            } else if (j.type === "closed") {
              term.write("\r\n\x1b[33m[encerrado]\x1b[0m\r\n");
              onClosed?.();
            }
          } catch {
            // mensagens de texto não-JSON também viram saída crua
            term.write(ev.data);
          }
        } else {
          term.write(new Uint8Array(ev.data));
        }
      });

      ws.addEventListener("error", () => {
        term.write("\r\n\x1b[31m[erro de conexão]\x1b[0m\r\n");
      });

      ws.addEventListener("close", () => {
        onClosed?.();
      });

      // stdin do user → WS
      term.onData((data: string) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(new TextEncoder().encode(data));
        }
      });

      // Resize observer mantém o terminal alinhado com o container
      const obs = new ResizeObserver(() => sendResize());
      obs.observe(host);
      resizeObsRef.current = obs;
    })();

    return () => {
      cancelled = true;
      try {
        resizeObsRef.current?.disconnect();
      } catch {
        // ignora
      }
      try {
        wsRef.current?.close();
      } catch {
        // ignora
      }
      try {
        termRef.current?.dispose();
      } catch {
        // ignora
      }
      wsRef.current = null;
      termRef.current = null;
      fitRef.current = null;
      resizeObsRef.current = null;
    };
  }, [terminalId, threadId, workspaceId, onClosed]);

  return <div ref={containerRef} className="h-full w-full bg-[#0a0a0a]" />;
}
