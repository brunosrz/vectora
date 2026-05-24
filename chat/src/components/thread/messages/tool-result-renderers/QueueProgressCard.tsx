"use client";

/**
 * QueueProgressCard — renderiza status de fila de embedding.
 *
 * Usado para `render_hint: "queue_progress"` (ingest_docs)
 * e `render_hint: "queue_badge"` (embedding).
 */

import { type QueueProgress } from "@/types/agent";

type QueueProgressProps = QueueProgress;

const STATUS_COLORS: Record<string, string> = {
  success: "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 border-green-200 dark:border-green-800/50",
  processing: "bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400 border-blue-200 dark:border-blue-800/50",
  pending: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800/50",
  failed: "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400 border-red-200 dark:border-red-800/50",
  queued: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-700",
};

export function QueueProgressCard({
  total,
  processed,
  status = "queued",
  queue_ids,
  queue_id,
  message,
}: QueueProgressProps) {
  const pct =
    total && total > 0 ? Math.round(((processed ?? 0) / total) * 100) : null;
  const colorClass = STATUS_COLORS[status] ?? STATUS_COLORS.queued;

  // Badge compacto para embedding (queue_badge)
  if (queue_id && !total) {
    return (
      <div
        className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${colorClass}`}
      >
        <span className="font-medium">{status}</span>
        <code className="opacity-70">{queue_id.slice(0, 8)}…</code>
        {message && <span className="opacity-70">— {message}</span>}
      </div>
    );
  }

  return (
    <div className={`rounded-md border p-3 text-sm ${colorClass}`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="font-medium capitalize">{status}</span>
        {pct !== null && (
          <span className="text-xs tabular-nums">
            {processed ?? 0}/{total} ({pct}%)
          </span>
        )}
      </div>

      {pct !== null && (
        <div className="w-full h-1.5 bg-white/50 rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-current rounded-full transition-all duration-300"
            style={{ width: `${pct}%`, opacity: 0.6 }}
          />
        </div>
      )}

      {message && <p className="text-xs opacity-80">{message}</p>}

      {queue_ids && queue_ids.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {queue_ids.slice(0, 5).map((id) => (
            <code
              key={id}
              className="text-xs opacity-60 bg-white/40 px-1 rounded"
            >
              {id.slice(0, 8)}
            </code>
          ))}
          {queue_ids.length > 5 && (
            <span className="text-xs opacity-60">+{queue_ids.length - 5}</span>
          )}
        </div>
      )}
    </div>
  );
}
