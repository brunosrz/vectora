"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { m } from "@/lib/paraglide/messages";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface HbSession {
  id: string;
  instruction: string;
  status: string;
  run_count: number;
  trigger_count: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchSessions(): Promise<HbSession[]> {
  const res = await fetch("/heartbreak/sessions");
  if (!res.ok) return [];
  return res.json();
}

async function stopSession(id: string): Promise<void> {
  await fetch(`/heartbreak/sessions/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function HeartbreakIndicator() {
  const [sessions, setSessions] = useState<HbSession[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSessions(await fetchSessions());
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10000);
    return () => clearInterval(id);
  }, [load]);

  const handleStop = async (id: string) => {
    await stopSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  if (sessions.length === 0) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className="relative flex items-center gap-1.5 text-xs text-amber-500 hover:text-amber-400 transition-colors"
          aria-label={m.heartbreak_indicator_label()}
          data-testid="heartbreak-indicator"
        >
          <span
            className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"
            data-testid="heartbreak-dot"
          />
          <span className="hidden sm:inline">
            {sessions.length}{" "}
            {sessions.length === 1
              ? m.heartbreak_sessions_label()
              : m.heartbreak_sessions_label_plural()}
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium">
            {m.heartbreak_indicator_label()}
          </span>
          {loading && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
        </div>
        {sessions.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            {m.heartbreak_empty()}
          </p>
        ) : (
          <ul className="space-y-2">
            {sessions.map((s) => (
              <li
                key={s.id}
                className="border border-border/60 rounded-md p-2 text-xs"
                data-testid="heartbreak-session-item"
              >
                <div className="flex items-start justify-between gap-1">
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-foreground/80">
                      {s.instruction}
                    </p>
                    <p className="text-muted-foreground mt-0.5">
                      {s.run_count} {m.heartbreak_runs()}
                    </p>
                  </div>
                  <button
                    onClick={() => void handleStop(s.id)}
                    className="p-0.5 text-muted-foreground hover:text-destructive shrink-0"
                    title={m.heartbreak_stop()}
                    data-testid="heartbreak-stop-btn"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
