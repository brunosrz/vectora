"use client";

/**
 * use-webhook-events — conecta ao SSE GET /webhook/events e despacha eventos
 * recebidos (GitHub CI, PRs, Slack, etc.) para os stores relevantes.
 *
 * - Reconecta automaticamente com backoff exponencial (1s → 30s)
 * - Para ao desmontar
 * - Repassa eventos de CI/PR para o workbench-store via toast (quando disponível)
 */

import { useEffect, useRef } from "react";

interface WebhookEvent {
  type: string;
  provider: string;
  event_type: string;
  data: Record<string, unknown>;
}

const MIN_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;

type WebhookEventHandler = (event: WebhookEvent) => void;

const _handlers: Set<WebhookEventHandler> = new Set();

export function onWebhookEvent(handler: WebhookEventHandler): () => void {
  _handlers.add(handler);
  return () => _handlers.delete(handler);
}

let _globalEs: EventSource | null = null;
let _globalReconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let _globalDelay = MIN_RECONNECT_MS;
let _refCount = 0;

function startGlobalSSE(): void {
  if (_globalEs) return;

  function connect() {
    _globalEs = new EventSource("/webhook/events");

    _globalEs.onmessage = (ev: MessageEvent) => {
      try {
        const event = JSON.parse(ev.data as string) as WebhookEvent;
        if (event.type === "connected") return;
        _globalDelay = MIN_RECONNECT_MS;
        for (const handler of _handlers) {
          handler(event);
        }
      } catch {
        // payload malformado — ignora
      }
    };

    _globalEs.onerror = () => {
      _globalEs?.close();
      _globalEs = null;
      _globalReconnectTimeout = setTimeout(() => {
        _globalDelay = Math.min(_globalDelay * 2, MAX_RECONNECT_MS);
        connect();
      }, _globalDelay);
    };
  }

  connect();
}

function stopGlobalSSE(): void {
  if (_globalReconnectTimeout) {
    clearTimeout(_globalReconnectTimeout);
    _globalReconnectTimeout = null;
  }
  _globalEs?.close();
  _globalEs = null;
  _globalDelay = MIN_RECONNECT_MS;
}

export function useWebhookEvents(onEvent?: WebhookEventHandler): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    _refCount++;
    startGlobalSSE();

    const wrapped: WebhookEventHandler = (event) => handlerRef.current?.(event);
    if (onEvent) _handlers.add(wrapped);

    return () => {
      if (onEvent) _handlers.delete(wrapped);
      _refCount--;
      if (_refCount <= 0) {
        _refCount = 0;
        stopGlobalSSE();
      }
    };
  }, []);
}
