"use client";

/**
 * Painel de detalhe de um card do Kanban — comentários + timeline de
 * transições de status. Abre num `Sheet` lateral a partir do botão "Ver
 * detalhes" do card (ver `kanban-board.tsx`).
 *
 * Fetch sob demanda ao abrir, mesmo padrão que `TaskCard` já usa pro
 * histórico de execuções (`runsOpen`/`runs`) — sem carregar nada enquanto o
 * painel está fechado.
 */

import { useEffect, useState } from "react";

import { m } from "@/lib/paraglide/messages";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";

interface TaskComment {
  id: string;
  user_id: string;
  body: string;
  created_at: string;
}

interface TaskEvent {
  id: string;
  from_status: string | null;
  to_status: string;
  block_kind: string | null;
  block_reason: string | null;
  created_at: string;
}

export function TaskDetailPanel({
  threadId,
  taskId,
  taskName,
  open,
  onOpenChange,
}: {
  threadId: string;
  taskId: string;
  taskName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const base = `/sessions/${threadId}/background/tasks/${taskId}`;
  const [comments, setComments] = useState<TaskComment[] | null>(null);
  const [events, setEvents] = useState<TaskEvent[] | null>(null);
  const [novoComentario, setNovoComentario] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const carregar = () => {
    void fetch(`${base}/comments`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setComments(Array.isArray(data) ? data : []))
      .catch(() => setComments([]));
    void fetch(`${base}/events`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setEvents(Array.isArray(data) ? data : []))
      .catch(() => setEvents([]));
  };

  useEffect(() => {
    if (open) carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId]);

  const enviarComentario = () => {
    const corpo = novoComentario.trim();
    if (!corpo) return;
    setEnviando(true);
    setErro(null);
    void fetch(`${base}/comments`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: corpo }),
    })
      .then((r) => {
        if (!r.ok) throw new Error("falha ao comentar");
        setNovoComentario("");
        carregar();
      })
      .catch(() => setErro(m.kanban_comment_error()))
      .finally(() => setEnviando(false));
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full max-w-md p-6 overflow-y-auto">
        <h2 className="text-sm font-semibold mb-4">{taskName}</h2>

        <section className="mb-6">
          <h3 className="text-xs font-medium uppercase text-muted-foreground mb-2">
            {m.kanban_comments_title()}
          </h3>
          <ScrollArea className="max-h-56 mb-2">
            <ul className="space-y-2 pr-2">
              {comments === null ? null : comments.length === 0 ? (
                <li className="text-xs text-muted-foreground">
                  {m.kanban_comment_empty()}
                </li>
              ) : (
                comments.map((c) => (
                  <li key={c.id} className="text-xs">
                    <p className="text-muted-foreground">
                      {c.user_id} · {new Date(c.created_at).toLocaleString()}
                    </p>
                    <p>{c.body}</p>
                  </li>
                ))
              )}
            </ul>
          </ScrollArea>
          <Textarea
            value={novoComentario}
            onChange={(e) => setNovoComentario(e.target.value)}
            placeholder={m.kanban_comment_placeholder()}
            aria-label={m.kanban_comment_placeholder()}
            className="text-xs min-h-[60px]"
          />
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={enviarComentario}
              disabled={enviando || !novoComentario.trim()}
              className="text-xs px-2 py-1 rounded bg-primary text-primary-foreground disabled:opacity-50"
            >
              {m.kanban_comment_submit()}
            </button>
            {erro && (
              <span className="text-[10px] text-destructive">{erro}</span>
            )}
          </div>
        </section>

        <section>
          <h3 className="text-xs font-medium uppercase text-muted-foreground mb-2">
            {m.kanban_events_title()}
          </h3>
          <ScrollArea className="max-h-56">
            <ul className="space-y-1.5 pr-2 text-xs">
              {events === null ? null : events.length === 0 ? (
                <li className="text-muted-foreground">
                  {m.kanban_events_empty()}
                </li>
              ) : (
                events.map((e) => (
                  <li key={e.id} className="text-muted-foreground">
                    <span>
                      {e.from_status ?? "—"} → {e.to_status}
                    </span>{" "}
                    · {new Date(e.created_at).toLocaleString()}
                    {e.block_reason && (
                      <p className="text-[10px]">{e.block_reason}</p>
                    )}
                  </li>
                ))
              )}
            </ul>
          </ScrollArea>
        </section>
      </SheetContent>
    </Sheet>
  );
}
